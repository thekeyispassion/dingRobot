"""预约管理模块 — 单元测试"""
import pytest
import json
import os
from skills.db_manager import init_db, seed_data, get_connection
from skills.cancellation import my_reservations, cancel_reservation

TEST_DB = "db/test_cancellation.db"


@pytest.fixture(autouse=True)
def setup_db():
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
    init_db(TEST_DB)
    seed_data(TEST_DB)
    yield
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)


class TestMyReservations:
    def test_query_my_reservations(self):
        """查询种子数据中 user002 的预约"""
        result = my_reservations("user002", TEST_DB)
        data = json.loads(result) if isinstance(result, str) else result
        assert data["success"] is True
        assert len(data["reservations"]) >= 1
        # 验证预约属于 user002
        for r in data["reservations"]:
            assert r["user_id"] == "user002"

    def test_query_user_with_no_reservations(self):
        """无预约用户返回空列表"""
        result = my_reservations("user999", TEST_DB)
        data = json.loads(result) if isinstance(result, str) else result
        assert data["success"] is True
        assert len(data["reservations"]) == 0


class TestCancelReservation:
    def test_cancel_own_reservation(self):
        """取消自己的预约"""
        result = cancel_reservation("user002", 1, TEST_DB)
        data = json.loads(result) if isinstance(result, str) else result
        assert data["success"] is True
        assert "取消成功" in data["message"]

        # 验证数据库中 status 变为 cancelled
        conn = get_connection(TEST_DB)
        row = conn.execute("SELECT status FROM reservations WHERE id = 1").fetchone()
        conn.close()
        assert row["status"] == "cancelled"

    def test_cancel_others_reservation(self):
        """不能取消别人的预约"""
        # reservation id=1 属于 user002
        result = cancel_reservation("user001", 1, TEST_DB)
        data = json.loads(result) if isinstance(result, str) else result
        assert data["success"] is False
        assert "权限" in data["message"] or "无权" in data["message"]

        # 验证数据库中 status 未变
        conn = get_connection(TEST_DB)
        row = conn.execute("SELECT status FROM reservations WHERE id = 1").fetchone()
        conn.close()
        assert row["status"] == "active"

    def test_cancel_nonexistent_reservation(self):
        """取消不存在的预约"""
        result = cancel_reservation("user001", 99999, TEST_DB)
        data = json.loads(result) if isinstance(result, str) else result
        assert data["success"] is False

    def test_cancel_already_cancelled(self):
        """重复取消已取消的预约"""
        # 先取消一次
        cancel_reservation("user002", 1, TEST_DB)
        # 再取消一次
        result = cancel_reservation("user002", 1, TEST_DB)
        data = json.loads(result) if isinstance(result, str) else result
        assert data["success"] is False
        assert "已取消" in data["message"]
