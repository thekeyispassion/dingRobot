"""LLM 客户端 — 调用大模型做意图分类和参数提取"""

import json
import os
import re
import urllib.request
import urllib.error
from interfaces.config import get_config, Config


def _load_prompt(filename: str) -> str:
    """加载 prompts/ 目录下的提示词文件"""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    filepath = os.path.join(base_dir, "prompts", filename)
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    return ""


def _build_messages(user_message: str) -> list[dict]:
    """构建 LLM 消息列表"""
    system_prompt = _load_prompt("system_prompt.md")
    intent_prompt = _load_prompt("intent_classify.md")

    system_content = system_prompt or "你是学院会议室预约助手。"
    if intent_prompt:
        system_content += "\n\n## 意图分类规则\n\n" + intent_prompt

    return [
        {"role": "system", "content": system_content},
        {"role": "user", "content": f"请分析以下用户消息的意图并提取参数：\n\n{user_message}\n\n请以 JSON 格式返回：{{\"intent\": \"...\", \"params\": {{...}}}}"},
    ]


def _call_llm(messages: list[dict], config: Config) -> str:
    """调用 OpenAI 兼容 API"""
    body = json.dumps({
        "model": config.llm_model,
        "messages": messages,
        "temperature": 0.1,
        "max_tokens": 500,
    }).encode("utf-8")

    url = config.llm_base_url.rstrip("/") + "/chat/completions"
    req = urllib.request.Request(url, data=body, headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {config.llm_api_key}",
    })

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"LLM API 调用失败 (HTTP {e.code}): {error_body[:300]}")
    except urllib.error.URLError as e:
        raise RuntimeError(f"LLM API 连接失败: {e.reason}")


def _parse_llm_response(content: str) -> dict:
    """从 LLM 回复中提取 JSON"""
    # 尝试直接解析
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass

    # 尝试从 markdown 代码块中提取
    match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', content, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # 尝试找到 JSON 对象
    match = re.search(r'\{.*\}', content, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    return {"intent": "unknown", "params": {}, "raw": content}


# ============================================================
# 本地关键词降级（LLM 不可用时）
# ============================================================

def _extract_room_name_from_text(text: str) -> str:
    """从文本中提取房间名称"""
    match = re.search(r'[A-Za-z]*\d{3,4}', text)
    if match:
        return match.group(0)
    match = re.search(r'\b(\d{3,4})\b', text)
    if match:
        return match.group(1)
    return None


def _local_classify(text: str) -> dict:
    """基于关键词的本地意图分类（LLM 降级方案）"""
    # 取消
    cancel_keywords = ["取消", "退订", "不要了", "删掉", "撤销"]
    if any(kw in text for kw in cancel_keywords):
        id_match = re.search(r'[iI][dD]\s*[:：]?\s*(\d+)', text)
        id_match2 = re.search(r'预约\s*(\d+)', text)
        rid = int(id_match.group(1)) if id_match else (int(id_match2.group(1)) if id_match2 else None)
        return {"intent": "cancel", "params": {"room_name": _extract_room_name_from_text(text), "reservation_id": rid}}

    # 我的预约
    my_keywords = ["我的预约", "我约了", "我订了", "我的记录", "我有哪些"]
    if any(kw in text for kw in my_keywords):
        return {"intent": "query_my", "params": {}}

    # 预约总览
    overview_keywords = ["预约情况", "占用情况", "都谁约了", "全部预约", "一览", "总览"]
    if any(kw in text for kw in overview_keywords):
        return {"intent": "query_overview", "params": {"room_name": _extract_room_name_from_text(text)}}

    # 查询空闲
    available_keywords = ["空房间", "空闲", "有哪些", "哪些空着", "空的", "可用的"]
    if any(kw in text for kw in available_keywords):
        return {"intent": "query_available", "params": {}}

    # 预约
    book_keywords = ["约", "定", "订", "预约", "帮我", "book", "预定", "预订"]
    if any(kw in text for kw in book_keywords):
        return {"intent": "book", "params": {"room_name": _extract_room_name_from_text(text)}}

    return {"intent": "unknown", "params": {}}


def classify_intent(user_message: str) -> dict:
    """分类用户意图

    优先调用 LLM API，不可用时降级到本地关键词匹配。

    Args:
        user_message: 用户输入的自然语言消息

    Returns:
        {"intent": "book"|"query_available"|"query_overview"|"query_my"|"cancel"|"unknown",
         "params": {...}}
    """
    config = get_config()

    if not config.llm_configured:
        return _local_classify(user_message)

    try:
        messages = _build_messages(user_message)
        response = _call_llm(messages, config)
        result = _parse_llm_response(response)
        # 确保结构正确
        if "intent" not in result:
            result["intent"] = "unknown"
        if "params" not in result:
            result["params"] = {}
        return result
    except Exception:
        # LLM 调用失败 → 降级到本地
        return _local_classify(user_message)
