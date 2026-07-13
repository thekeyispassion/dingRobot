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
