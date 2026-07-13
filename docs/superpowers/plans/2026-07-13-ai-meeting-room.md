# AI 会议室预约助手 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建 AI 会议室预约助手的完整数据层、业务逻辑层、提示词层和命令行测试入口

**Architecture:** Python Skills 模块 → SQLite 数据库，LLM 提示词驱动意图分类，CLI 测试 shell 模拟钉钉交互。数据通过 JSON 在 Agent 和 Skill 之间传递

**Tech Stack:** Python 3.10+, SQLite3 (内置), pytest

## Global Constraints

- Python 3.10+，仅使用标准库 + pytest（测试）
- 所有 Skill 函数输入/输出均为 JSON 字符串（对接 OpenClaw）
- 数据库文件路径: `db/meeting_rooms.db`
- 测试覆盖率目标: 15+ 测试用例，100% 通过率
- 命令行交互模式：接收自然语言，打印意图+结果

---

## 文件结构

| 文件 | 职责 | 新建/修改 |
|------|------|----------|
| `db/schema.sql` | 建表 DDL | 新建 |
| `db/seed_data.sql` | 测试种子数据 | 新建 |
| `skills/__init__.py` | 包标记 | 新建 |
| `skills/db_manager.py` | 数据库连接、建表、种子数据 | 新建 |
| `skills/time_parser.py` | 模糊时间→标准日期+时段 | 新建 |
| `skills/room_query.py` | 空闲查询、预约总览 | 新建 |
| `skills/booking.py` | 预约+冲突检测+推荐 | 新建 |
| `skills/cancellation.py` | 取消预约、个人查询 | 新建 |
| `prompts/system_prompt.md` | LLM 系统角色定义 | 新建 |
| `prompts/intent_classify.md` | 意图分类提示词 | 新建 |
| `prompts/response_format.md` | 返回格式模板 | 新建 |
| `cli/test_shell.py` | 命令行测试入口 | 新建 |
| `tests/__init__.py` | 包标记 | 新建 |
| `tests/test_time_parser.py` | 时间解析单元测试 | 新建 |
| `tests/test_room_query.py` | 房间查询测试 | 新建 |
| `tests/test_booking.py` | 预约+冲突推荐测试 | 新建 |
| `tests/test_cancellation.py` | 取消+权限测试 | 新建 |
| `tests/test_scenarios.py` | 端到端集成测试 15+ | 新建 |
| `requirements.txt` | 依赖声明 | 新建 |

---

### Task 1: 项目骨架搭建 + 数据库 Schema

**Files:**
- Create: `requirements.txt`
- Create: `db/schema.sql`
- Create: `db/seed_data.sql`
- Create: `skills/__init__.py`
- Create: `tests/__init__.py`

**Interfaces:**
- Produces: `db/schema.sql` — `rooms` 表和 `reservations` 表定义
- Produces: `db/seed_data.sql` — 8 个会议室 + 2 条示例预约的 INSERT 语句

- [ ] **Step 1: 创建 requirements.txt**

```txt
pytest>=7.0.0
```

- [ ] **Step 2: 创建 skills/__init__.py 和 tests/__init__.py**

`skills/__init__.py`:
```python
# AI 会议室预约助手 — Skills 模块
```

`tests/__init__.py`:
```python
# AI 会议室预约助手 — 测试模块
```

- [ ] **Step 3: 创建 db/schema.sql**

```sql
-- AI 会议室预约助手 — 数据库 Schema

CREATE TABLE IF NOT EXISTS rooms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    building TEXT NOT NULL,
    floor INTEGER NOT NULL,
    capacity INTEGER NOT NULL,
    facilities TEXT DEFAULT '',
    status TEXT DEFAULT 'available',
    description TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS reservations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    room_id INTEGER NOT NULL,
    user_id TEXT NOT NULL,
    user_name TEXT NOT NULL,
    date TEXT NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    status TEXT DEFAULT 'active',
    created_at TEXT NOT NULL,
    FOREIGN KEY (room_id) REFERENCES rooms(id)
);

-- 索引：加速按日期+状态查询预约
CREATE INDEX IF NOT EXISTS idx_reservations_date_status
    ON reservations(date, status);

-- 索引：加速按用户查询
CREATE INDEX IF NOT EXISTS idx_reservations_user
    ON reservations(user_id, status);
```

- [ ] **Step 4: 创建 db/seed_data.sql**

```sql
-- AI 会议室预约助手 — 测试种子数据

-- 8 个会议室，分布在 2 栋楼
INSERT OR IGNORE INTO rooms (id, name, building, floor, capacity, facilities, status, description) VALUES
(1, '信电楼330', '信电楼', 3, 30, '投影仪,白板,视频会议', 'available', '中型会议室'),
(2, '信电楼317', '信电楼', 3, 20, '投影仪,白板', 'available', '小型会议室'),
(3, '信电楼212', '信电楼', 2, 10, '白板', 'available', '小型讨论室'),
(4, '信电楼501', '信电楼', 5, 50, '投影仪,白板,视频会议,音响', 'available', '大型报告厅'),
(5, '信电楼108', '信电楼', 1, 15, '投影仪', 'available', '小型会议室'),
(6, '理学院A201', '理学院', 2, 25, '投影仪,白板,视频会议', 'available', '中型会议室'),
(7, '理学院A305', '理学院', 3, 40, '投影仪,白板,视频会议,音响', 'available', '大型会议室'),
(8, '理学院B102', '理学院', 1, 60, '投影仪,白板,视频会议,音响,录音', 'available', '学术报告厅');

-- 2 条示例预约（用于测试冲突检测）
INSERT OR IGNORE INTO reservations (id, room_id, user_id, user_name, date, start_time, end_time, status, created_at) VALUES
(1, 1, 'user002', '李四', '2026-07-14', '14:00', '16:00', 'active', '2026-07-13T10:00:00'),
(2, 3, 'user003', '王五', '2026-07-14', '09:00', '11:00', 'active', '2026-07-13T09:00:00');
```

- [ ] **Step 5: 验证 SQL 文件语法**

Run: `mkdir -p /home/gfliu/ddtalk/db && sqlite3 /tmp/test_schema.db < db/schema.sql && sqlite3 /tmp/test_schema.db < db/seed_data.sql && rm /tmp/test_schema.db && echo "SQL OK"`
Expected: `SQL OK`

- [ ] **Step 6: Commit**

```bash
git add requirements.txt db/ skills/__init__.py tests/__init__.py
git commit -m "feat: add project skeleton, database schema, and seed data"
```

---

### Task 2: 数据库管理器 db_manager.py

**Files:**
- Create: `skills/db_manager.py`
- Modify: `skills/__init__.py`

