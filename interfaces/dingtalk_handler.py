"""钉钉消息处理器 — 消息解析 & 回复格式化"""

import json
from typing import Optional


def parse_incoming(payload: dict) -> dict:
    """解析传入消息，提取用户身份和消息内容

    支持两种模式：
    - OpenClaw 模式：OpenClaw 已解析好，直接读取字段
    - 独立模式：从钉钉原始 webhook payload 解析

    Args:
        payload: 消息体

    Returns:
        {"user_id": str, "user_name": str, "message": str}
    """
    # 尝试 OpenClaw 标准格式
    if "sender" in payload:
        sender = payload.get("sender", {})
        return {
            "user_id": sender.get("userId", sender.get("user_id", "unknown")),
            "user_name": sender.get("userName", sender.get("user_name", "用户")),
            "message": _extract_text(payload),
        }

    # 尝试钉钉原始格式
    if "senderId" in payload:
        return {
            "user_id": payload.get("senderId", "unknown"),
            "user_name": payload.get("senderNick", payload.get("senderId", "用户")),
            "message": _extract_text(payload),
        }

    # 最简格式：字段直接在顶层
    return {
        "user_id": payload.get("user_id", "unknown"),
        "user_name": payload.get("user_name", "用户"),
        "message": payload.get("message", payload.get("text", payload.get("content", str(payload)))),
    }


def _extract_text(payload: dict) -> str:
    """从 payload 中提取文本内容"""
    # OpenClaw 格式
    if "message" in payload and isinstance(payload["message"], dict):
        msg = payload["message"]
        return msg.get("text", msg.get("content", str(msg)))
    if "text" in payload:
        text = payload["text"]
        if isinstance(text, dict):
            return text.get("content", str(text))
        return str(text)
    if "content" in payload:
        return str(payload["content"])
    if "body" in payload:
        body = payload["body"]
        if isinstance(body, dict):
            return body.get("text", body.get("content", str(body)))
        return str(body)
    return str(payload)


def format_response(skill_result: dict) -> str:
    """将 Skill 返回的 JSON 格式化为钉钉消息文本

    如果 skill 已经包含 message 字段，直接使用——
    skills 层已经做了自然语言格式化。

    Args:
        skill_result: skill 返回的结果字典（已从 JSON 解析）

    Returns:
        适合在钉钉群聊展示的文本
    """
    # 如果 skill 已经提供了友好的 message，直接使用
    if "message" in skill_result:
        return skill_result["message"]

    # 否则构建结构化回复
    if skill_result.get("success") is True:
        return _format_success(skill_result)
    else:
        return _format_error(skill_result)


def _format_success(data: dict) -> str:
    """格式化成功回复"""
    parts = []

    # 预约成功
    if "reservation_id" in data:
        parts.append(f"预约成功！{data.get('room', '')} | {data.get('date', '')} {data.get('start_time', '')}-{data.get('end_time', '')} | ID: {data['reservation_id']}")
        return "\n".join(parts)

    # 房间列表（空闲查询 / 预约总览）
    rooms = data.get("rooms", [])
    if rooms:
        parts.append(f"共 {len(rooms)} 间：")
        for r in rooms:
            status_icon = "🟢" if r.get("status") in ("available", None) else "🔴"
            parts.append(f"  {status_icon} {r['name']}（{r.get('capacity', '?')}人）")
        return "\n".join(parts)

    # 我的预约
    reservations = data.get("reservations", [])
    if reservations:
        parts.append(f"您有 {len(reservations)} 个预约：")
        for r in reservations:
            parts.append(f"  • {r['room_name']} | {r['date']} {r['start_time']}-{r['end_time']} | ID: {r['id']}")
        return "\n".join(parts)

    # 取消成功
    if "reservation_id" in data and data.get("success"):
        return f"已取消预约 ID: {data['reservation_id']}"

    return json.dumps(data, ensure_ascii=False, indent=2)


def _format_error(data: dict) -> str:
    """格式化错误回复"""
    message = data.get("message", data.get("error", "操作失败"))
    return f"抱歉，{message}"


def build_sender_from_env() -> dict:
    """从环境变量构建模拟用户（CLI 测试模式用）"""
    import os
    return {
        "user_id": os.environ.get("DDTALK_USER_ID", "user001"),
        "user_name": os.environ.get("DDTALK_USER_NAME", "测试用户"),
        "message": "",
    }
