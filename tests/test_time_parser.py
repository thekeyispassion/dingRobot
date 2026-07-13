"""模糊时间解析器 — 单元测试"""
import pytest
from datetime import date
from skills.time_parser import parse_fuzzy_datetime, PERIOD_MAP


class TestPeriodMap:
    def test_period_map_has_standard_periods(self):
        assert "上午" in PERIOD_MAP
        assert "下午" in PERIOD_MAP
        assert "晚上" in PERIOD_MAP
        assert PERIOD_MAP["上午"] == ("08:00", "12:00")
        assert PERIOD_MAP["下午"] == ("14:00", "18:00")

    def test_period_map_has_evening(self):
        assert "傍晚" in PERIOD_MAP
        assert PERIOD_MAP["傍晚"] == ("18:00", "21:00")


class TestBasicDateParsing:
    def test_today_afternoon(self):
        """今天下午 → 今天日期 + 下午时段"""
        result = parse_fuzzy_datetime("今天下午", reference_date=date(2026, 7, 14))
        assert result["date"] == "2026-07-14"
        assert result["start_time"] == "14:00"
        assert result["end_time"] == "18:00"

    def test_tomorrow_morning(self):
        """明天上午 → 明天日期 + 上午时段"""
        result = parse_fuzzy_datetime("明天上午", reference_date=date(2026, 7, 14))
        assert result["date"] == "2026-07-15"
        assert result["start_time"] == "08:00"
        assert result["end_time"] == "12:00"

    def test_day_after_tomorrow_evening(self):
        """后天晚上 → 后天日期 + 晚上时段"""
        result = parse_fuzzy_datetime("后天晚上", reference_date=date(2026, 7, 14))
        assert result["date"] == "2026-07-16"
        assert result["start_time"] == "19:00"
        assert result["end_time"] == "22:00"

    def test_now(self):
        """现在 → 当前时间"""
        result = parse_fuzzy_datetime("现在", reference_date=date(2026, 7, 14))
        assert result["date"] == "2026-07-14"
        # "现在" 应该有合理的时间段
        assert "start_time" in result
        assert "end_time" in result

    def test_only_period(self):
        """下午 → 今天日期 + 下午时段"""
        result = parse_fuzzy_datetime("下午", reference_date=date(2026, 7, 14))
        assert result["date"] == "2026-07-14"
        assert result["start_time"] == "14:00"
        assert result["end_time"] == "18:00"

    def test_only_date(self):
        """明天 → 明天日期 + 默认全天"""
        result = parse_fuzzy_datetime("明天", reference_date=date(2026, 7, 14))
        assert result["date"] == "2026-07-15"


class TestWeekdayParsing:
    def test_next_monday(self):
        """下周一 → 下周一的日期"""
        # 2026-07-14 是周二，下周一是 2026-07-20
        result = parse_fuzzy_datetime("下周一上午", reference_date=date(2026, 7, 14))
        assert result["date"] == "2026-07-20"
        assert result["start_time"] == "08:00"


class TestErrorHandling:
    def test_unparseable_input(self):
        """无法解析的输入返回 error"""
        result = parse_fuzzy_datetime("xyzabc123", reference_date=date(2026, 7, 14))
        assert "error" in result

    def test_empty_input(self):
        """空输入返回 error"""
        result = parse_fuzzy_datetime("", reference_date=date(2026, 7, 14))
        assert "error" in result


class TestComplexExpressions:
    def test_tomorrow_afternoon_with_room(self):
        """明天下午 330 → 正确解析时间"""
        result = parse_fuzzy_datetime("明天下午330", reference_date=date(2026, 7, 14))
        assert result["date"] == "2026-07-15"
        assert result["start_time"] == "14:00"
        assert result["end_time"] == "18:00"

    def test_this_afternoon(self):
        """今天下午 → 今天下午"""
        result = parse_fuzzy_datetime("今天下午", reference_date=date(2026, 7, 14))
        assert result["date"] == "2026-07-14"
        assert result["start_time"] == "14:00"