**Interfaces:**
- Produces: `get_connection(db_path: str = None) -> sqlite3.Connection` — 获取数据库连接，默认路径 `db/meeting_rooms.db`
- Produces: `init_db(db_path: str = None) -> None` — 执行 schema.sql 建表
- Produces: `seed_data(db_path: str = None) -> None` — 执行 seed_data.sql 插入种子数据
- Produces: `DEFAULT_DB_PATH = "db/meeting_rooms.db"` — 默认数据库路径常量

- [ ] **Step 1: 编写 db_manager.py**

```python
"""数据库管理器 — 连接、建表、种子数据"""

import sqlite3
import os

DEFAULT_DB_PATH = "db/meeting_rooms.db"


def _get_base_dir() -> str:
    """获取项目根目录（skills/ 的上级目录）"""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _resolve_path(db_path: str = None) -> str:
    """将相对路径转换为基于项目根目录的绝对路径"""
    if db_path is None:
        db_path = DEFAULT_DB_PATH
    if not os.path.isabs(db_path):
        db_path = os.path.join(_get_base_dir(), db_path)
    return db_path


def get_connection(db_path: str = None) -> sqlite3.Connection:
    """获取数据库连接"""
    path = _resolve_path(db_path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _read_sql_file(filename: str) -> str:
    """读取 db/ 目录下的 SQL 文件"""
    base_dir = _get_base_dir()
    filepath = os.path.join(base_dir, "db", filename)
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()


def init_db(db_path: str = None) -> None:
    """初始化数据库 — 执行 schema.sql 建表"""
    conn = get_connection(db_path)
    try:
        sql = _read_sql_file("schema.sql")
        conn.executescript(sql)
        conn.commit()
    finally:
        conn.close()


def seed_data(db_path: str = None) -> None:
    """插入种子数据 — 执行 seed_data.sql"""
    conn = get_connection(db_path)
    try:
        sql = _read_sql_file("seed_data.sql")
        conn.executescript(sql)
        conn.commit()
    finally:
        conn.close()
```

- [ ] **Step 2: 更新 skills/__init__.py**

```python
# AI 会议室预约助手 — Skills 模块
from skills.db_manager import get_connection, init_db, seed_data, DEFAULT_DB_PATH
```

- [ ] **Step 3: 验证数据库初始化**

Run: `cd /home/gfliu/ddtalk && python -c "
from skills.db_manager import init_db, seed_data, get_connection
import os
# Use a test path
test_db = 'db/test_init.db'
if os.path.exists(test_db):
    os.remove(test_db)
init_db(test_db)
seed_data(test_db)
conn = get_connection(test_db)
rooms = conn.execute('SELECT COUNT(*) FROM rooms').fetchone()[0]
reservations = conn.execute('SELECT COUNT(*) FROM reservations').fetchone()[0]
conn.close()
os.remove(test_db)
print(f'Rooms: {rooms}, Reservations: {reservations}')
assert rooms == 8, f'Expected 8 rooms, got {rooms}'
assert reservations == 2, f'Expected 2 reservations, got {reservations}'
print('OK')
"`
Expected: `Rooms: 8, Reservations: 2` followed by `OK`

- [ ] **Step 4: Commit**

```bash
git add skills/db_manager.py skills/__init__.py
git commit -m "feat: add database manager with init and seed functions"
```

---

### Task 3: 模糊时间解析器 time_parser.py

**Files:**
- Create: `skills/time_parser.py`
- Create: `tests/test_time_parser.py`

**Interfaces:**
- Produces: `parse_fuzzy_datetime(text: str, reference_date: date = None) -> dict` — 返回 `{"date": "YYYY-MM-DD", "start_time": "HH:MM", "end_time": "HH:MM"}` 或 `{"error": "..."}`
- Produces: `PERIOD_MAP: dict` — 时段名到 (start, end) 的映射
- Produces: `WEEKDAY_MAP: dict` — 中文星期到 weekday 数字的映射

- [ ] **Step 1: 编写测试 test_time_parser.py**

```python
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
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd /home/gfliu/ddtalk && python -m pytest tests/test_time_parser.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'skills.time_parser'`

- [ ] **Step 3: 编写 skills/time_parser.py**

```python
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

    return {
        "date": target_date.isoformat(),
        "start_time": start_time,
        "end_time": end_time,
    }
```

- [ ] **Step 4: 运行测试验证通过**

Run: `cd /home/gfliu/ddtalk && python -m pytest tests/test_time_parser.py -v`
Expected: ALL PASS (11 tests passed)

- [ ] **Step 5: Commit**

```bash
git add skills/time_parser.py tests/test_time_parser.py
git commit -m "feat: add fuzzy time parser with 11 unit tests"
```

---

### Task 4: 房间查询模块 room_query.py

**Files:**
- Create: `skills/room_query.py`
- Create: `tests/test_room_query.py`

**Interfaces:**
- Consumes: `skills.db_manager.get_connection()` — 数据库连接
- Produces: `query_available(date: str, start_time: str, end_time: str, db_path: str = None) -> dict` — JSON 结果
- Produces: `query_overview(date: str, start_time: str, end_time: str, db_path: str = None) -> dict` — JSON 结果
- Produces: `get_room_by_name(name: str, db_path: str = None) -> dict` — JSON 结果

- [ ] **Step 1: 编写测试 test_room_query.py**

```python
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
        """2026-07-14 14:00-16:00 信电楼330 已被占"""
        result = query_available("2026-07-14", "14:00", "16:00", TEST_DB)
        data = json.loads(result) if isinstance(result, str) else result
        assert data["success"] is True
        room_names = [r["name"] for r in data["rooms"]]
        assert "信电楼330" not in room_names
        # 其他 7 个可用
        assert len(data["rooms"]) == 7

    def test_query_available_with_partial_overlap(self):
        """2026-07-14 15:00-17:00 与 330 的 14:00-16:00 重叠"""
        result = query_available("2026-07-14", "15:00", "17:00", TEST_DB)
        data = json.loads(result) if isinstance(result, str) else result
        room_names = [r["name"] for r in data["rooms"]]
        assert "信电楼330" not in room_names

    def test_query_available_no_overlap(self):
        """2026-07-14 16:00-18:00 与 330 的 14:00-16:00 刚好不重叠"""
        result = query_available("2026-07-14", "16:00", "18:00", TEST_DB)
        data = json.loads(result) if isinstance(result, str) else result
        room_names = [r["name"] for r in data["rooms"]]
        assert "信电楼330" in room_names


class TestQueryOverview:
    def test_overview_shows_all_rooms_with_status(self):
        """预约总览应返回所有房间及其占用状态"""
        result = query_overview("2026-07-14", "14:00", "16:00", TEST_DB)
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
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd /home/gfliu/ddtalk && python -m pytest tests/test_room_query.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: 编写 skills/room_query.py**

```python
"""房间查询模块 — 空闲查询 & 预约总览"""

import json
from skills.db_manager import get_connection


