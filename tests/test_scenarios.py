"""端到端集成测试 — 覆盖正常流程与边界情况（17 个测试用例）"""

import pytest
import json
import os
from skills.db_manager import init_db, seed_data, get_connection
from skills.room_query import query_available, query_overview, get_room_by_name
from skills.booking import book_room, recommend_alternatives
from skills.cancellation import my_reservations, cancel_reservation
from skills.time_parser import parse_fuzzy_datetime

TEST_DB = "db/test_scenarios.db"


@pytest.fixture(autouse=True)
def setup_db():
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
    init_db(TEST_DB)
    seed_data(TEST_DB)
    yield
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)


# ============================================================
# 基础预约 (3 个用例)
# ============================================================

class TestBasicBooking:
    """TC01-TC03: 基础预约"""

    def test_tc01_book_available_room_success(self):
        """TC01: 正常预约空闲房间 → 预约成功，返回预约ID"""
        result = json.loads(book_room("user001", "张三", "信电楼317", "2026-07-15", "09:00", "11:00", TEST_DB))
        assert result["success"] is True
        assert "预约成功" in result["message"]
        assert result["reservation_id"] is not None
        assert result["room"] == "信电楼317"

    def test_tc02_book_occupied_room_with_recommendation(self):
        """TC02: 预约已被占用的房间时段 → 返回冲突+推荐替代"""
        result = json.loads(book_room("user001", "张三", "信电楼330", "2026-12-15", "14:00", "16:00", TEST_DB))
        assert result["success"] is False
        assert "recommendations" in result
        assert len(result["recommendations"]) > 0

    def test_tc03_book_nonexistent_room(self):
        """TC03: 预约不存在的房间 → 友好提示"""
        result = json.loads(book_room("user001", "张三", "幽灵房间999", "2026-07-15", "09:00", "11:00", TEST_DB))
        assert result["success"] is False
        assert "message" in result


# ============================================================
# 空闲查询 (2 个用例)
# ============================================================

class TestAvailabilityQuery:
    """TC04-TC05: 空闲查询"""

    def test_tc04_query_empty_period_all_available(self):
        """TC04: 无预约的时段 → 所有房间空闲"""
        result = json.loads(query_available("2026-07-15", "09:00", "11:00", TEST_DB))
        assert result["success"] is True
        assert result["count"] == 8

    def test_tc05_query_occupied_period_excludes_conflicts(self):
        """TC05: 有冲突的时段 → 排除被占用的房间"""
        result = json.loads(query_available("2026-12-15", "14:00", "16:00", TEST_DB))
        assert result["success"] is True
        room_names = [r["name"] for r in result["rooms"]]
        assert "信电楼330" not in room_names  # 被占用
        assert "信电楼317" in room_names       # 空闲


# ============================================================
# 预约总览 (1 个用例)
# ============================================================

class TestOverview:
    """TC06: 预约总览"""

    def test_tc06_overview_shows_all_rooms_with_status(self):
        """TC06: 查询某时段所有房间状态 → 返回占用/空闲一览"""
        result = json.loads(query_overview("2026-12-15", "14:00", "16:00", TEST_DB))
        assert result["success"] is True
        assert len(result["rooms"]) == 8
        occupied = [r for r in result["rooms"] if r["status"] == "occupied"]
        available = [r for r in result["rooms"] if r["status"] == "available"]
        assert len(occupied) >= 1
        assert len(available) >= 1


# ============================================================
# 模糊时间解析 (3 个用例)
# ============================================================

class TestFuzzyTimeParsing:
    """TC07-TC09: 模糊时间解析"""

    def test_tc07_tomorrow_afternoon(self):
        """TC07: "明天下午" → 正确解析为明日+下午时段"""
        from datetime import date
        result = parse_fuzzy_datetime("明天下午", reference_date=date(2026, 7, 14))
        assert result["date"] == "2026-07-15"
        assert result["start_time"] == "14:00"
        assert result["end_time"] == "18:00"

    def test_tc08_evening(self):
        """TC08: "傍晚" → 正确解析为 18:00-21:00"""
        from datetime import date
        result = parse_fuzzy_datetime("傍晚", reference_date=date(2026, 7, 14))
        assert result["date"] == "2026-07-14"
        assert result["start_time"] == "18:00"
        assert result["end_time"] == "21:00"

    def test_tc09_day_after_tomorrow_morning(self):
        """TC09: "后天上午" → 正确解析为后天+上午时段"""
        from datetime import date
        result = parse_fuzzy_datetime("后天上午", reference_date=date(2026, 7, 14))
        assert result["date"] == "2026-07-16"
        assert result["start_time"] == "08:00"
        assert result["end_time"] == "12:00"


