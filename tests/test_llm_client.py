"""LLM 客户端 — 本地降级模式测试"""
import pytest
from interfaces.llm_client import _local_classify, _extract_room_name_from_text, _parse_llm_response


class TestLocalClassify:
    """本地关键词分类（不需要 LLM API）"""

    def test_book_intent_with_room(self):
        result = _local_classify("帮我约明天下午 330")
        assert result["intent"] == "book"
        assert result["params"]["room_name"] is not None

    def test_book_intent_with_full_room_name(self):
        result = _local_classify("预约下周一上午信电楼501")
        assert result["intent"] == "book"

    def test_query_available_intent(self):
        result = _local_classify("现在有哪些空房间？")
        assert result["intent"] == "query_available"

    def test_query_available_variant(self):
        result = _local_classify("明天下午有哪些会议室空着？")
        assert result["intent"] == "query_available"

    def test_query_overview_intent(self):
        result = _local_classify("明天下午各会议室的预约情况")
        assert result["intent"] == "query_overview"

    def test_query_my_intent(self):
        result = _local_classify("查看我的预约")
        assert result["intent"] == "query_my"

    def test_query_my_variant(self):
        result = _local_classify("我有哪些预约？")
        assert result["intent"] == "query_my"

    def test_cancel_intent_with_id(self):
        result = _local_classify("取消预约 1001")
        assert result["intent"] == "cancel"
        assert result["params"]["reservation_id"] == 1001

    def test_cancel_intent_with_id_prefix(self):
        result = _local_classify("取消 ID: 8852")
        assert result["intent"] == "cancel"
        assert result["params"]["reservation_id"] == 8852

    def test_unknown_intent(self):
        result = _local_classify("今天天气怎么样")
        assert result["intent"] == "unknown"


class TestExtractRoomName:
    def test_extract_full_name(self):
        # 正则提取房间号（支持 LIKE 模糊匹配）
        assert _extract_room_name_from_text("信电楼330") == "330"

    def test_extract_alphanumeric_room(self):
        assert _extract_room_name_from_text("理学院A201") == "A201"

    def test_extract_number_only(self):
        assert _extract_room_name_from_text("帮我约 317") == "317"

    def test_extract_no_room(self):
        assert _extract_room_name_from_text("帮我约个会议室") is None


class TestParseLLMResponse:
    def test_direct_json(self):
        result = _parse_llm_response('{"intent": "book", "params": {"room_name": "330"}}')
        assert result["intent"] == "book"
        assert result["params"]["room_name"] == "330"

    def test_markdown_code_block(self):
        result = _parse_llm_response('```json\n{"intent": "query_available", "params": {}}\n```')
        assert result["intent"] == "query_available"

    def test_json_in_text(self):
        result = _parse_llm_response('分析结果如下：{"intent": "cancel", "params": {"reservation_id": 1001}}')
        assert result["intent"] == "cancel"
        assert result["params"]["reservation_id"] == 1001

    def test_unparseable(self):
        result = _parse_llm_response("抱歉，我无法理解您的请求")
        assert result["intent"] == "unknown"