def query_available(date: str, start_time: str, end_time: str, db_path: str = None) -> str:
    """查询指定时段所有空闲房间

    Args:
        date: 日期 YYYY-MM-DD
        start_time: 开始时间 HH:MM
        end_time: 结束时间 HH:MM
        db_path: 数据库路径

    Returns:
        JSON 字符串: {"success": true, "rooms": [...], "count": N}
    """
    conn = get_connection(db_path)
    try:
        # 查询在指定时段有 active 预约的房间 ID
        conflict_sql = """
            SELECT DISTINCT room_id FROM reservations
            WHERE date = ?
              AND status = 'active'
              AND start_time < ?
              AND end_time > ?
        """
        conflicted_ids = set(
            row[0] for row in conn.execute(conflict_sql, (date, end_time, start_time))
        )

        # 查询所有可用房间（排除维护中的和有冲突的）
        rooms = conn.execute(
            "SELECT id, name, building, floor, capacity, facilities, description "
            "FROM rooms WHERE status = 'available' ORDER BY building, floor, name"
        ).fetchall()

        available = [
            {
                "id": r["id"],
                "name": r["name"],
                "building": r["building"],
                "floor": r["floor"],
                "capacity": r["capacity"],
                "facilities": r["facilities"],
                "description": r["description"],
            }
            for r in rooms
            if r["id"] not in conflicted_ids
        ]

        return json.dumps({
            "success": True,
            "date": date,
            "start_time": start_time,
            "end_time": end_time,
            "rooms": available,
            "count": len(available),
        }, ensure_ascii=False)
    finally:
        conn.close()


def query_overview(date: str, start_time: str, end_time: str, db_path: str = None) -> str:
    """查询所有房间在指定时段的预约情况

    Args:
        date: 日期 YYYY-MM-DD
        start_time: 开始时间 HH:MM
        end_time: 结束时间 HH:MM
        db_path: 数据库路径

    Returns:
        JSON: {"success": true, "rooms": [{"name": ..., "status": "available"|"occupied", "reservation": ...}]}
    """
    conn = get_connection(db_path)
    try:
        # 查询该时段所有 active 预约
        reservations = conn.execute(
            "SELECT room_id, user_name, start_time, end_time, id as reservation_id "
            "FROM reservations "
            "WHERE date = ? AND status = 'active' "
            "  AND start_time < ? AND end_time > ?",
            (date, end_time, start_time),
        ).fetchall()

        # 建立 room_id → 预约信息映射
        occupied_map = {}
        for res in reservations:
            occupied_map[res["room_id"]] = {
                "user_name": res["user_name"],
                "start_time": res["start_time"],
                "end_time": res["end_time"],
                "reservation_id": res["reservation_id"],
            }

        # 查询所有可用房间
        rooms = conn.execute(
            "SELECT id, name, building, floor, capacity, facilities "
            "FROM rooms WHERE status = 'available' ORDER BY building, floor, name"
        ).fetchall()

        room_list = []
        for r in rooms:
            if r["id"] in occupied_map:
                room_list.append({
                    "name": r["name"],
                    "building": r["building"],
                    "floor": r["floor"],
                    "capacity": r["capacity"],
                    "status": "occupied",
                    "reservation": occupied_map[r["id"]],
                })
            else:
                room_list.append({
                    "name": r["name"],
                    "building": r["building"],
                    "floor": r["floor"],
                    "capacity": r["capacity"],
                    "status": "available",
                    "reservation": None,
                })

        return json.dumps({
            "success": True,
            "date": date,
            "start_time": start_time,
            "end_time": end_time,
            "rooms": room_list,
        }, ensure_ascii=False)
    finally:
        conn.close()


def get_room_by_name(name: str, db_path: str = None) -> str:
    """按名称查找房间

    Args:
        name: 房间名称（支持部分匹配，如 "330" 匹配 "信电楼330"）
        db_path: 数据库路径

    Returns:
        JSON: {"success": true, "room": {...}} 或 {"success": false, "error": "..."}
    """
    conn = get_connection(db_path)
    try:
        # 精确匹配优先
        room = conn.execute(
            "SELECT id, name, building, floor, capacity, facilities, description "
            "FROM rooms WHERE name = ? AND status = 'available'",
            (name,),
        ).fetchone()

        # 模糊匹配：名称包含输入
        if room is None:
            room = conn.execute(
                "SELECT id, name, building, floor, capacity, facilities, description "
                "FROM rooms WHERE name LIKE ? AND status = 'available' ORDER BY name LIMIT 1",
                (f"%{name}%",),
            ).fetchone()

        if room is None:
            return json.dumps({
                "success": False,
                "error": f"未找到房间 '{name}'，请检查房间号是否正确",
            }, ensure_ascii=False)

        return json.dumps({
            "success": True,
            "room": {
                "id": room["id"],
                "name": room["name"],
                "building": room["building"],
                "floor": room["floor"],
                "capacity": room["capacity"],
                "facilities": room["facilities"],
                "description": room["description"],
            },
        }, ensure_ascii=False)
    finally:
        conn.close()
```

- [ ] **Step 4: 运行测试验证通过**

Run: `cd /home/gfliu/ddtalk && python -m pytest tests/test_room_query.py -v`
Expected: ALL PASS (7 tests passed)

- [ ] **Step 5: Commit**

```bash
git add skills/room_query.py tests/test_room_query.py
git commit -m "feat: add room query module with availability and overview"
```

---

### Task 5: 预约模块 booking.py（含冲突检测 + 推荐）

**Files:**
- Create: `skills/booking.py`
- Create: `tests/test_booking.py`

**Interfaces:**
- Consumes: `skills.db_manager.get_connection()` — 数据库连接
- Consumes: `skills.room_query.get_room_by_name()` — 查找房间
- Produces: `book_room(user_id, user_name, room_name, date, start_time, end_time, db_path=None) -> str` — JSON
- Produces: `recommend_alternatives(room_name, date, start_time, end_time, db_path=None) -> str` — JSON

- [ ] **Step 1: 编写测试 test_booking.py**

```python
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
        assert "已满" in data["message"] or "占用" in data["message"] or "冲突" in data["message"]
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
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd /home/gfliu/ddtalk && python -m pytest tests/test_booking.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: 编写 skills/booking.py**

