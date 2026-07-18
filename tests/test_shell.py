#!/usr/bin/env python3
"""AI 会议室预约助手 — 命令行测试入口

模拟钉钉群机器人交互：接收自然语言，调用 Skill，返回结果。

注意：本 CLI 仅用于本地开发测试。生产环境中由 OpenClaw AI 读取
SKILL.md 直接理解用户意图并执行 Python 命令，不需本文件中的关键词匹配。
"""

import json
import re
import sys
import os
from datetime import date

# 确保项目根目录在 path 中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from meeting_room.db_manager import init_db, seed_data
from meeting_room.time_parser import parse_fuzzy_datetime
from meeting_room.room_query import query_available, query_today_status, query_day_schedule, get_room_by_name
from meeting_room.booking import book_room, recommend_alternatives
from meeting_room.cancellation import my_reservations, cancel_reservation


# ============================================================
# 关键词意图分类（仅 CLI 测试用，生产环境由 OpenClaw AI 替代）
# ============================================================

def _extract_room_name(text: str) -> str:
    """从文本中提取房间名称"""
    match = re.search(r'[A-Za-z]*\d{3,4}', text)
    if match:
        return match.group(0)
    match = re.search(r'\b(\d{3,4})\b', text)
    if match:
        return match.group(1)
    return None


def classify_intent(text: str) -> dict:
    """基于关键词的简易意图分类

    Returns:
        {"intent": "book"|"query_available"|"today_status"|"day_schedule"|"query_my"|"cancel"|"unknown",
         "params": {"room_name": ..., "reservation_id": ...}}
    """
    # 取消预约
    cancel_keywords = ["取消", "退订", "不要了", "删掉", "撤销"]
    if any(kw in text for kw in cancel_keywords):
        id_match = re.search(r'[iI][dD]\s*[:：]?\s*(\d+)', text)
        id_match2 = re.search(r'预约\s*(\d+)', text)
        rid = int(id_match.group(1)) if id_match else (int(id_match2.group(1)) if id_match2 else None)
        return {"intent": "cancel", "params": {"room_name": _extract_room_name(text), "reservation_id": rid}}

    # 查询我的预约
    my_keywords = ["我的预约", "我约了", "我订了", "我的记录", "我有哪些"]
    if any(kw in text for kw in my_keywords):
        return {"intent": "query_my", "params": {}}

    # 今日实时状态（"现在""今天" + 状态/情况/谁在用）
    today_status_keywords = ["现在谁在", "今天谁在", "当前状态", "现在状态", "在用"]
    if any(kw in text for kw in today_status_keywords):
        return {"intent": "today_status", "params": {}}

    # 某天预约日程（"XX的预约情况""明天谁约了""今天日程"）
    schedule_keywords = ["预约情况", "占用情况", "都谁约了", "全部预约", "一览", "总览", "谁约了", "日程", "预约了"]
    if any(kw in text for kw in schedule_keywords):
        return {"intent": "day_schedule", "params": {}}

    # 查询空闲
    available_keywords = ["空房间", "空闲", "有哪些", "哪些空着", "空的", "可用的"]
    if any(kw in text for kw in available_keywords):
        return {"intent": "query_available", "params": {}}

    # 预约房间
    book_keywords = ["约", "定", "订", "预约", "帮我", "book", "预定", "预订"]
    if any(kw in text for kw in book_keywords):
        return {"intent": "book", "params": {"room_name": _extract_room_name(text)}}

    return {"intent": "unknown", "params": {}}


# ============================================================
# 命令处理
# ============================================================

def handle_command(user_id: str, user_name: str, text: str) -> str:
    """处理用户输入，返回回复文本"""
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
    # today_status 不需要时间参数——它用当前时间
    if intent == "today_status":
        booking_date = date.today().isoformat()
        start_time = ""
        end_time = ""
    else:
        time_info = parse_fuzzy_datetime(text)
        if "error" in time_info:
            if intent in ("query_my", "cancel", "day_schedule"):
                # day_schedule 时间解析失败时默认用今天
                booking_date = date.today().isoformat()
                start_time = ""
                end_time = ""
            else:
                return f"⏰ 时间解析失败：{time_info['error']}\n请尝试更明确的时间表达，如「明天下午」"
        else:
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

    # === 今日实时状态 ===
    if intent == "today_status":
        result = json.loads(query_today_status())
        if result["success"]:
            lines = [f"📋 今日实时状态（{result['current_time']}）：", ""]
            for r in result["rooms"]:
                if r["status"] == "occupied":
                    cur = r["current"]
                    lines.append(f"  🔴 {r['name']}（{r['capacity']}人）— {cur['user_name']} 使用中（{cur['start_time']}-{cur['end_time']}）")
                else:
                    upcoming_str = ""
                    if r["upcoming"]:
                        next_b = r["upcoming"][0]
                        upcoming_str = f"  ⏰ {next_b['start_time']} {next_b['user_name']} 预约"
                    lines.append(f"  🟢 {r['name']}（{r['capacity']}人）— 空闲{upcoming_str}")
            return "\n".join(lines)
        return f"❌ 查询失败：{result.get('message', '未知错误')}"

    # === 某天预约日程 ===
    if intent == "day_schedule":
        result = json.loads(query_day_schedule(booking_date))
        if result["success"]:
            lines = [f"📋 {booking_date} 预约日程（共 {result['total_bookings']} 个预约）：", ""]
            for r in result["rooms"]:
                if r["booking_count"] > 0:
                    lines.append(f"🏢 {r['name']}（{r['capacity']}人）：")
                    for b in r["bookings"]:
                        lines.append(f"  • {b['start_time']}-{b['end_time']}  {b['user_name']}（ID: {b['reservation_id']}）")
                else:
                    lines.append(f"🏢 {r['name']}（{r['capacity']}人）— 全天可约")
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
  • "现在谁在用会议室？"
  • "明天有哪些预约？"
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

3. 今日实时状态
   示例：现在谁在用会议室？
4. 某天预约日程
   示例：明天各会议室的预约情况

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
    print(f"  意图分类: 关键词匹配（生产环境由 OpenClaw AI 替代）")
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
