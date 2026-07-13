"""模糊时间解析器 — 自然语言时间表达 → 标准日期+时段"""

from datetime import date, datetime, timedelta
import re

# 时段映射：中文时段名 → (开始时间, 结束时间)
PERIOD_MAP = {
    "凌晨": ("00:00", "06:00"),
    "早上": ("06:00", "08:00"),
    "上午": ("08:00", "12:00"),
    "中午": ("12:00", "14:00"),
    "下午": ("14:00", "18:00"),
    "傍晚": ("18:00", "21:00"),
    "晚上": ("19:00", "22:00"),
    "夜间": ("22:00", "23:59"),
}

# 全天默认时段
DEFAULT_PERIOD = ("08:00", "18:00")

# 星期映射
WEEKDAY_MAP = {
    "周一": 0, "星期一": 0, "礼拜一": 0,
    "周二": 1, "星期二": 1, "礼拜二": 1,
    "周三": 2, "星期三": 2, "礼拜三": 2,
    "周四": 3, "星期四": 3, "礼拜四": 3,
    "周五": 4, "星期五": 4, "礼拜五": 4,
    "周六": 5, "星期六": 5, "礼拜六": 5,
    "周日": 6, "星期天": 6, "星期日": 6, "礼拜天": 6, "礼拜日": 6,
}

# 日期偏移关键词
DATE_OFFSET_MAP = {
    "今天": 0, "今日": 0,
    "明天": 1, "明日": 1,
    "后天": 2, "后日": 2,
    "昨天": -1, "昨日": -1,
    "前天": -2, "前日": -2,
}


def _extract_date_hint(text: str, reference_date: date) -> date:
    """从文本中提取日期偏移或具体日期，返回目标日期"""
    # 检查 "下周X"
    next_week_match = re.search(r"下周(一|二|三|四|五|六|日|天)", text)
    if next_week_match:
        weekday_key = "周" + next_week_match.group(1)
        target_weekday = WEEKDAY_MAP.get(weekday_key, 0)
        days_ahead = (target_weekday - reference_date.weekday()) % 7
        if days_ahead == 0:
            days_ahead = 7  # 本周同一天 → 下周
        return reference_date + timedelta(days=days_ahead)

    # 检查 "上周末/本周X"
    this_week_match = re.search(r"本周(一|二|三|四|五|六|日|天)", text)
    if this_week_match:
        weekday_key = "周" + this_week_match.group(1)
        target_weekday = WEEKDAY_MAP.get(weekday_key, 0)
        days_diff = target_weekday - reference_date.weekday()
        if days_diff < 0:
            days_diff += 7  # 已经过了，取下周
        return reference_date + timedelta(days=days_diff)

    # 检查日期偏移关键词：今天/明天/后天/昨天/前天
    for keyword, offset in DATE_OFFSET_MAP.items():
        if keyword in text:
            return reference_date + timedelta(days=offset)

    # 没有日期关键词，默认今天
    return reference_date


def _extract_period(text: str) -> tuple:
    """从文本中提取时段，返回 (start_time, end_time)"""
    # 按长度降序匹配，避免"上午"在"上午"匹配前被"上"误匹配
    sorted_periods = sorted(PERIOD_MAP.keys(), key=len, reverse=True)
    for period_name in sorted_periods:
        if period_name in text:
            return PERIOD_MAP[period_name]

    # "现在" → 基于当前时间的合理时段
    if "现在" in text:
        now = datetime.now()
        hour = now.hour
        for period_name, (start, end) in PERIOD_MAP.items():
            start_hour = int(start.split(":")[0])
            end_hour = int(end.split(":")[0])
            if start_hour <= hour < end_hour:
                return (start, end)
        return ("14:00", "18:00")  # 默认下午

    # 无时段关键词 → 默认全天
    return DEFAULT_PERIOD


def parse_fuzzy_datetime(text: str, reference_date: date = None) -> dict:
    """解析模糊时间表达，返回标准日期+时段

    Args:
        text: 用户输入的自然语言文本
        reference_date: 参考日期，默认为今天

    Returns:
        {"date": "YYYY-MM-DD", "start_time": "HH:MM", "end_time": "HH:MM"}
        或 {"error": "错误描述"}
    """
    if not text or not text.strip():
        return {"error": "输入为空，请描述您需要的时间"}

    text = text.strip()

    if reference_date is None:
        reference_date = date.today()

    # 尝试解析具体日期格式 YYYY-MM-DD 或 YYYY/MM/DD
    date_match = re.search(r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})", text)
    if date_match:
        try:
            year, month, day = int(date_match.group(1)), int(date_match.group(2)), int(date_match.group(3))
            target_date = date(year, month, day)
        except ValueError:
            return {"error": f"日期格式不正确: {date_match.group(0)}"}
    else:
        target_date = _extract_date_hint(text, reference_date)

    # 检查是否过去了（对于没有明确日期关键词的模糊表达，如"下午"）
    start_time, end_time = _extract_period(text)

    # 如果目标日期早于参考日期，报错
    if target_date < reference_date:
        return {"error": f"不能预约过去的日期 ({target_date.isoformat()})，请重新输入"}

    # 检查输入是否包含任何可识别的日期/时段关键词
    all_tokens = list(DATE_OFFSET_MAP.keys()) + list(PERIOD_MAP.keys()) + ["现在", "下周", "本周"]
    has_recognizable_token = any(token in text for token in all_tokens)
    if not date_match and not has_recognizable_token:
        return {"error": "无法解析的时间表达，请使用类似「今天下午」「明天上午」的格式"}

    return {
        "date": target_date.isoformat(),
        "start_time": start_time,
        "end_time": end_time,
    }