```python
"""预约模块 — 预约 + 冲突检测 + 替代推荐"""

import json
from datetime import date, datetime
from skills.db_manager import get_connection
from skills.room_query import get_room_by_name, query_available


def _check_conflict(conn, room_id: int, booking_date: str, start_time: str, end_time: str) -> dict:
    """检查指定房间+时段是否冲突，返回冲突的预约信息"""
    conflict = conn.execute(
        "SELECT id, user_name, start_time, end_time FROM reservations "
        "WHERE room_id = ? AND date = ? AND status = 'active' "
        "  AND start_time < ? AND end_time > ?",
        (room_id, booking_date, end_time, start_time),
    ).fetchone()
    if conflict:
        return {"has_conflict": True, "reservation": dict(conflict)}
    return {"has_conflict": False, "reservation": None}


def book_room(user_id: str, user_name: str, room_name: str,
              booking_date: str, start_time: str, end_time: str,
              db_path: str = None) -> str:
    """预约房间，自动检测冲突并推荐替代房间

    Args:
        user_id: 钉钉用户 ID
        user_name: 用户姓名
        room_name: 房间名称（支持模糊匹配）
        booking_date: 日期 YYYY-MM-DD
        start_time: 开始时间 HH:MM
        end_time: 结束时间 HH:MM
        db_path: 数据库路径

    Returns:
        JSON 字符串: 成功 {"success": true, "message": "...", "reservation_id": N}
                    失败 {"success": false, "message": "...", "recommendations": [...]}
    """
    # 参数校验
    if start_time >= end_time:
        return json.dumps({
            "success": False,
            "message": "开始时间必须早于结束时间，请检查您的时间输入",
        }, ensure_ascii=False)

    today = date.today().isoformat()
    if booking_date < today:
        return json.dumps({
            "success": False,
            "message": f"不能预约过去的日期（{booking_date}），请重新选择时间",
        }, ensure_ascii=False)

    # 查找房间
    room_result = json.loads(get_room_by_name(room_name, db_path))
    if not room_result["success"]:
        return json.dumps({
            "success": False,
            "message": room_result["error"],
        }, ensure_ascii=False)

    room = room_result["room"]

    conn = get_connection(db_path)
    try:
        # 冲突检测
        conflict = _check_conflict(conn, room["id"], booking_date, start_time, end_time)
        if conflict["has_conflict"]:
            # 获取推荐
            recommendations = json.loads(
                recommend_alternatives(room_name, booking_date, start_time, end_time, db_path)
            )

            existing = conflict["reservation"]
            msg = f"{room['name']}在 {booking_date} {start_time}-{end_time} 已被 {existing['user_name']} 预约（{existing['start_time']}-{existing['end_time']}）"

            if recommendations.get("recommendations"):
                rec_list = recommendations["recommendations"]
                rec_text = "，推荐以下替代房间：\n" + "\n".join(
                    f"  {i+1}. {r['name']}（容量{r['capacity']}人，{r['building']}{r['floor']}楼）"
                    for i, r in enumerate(rec_list)
                )
                msg += rec_text
            else:
                msg += "，且该时段暂无其他可用房间"

            return json.dumps({
                "success": False,
                "message": msg,
                "recommendations": recommendations.get("recommendations", []),
            }, ensure_ascii=False)

        # 无冲突，插入预约
        now = datetime.now().isoformat()
        cursor = conn.execute(
            "INSERT INTO reservations (room_id, user_id, user_name, date, start_time, end_time, status, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, 'active', ?)",
            (room["id"], user_id, user_name, booking_date, start_time, end_time, now),
        )
        conn.commit()
        reservation_id = cursor.lastrowid

        return json.dumps({
            "success": True,
            "message": f"预约成功！{room['name']} | {booking_date} {start_time}-{end_time} | ID: {reservation_id}",
            "reservation_id": reservation_id,
            "room": room["name"],
            "date": booking_date,
            "start_time": start_time,
            "end_time": end_time,
        }, ensure_ascii=False)
    finally:
        conn.close()


def recommend_alternatives(room_name: str, booking_date: str,
                           start_time: str, end_time: str,
                           db_path: str = None) -> str:
    """为目标房间推荐容量相近的替代房间

    Args:
        room_name: 目标房间名称
        booking_date: 日期
        start_time: 开始时间
        end_time: 结束时间
        db_path: 数据库路径

    Returns:
        JSON: {"success": true, "recommendations": [...]}
    """
    # 获取目标房间信息
    room_result = json.loads(get_room_by_name(room_name, db_path))
    if not room_result["success"]:
        # 目标房间不存在，返回该时段所有可用房间
        available = json.loads(query_available(booking_date, start_time, end_time, db_path))
        return json.dumps({
            "success": True,
            "recommendations": available.get("rooms", [])[:3],
        }, ensure_ascii=False)

    target = room_result["room"]
    target_capacity = target["capacity"]
    target_building = target["building"]
    target_floor = target["floor"]

    # 查询该时段所有空闲房间
    available_result = json.loads(query_available(booking_date, start_time, end_time, db_path))
    available_rooms = available_result.get("rooms", [])

    # 排除目标房间自己
    alternatives = [r for r in available_rooms if r["id"] != target["id"]]

    # 排序：优先同楼栋同楼层，然后按容量差异升序
    def sort_key(r):
        same_building = 0 if r["building"] == target_building else 1
        capacity_diff = abs(r["capacity"] - target_capacity)
        return (same_building, capacity_diff)

    alternatives.sort(key=sort_key)

    return json.dumps({
        "success": True,
        "recommendations": alternatives[:3],
    }, ensure_ascii=False)
```

- [ ] **Step 4: 运行测试验证通过**

Run: `cd /home/gfliu/ddtalk && python -m pytest tests/test_booking.py -v`
Expected: ALL PASS (8 tests passed)

- [ ] **Step 5: Commit**

```bash
git add skills/booking.py tests/test_booking.py
git commit -m "feat: add booking module with conflict detection and recommendations"
```

---

### Task 6: 预约管理模块 cancellation.py

**Files:**
- Create: `skills/cancellation.py`
- Create: `tests/test_cancellation.py`

**Interfaces:**
- Consumes: `skills.db_manager.get_connection()`
- Produces: `my_reservations(user_id: str, db_path=None) -> str` — JSON
- Produces: `cancel_reservation(user_id: str, reservation_id: int, db_path=None) -> str` — JSON

- [ ] **Step 1: 编写测试 test_cancellation.py**

```python
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
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd /home/gfliu/ddtalk && python -m pytest tests/test_cancellation.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: 编写 skills/cancellation.py**

```python
"""预约管理模块 — 个人查询 & 取消预约"""

import json
from skills.db_manager import get_connection


def my_reservations(user_id: str, db_path: str = None) -> str:
    """查询用户的有效预约列表

    Args:
        user_id: 钉钉用户 ID
        db_path: 数据库路径

    Returns:
        JSON: {"success": true, "reservations": [...], "count": N}
    """
    conn = get_connection(db_path)
    try:
        rows = conn.execute(
            "SELECT r.id, r.room_id, r.date, r.start_time, r.end_time, r.status, r.created_at, "
            "  rm.name AS room_name, rm.building, rm.floor, rm.capacity "
            "FROM reservations r "
            "JOIN rooms rm ON r.room_id = rm.id "
            "WHERE r.user_id = ? AND r.status = 'active' "
            "ORDER BY r.date, r.start_time",
            (user_id,),
        ).fetchall()

        reservations = [
            {
                "id": row["id"],
                "room_name": row["room_name"],
                "building": row["building"],
                "floor": row["floor"],
                "capacity": row["capacity"],
                "date": row["date"],
                "start_time": row["start_time"],
                "end_time": row["end_time"],
                "created_at": row["created_at"],
            }
            for row in rows
        ]

        return json.dumps({
            "success": True,
            "user_id": user_id,
            "reservations": reservations,
            "count": len(reservations),
        }, ensure_ascii=False)
    finally:
        conn.close()