# ============================================================
# 冲突推荐 (2 个用例)
# ============================================================

class TestConflictRecommendation:
    """TC10-TC11: 冲突推荐"""

    def test_tc10_recommend_similar_room_when_occupied(self):
        """TC10: 目标房间占用 → 推荐容量相近的替代房间"""
        result = json.loads(recommend_alternatives("信电楼330", "2026-12-15", "14:00", "16:00", TEST_DB))
        assert result["success"] is True
        assert len(result["recommendations"]) > 0
        # 信电楼317（同层，20人）应在推荐中
        names = [r["name"] for r in result["recommendations"]]
        assert "信电楼317" in names

    def test_tc11_no_recommendation_when_all_full(self):
        """TC11: 所有房间都满 → 返回空推荐列表"""
        conn = get_connection(TEST_DB)
        rooms = conn.execute("SELECT id FROM rooms WHERE status = 'available'").fetchall()
        for r in rooms:
            conn.execute(
                "INSERT INTO reservations (room_id, user_id, user_name, date, start_time, end_time, status, created_at) "
                "VALUES (?, 'test', 'Tester', '2026-07-16', '10:00', '12:00', 'active', '2026-07-13T00:00:00')",
                (r["id"],),
            )
        conn.commit()
        conn.close()
        result = json.loads(recommend_alternatives("信电楼330", "2026-07-16", "10:00", "12:00", TEST_DB))
        assert result["success"] is True
        assert len(result["recommendations"]) == 0


# ============================================================
# 个人管理 (3 个用例)
# ============================================================

class TestPersonalManagement:
    """TC12-TC14: 个人预约管理"""

    def test_tc12_query_my_reservations(self):
        """TC12: 查询我的预约 → 返回本人预约列表"""
        result = json.loads(my_reservations("user002", TEST_DB))
        assert result["success"] is True
        assert result["count"] >= 1
        for r in result["reservations"]:
            assert r["id"] is not None

    def test_tc13_cancel_own_reservation(self):
        """TC13: 取消自己的预约 → 成功取消"""
        result = json.loads(cancel_reservation("user002", 1, TEST_DB))
        assert result["success"] is True
        assert "取消成功" in result["message"]

    def test_tc14_cancel_others_reservation_permission_denied(self):
        """TC14: 取消别人的预约 → 权限拒绝"""
        result = json.loads(cancel_reservation("user001", 1, TEST_DB))
        assert result["success"] is False
        assert "message" in result


# ============================================================
# 边界情况 (3 个用例)
# ============================================================

class TestBoundaryCases:
    """TC15-TC17: 边界情况"""

    def test_tc15_unparseable_input(self):
        """TC15: 无法理解的乱码输入 → 时间解析返回 error"""
        result = parse_fuzzy_datetime("xyzabc123###", reference_date=__import__('datetime').date(2026, 7, 14))
        assert "error" in result

    def test_tc16_past_date_booking(self):
        """TC16: 预约过去的日期 → 拒绝"""
        result = json.loads(book_room("user001", "张三", "信电楼317", "2020-01-01", "09:00", "11:00", TEST_DB))
        assert result["success"] is False

    def test_tc17_reverse_time_range(self):
        """TC17: 开始时间晚于结束时间 → 拒绝"""
        result = json.loads(book_room("user001", "张三", "信电楼317", "2026-07-15", "18:00", "09:00", TEST_DB))
        assert result["success"] is False


# ============================================================
# 额外边界测试
# ============================================================

class TestExtraBoundary:
    """TC18-TC19: 额外边界验证"""

    def test_tc18_exact_boundary_no_conflict(self):
        """TC18: 时间刚好相邻不重叠 → 预约成功"""
        result = json.loads(book_room("user001", "张三", "信电楼330", "2026-12-15", "16:00", "18:00", TEST_DB))
        assert result["success"] is True

    def test_tc19_empty_user_no_reservations(self):
        """TC19: 无预约记录的用户查询 → 返回空列表"""
        result = json.loads(my_reservations("user999", TEST_DB))
        assert result["success"] is True
        assert result["count"] == 0
