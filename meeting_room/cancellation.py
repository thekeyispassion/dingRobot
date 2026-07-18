"""预约管理模块 — 个人查询 & 取消预约"""

import json
from meeting_room.db_manager import get_connection


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
                "user_id": user_id,
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
                "message": "该预约已取消，无需重复操作",
            }, ensure_ascii=False)

        # 权限检查：只能取消自己的预约
        if reservation["user_id"] != user_id:
            return json.dumps({
                "success": False,
                "message": "您没有权限取消该预约，您只能取消自己的预约",
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
