"""会议室管理 — 增删改查会议室基本信息"""

import json
from datetime import datetime
from meeting_room.db_manager import get_connection
from room_manager.admin_check import require_admin


def list_rooms(include_maintenance: bool = True, db_path: str = None) -> str:
    """列出所有会议室（含完整信息）

    Args:
        include_maintenance: 是否包含维护中的房间
        db_path: 数据库路径

    Returns:
        JSON: {"success": true, "rooms": [...], "count": N}
    """
    conn = get_connection(db_path)
    try:
        if include_maintenance:
            rooms = conn.execute(
                "SELECT id, name, building, floor, capacity, facilities, status, description "
                "FROM rooms ORDER BY building, floor, name"
            ).fetchall()
        else:
            rooms = conn.execute(
                "SELECT id, name, building, floor, capacity, facilities, status, description "
                "FROM rooms WHERE status = 'available' ORDER BY building, floor, name"
            ).fetchall()

        room_list = [
            {
                "id": r["id"],
                "name": r["name"],
                "building": r["building"],
                "floor": r["floor"],
                "capacity": r["capacity"],
                "facilities": r["facilities"],
                "status": r["status"],
                "description": r["description"],
            }
            for r in rooms
        ]

        return json.dumps({
            "success": True,
            "rooms": room_list,
            "count": len(room_list),
        }, ensure_ascii=False)
    finally:
        conn.close()


def add_room(user_id: str, name: str, building: str, floor: int,
             capacity: int, facilities: str = "", description: str = "",
             db_path: str = None) -> str:
    """添加新会议室

    Args:
        user_id: 操作者钉钉 ID
        name: 会议室名称
        building: 楼栋
        floor: 楼层
        capacity: 容量
        facilities: 设备列表
        description: 备注
        db_path: 数据库路径

    Returns:
        JSON: {"success": true, "room": {...}} 或 {"success": false, "message": "..."}
    """
    # 权限检查
    auth = json.loads(require_admin(user_id, db_path))
    if not auth["authorized"]:
        return json.dumps({
            "success": False,
            "message": auth["message"],
        }, ensure_ascii=False)

    conn = get_connection(db_path)
    try:
        # 检查是否已存在同名房间
        existing = conn.execute(
            "SELECT id FROM rooms WHERE name = ?", (name,)
        ).fetchone()
        if existing:
            return json.dumps({
                "success": False,
                "message": f"会议室 '{name}' 已存在，请使用其他名称",
            }, ensure_ascii=False)

        cursor = conn.execute(
            "INSERT INTO rooms (name, building, floor, capacity, facilities, status, description) "
            "VALUES (?, ?, ?, ?, ?, 'available', ?)",
            (name, building, floor, capacity, facilities, description),
        )
        conn.commit()

        return json.dumps({
            "success": True,
            "message": f"会议室 '{name}' 添加成功",
            "room": {
                "id": cursor.lastrowid,
                "name": name,
                "building": building,
                "floor": floor,
                "capacity": capacity,
                "facilities": facilities,
                "status": "available",
                "description": description,
            },
        }, ensure_ascii=False)
    finally:
        conn.close()


def update_room(user_id: str, room_id: int, db_path: str = None, **fields) -> str:
    """修改会议室信息

    可修改的字段：name, building, floor, capacity, facilities, description
    不可修改 status——用 disable_room/enable_room

    Args:
        user_id: 操作者钉钉 ID
        room_id: 会议室 ID
        **fields: 要修改的字段和值
        db_path: 数据库路径

    Returns:
        JSON: {"success": true, "message": "..."}
    """
    auth = json.loads(require_admin(user_id, db_path))
    if not auth["authorized"]:
        return json.dumps({
            "success": False,
            "message": auth["message"],
        }, ensure_ascii=False)

    allowed_fields = {"name", "building", "floor", "capacity", "facilities", "description"}
    updates = {k: v for k, v in fields.items() if k in allowed_fields}
    if not updates:
        return json.dumps({
            "success": False,
            "message": "没有有效的修改字段。可修改：名称(name)、楼栋(building)、楼层(floor)、容量(capacity)、设备(facilities)、备注(description)",
        }, ensure_ascii=False)

    conn = get_connection(db_path)
    try:
        # 检查房间是否存在
        room = conn.execute("SELECT id, name FROM rooms WHERE id = ?", (room_id,)).fetchone()
        if not room:
            return json.dumps({
                "success": False,
                "message": f"未找到会议室 ID: {room_id}",
            }, ensure_ascii=False)

        # 如果要改名，检查新名字是否已被占用
        if "name" in updates and updates["name"] != room["name"]:
            dup = conn.execute("SELECT id FROM rooms WHERE name = ? AND id != ?",
                               (updates["name"], room_id)).fetchone()
            if dup:
                return json.dumps({
                    "success": False,
                    "message": f"会议室名称 '{updates['name']}' 已被占用",
                }, ensure_ascii=False)

        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [room_id]
        conn.execute(f"UPDATE rooms SET {set_clause} WHERE id = ?", values)
        conn.commit()

        changed = ", ".join(f"{k} → {v}" for k, v in updates.items())
        return json.dumps({
            "success": True,
            "message": f"会议室 ID:{room_id} 修改成功：{changed}",
        }, ensure_ascii=False)
    finally:
        conn.close()


