#!/usr/bin/env python3
"""AI 会议室预约助手 — 命令行测试入口

模拟钉钉群机器人交互：接收自然语言，调用 Skill，返回结果。
接口层：interfaces/llm_client（意图分类）+ interfaces/dingtalk_handler（消息处理）
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

from interfaces.llm_client import classify_intent
from interfaces.dingtalk_handler import parse_incoming, format_response, build_sender_from_env
from interfaces.config import get_config, mask_key


# ============================================================
# 命令处理
# ============================================================

def handle_command(user_id: str, user_name: str, text: str) -> str:
    """处理用户输入，返回回复文本

    Args:
        user_id: 用户 ID
        user_name: 用户姓名
        text: 用户输入的自然语言

    Returns:
        格式化后的回复文本
    """
    intent_info = classify_intent(text)
    intent = intent_info.get("intent", "unknown")
    params = intent_info.get("params", {})

    # === 查询我的预约 ===
    if intent == "query_my":
        result = json.loads(my_reservations(user_id))
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
    if intent == "cancel":
        rid = params.get("reservation_id")
        if rid is None:
            # 先查用户的预约列表
            my_list = json.loads(my_reservations(user_id))
            if my_list["count"] == 0:
                return "📋 您目前没有预约可以取消。"
            lines = ["📋 请告诉我您要取消哪个预约：", ""]
            for i, r in enumerate(my_list["reservations"], 1):
                lines.append(f"  {i}. {r['room_name']} | {r['date']} {r['start_time']}-{r['end_time']} | ID: {r['id']}")
            return "\n".join(lines)

        result = json.loads(cancel_reservation(user_id, rid))
        if result["success"]:
            return f"✅ {result['message']}"
        return f"❌ {result['message']}"

    # === 时间解析 ===
    time_info = parse_fuzzy_datetime(text)
    if "error" in time_info:
        if intent in ("query_my", "cancel"):
            pass
        else:
            return f"⏰ 时间解析失败：{time_info['error']}\n请尝试更明确的时间表达，如「明天下午」"

    booking_date = time_info.get("date", date.today().isoformat())
    start_time = time_info.get("start_time", "14:00")
    end_time = time_info.get("end_time", "18:00")

    # === 查询空闲 ===
    if intent == "query_available":
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
                    facilities = f" | {r['facilities']}" if r.get('facilities') else ""
                    lines.append(f"  • {r['name']} — {r['capacity']}人{facilities}")
                lines.append("")
            return "\n".join(lines)
        return f"❌ 查询失败：{result.get('message', '未知错误')}"

    # === 预约总览 ===
    if intent == "query_overview":
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
    if intent == "book":
        room_name = params.get("room_name")
        if room_name is None:
            return "🤔 请问您想预约哪个房间？例如「信电楼330」或「317」"

        result = json.loads(book_room(
            user_id, user_name, room_name,
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
   help   — 显示此帮助
   users  — 切换模拟用户
   config — 查看当前配置
   quit   — 退出程序"""


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

    # 加载配置
    config = get_config()
    llm_status = "已配置" if config.llm_configured else "本地模式（未检测到 LLM API Key）"

    # 模拟用户列表
    users = [
        {"user_id": "user001", "user_name": "张三"},
        {"user_id": "user002", "user_name": "李四"},
        {"user_id": "user003", "user_name": "王五"},
    ]
    current_user = users[0]

    print("=" * 50)
    print("  AI 会议室预约助手 — 命令行测试模式")
    print("=" * 50)
    print(f"  LLM 状态: {llm_status}")
    print(f"  当前模拟用户: {current_user['user_name']} ({current_user['user_id']})")
    print("  输入 'help' 查看帮助, 'quit' 退出")
    print("=" * 50)
    print()

    while True:
        try:
            user_input = input(f"[{current_user['user_name']}] > ").strip()
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

        if user_input.lower() == "config":
            print(f"LLM Base URL: {config.llm_base_url}")
            print(f"LLM Model:    {config.llm_model}")
            print(f"LLM API Key:  {mask_key(config.llm_api_key)}")
            print(f"DingTalk Mode: {config.dingtalk_mode}")
            print()
            continue

        if user_input.lower() == "users":
            print("可用模拟用户：")
            for i, u in enumerate(users):
                marker = " ← 当前" if u["user_id"] == current_user["user_id"] else ""
                print(f"  {i+1}. {u['user_name']} ({u['user_id']}){marker}")
            print("输入序号切换用户：")
            try:
                choice = input("> ").strip()
                idx = int(choice) - 1
                if 0 <= idx < len(users):
                    current_user = users[idx]
                    print(f"✅ 已切换到: {current_user['user_name']}")
                else:
                    print("❌ 无效序号")
            except ValueError:
                print("❌ 请输入数字")
            print()
            continue

        # 处理输入
        print()
        response = handle_command(current_user["user_id"], current_user["user_name"], user_input)
        print(response)
        print()


if __name__ == "__main__":
    main()
