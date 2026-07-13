"""预约模块 — 单元测试"""
import pytest
import json
import os
from skills.db_manager import init_db, seed_data, get_connection
from skills.booking import book_room, recommend_alternatives

TEST_DB = "db/test_booking.db"


@pytest.fixture(autouse=True)
def setup_db():
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
    init_db(TEST_DB)
    seed_data(TEST_DB)
    yield
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)


class TestBookRoom:
    def test_book_available_room(self):
        """正常预约空闲房间"""
        result = book_room("user001", "张三", "信电楼317", "2026-07-15", "09:00", "11:00", TEST_DB)
        data = json.loads(result) if isinstance(result, str) else result
        assert data["success"] is True
        assert "预约成功" in data["message"]
        assert data["reservation_id"] is not None

    def test_book_conflicting_room_with_recommendation(self):
        """预约已被占用的房间时段 → 返回冲突 + 推荐"""
        # 种子数据: user002 已占用 信电楼330 7月14日 14:00-16:00
        result = book_room("user001", "张三", "信电楼330", "2026-07-14", "14:00", "16:00", TEST_DB)
        data = json.loads(result) if isinstance(result, str) else result
        assert data["success"] is False
        assert any(word in data["message"] for word in ["已满", "占用", "冲突", "已被"])
        assert "recommendations" in data
        assert len(data["recommendations"]) > 0

    def test_book_nonexistent_room(self):
        """预约不存在的房间"""
        result = book_room("user001", "张三", "幽灵房间999", "2026-07-15", "09:00", "11:00", TEST_DB)
        data = json.loads(result) if isinstance(result, str) else result
        assert data["success"] is False

    def test_book_past_date(self):
        """预约过去的日期"""
        result = book_room("user001", "张三", "信电楼317", "2020-01-01", "09:00", "11:00", TEST_DB)
        data = json.loads(result) if isinstance(result, str) else result
        assert data["success"] is False
        assert "过去" in data.get("message", "")

    def test_book_reverse_time(self):
        """开始时间晚于结束时间"""
        result = book_room("user001", "张三", "信电楼317", "2026-07-15", "18:00", "09:00", TEST_DB)
        data = json.loads(result) if isinstance(result, str) else result
        assert data["success"] is False

    def test_book_exact_adjacent_no_conflict(self):
        """刚好不重叠的时段应预约成功"""
        # 种子数据: 330 14:00-16:00, 预约 16:00-18:00 应成功
        result = book_room("user001", "张三", "信电楼330", "2026-07-14", "16:00", "18:00", TEST_DB)
        data = json.loads(result) if isinstance(result, str) else result
        assert data["success"] is True


class TestRecommendAlternatives:
    def test_recommend_same_floor(self):
        """推荐同楼层容量相近的房间"""
        result = recommend_alternatives("信电楼330", "2026-07-14", "14:00", "16:00", TEST_DB)
        data = json.loads(result) if isinstance(result, str) else result
        assert data["success"] is True
        assert len(data["recommendations"]) > 0
        # 信电楼317（同层，20人）应排在前面
        names = [r["name"] for r in data["recommendations"]]
        assert "信电楼317" in names

    def test_recommend_when_all_full(self):
        """所有房间都满时返回空推荐"""
        # 预约所有房间
        conn = get_connection(TEST_DB)
        rooms = conn.execute("SELECT id, name FROM rooms WHERE status = 'available'").fetchall()
        for r in rooms:
            conn.execute(
                "INSERT INTO reservations (room_id, user_id, user_name, date, start_time, end_time, status, created_at) "
                "VALUES (?, 'test', 'test', '2026-07-16', '10:00', '12:00', 'active', '2026-07-13T00:00:00')",
                (r["id"],),
            )
        conn.commit()
        conn.close()

        result = recommend_alternatives("信电楼330", "2026-07-16", "10:00", "12:00", TEST_DB)
        data = json.loads(result) if isinstance(result, str) else result
        assert data["success"] is True
        assert len(data["recommendations"]) == 0
