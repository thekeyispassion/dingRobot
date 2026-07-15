#!/usr/bin/env python3
"""AI 会议室预约助手 — 一键验证脚本

验证层次：
  L1: 数据库初始化 + 种子数据
  L2: 全部单元测试（53 个）
  L3: CLI 功能测试

用法: python verify.py
"""

import subprocess
import sys
import os
import json

GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
BOLD = "\033[1m"
RESET = "\033[0m"

passed_total = 0
failed_total = 0


def banner(text: str):
    print(f"\n{BOLD}{'='*60}{RESET}")
    print(f"{BOLD}  {text}{RESET}")
    print(f"{BOLD}{'='*60}{RESET}\n")


def check(label: str, success: bool, detail: str = ""):
    global passed_total, failed_total
    marker = f"{GREEN}✅{RESET}" if success else f"{RED}❌{RESET}"
    print(f"  {marker} {label}")
    if detail:
        print(f"     {detail}")
    if success:
        passed_total += 1
    else:
        failed_total += 1
    return success


# ============================================================
# Layer 1: 数据库初始化
# ============================================================

def test_layer1_db():
    banner("Layer 1: 数据库初始化 + 种子数据")

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from skills.db_manager import init_db, seed_data, get_connection

    test_db = "db/_verify_test.db"
    if os.path.exists(test_db):
        os.remove(test_db)

    try:
        init_db(test_db)
        seed_data(test_db)

        conn = get_connection(test_db)
        room_count = conn.execute("SELECT COUNT(*) FROM rooms").fetchone()[0]
        res_count = conn.execute("SELECT COUNT(*) FROM reservations").fetchone()[0]

        # 验证表结构：直接查数据验证列存在
        room = conn.execute("SELECT id, name, building, floor, capacity FROM rooms LIMIT 1").fetchone()
        res = conn.execute("SELECT id, room_id, user_id, user_name, date, start_time, end_time FROM reservations LIMIT 1").fetchone()

        # 验证索引
        indexes = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='index'").fetchall()]
        conn.close()

        check("rooms 表建表成功 (字段 id/name/building/capacity)", room is not None)
        check("reservations 表建表成功 (字段 room_id/user_id/date)", res is not None)
        check("外键索引已创建", any("reservations" in idx for idx in indexes))
        check(f"种子数据: 8 个会议室", room_count == 8, f"实际: {room_count}")
        check(f"种子数据: 2 条示例预约", res_count == 2, f"实际: {res_count}")

        # 验证数据完整性
        conn = get_connection(test_db)
        room330 = conn.execute("SELECT * FROM rooms WHERE name = '信电楼330'").fetchone()
        conn.close()
        check("信电楼330 数据完整", room330 is not None and room330["capacity"] == 30)

        os.remove(test_db)
        return True
    except Exception as e:
        check("数据库初始化", False, str(e))
        if os.path.exists(test_db):
            os.remove(test_db)
        return False


# ============================================================
# Layer 2: 单元测试
# ============================================================

def test_layer2_pytest():
    banner("Layer 2: 自动化测试")

    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "-v", "--tb=line"],
        capture_output=True, text=True, timeout=120
    )

    # 解析输出
    lines = result.stdout.split("\n")
    test_results = []
    for line in lines:
        if "PASSED" in line and "::" in line:
            test_results.append(("pass", line.strip()))
        elif "FAILED" in line and "::" in line:
            test_results.append(("fail", line.strip()))

    passed = sum(1 for t in test_results if t[0] == "pass")
    failed = sum(1 for t in test_results if t[0] == "fail")

    # 按模块分组统计
    modules = {}
    for status, line in test_results:
        # 提取模块名
        parts = line.split("::")[0].replace("tests/", "")
        module = parts.split("/")[0].replace("test_", "").replace(".py", "")
        modules.setdefault(module, {"pass": 0, "fail": 0})
        modules[module][status] += 1

    for module, counts in sorted(modules.items()):
        total = counts["pass"] + counts["fail"]
        label = f"{module} ({total} tests)"
        check(label, counts["fail"] == 0, f"{counts['pass']} passed")

    check(f"总计: {passed}/{passed+failed} passed", failed == 0)

    if failed > 0:
        print(f"\n{YELLOW}  失败的测试:{RESET}")
        for status, line in test_results:
            if status == "fail":
                print(f"    {RED}✗{RESET} {line.split(' ')[0]}")

    return failed == 0


# ============================================================
# Layer 3: CLI 功能测试
# ============================================================

