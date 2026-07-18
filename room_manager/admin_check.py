"""管理员校验 — 检查用户是否在 admins 表中"""

import json
from meeting_room.db_manager import get_connection


def is_admin(user_id: str, db_path: str = None) -> str:
    """检查用户是否为管理员

    Args:
        user_id: 钉钉用户 ID
        db_path: 数据库路径

    Returns:
        JSON: {"success": true, "is_admin": true/false, "user_name": "..."}
    """
    conn = get_connection(db_path)
    try:
        admin = conn.execute(
            "SELECT user_name, role FROM admins WHERE user_id = ?",
            (user_id,),
        ).fetchone()

        if admin:
            return json.dumps({
                "success": True,
                "is_admin": True,
                "user_name": admin["user_name"],
                "role": admin["role"],
            }, ensure_ascii=False)
        else:
            return json.dumps({
                "success": True,
                "is_admin": False,
                "message": "您不是管理员，无权执行此操作",
            }, ensure_ascii=False)
    finally:
        conn.close()


def require_admin(user_id: str, db_path: str = None) -> str:
    """要求管理员权限，否则返回错误

    Returns:
        如果是管理员 → {"authorized": true, "user_name": "..."}
        否则 → {"authorized": false, "message": "权限不足"}
    """
    result = json.loads(is_admin(user_id, db_path))
    if result["is_admin"]:
        return json.dumps({
            "authorized": True,
            "user_name": result["user_name"],
        }, ensure_ascii=False)
    else:
        return json.dumps({
            "authorized": False,
            "message": "权限不足——只有管理员才能执行此操作",
        }, ensure_ascii=False)
