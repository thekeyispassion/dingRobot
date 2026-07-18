"""房间查询模块 — 空闲查询、今日实时状态、日程查询"""

import json
from meeting_room.db_manager import get_connection


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


def query_today_status(db_path: str = None) -> str:
    """查询今天每个房间的实时状态——此刻谁在用、之后谁约了

    不需要参数，自动使用当前日期和时间。

    Returns:
        JSON: {
            "success": true,
            "date": "2026-07-15",
            "current_time": "15:30",
            "rooms": [
                {
                    "name": "信电楼330", "building": "信电楼", "floor": 3, "capacity": 30,
                    "status": "occupied",           # "occupied" | "available"
                    "current": {                    # 正在进行的预约（status=occupied 时有值）
                        "user_name": "李四",
                        "start_time": "14:00",
                        "end_time": "16:00",
                        "reservation_id": 1
                    },
                    "upcoming": [                   # 今天后续的预约（按时间排序）
                        {"user_name": "王五", "start_time": "16:00", "end_time": "18:00", "reservation_id": 5}
                    ]
                },
                ...
            ]
        }
    """
    from datetime import datetime

    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    now_str = now.strftime("%H:%M")

    conn = get_connection(db_path)
    try:
        # 查询今天所有 active 预约
        reservations = conn.execute(
            "SELECT id, room_id, user_name, start_time, end_time "
            "FROM reservations "
            "WHERE date = ? AND status = 'active' "
            "ORDER BY start_time",
            (today_str,),
        ).fetchall()

        # 按房间分组
        room_bookings = {}
        for res in reservations:
            room_bookings.setdefault(res["room_id"], []).append({
                "user_name": res["user_name"],
                "start_time": res["start_time"],
                "end_time": res["end_time"],
                "reservation_id": res["id"],
            })

        # 查询所有房间
        rooms = conn.execute(
            "SELECT id, name, building, floor, capacity, facilities "
            "FROM rooms WHERE status = 'available' ORDER BY building, floor, name"
        ).fetchall()

        room_list = []
        for r in rooms:
            bookings = room_bookings.get(r["id"], [])

            # 找正在进行的预约
            current = None
            upcoming = []
            for b in bookings:
                if b["start_time"] <= now_str < b["end_time"]:
                    current = b
                elif b["start_time"] > now_str:
                    upcoming.append(b)

            room_list.append({
                "name": r["name"],
                "building": r["building"],
                "floor": r["floor"],
                "capacity": r["capacity"],
                "status": "occupied" if current else "available",
                "current": current,
                "upcoming": upcoming,
            })

        return json.dumps({
            "success": True,
            "date": today_str,
            "current_time": now_str,
            "rooms": room_list,
        }, ensure_ascii=False)
    finally:
        conn.close()


def query_day_schedule(date: str, db_path: str = None) -> str:
    """查询某天所有房间的预约日程——每个房间今天的预约时间线

    Args:
        date: 日期 YYYY-MM-DD（"今天" 也可以传具体日期）
        db_path: 数据库路径

    Returns:
        JSON: {
            "success": true,
            "date": "2026-07-15",
            "rooms": [
                {
                    "name": "信电楼330", "building": "信电楼", "floor": 3, "capacity": 30,
                    "bookings": [
                        {"user_name": "李四", "start_time": "09:00", "end_time": "11:00", "reservation_id": 1},
                        {"user_name": "王五", "start_time": "14:00", "end_time": "16:00", "reservation_id": 2}
                    ],
                    "booking_count": 2
                },
                {
                    "name": "信电楼317", ...,
                    "bookings": [],           # 今天没人约——全天空闲
                    "booking_count": 0
                },
                ...
            ],
            "total_bookings": 5               # 当天预约总数
        }
    """
    conn = get_connection(db_path)
    try:
        # 查询该日期所有 active 预约
        reservations = conn.execute(
            "SELECT id, room_id, user_name, start_time, end_time "
            "FROM reservations "
            "WHERE date = ? AND status = 'active' "
            "ORDER BY start_time",
            (date,),
        ).fetchall()

        # 按房间分组
        room_bookings = {}
        total = 0
        for res in reservations:
            room_bookings.setdefault(res["room_id"], []).append({
                "user_name": res["user_name"],
                "start_time": res["start_time"],
                "end_time": res["end_time"],
                "reservation_id": res["id"],
            })
            total += 1

        # 查询所有房间
        rooms = conn.execute(
            "SELECT id, name, building, floor, capacity, facilities "
            "FROM rooms WHERE status = 'available' ORDER BY building, floor, name"
        ).fetchall()

        room_list = []
        for r in rooms:
            bookings = room_bookings.get(r["id"], [])
            room_list.append({
                "name": r["name"],
                "building": r["building"],
                "floor": r["floor"],
                "capacity": r["capacity"],
                "bookings": bookings,
                "booking_count": len(bookings),
            })

        return json.dumps({
            "success": True,
            "date": date,
            "rooms": room_list,
            "total_bookings": total,
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
