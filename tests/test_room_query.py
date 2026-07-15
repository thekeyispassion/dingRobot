"""房间查询模块 — 单元测试"""
import pytest
import json
import os
from skills.db_manager import init_db, seed_data, DEFAULT_DB_PATH
from skills.room_query import query_available, query_overview, get_room_by_name

TEST_DB = "db/test_room_query.db"


@pytest.fixture(autouse=True)
def setup_db():
    """每个测试前重建数据库"""
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
    init_db(TEST_DB)
    seed_data(TEST_DB)
    yield
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)


class TestQueryAvailable:
    def test_query_all_available_at_empty_slot(self):
        """2026-07-15 14:00-16:00 无预约，所有可用房间应返回"""
        result = query_available("2026-07-15", "14:00", "16:00", TEST_DB)
        data = json.loads(result) if isinstance(result, str) else result
        assert data["success"] is True
        # 8 个房间全部可用
        assert len(data["rooms"]) == 8

    def test_query_available_with_conflict(self):
        """2026-12-15 14:00-16:00 信电楼330 已被占"""
        result = query_available("2026-12-15", "14:00", "16:00", TEST_DB)
        data = json.loads(result) if isinstance(result, str) else result
        assert data["success"] is True
        room_names = [r["name"] for r in data["rooms"]]
        assert "信电楼330" not in room_names
        # 其他 7 个可用
        assert len(data["rooms"]) == 7

    def test_query_available_with_partial_overlap(self):
        """2026-12-15 15:00-17:00 与 330 的 14:00-16:00 重叠"""
        result = query_available("2026-12-15", "15:00", "17:00", TEST_DB)
        data = json.loads(result) if isinstance(result, str) else result
        room_names = [r["name"] for r in data["rooms"]]
        assert "信电楼330" not in room_names

    def test_query_available_no_overlap(self):
        """2026-12-15 16:00-18:00 与 330 的 14:00-16:00 刚好不重叠"""
        result = query_available("2026-12-15", "16:00", "18:00", TEST_DB)
        data = json.loads(result) if isinstance(result, str) else result
        room_names = [r["name"] for r in data["rooms"]]
        assert "信电楼330" in room_names


class TestQueryOverview:
    def test_overview_shows_all_rooms_with_status(self):
        """预约总览应返回所有房间及其占用状态"""
        result = query_overview("2026-12-15", "14:00", "16:00", TEST_DB)
        data = json.loads(result) if isinstance(result, str) else result
        assert data["success"] is True
        assert len(data["rooms"]) == 8
        # 找到信电楼330，它应该是 occupied
        room330 = next(r for r in data["rooms"] if r["name"] == "信电楼330")
        assert room330["status"] == "occupied"
        # 信电楼317 应该是 available
        room317 = next(r for r in data["rooms"] if r["name"] == "信电楼317")
        assert room317["status"] == "available"


class TestGetRoomByName:
    def test_existing_room(self):
        result = get_room_by_name("信电楼330", TEST_DB)
        data = json.loads(result) if isinstance(result, str) else result
        assert data["success"] is True
        assert data["room"]["capacity"] == 30
        assert data["room"]["building"] == "信电楼"

    def test_nonexistent_room(self):
        result = get_room_by_name("不存在的房间999", TEST_DB)
        data = json.loads(result) if isinstance(result, str) else result
        assert data["success"] is False
        assert "error" in data
