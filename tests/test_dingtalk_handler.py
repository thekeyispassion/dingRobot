"""钉钉消息处理器 — 单元测试"""
import pytest
from interfaces.dingtalk_handler import parse_incoming, format_response


class TestParseIncoming:
    """消息解析"""

    def test_openclaw_format(self):
        """OpenClaw 标准格式"""
        payload = {
            "sender": {
                "userId": "user001",
                "userName": "张三",
            },
            "message": {
                "text": "帮我约明天下午330",
            },
        }
        result = parse_incoming(payload)
        assert result["user_id"] == "user001"
        assert result["user_name"] == "张三"
        assert result["message"] == "帮我约明天下午330"

    def test_dingtalk_raw_format(self):
        """钉钉原始 webhook 格式"""
        payload = {
            "senderId": "dingtalk-user-abc",
            "senderNick": "李四",
            "text": {"content": "查询空闲会议室"},
        }
        result = parse_incoming(payload)
        assert result["user_id"] == "dingtalk-user-abc"
        assert result["user_name"] == "李四"
        assert result["message"] == "查询空闲会议室"

    def test_minimal_format(self):
        """最简格式——字段在顶层"""
        payload = {
            "user_id": "user999",
            "user_name": "测试用户",
            "message": "帮我取消预约",
        }
        result = parse_incoming(payload)
        assert result["user_id"] == "user999"
        assert result["user_name"] == "测试用户"

    def test_fallback_to_str(self):
        """无法识别的格式——回退到字符串"""
        payload = {"raw": "some unstructured data"}
        result = parse_incoming(payload)
        assert result["user_id"] == "unknown"
        assert "raw" in result["message"]


class TestFormatResponse:
    """回复格式化"""

    def test_booking_success(self):
        result = format_response({
            "success": True,
            "message": "预约成功！信电楼330 | 2026-07-14 14:00-16:00 | ID: 1001",
        })
        assert "预约成功" in result
        assert "1001" in result

    def test_booking_conflict_with_recommendation(self):
        result = format_response({
            "success": False,
            "message": "信电楼330已被占用，推荐：1. 信电楼317（容量20人）",
        })
        assert "已被占用" in result
        assert "信电楼317" in result

    def test_cancellation_success(self):
        result = format_response({
            "success": True,
            "message": "取消成功！信电楼330 | 2026-07-14 | ID: 1 已取消",
        })
        assert "取消成功" in result

    def test_permission_denied(self):
        result = format_response({
            "success": False,
            "message": "您只能取消自己的预约",
        })
        assert "只能取消自己" in result

    def test_room_list(self):
        result = format_response({
            "success": True,
            "rooms": [
                {"name": "信电楼330", "capacity": 30, "status": "available"},
                {"name": "信电楼317", "capacity": 20, "status": "available"},
            ],
        })
        assert "330" in result
        assert "317" in result

    def test_my_reservations(self):
        result = format_response({
            "success": True,
            "reservations": [
                {"id": 1, "room_name": "信电楼330", "date": "2026-07-14", "start_time": "14:00", "end_time": "16:00"},
            ],
        })
        assert "信电楼330" in result
        assert "14:00" in result

    def test_error_without_message(self):
        result = format_response({"success": False})
        assert "抱歉" in result
