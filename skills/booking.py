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
