# AI 会议室预约助手

> 一句话，约一间房。不用找管理员，不用填表单，在钉钉群里 @机器人 说句话就行。

基于 OpenClaw 框架的智能会议室预约系统，以钉钉群机器人形态运行。数据存储在钉钉 AI 表格中，通过 MCP 工具直接读写，无需自建数据库。

---

## 目录

- [项目结构](#项目结构)
- [部署指南](#部署指南)
- [使用指南](#使用指南)
- [技术架构](#技术架构)
- [配置说明](#配置说明)

---

## 项目结构

```
ddtalk/
├── MEMORY.md                    # 身份约束——防注入、必须查数据
├── SOUL.md                      # 说话风格——10 种场景指南
├── meeting_room/                # Skill: 会议室预约（7 个操作）
│   └── SKILL.md                 #   操作手册——MCP 工具操作钉钉 AI 表格
├── room_manager/                # Skill: 会议室管理（5 个操作）
│   └── SKILL.md                 #   三级权限模型 + 协商确认流程
├── manage-admin/                # Skill: 管理员账号管理
│   └── SKILL.md                 #   添加/删除/查看管理员 + 双重匹配校验
└── deploy-ai-table/             # Skill: AI 表格一键部署
    └── SKILL.md                 #   3 张表的结构定义 + 创建流程
```

**三个 Skill 的分工：**

| Skill | 用途 | 谁用 |
|-------|------|------|
| `deploy-ai-table` | 一键创建钉钉 AI 表格（Base + 3 张 Sheet） | 部署时执行一次 |
| `meeting_room` | 查询空闲、预约、取消、日程查看 | 所有人 |
| `room_manager` | 添加/修改/停用/启用会议室 | 分三级权限 |
| `manage-admin` | 添加/删除/查看管理员 | 管理员专用 |

---

## 部署指南

### 前置条件

- 云服务器（已安装 OpenClaw + 钉钉通道插件 `@soimy/dingtalk`）
- 钉钉企业内部机器人应用（已获取 Client ID / Client Secret）
- 两个钉钉 MCP 已配置（在 [AI Hub](https://aihub.dingtalk.com/#/mcp) 找到并配置，OpenClaw 自动完成连接）：

| MCP | 用途 |
|-----|------|
| 钉钉 AI 表格 | 数据存储——读写会议室信息、预约记录、管理员 |
| 钉钉通讯录 | 管理员管理——用户名→userId 解析 |

### 第一步：上传项目代码

```bash
scp -r ./ddtalk user@your-server-ip:/opt/ding-room
```

### 第二步：配置 OpenClaw

> 以下配置方法来自 OpenClaw 阿里一体机云服务器部署实践。推荐用 Python 脚本操作配置文件（避免 JSON 格式问题）。

#### 2.1 添加 MCP 服务器

在 `~/.openclaw/openclaw.json` 中添加 `mcp.servers`：

```json5
{
  mcp: {
    servers: {
      "dingtalk-ai-table": {
        type: "url",
        transport: "streamable-http",    // ← 必须！钉钉 MCP 不支持 SSE
        url: "https://mcp-gw.dingtalk.com/server/<你的AI表格MCP地址>",
      },
      "dingtalk-contact": {
        type: "url",
        transport: "streamable-http",
        url: "https://mcp-gw.dingtalk.com/server/<你的通讯录MCP地址>",
      },
    },
  },
}
```

> ⚠️ **传输协议坑：** 钉钉 MCP Server 使用 `streamable-http` 协议，不是默认的 SSE。不加 `transport` 字段会报 405 错误。

#### 2.2 添加 ding-room Agent 和路由

```json5
{
  agents: {
    list: [
      { id: "main", /* 原有配置 */ },
      {
        id: "ding-room",
        workspace: "/opt/ding-room",
        identity: { name: "会议室预约助手", emoji: "🏢" },
      },
    ],
  },
  // 路由用顶层 bindings，不是 routing 或 routing.rules
  bindings: [
    {
      type: "route",
      agentId: "ding-room",
      match: { channel: "dingtalk-connector" },  // 匹配所有钉钉流量
    },
  ],
}
```

> ⚠️ **路由字段坑：** 多 agent 路由使用顶层 `bindings` 字段，而不是 `routing.rules`。`match` 中 `peer.kind` 可选（`group`/`direct`），但不传 id 可能校验失败，直接用 `channel` 匹配即可。

> ⚠️ **last-good 覆盖坑：** `openclaw doctor --fix` 会自动恢复配置到上一个通过校验的版本。每次改配置后，同步更新 `~/.openclaw/openclaw.json.last-good` 文件，否则重启后改动丢失。

> ⚠️ **JSON 格式坑：** 不要用文本编辑器直接写入包含特殊字符（如 `…` 省略号）的配置。始终用 Python `json.dump()` 等工具确保输出严格合法的 JSON。

#### 2.3 验证配置并重启

```bash
# 验证配置
openclaw config validate

# 同时更新 last-good，防止 doctor 回滚
cp ~/.openclaw/openclaw.json ~/.openclaw/openclaw.json.last-good

# 重启 gateway
systemctl --user restart openclaw-gateway

# 确认 MCP 连接
openclaw mcp probe dingtalk-ai-table
openclaw mcp probe dingtalk-contact
```

MEMORY.md、SOUL.md 放在 workspace 根目录会自动加载；SKILL.md **必须放在 `skills/` 子目录下**才能被自动发现。
校验Agent 启动时是否加载：

- `MEMORY.md` → 身份约束（"你是会议室助手，必须查数据"）
- `SOUL.md` → 说话风格
- 4 个 SKILL.md → 技能（meeting_room / room_manager / manage-admin / deploy-ai-table）

### 第三步：创建钉钉 AI 表格

检查 Base 是否已存在：

```bash
curl -s -X POST "<你的AI表格MCP地址>" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"list_bases","arguments":{}}}'
```

如果返回中已有「AI会议室预约助手」，确认表结构一致即可直接使用。

如果不存在，在 OpenClaw 中对 agent 说：

> 执行 deploy-ai-table skill

Agent 会自动在钉钉中创建 Base「AI会议室预约助手」和 3 张数据表（会议室信息、预约记录、管理员）。

### 第四步：配置钉钉通道

```bash
openclaw config → Channels → DingTalk
# Agent 字段填入: ding-room
# 钉钉群消息自动路由到会议室助手
```

### 第五步：启动服务

```bash
systemctl --user restart openclaw-gateway
openclaw status  # 确认: Agents=2, DingTalk=OK
```

---

## 使用指南

在钉钉群中 @机器人 即可使用：

### 预约会议室
```
@预约助手 帮我约明天下午 330
```
→ 返回预约成功信息（房间、时段、记录 ID）。如冲突则推荐替代房间。

### 查询空闲房间
```
@预约助手 现在有哪些空房间？
```
→ 按楼栋分组，显示房间名、容量、设备。

### 今日实时状态
```
@预约助手 现在谁在用会议室？
```
→ 标注每个房间「使用中」还是「空闲」，显示当前使用者和后续预约。

### 预约日程
```
@预约助手 明天有哪些预约？
```
→ 按房间列出全天预约时间线，无预约的房间标注「全天可约」。

### 我的预约
```
@预约助手 查看我的预约
```

### 取消预约
```
@预约助手 取消预约 <记录ID>
```

### 管理会议室
```
@预约助手 添加一间会议室：理学院C502，容量40人，设备是投影仪和白板
@预约助手 把信电楼330的容量改成50人
@预约助手 停用信电楼108          # 任何人可触发，自动协商受影响用户
@预约助手 重新启用信电楼108       # 任何人可操作
```

### 管理管理员
```
@预约助手 把张三加为管理员         # 自动通过通讯录解析userId
@预约助手 把李四从管理员移除
@预约助手 有哪些管理员
```

### 支持的表达方式

**时间表达：**

| 用户说 | 系统解析 |
|--------|---------|
| 明天下午 | 明天 14:00-18:00 |
| 后天上午 | 后天 08:00-12:00 |
| 傍晚 | 今天 18:00-21:00 |
| 下周一 | 下周对应日期 |

**时段映射：**

| 中文 | 时段 |
|------|------|
| 上午 | 08:00-12:00 |
| 中午 | 12:00-14:00 |
| 下午 | 14:00-18:00 |
| 傍晚 | 18:00-21:00 |
| 晚上 | 19:00-22:00 |

**房间名称：** 支持完整名称（信电楼330）和房间号（330）模糊匹配。

---

## 技术架构

```
┌─────────────────────────────────────────┐
│              钉钉群 @机器人               │
└────────────────┬────────────────────────┘
                 │
┌────────────────┴────────────────────────┐
│         OpenClaw (小龙虾 Agent)           │
│  ┌──────────────────────────────────┐   │
│  │ AI 读取 SKILL.md → 理解意图       │   │
│  │ → 调用 MCP 工具操作钉钉 AI 表格   │   │
│  └──────────────────────────────────┘   │
└────────────────┬────────────────────────┘
                 │  MCP (Streamable HTTP)
         ┌───────┴───────┐
         v               v
┌─────────────────┐ ┌─────────────────┐
│ 钉钉 AI 表格     │ │ 钉钉通讯录       │
│ (数据存储)       │ │ (用户→userId)   │
│                 │ │                 │
│ 会议室信息       │ │ 姓名搜索        │
│ 预约记录         │ │ userId查询      │
│ 管理员           │ │                 │
└─────────────────┘ └─────────────────┘
```

**数据流：** 用户 @机器人 → OpenClaw AI 读 SKILL.md 理解意图 → 通过 MCP 工具读写钉钉 AI 表格 → AI 按 SOUL.md 的风格格式化 → 回复钉钉群

**技术栈：** OpenClaw / 钉钉 AI 表格 / MCP / 钉钉机器人

---

## 配置说明

### 三层配置文件

| 文件 | 大小 | 职责 | 被截风险 |
|------|------|------|---------|
| `MEMORY.md` | ~40 行 | 身份定义 + 核心约束（"你是会议室助手，必须查数据"） | 几乎为零 |
| `SOUL.md` | ~60 行 | 说话风格（10 种场景指南 + emoji 规范） | 低 |
| `SKILL.md` ×4 | ~600 行 | 工具手册（操作步骤 + 表结构 + 权限规则） | 中 |

**为什么拆成多个文件？**

1. **上下文超限安全** — 会话长了 SKILL.md 可能被截断，但 MEMORY.md 只有几十行，几乎不会被截。即使忘了怎么操作，至少知道不能编造数据
2. **身份持久性** — MEMORY.md 定义"你是谁"，跨会话生效；SKILL.md 只是"工具说明书"
3. **关注点分离** — 改说话风格只改 SOUL.md，改操作只改 SKILL.md，互不干扰

---

## 常见部署问题

> 以下排障经验来自 OpenClaw 阿里一体机云服务器部署实践。

### ❌ MCP probe 报 405

**现象：** `openclaw mcp probe` 返回 `Non-200 status code (405)`

**原因：** 钉钉 MCP Server 使用 Streamable HTTP 协议，不是默认的 SSE。

**修复：** 在 `openclaw.json` 的 MCP 配置中加 `transport` 字段：

```json5
{
  mcp: {
    servers: {
      "dingtalk-ai-table": {
        type: "url",
        transport: "streamable-http",   // ← 加这一行
        url: "...",
      },
    },
  },
}
```

### ❌ 配置改完重启后丢失

**现象：** 手动编辑 `openclaw.json` 后重启，改动不见了

**原因：** `openclaw doctor --fix` 或 gateway 重启时检测到校验失败，自动从 `openclaw.json.last-good` 恢复

**修复：** 改完配置后同步更新 last-good：

```bash
# 1. 确认配置校验通过
openclaw config validate

# 2. 同步更新 last-good
cp ~/.openclaw/openclaw.json ~/.openclaw/openclaw.json.last-good

# 3. 再重启
systemctl --user restart openclaw-gateway
```

### ❌ 配置报 "Invalid input" 但没有具体字段

**现象：** `openclaw config validate` 只返回 `<root>: Invalid input`

**常见原因与修复：**

| 原因 | 修复 |
|------|------|
| 用了 `routing.rules` | 改为顶层 `bindings`（见第二步配置说明） |
| 使用了旧版 JSON 结构 | 先跑一次 `openclaw doctor --fix` 让工具自动格式化为新版 |
| MCP URL 包含特殊字符 | 用 Python `json.dump()` 写入，不要手动编辑 |

### ❌ 新增 agent 后 DingTalk 消息仍然路由到 main

**现象：** 钉钉消息没有走 ding-room agent，还是 main 在处理

**原因：** 没有添加 `bindings` 路由规则，或 `bindings` 里 `agentId` 拼写错误

**检查：**

```bash
# 确认 agent 存在
openclaw config get agents.list

# 确认绑定已生效
openclaw config get bindings
```

### ❌ MCP 工具能探到但 agent 调用时报错

**现象：** `openclaw mcp probe` 成功，但 agent 说找不到 MCP 工具

**修复：**

```bash
# 重载 MCP 运行时缓存
openclaw mcp reload

# 如果还不行，重启 gateway
systemctl --user restart openclaw-gateway
```
