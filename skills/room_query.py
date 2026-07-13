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
