# AI 会议室预约助手 — 接口层设计文档

**日期：** 2026-07-14  
**版本：** v2.0（在 v1.0 基础上补充接口层）  

---

## 一、背景

v1.0 完成了 Skills 业务逻辑层（数据库、房间查询、预约、取消）和 CLI 测试入口。但存在两个问题：

1. **LLM API 调用缺失** — 意图分类靠硬编码关键词，没有真正调用大模型
2. **钉钉接口缺失** — 用户身份是 Mock 的，消息收发没有对接真实钉钉
3. **隐私风险** — API Key 等敏感配置没有管理方案

本次补充 `interfaces/` 层，把上述职责从 CLI 中独立出来。

---

## 二、架构

```
cli/test_shell.py          ← 测试入口（调用接口层）
       │
┌──────┴──────────────┐
│  interfaces/         │
│  ├── config.py       │  ← 配置加载（config.yaml → 环境变量）
│  ├── llm_client.py   │  ← LLM API 调用（OpenAI 兼容协议）
│  └── dingtalk_handler│  ← 钉钉消息解析 + 回复格式化
└──────┬──────────────┘
       │
┌──────┴──────┐
│  skills/    │  ← 业务逻辑（不动）
└─────────────┘
```

---

## 三、模块设计

### 3.1 config.py

- `Config` 数据类，字段：
  - `llm_api_key: str` — API 密钥
  - `llm_base_url: str` — API 端点（默认 `https://dashscope.aliyuncs.com/compatible-mode/v1`）
  - `llm_model: str` — 模型名（默认 `qwen-plus`）
  - `dingtalk_mode: str` — `"openclaw"` 或 `"standalone"`
- `load_config() -> Config` — 加载顺序：config.yaml > 环境变量 > 默认值
- `mask_key(key: str) -> str` — 脱敏输出（日志安全）

### 3.2 llm_client.py

- `classify_intent(user_message: str) -> dict`
  - 返回 `{"intent": "book"|"query_available"|..., "params": {...}}`
  - 有 API Key → 调 OpenAI 兼容 `/v1/chat/completions`
  - 无 API Key → 降级到本地 `_local_classify()`（关键词匹配）
- `_build_messages(user_message: str) -> list` — 拼接 system + intent prompt
- `_parse_llm_response(content: str) -> dict` — 解析 JSON 回复
- `_local_classify(text: str) -> dict` — 备用关键词分类

### 3.3 dingtalk_handler.py

- `parse_incoming(payload: dict) -> dict`
  - 输入：OpenClaw 转发的消息体
  - 输出：`{"user_id": "...", "user_name": "...", "message": "..."}`
  - 兼容两种模式：OpenClaw 标准格式 / 钉钉原始 webhook 格式
- `format_response(skill_result: dict) -> str`
  - 输入：Skill 返回的 JSON
  - 输出：适合钉钉群聊展示的文本

### 3.4 config.example.yaml

```yaml
# AI 会议室预约助手 — 配置模板
# 复制为 config.yaml 后填入真实值

llm:
  api_key: "your-api-key-here"
  base_url: "https://dashscope.aliyuncs.com/compatible-mode/v1"
  model: "qwen-plus"

dingtalk:
  mode: "openclaw"  # openclaw | standalone
```

---

## 四、隐私安全

| 文件 | 处理 |
|------|------|
| `config.yaml` | `.gitignore` 已添加 |
| `config.example.yaml` | 仅含占位符，可安全提交 |
| `DDTALK_LLM_KEY` 等环境变量 | 代码支持，优先级低于 config.yaml |
| `*.db` | `.gitignore` 已有 |

---

## 五、测试

- `tests/test_config.py` — 配置加载、脱敏、环境变量回退
- `tests/test_llm_client.py` — 本地降级分类、消息构建
- `tests/test_dingtalk_handler.py` — 消息解析、回复格式化
