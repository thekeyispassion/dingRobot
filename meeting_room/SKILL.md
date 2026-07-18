---
name: meeting-room
description: 学院会议室预约助手，通过 Python 脚本操作 SQLite 数据库。查询空闲、预约、取消、日程查看。
alwaysActive: true
---

# 会议室预约助手 — 操作手册

## 环境信息

- 项目根目录: `/opt/ding-robot`
- Python 路径: `/opt/ding-robot/myven/bin/python`（如用虚拟环境）或系统 Python
- 数据库路径: `/opt/ding-robot/db/meeting_rooms.db`
- 所有命令从项目根目录执行: `cd /opt/ding-robot`

## 命令格式

```bash
cd /opt/ding-robot && python -c "
import json
from meeting_room.xxx import yyy
result = yyy(...)
print(result)
"
```

> 所有函数返回 JSON 字符串，`print()` 输出后读取结果。

## 触发规则

当用户消息涉及以下场景时，自动触发：

| 场景 | 关键词/意图 | 执行操作 |
|------|------------|---------|
| 预约会议室 | 约、定、订、预约、帮我订、book | 解析时间+房间 → `book_room` |
| 查询空闲 | 空房间、空闲、有哪些、空着 | 解析时间 → `query_available` |
| 今日状态 | 现在谁在、当前状态、在用 | `query_today_status` |
| 预约日程 | 预约情况、谁约了、日程、一览 | 解析日期 → `query_day_schedule` |
| 我的预约 | 我的预约、我约了、我订了 | `my_reservations` |
| 取消预约 | 取消、退订、不要了 | 有 ID 直接取消，无 ID 先查再确认 |
| 询问房间 | 有哪些房间、会议室列表 | 执行数据库查询 |

---

## 可用操作

### 1. 查询空闲房间

```bash
cd /opt/ding-robot && python -c "
import json
from meeting_room.room_query import query_available
print(query_available('DATE', 'START_TIME', 'END_TIME'))
"
```

**参数：** `DATE` YYYY-MM-DD, `START_TIME` HH:MM, `END_TIME` HH:MM

**返回：** `{"success": true, "rooms": [{"name": "信电楼317", "building": "信电楼", "floor": 3, "capacity": 20, "facilities": "投影仪,白板"}, ...], "count": 7}`

### 2. 今日实时状态

```bash
cd /opt/ding-robot && python -c "
import json
from meeting_room.room_query import query_today_status
print(query_today_status())
"
```

无需参数，自动使用当前时间。

**返回：** `{"success": true, "current_time": "15:30", "rooms": [{"name": "信电楼330", "status": "occupied", "current": {"user_name": "李四", "start_time": "14:00", "end_time": "16:00"}, "upcoming": []}, {"name": "信电楼317", "status": "available", "current": null, "upcoming": [{"user_name": "王五", "start_time": "16:00"}]}]}`

- `status`: "occupied" / "available"
- `current`: 正在进行的预约（谁、到几点）
- `upcoming`: 今天后续的预约列表

### 3. 某天预约日程

```bash
cd /opt/ding-robot && python -c "
import json
from meeting_room.room_query import query_day_schedule
print(query_day_schedule('DATE'))
"
```

**参数：** `DATE` YYYY-MM-DD

**返回：** `{"success": true, "date": "2026-07-15", "rooms": [{"name": "信电楼330", "bookings": [{"user_name": "李四", "start_time": "09:00", "end_time": "11:00"}], "booking_count": 1}, {"name": "信电楼317", "bookings": [], "booking_count": 0}], "total_bookings": 5}`

`booking_count == 0` = 全天可约。

### 4. 预约会议室

```bash
cd /opt/ding-robot && python -c "
import json
from meeting_room.booking import book_room
print(book_room('USER_ID', 'USER_NAME', 'ROOM_NAME', 'DATE', 'START_TIME', 'END_TIME'))
"
```

**参数：** `USER_ID` 钉钉用户ID, `USER_NAME` 姓名, `ROOM_NAME` 房间名或房间号（支持模糊匹配），`DATE` YYYY-MM-DD, `START_TIME`/`END_TIME` HH:MM

**返回（成功）：** `{"success": true, "message": "预约成功！信电楼330 | 2026-07-15 14:00-16:00 | ID: 1001", "reservation_id": 1001}`

**返回（冲突，有推荐）：** `{"success": false, "message": "信电楼330已被占用，推荐：1. 信电楼317（容量20人）2. ...", "recommendations": [...]}`

> 返回 `success: false` 且有 `recommendations` 时，直接把 `message` 展示给用户。

### 5. 查询我的预约

```bash
cd /opt/ding-robot && python -c "
import json
from meeting_room.cancellation import my_reservations
print(my_reservations('USER_ID'))
"
```

**返回：** `{"success": true, "reservations": [{"id": 1, "room_name": "信电楼330", "date": "2026-07-15", "start_time": "14:00", "end_time": "16:00"}], "count": 1}`

### 6. 取消预约

```bash
cd /opt/ding-robot && python -c "
import json
from meeting_room.cancellation import cancel_reservation
print(cancel_reservation('USER_ID', RESERVATION_ID))
"
```

**参数：** `USER_ID` 钉钉用户ID, `RESERVATION_ID` 预约ID（整数）

**返回：** 成功 `{"success": true, "message": "取消成功！..."}` / 失败 `{"success": false, "message": "您只能取消自己的预约..."}`

> 用户只说"取消"不提供ID时，先执行"查询我的预约"，列出让用户选。

### 7. 时间解析辅助（可选）

```bash
cd /opt/ding-robot && python -c "
import json
from meeting_room.time_parser import parse_fuzzy_datetime
print(json.dumps(parse_fuzzy_datetime('明天下午')))
"
```

**返回：** `{"date": "2026-07-15", "start_time": "14:00", "end_time": "18:00"}`

> 这个函数是可选的兜底方案——你本身就能理解"明天下午"的意思。