def test_layer3_cli():
    banner("Layer 3: CLI 功能测试")

    # 每次测试前重置数据库，确保测试隔离
    def _reset_db():
        db_file = "db/meeting_rooms.db"
        if os.path.exists(db_file):
            os.remove(db_file)
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from skills.db_manager import init_db, seed_data
        init_db(db_file)
        seed_data(db_file)

    # Test 1: CLI 启动
    _reset_db()
    result = subprocess.run(
        [sys.executable, "cli/test_shell.py"], input="quit\n",
        capture_output=True, text=True, timeout=30
    )
    check("CLI 启动正常", "AI 会议室预约助手" in result.stdout)
    check("CLI 退出正常", "再见" in result.stdout)

    # Test 2: 帮助命令
    _reset_db()
    result = subprocess.run(
        [sys.executable, "cli/test_shell.py"], input="help\nquit\n",
        capture_output=True, text=True, timeout=30
    )
    check("help 命令", "使用帮助" in result.stdout)

    # Test 3: 预约功能
    _reset_db()
    result = subprocess.run(
        [sys.executable, "cli/test_shell.py"],
        input="帮我约明天下午 317\nquit\n",
        capture_output=True, text=True, timeout=30
    )
    check("预约房间", "317" in result.stdout and ("成功" in result.stdout or "ID:" in result.stdout))

    # Test 4: 查询空闲
    _reset_db()
    result = subprocess.run(
        [sys.executable, "cli/test_shell.py"],
        input="明天下午有哪些空房间？\nquit\n",
        capture_output=True, text=True, timeout=30
    )
    check("查询空闲房间", "空闲" in result.stdout and "信电楼" in result.stdout)

    # Test 5: 我的预约
    _reset_db()
    result = subprocess.run(
        [sys.executable, "cli/test_shell.py"],
        input="我的预约\nquit\n",
        capture_output=True, text=True, timeout=30
    )
    check("查询我的预约", "预约" in result.stdout)

    # Test 6: 预约总览
    _reset_db()
    result = subprocess.run(
        [sys.executable, "cli/test_shell.py"],
        input="明天下午各会议室的预约情况\nquit\n",
        capture_output=True, text=True, timeout=30
    )
    check("预约总览", "预约" in result.stdout and ("空闲" in result.stdout or "占用" in result.stdout))

    return True


# ============================================================
# Layer 4: LLM 配置检查（信息展示）
# ============================================================

def test_layer4_info():
    banner("Layer 4: 架构说明")

    print(f"  💡 本项目为 OpenClaw Skill——生产环境中：")
    print(f"     1. OpenClaw AI 读取 SKILL.md 获取操作指南")
    print(f"     2. AI 直接理解用户意图，执行 Python 命令操作数据库")
    print(f"     3. 不需要项目内再调用外部 LLM 做意图分类")
    print()
    print(f"  🧪 CLI 测试模式使用内置关键词匹配作为简易替代")
    print(f"     启动: python cli/test_shell.py")
    print()
    print(f"  📋 部署到 OpenClaw：")
    print(f"     ln -s $(pwd) ~/.openclaw/workspace/skills/meeting-room")
    print(f"     openclaw skills reload")


# ============================================================
# 主流程
# ============================================================

def main():
    global passed_total, failed_total

    print(f"\n{BOLD}{GREEN}🔍 AI 会议室预约助手 — 一键验证{RESET}\n")
    print(f"  Python: {sys.version.split()[0]}")
    print(f"  工作目录: {os.getcwd()}")

    # 清理上次验证残留的数据库
    for f in ["db/_verify_test.db", "db/meeting_rooms.db"]:
        if os.path.exists(f) and "_verify" in f:
            os.remove(f)

    test_layer1_db()
    test_layer2_pytest()
    test_layer3_cli()
    test_layer4_info()

    # 清理
    for f in ["db/_verify_test.db"]:
        if os.path.exists(f):
            os.remove(f)

    # 最终结果
    banner("验证结果")
    total = passed_total + failed_total
    if failed_total == 0:
        print(f"  {GREEN}{BOLD}🎉 全部通过！{passed_total}/{total} 项检查通过{RESET}")
        print()
        print(f"  {BOLD}下一步:{RESET}")
        print(f"  1. 本地测试: python cli/test_shell.py")
        print(f"  2. 部署 OpenClaw: ln -s $(pwd) ~/.openclaw/workspace/skills/meeting-room")
        print(f"  3. 参考 README.md 部署指南完成钉钉机器人接入")
    else:
        print(f"  {RED}{BOLD}⚠️  {failed_total}/{total} 项检查失败，请检查上方红色标记{RESET}")

    print()
    return 0 if failed_total == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