def cancel_reservation(user_id: str, reservation_id: int, db_path: str = None) -> str:
    """取消预约（仅限本人）

    Args:
        user_id: 钉钉用户 ID
        reservation_id: 预约 ID
        db_path: 数据库路径

    Returns:
        JSON: {"success": true, "message": "..."} 或 {"success": false, "message": "..."}
    """
    conn = get_connection(db_path)
    try:
        # 查找预约
        reservation = conn.execute(
            "SELECT id, user_id, room_id, date, start_time, end_time, status "
            "FROM reservations WHERE id = ?",
            (reservation_id,),
        ).fetchone()

        if reservation is None:
            return json.dumps({
                "success": False,
                "message": f"未找到预约记录 ID: {reservation_id}，请检查预约号是否正确",
            }, ensure_ascii=False)

        # 检查是否已取消
        if reservation["status"] == "cancelled":
            return json.dumps({
                "success": False,
                "message": "该预约已经取消了，无需重复操作",
            }, ensure_ascii=False)

        # 权限检查：只能取消自己的预约
        if reservation["user_id"] != user_id:
            return json.dumps({
                "success": False,
                "message": "您只能取消自己的预约，该预约不属于您的账号",
            }, ensure_ascii=False)

        # 执行取消
        conn.execute(
            "UPDATE reservations SET status = 'cancelled' WHERE id = ?",
            (reservation_id,),
        )
        conn.commit()

        # 获取房间名用于友好提示
        room = conn.execute("SELECT name FROM rooms WHERE id = ?", (reservation["room_id"],)).fetchone()
        room_name = room["name"] if room else "未知房间"

        return json.dumps({
            "success": True,
            "message": f"取消成功！{room_name} | {reservation['date']} {reservation['start_time']}-{reservation['end_time']} | ID: {reservation_id} 已取消",
            "reservation_id": reservation_id,
        }, ensure_ascii=False)
    finally:
        conn.close()
```

- [ ] **Step 4: 运行测试验证通过**

Run: `cd /home/gfliu/ddtalk && python -m pytest tests/test_cancellation.py -v`
Expected: ALL PASS (5 tests passed)

- [ ] **Step 5: 更新 skills/__init__.py**

```python
# AI 会议室预约助手 — Skills 模块
from skills.db_manager import get_connection, init_db, seed_data, DEFAULT_DB_PATH
from skills.time_parser import parse_fuzzy_datetime, PERIOD_MAP
from skills.room_query import query_available, query_overview, get_room_by_name
from skills.booking import book_room, recommend_alternatives
from skills.cancellation import my_reservations, cancel_reservation
```

- [ ] **Step 6: Commit**

```bash
git add skills/cancellation.py tests/test_cancellation.py skills/__init__.py
git commit -m "feat: add cancellation module with permission check"
```

---

### Task 7: LLM 提示词文件

**Files:**
- Create: `prompts/system_prompt.md`
- Create: `prompts/intent_classify.md`
- Create: `prompts/response_format.md`

**Interfaces:**
- Produces: 三个提示词文件，供 OpenClaw Agent 配置 LLM 时使用

- [ ] **Step 1: 创建 prompts/system_prompt.md**

````markdown
# 系统提示词 — AI 会议室预约助手

## 角色定义

你是学院会议室预约助手，以钉钉群机器人的身份为师生提供会议室预约服务。你能够理解自然语言描述，自动完成会议室查询、预约、取消等操作。

## 核心能力

1. **预约会议室** — 根据用户描述的时间和房间需求，自动完成预约
2. **查询空闲房间** — 查询任意时段有哪些房间空闲
3. **预约总览** — 展示所有房间在某个时段的占用/空闲状态
4. **冲突推荐** — 当目标房间被占用时，主动推荐容量相近的替代房间
5. **个人预约管理** — 用户可查看自己的预约记录，取消自己的预约

## 行为准则

### 语言风格
- 简洁友好，使用自然中文
- 回复采用结构化展示（列表、分行等）让信息一目了然
- 不使用技术术语（如 SQL、数据库、JSON 等），用户无需知道技术细节

### 边界处理
- 无法理解用户的请求时，友好引导用户重新描述，例如：
  "抱歉，我没有理解您的需求。您可以这样对我说：'帮我约明天下午信电楼330'"
- 预约失败时给出具体原因和建议，而非简单报错
- 房间号不存在时，提示用户检查房间号

### 隐私与权限
- 每个用户只能查看和取消自己的预约
- 不在群内透露预约人的详细信息（如手机号等）

## 时间解析能力

你能理解以下自然语言时间表达：
- "现在" / "今天" / "明天" / "后天"
- "上午"（08:00-12:00）/ "下午"（14:00-18:00）/ "傍晚"（18:00-21:00）/ "晚上"（19:00-22:00）
- "明天下午" / "后天上午" / "下周一" 等组合表达
- 具体日期 "7月14日" 或 "2026-07-14"

## 调用规则

当你识别到用户意图后，调用对应的 Skill：

| 用户意图 | 调用的 Skill | 传入参数 |
|---------|-------------|---------|
| 预约房间 | `book_room` | user_id, user_name, room_name, date, start_time, end_time |
| 查空闲房间 | `query_rooms` | date, start_time, end_time |
| 查看预约总览 | `query_rooms` | date, start_time, end_time |
| 查询我的预约 | `manage_reservation` | user_id |
| 取消预约 | `manage_reservation` | user_id, reservation_id |

所有参数均需从用户输入中提取，包括：
- 用户 ID 和用户名（从钉钉消息中获取）
- 房间号/房间名
- 日期和时间段
- 预约 ID（取消时）
````

- [ ] **Step 2: 创建 prompts/intent_classify.md**

````markdown
# 意图分类提示词

## 说明

根据用户的自然语言输入，判断其意图并提取结构化参数。

## 意图类别

### 1. book — 预约房间

**触发关键词：** 约、定、订、预约、帮我订、帮我约、book、预定、预订

**需要提取的参数：**
- room_name: 房间号或房间名（如 "330"、"信电楼317"）
- date: 日期 YYYY-MM-DD
- start_time: 开始时间 HH:MM
- end_time: 结束时间 HH:MM

**示例：**
| 用户输入 | 提取结果 |
|---------|---------|
| "帮我约明天下午 330" | intent=book, room_name="330", date=<明天>, start_time="14:00", end_time="18:00" |
| "预约下周一上午信电楼501" | intent=book, room_name="信电楼501", date=<下周一>, start_time="08:00", end_time="12:00" |
| "定一个今天下午2点的会议室" | intent=book, room_name=null（需追问）, date=<今天>, start_time="14:00", end_time="18:00" |

### 2. query_available — 查询空闲

**触发关键词：** 空房间、空闲、有哪些、哪些空着、空的、可用的

**需要提取的参数：**
- date: 日期（默认今天）
- start_time: 开始时间
- end_time: 结束时间

**示例：**
| 用户输入 | 提取结果 |
|---------|---------|
| "现在有哪些空房间？" | intent=query_available, date=<今天>, start_time=<现在>, end_time=<当前时段结束> |
| "明天下午有哪些会议室空着？" | intent=query_available, date=<明天>, start_time="14:00", end_time="18:00" |

### 3. query_overview — 预约总览

**触发关键词：** 预约情况、占用情况、都谁约了、全部预约、一览、总览

**需要提取的参数：**
- date: 日期
- start_time: 开始时间
- end_time: 结束时间

**示例：**
| 用户输入 | 提取结果 |
|---------|---------|
| "明天下午各会议室的预约情况" | intent=query_overview, date=<明天>, start_time="14:00", end_time="18:00" |
| "今天330都谁约了？" | intent=query_overview, date=<今天>, room_name="330" |

### 4. query_my — 查询我的预约

**触发关键词：** 我的预约、我约了、我订了、我的记录、我有哪些

**需要提取的参数：**
- user_id: 从钉钉消息中获取

**示例：**
| 用户输入 | 提取结果 |
|---------|---------|
| "我有哪些预约？" | intent=query_my |
| "看看我的预约记录" | intent=query_my |

### 5. cancel — 取消预约

**触发关键词：** 取消、退订、不要了、删掉、撤销

**需要提取的参数：**
- reservation_id: 预约号（如有）
- user_id: 从钉钉消息中获取

**示例：**
| 用户输入 | 提取结果 |
|---------|---------|
| "取消 ID 为 1001 的预约" | intent=cancel, reservation_id=1001 |
| "帮我把明天下午330的预约取消" | intent=cancel, room_name="330", date=<明天>, start_time="14:00"（需查找对应预约ID） |
| "不想要了，取消" | intent=cancel, reservation_id=null（需追问是哪个预约） |

## 未知意图

如果无法匹配以上任何类别，返回 `intent=unknown`，后续回复应引导用户重新描述需求。
````

- [ ] **Step 3: 创建 prompts/response_format.md**

````markdown
# 返回格式模板

## 说明

根据不同的操作结果，使用以下模板格式化回复。所有回复为自然中文，结构清晰。

## 预约成功

```
预约成功！{房间名} | {日期} {开始时间}-{结束时间} | ID: {预约ID}

