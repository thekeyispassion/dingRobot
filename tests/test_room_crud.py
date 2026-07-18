"""会议室管理 — 单元测试"""
import pytest
import json
import os
from meeting_room.db_manager import init_db, seed_data, get_connection
from room_manager.admin_check import is_admin, require_admin
from room_manager.room_crud import list_rooms, add_room, update_room, disable_room, enable_room

TEST_DB = "db/test_room_crud.db"


@pytest.fixture(autouse=True)
def setup_db():
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
    init_db(TEST_DB)
    seed_data(TEST_DB)
    # 插入一个管理员用于测试
    conn = get_connection(TEST_DB)
    conn.execute(
        "INSERT OR IGNORE INTO admins (user_id, user_name, role, created_at) "
        "VALUES ('admin001', '管理员', 'admin', '2026-07-13T00:00:00')"
    )
    conn.commit()
    conn.close()
    yield
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)


class TestAdminCheck:
    def test_is_admin_true(self):
        result = json.loads(is_admin("admin001", TEST_DB))
        assert result["is_admin"] is True
        assert result["user_name"] == "管理员"

    def test_is_admin_false(self):
        result = json.loads(is_admin("user999", TEST_DB))
        assert result["is_admin"] is False

    def test_require_admin_authorized(self):
        result = json.loads(require_admin("admin001", TEST_DB))
        assert result["authorized"] is True

    def test_require_admin_denied(self):
        result = json.loads(require_admin("user999", TEST_DB))
        assert result["authorized"] is False


class TestListRooms:
    def test_list_all_rooms(self):
        result = json.loads(list_rooms(db_path=TEST_DB))
        assert result["success"] is True
        assert result["count"] == 8

    def test_list_only_available(self):
        result = json.loads(list_rooms(include_maintenance=False, db_path=TEST_DB))
        assert all(r["status"] == "available" for r in result["rooms"])


class TestAddRoom:
    def test_add_room_as_admin(self):
        result = json.loads(add_room("admin001", "测试楼999", "测试楼", 9, 100, "投影仪", "测试", TEST_DB))
        assert result["success"] is True
        assert "添加成功" in result["message"]

        # 验证数据库
        conn = get_connection(TEST_DB)
        room = conn.execute("SELECT * FROM rooms WHERE name = '测试楼999'").fetchone()
        conn.close()
        assert room is not None
        assert room["capacity"] == 100

    def test_add_room_as_non_admin(self):
        result = json.loads(add_room("user999", "测试楼999", "测试楼", 9, 100, db_path=TEST_DB))
        assert result["success"] is False
        assert "权限" in result["message"]

    def test_add_duplicate_name(self):
        result = json.loads(add_room("admin001", "信电楼330", "信电楼", 3, 30, db_path=TEST_DB))
        assert result["success"] is False
        assert "已存在" in result["message"]


class TestUpdateRoom:
    def test_update_room_name(self):
        result = json.loads(update_room("admin001", 1, name="信电楼330-改", db_path=TEST_DB))
        assert result["success"] is True

        conn = get_connection(TEST_DB)
        room = conn.execute("SELECT name FROM rooms WHERE id = 1").fetchone()
        conn.close()
        assert room["name"] == "信电楼330-改"

    def test_update_room_capacity(self):
        result = json.loads(update_room("admin001", 1, capacity=50, db_path=TEST_DB))
        assert result["success"] is True

        conn = get_connection(TEST_DB)
        room = conn.execute("SELECT capacity FROM rooms WHERE id = 1").fetchone()
        conn.close()
        assert room["capacity"] == 50

    def test_update_as_non_admin(self):
        result = json.loads(update_room("user999", 1, name="尝试改名", db_path=TEST_DB))
        assert result["success"] is False

    def test_update_nonexistent_room(self):
        result = json.loads(update_room("admin001", 999, name="不存在", db_path=TEST_DB))
        assert result["success"] is False

    def test_update_no_valid_fields(self):
        result = json.loads(update_room("admin001", 1, status="maintenance", db_path=TEST_DB))
        assert result["success"] is False
        assert "有效的修改字段" in result["message"]


class TestDisableRoom:
    def test_disable_without_reservations(self):
        # 317 没有活跃预约
        result = json.loads(disable_room("admin001", 2, TEST_DB))
        assert result["success"] is True
        assert "已停用" in result["message"]

        conn = get_connection(TEST_DB)
        room = conn.execute("SELECT status FROM rooms WHERE id = 2").fetchone()
        conn.close()
        assert room["status"] == "maintenance"

    def test_disable_with_active_reservations(self):
        # 330 有活跃预约（种子数据）
        result = json.loads(disable_room("admin001", 1, TEST_DB))
        assert result["success"] is False
        assert "预约" in result["message"]

    def test_disable_already_disabled(self):
        disable_room("admin001", 2, TEST_DB)  # 先停用
        result = json.loads(disable_room("admin001", 2, TEST_DB))  # 再停用
        assert result["success"] is False
        assert "已经" in result["message"]

    def test_disable_as_non_admin(self):
        result = json.loads(disable_room("user999", 2, TEST_DB))
        assert result["success"] is False


class TestEnableRoom:
    def test_enable_room(self):
        # 先停用
        disable_room("admin001", 2, TEST_DB)
        # 再启用
        result = json.loads(enable_room("admin001", 2, TEST_DB))
        assert result["success"] is True
        assert "已启用" in result["message"]

        conn = get_connection(TEST_DB)
        room = conn.execute("SELECT status FROM rooms WHERE id = 2").fetchone()
        conn.close()
        assert room["status"] == "available"

    def test_enable_already_available(self):
        result = json.loads(enable_room("admin001", 2, TEST_DB))
        assert result["success"] is False
        assert "已经" in result["message"]

    def test_enable_as_non_admin(self):
        result = json.loads(enable_room("user999", 2, TEST_DB))
        assert result["success"] is False