def disable_room(user_id: str, room_id: int, db_path: str = None) -> str:
    """停用会议室（有活跃预约时拒绝）

    Args:
        user_id: 操作者钉钉 ID
        room_id: 会议室 ID
        db_path: 数据库路径

    Returns:
        JSON: {"success": true/false, "message": "..."}
    """
    auth = json.loads(require_admin(user_id, db_path))
    if not auth["authorized"]:
        return json.dumps({
            "success": False,
            "message": auth["message"],
        }, ensure_ascii=False)

    conn = get_connection(db_path)
    try:
        room = conn.execute("SELECT id, name, status FROM rooms WHERE id = ?", (room_id,)).fetchone()
        if not room:
            return json.dumps({
                "success": False,
                "message": f"未找到会议室 ID: {room_id}",
            }, ensure_ascii=False)

        if room["status"] == "maintenance":
            return json.dumps({
                "success": False,
                "message": f"会议室 '{room['name']}' 已经是停用状态",
            }, ensure_ascii=False)

        # 检查是否有活跃预约
        today = datetime.now().strftime("%Y-%m-%d")
        active = conn.execute(
            "SELECT COUNT(*) as cnt FROM reservations "
            "WHERE room_id = ? AND status = 'active' AND date >= ?",
            (room_id, today),
        ).fetchone()

        if active["cnt"] > 0:
            return json.dumps({
                "success": False,
                "message": f"无法停用 '{room['name']}'——该会议室有 {active['cnt']} 个未完成的预约，请先处理预约后再停用",
            }, ensure_ascii=False)

        conn.execute("UPDATE rooms SET status = 'maintenance' WHERE id = ?", (room_id,))
        conn.commit()

        return json.dumps({
            "success": True,
            "message": f"会议室 '{room['name']}' 已停用",
        }, ensure_ascii=False)
    finally:
        conn.close()


def enable_room(user_id: str, room_id: int, db_path: str = None) -> str:
    """启用会议室（从 maintenance 恢复为 available）

    Args:
        user_id: 操作者钉钉 ID
        room_id: 会议室 ID
        db_path: 数据库路径

    Returns:
        JSON: {"success": true/false, "message": "..."}
    """
    auth = json.loads(require_admin(user_id, db_path))
    if not auth["authorized"]:
        return json.dumps({
            "success": False,
            "message": auth["message"],
        }, ensure_ascii=False)

    conn = get_connection(db_path)
    try:
        room = conn.execute("SELECT id, name, status FROM rooms WHERE id = ?", (room_id,)).fetchone()
        if not room:
            return json.dumps({
                "success": False,
                "message": f"未找到会议室 ID: {room_id}",
            }, ensure_ascii=False)

        if room["status"] == "available":
            return json.dumps({
                "success": False,
                "message": f"会议室 '{room['name']}' 已经是启用状态",
            }, ensure_ascii=False)

        conn.execute("UPDATE rooms SET status = 'available' WHERE id = ?", (room_id,))
        conn.commit()

        return json.dumps({
            "success": True,
            "message": f"会议室 '{room['name']}' 已启用",
        }, ensure_ascii=False)
    finally:
        conn.close()