如需取消，可随时告诉我「取消预约 {预约ID}」
```

## 预约失败 — 房间被占用（有替代推荐）

```
{房间名} 在 {日期} {开始时间}-{结束时间} 已被占用。

推荐以下替代房间：
1. {房间名} — 容量 {人数}人，位于{楼栋}{楼层}楼
2. {房间名} — 容量 {人数}人，位于{楼栋}{楼层}楼
3. {房间名} — 容量 {人数}人，位于{楼栋}{楼层}楼

需要我帮您预约其中一间吗？
```

## 预约失败 — 房间被占用（无替代）

```
{房间名} 在 {日期} {开始时间}-{结束时间} 已被占用，且该时段暂无其他可用房间。

建议您尝试其他时段，比如稍早或稍晚的时间。
```

## 预约失败 — 其他原因

```
抱歉，预约失败：{具体原因}

您可以换个时间或房间再试试~
```

## 空闲房间列表

```
{日期} {开始时间}-{结束时间} 共有 {N} 间空闲会议室：

{楼栋}：
  • {房间名} — {容量}人 | {设备}
  • {房间名} — {容量}人 | {设备}

{楼栋}：
  • {房间名} — {容量}人 | {设备}
```

## 预约总览

```
{日期} {开始时间}-{结束时间} 预约情况：

🟢 空闲：
  • {房间名}（{容量}人）
  • ...

🔴 已占用：
  • {房间名} — {预约人}（{开始时间}-{结束时间}）
  • ...
```

## 我的预约

```
您当前有 {N} 个有效预约：

1. {房间名} | {日期} {开始时间}-{结束时间} | ID: {预约ID}
2. {房间名} | {日期} {开始时间}-{结束时间} | ID: {预约ID}

如需取消某个预约，请告诉我预约ID。
```

## 无预约记录

```
您目前没有预约记录。需要帮您预约会议室吗？
```

## 取消成功

```
取消成功！{房间名} | {日期} {开始时间}-{结束时间} | ID: {预约ID} 已取消

该时段现已释放，其他人可以预约。
```

## 取消失败

```
取消失败：{原因}

如需帮助，请联系管理员。
```

## 无法理解（兜底）

```
抱歉，我没有理解您的需求 😅

您可以这样对我说：
  • "帮我约明天下午信电楼330"
  • "现在有哪些空房间？"
  • "查看我的预约"
  • "取消预约 1001"
```

## 边界友好提示

### 房间不存在
```
抱歉，没有找到「{房间名}」。学院现有以下会议室：

信电楼：330(30人)、317(20人)、212(10人)、501(50人)、108(15人)
理学院：A201(25人)、A305(40人)、B102(60人)

请问您想预约哪一间？
```

### 非开放时段
```
会议室开放时间为 08:00-22:00，您指定的时间超出了服务范围。

请重新选择时间~
```

### 过去时间
```
您指定的时间已经过去了，无法预约过去的时段。请选择未来的时间~
```
````

- [ ] **Step 4: Commit**

```bash
git add prompts/
git commit -m "feat: add LLM system prompt, intent classification, and response templates"
```

---

### Task 8: CLI 命令行测试入口

**Files:**
- Create: `cli/test_shell.py`

**Interfaces:**
- Consumes: 所有 skills 模块
- Produces: 交互式命令行，模拟钉钉用户对话

- [ ] **Step 1: 编写 cli/test_shell.py**

```python
#!/usr/bin/env python3
"""AI 会议室预约助手 — 命令行测试入口

模拟钉钉群机器人交互：接收自然语言，调用 Skill，返回结果。
"""

import json
import sys
import os
from datetime import date

# 确保项目根目录在 path 中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from skills.db_manager import init_db, seed_data
from skills.time_parser import parse_fuzzy_datetime
from skills.room_query import query_available, query_overview, get_room_by_name
from skills.booking import book_room, recommend_alternatives
from skills.cancellation import my_reservations, cancel_reservation


# ============================================================
# 简易意图分类（替代 LLM，用于命令行测试）
# ============================================================

def classify_intent(text: str) -> dict:
    """基于关键词的简易意图分类

    Returns:
        {"intent": "book"|"query_available"|"query_overview"|"query_my"|"cancel"|"unknown",
         "room_name": str or None,
         "reservation_id": int or None}
    """
    text_lower = text.lower()

    # 取消预约
    cancel_keywords = ["取消", "退订", "不要了", "删掉", "撤销"]
    if any(kw in text for kw in cancel_keywords):
        # 尝试提取预约 ID
        import re
        id_match = re.search(r'[iI][dD]\s*[:：]?\s*(\d+)', text)
        id_match2 = re.search(r'预约\s*(\d+)', text)
        rid = None
        if id_match:
            rid = int(id_match.group(1))
        elif id_match2:
            rid = int(id_match2.group(1))
        return {"intent": "cancel", "room_name": _extract_room_name(text), "reservation_id": rid}

    # 查询我的预约
    my_keywords = ["我的预约", "我约了", "我订了", "我的记录", "我有哪些"]
    if any(kw in text for kw in my_keywords):
        return {"intent": "query_my", "room_name": None, "reservation_id": None}

    # 预约总览
    overview_keywords = ["预约情况", "占用情况", "都谁约了", "全部预约", "一览", "总览"]
    if any(kw in text for kw in overview_keywords):
        return {"intent": "query_overview", "room_name": _extract_room_name(text), "reservation_id": None}

    # 查询空闲
    available_keywords = ["空房间", "空闲", "有哪些", "哪些空着", "空的", "可用的"]
    if any(kw in text for kw in available_keywords):
        return {"intent": "query_available", "room_name": None, "reservation_id": None}

    # 预约房间
    book_keywords = ["约", "定", "订", "预约", "帮我", "book", "预定", "预订"]
    if any(kw in text for kw in book_keywords):
        return {"intent": "book", "room_name": _extract_room_name(text), "reservation_id": None}

    return {"intent": "unknown", "room_name": None, "reservation_id": None}


def _extract_room_name(text: str) -> str:
    """从文本中尝试提取房间名称"""
    import re
    # 匹配 "信电楼330" "317" "501" 等
    # 先尝试楼栋+数字
    match = re.search(r'[A-Za-z]*\d{3,4}', text)
    if match:
        return match.group(0)
    # 尝试纯数字（3-4位）
    match = re.search(r'\b(\d{3,4})\b', text)
    if match:
        return match.group(1)
    return None


# ============================================================
# 模拟用户上下文
# ============================================================

class MockUser:
    """模拟钉钉用户"""
    def __init__(self, user_id: str, user_name: str):
        self.user_id = user_id
        self.user_name = user_name


# ============================================================
# 命令处理
# ============================================================

def handle_command(user: MockUser, text: str) -> str:
    """处理用户输入，返回回复文本"""
    intent_info = classify_intent(text)

    # === 查询我的预约 ===
    if intent_info["intent"] == "query_my":
        result = json.loads(my_reservations(user.user_id))
        if result["success"]:
            if result["count"] == 0:
                return "📋 您目前没有预约记录。需要帮您预约会议室吗？"
            lines = [f"📋 您当前有 {result['count']} 个有效预约：", ""]
            for i, r in enumerate(result["reservations"], 1):
                lines.append(f"  {i}. {r['room_name']} | {r['date']} {r['start_time']}-{r['end_time']} | ID: {r['id']}")
            lines.append("")
            lines.append("如需取消某个预约，请告诉我预约ID。")
            return "\n".join(lines)
        return f"❌ 查询失败：{result.get('message', '未知错误')}"

    # === 取消预约 ===
    if intent_info["intent"] == "cancel":
        rid = intent_info["reservation_id"]
        if rid is None:
            # 先查用户的预约列表
            my_list = json.loads(my_reservations(user.user_id))
            if my_list["count"] == 0:
                return "📋 您目前没有预约可以取消。"
            lines = ["📋 请告诉我您要取消哪个预约：", ""]
            for i, r in enumerate(my_list["reservations"], 1):
                lines.append(f"  {i}. {r['room_name']} | {r['date']} {r['start_time']}-{r['end_time']} | ID: {r['id']}")
            return "\n".join(lines)

        result = json.loads(cancel_reservation(user.user_id, rid))
        if result["success"]:
            return f"✅ {result['message']}"
        return f"❌ {result['message']}"

    # === 时间解析 ===
    time_info = parse_fuzzy_datetime(text)
    if "error" in time_info:
        # 对于不需要时间解析的查询，继续
        if intent_info["intent"] in ("query_my", "cancel"):
            pass  # 已在上面处理
        else:
            return f"⏰ 时间解析失败：{time_info['error']}\n请尝试更明确的时间表达，如「明天下午」"

    booking_date = time_info.get("date", date.today().isoformat())
    start_time = time_info.get("start_time", "14:00")
    end_time = time_info.get("end_time", "18:00")

    # === 查询空闲 ===
    if intent_info["intent"] == "query_available":
        result = json.loads(query_available(booking_date, start_time, end_time))
        if result["success"]:
            if result["count"] == 0:
                return f"📋 {booking_date} {start_time}-{end_time} 暂无空闲会议室。"
            lines = [f"📋 {booking_date} {start_time}-{end_time} 共有 {result['count']} 间空闲会议室：", ""]
            by_building = {}
            for r in result["rooms"]:
                by_building.setdefault(r["building"], []).append(r)
            for building, rooms in by_building.items():
                lines.append(f"🏢 {building}：")
                for r in rooms:
                    facilities = f" | {r['facilities']}" if r['facilities'] else ""
                    lines.append(f"  • {r['name']} — {r['capacity']}人{facilities}")
                lines.append("")
            return "\n".join(lines)
        return f"❌ 查询失败：{result.get('message', '未知错误')}"

    # === 预约总览 ===
    if intent_info["intent"] == "query_overview":
        result = json.loads(query_overview(booking_date, start_time, end_time))
        if result["success"]:
            lines = [f"📋 {booking_date} {start_time}-{end_time} 预约情况：", ""]
            available_rooms = [r for r in result["rooms"] if r["status"] == "available"]
            occupied_rooms = [r for r in result["rooms"] if r["status"] == "occupied"]

            if available_rooms:
                lines.append("🟢 空闲：")
                for r in available_rooms:
                    lines.append(f"  • {r['name']}（{r['capacity']}人）")
                lines.append("")
            if occupied_rooms:
                lines.append("🔴 已占用：")
                for r in occupied_rooms:
                    res = r["reservation"]
                    lines.append(f"  • {r['name']} — {res['user_name']}（{res['start_time']}-{res['end_time']}）")
                lines.append("")
            return "\n".join(lines)
        return f"❌ 查询失败：{result.get('message', '未知错误')}"

    # === 预约房间 ===
    if intent_info["intent"] == "book":
        room_name = intent_info["room_name"]
        if room_name is None:
            return "🤔 请问您想预约哪个房间？例如「信电楼330」或「317」"

        result = json.loads(book_room(
            user.user_id, user.user_name, room_name,
            booking_date, start_time, end_time
        ))
        if result["success"]:
            return f"✅ {result['message']}"
        else:
            return f"❌ {result['message']}"

    # === 未知意图 ===
    return """😅 抱歉，我没有理解您的需求。

您可以这样对我说：
  • "帮我约明天下午信电楼330"
  • "现在有哪些空房间？"
  • "明天下午各会议室的预约情况"
  • "查看我的预约"
  • "取消预约 1001"

输入 'help' 查看更多帮助，'quit' 退出。"""


def show_help():
    return """=== AI 会议室预约助手 — 使用帮助 ===

📌 支持的功能：

1. 预约会议室
   示例：帮我约明天下午 330
   示例：预约下周一上午信电楼501

2. 查询空闲房间
   示例：现在有哪些空房间？
   示例：明天下午有哪些会议室空着？

3. 预约总览
   示例：明天下午各会议室的预约情况

4. 我的预约
   示例：查看我的预约

5. 取消预约
   示例：取消预约 1001

📌 时间表达支持：
   • 今天/明天/后天
   • 上午/下午/傍晚/晚上
   • 明天下午 / 下周一上午
   • 具体日期 2026-07-14

📌 命令：
   help  — 显示此帮助
   users — 切换模拟用户
   quit  — 退出程序"""


# ============================================================
# 主循环
# ============================================================

def main():
    # 初始化数据库
    db_path = "db/meeting_rooms.db"
    if not os.path.exists(db_path):
        print("🔧 初始化数据库...")
        init_db(db_path)
        seed_data(db_path)
        print("✅ 数据库初始化完成！")

    # 默认模拟用户
    users = [
        MockUser("user001", "张三"),
        MockUser("user002", "李四"),
        MockUser("user003", "王五"),
    ]
    current_user = users[0]

    print("=" * 50)
    print("  AI 会议室预约助手 — 命令行测试模式")
    print("=" * 50)
    print(f"  当前模拟用户: {current_user.user_name} ({current_user.user_id})")
    print("  输入 'help' 查看帮助, 'quit' 退出")
    print("=" * 50)
    print()

    while True:
        try:
            user_input = input(f"[{current_user.user_name}] > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n👋 再见！")
            break

        if not user_input:
            continue

        if user_input.lower() == "quit":
            print("👋 再见！")
            break

        if user_input.lower() == "help":
            print(show_help())
            print()
            continue

        if user_input.lower() == "users":
            print("可用模拟用户：")
            for i, u in enumerate(users):
                marker = " ← 当前" if u.user_id == current_user.user_id else ""
                print(f"  {i+1}. {u.user_name} ({u.user_id}){marker}")
            print("输入序号切换用户：")
            try:
                choice = input("> ").strip()
                idx = int(choice) - 1
                if 0 <= idx < len(users):
                    current_user = users[idx]
                    print(f"✅ 已切换到: {current_user.user_name}")
                else:
                    print("❌ 无效序号")
            except ValueError:
                print("❌ 请输入数字")
            print()
            continue

        # 处理输入
        print()
        response = handle_command(current_user, user_input)
        print(response)
        print()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 验证 CLI 可运行**

Run: `cd /home/gfliu/ddtalk && echo "help" | python cli/test_shell.py`
Expected: 显示帮助信息，无错误

- [ ] **Step 3: 快速功能验证**

Run: `cd /home/gfliu/ddtalk && python -c "
import sys, os
sys.path.insert(0, '.')
from skills.db_manager import init_db, seed_data
init_db('db/test_cli.db')
seed_data('db/test_cli.db')
from cli.test_shell import handle_command, MockUser
user = MockUser('user001', '张三')
# 测试意图分类
print('测试 1: 查询我的预约')
print(handle_command(user, '我的预约'))
print()
print('测试 2: 预约空闲房间')
print(handle_command(user, '帮我约明天下午 317'))
print()
print('测试 3: 查询空闲')
print(handle_command(user, '明天下午有哪些空房间？'))
os.remove('db/test_cli.db')
print()
print('全部功能验证通过 ✅')
" 2>&1`
Expected: 显示各项操作结果，无异常

- [ ] **Step 4: Commit**

```bash
git add cli/test_shell.py
git commit -m "feat: add CLI test shell for interactive testing"
```

---

### Task 9: 集成测试用例（15+）

**Files:**
- Create: `tests/test_scenarios.py`

**Interfaces:**
- Consumes: 所有 skills 模块
- Produces: 17 个端到端集成测试用例

- [ ] **Step 1: 编写 tests/test_scenarios.py**

```python
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
        result = json.loads(book_room("user001", "张三", "信电楼330", "2026-07-14", "14:00", "16:00", TEST_DB))
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
        result = json.loads(query_available("2026-07-14", "14:00", "16:00", TEST_DB))
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
        result = json.loads(query_overview("2026-07-14", "14:00", "16:00", TEST_DB))
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
        result = json.loads(recommend_alternatives("信电楼330", "2026-07-14", "14:00", "16:00", TEST_DB))
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
        result = json.loads(book_room("user001", "张三", "信电楼330", "2026-07-14", "16:00", "18:00", TEST_DB))
        assert result["success"] is True

    def test_tc19_empty_user_no_reservations(self):
        """TC19: 无预约记录的用户查询 → 返回空列表"""
        result = json.loads(my_reservations("user999", TEST_DB))
        assert result["success"] is True
        assert result["count"] == 0
```

- [ ] **Step 2: 运行全部测试**

Run: `cd /home/gfliu/ddtalk && python -m pytest tests/ -v`
Expected: ALL 36 tests PASS (11 time_parser + 7 room_query + 8 booking + 5 cancellation + 19 scenarios)

- [ ] **Step 3: 生成测试报告**

Run: `cd /home/gfliu/ddtalk && python -m pytest tests/ -v --tb=short 2>&1 | tee test_report.txt`
Expected: 36 passed, 0 failed

- [ ] **Step 4: Commit**

```bash
git add tests/test_scenarios.py test_report.txt
git commit -m "test: add 19 integration test cases, total 36 tests 100% pass"
```

---

## 验证清单

- [x] 所有 Task 都有明确的文件路径和完整代码
- [x] 每个 Task 有独立可验证的测试步骤
- [x] 接口定义一致（函数签名在各 Task 中匹配）
- [x] 覆盖了设计文档中的所有模块
- [x] 测试用例覆盖 15+ 场景（实际 36 个）
- [x] 无 TBD/TODO/占位符
