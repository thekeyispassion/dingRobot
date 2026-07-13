# AI 会议室预约助手

> 一句话，约一间房。不用找管理员，不用填表单，在钉钉群里 @机器人 说句话就行。

基于 OpenClaw 框架的智能会议室预约系统，以钉钉群机器人形态运行。师生通过 @机器人 + 自然语言即可完成会议室查询、预约、取消等操作。

---

## 目录

- [快速开始](#快速开始)
- [部署指南](#部署指南)
  - [本地开发环境](#本地开发环境)
  - [云服务器部署](#云服务器部署)
  - [配置说明](#配置说明)
- [使用指南](#使用指南)
  - [命令行测试模式](#命令行测试模式)
  - [钉钉群使用](#钉钉群使用)
  - [支持的表达方式](#支持的表达方式)
- [项目结构](#项目结构)
- [运行测试](#运行测试)
- [技术架构](#技术架构)

---

## 快速开始

```bash
# 1. 克隆项目
git clone <repo-url> && cd ddtalk

# 2. 创建虚拟环境
python3 -m venv myven && source myven/bin/activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 初始化数据库
python -c "from skills.db_manager import init_db, seed_data; init_db(); seed_data()"

# 5. 配置 LLM（可选，不配也能用本地模式）
cp config.example.yaml config.yaml
vim config.yaml  # 填入 API Key

# 6. 启动命令行测试
python cli/test_shell.py
```

---

## 部署指南

### 本地开发环境

**前置条件：** Python 3.10+

```bash
# 安装依赖
pip install -r requirements.txt

# 初始化数据库（含种子数据：8 个会议室 + 2 条示例预约）
python -c "
from skills.db_manager import init_db, seed_data
init_db()
seed_data()
print('数据库初始化完成')
"
```

**启动命令行交互：**
```bash
python cli/test_shell.py
```

**配置 LLM（可选）：**
```bash
cp config.example.yaml config.yaml
# 编辑 config.yaml，填入你的 API Key
```

不配置 LLM 也能正常运行——系统会自动降级到本地关键词匹配模式。

---

### 云服务器部署

**前置条件：**
- 云服务器（阿里云/腾讯云/百度云均可，2核2G 就够）
- 已安装 OpenClaw（小龙虾 Agent）
- 已安装钉钉通道插件 `@soimy/dingtalk`

**第一步：上传项目代码**
```bash
scp -r ./ddtalk user@your-server-ip:/opt/
```

**第二步：服务器上安装依赖**
```bash
ssh user@your-server-ip
cd /opt/ddtalk
pip install -r requirements.txt
```

**第三步：初始化数据库**
```bash
python -c "from skills.db_manager import init_db, seed_data; init_db(); seed_data()"
```

**第四步：配置 LLM API Key**
```bash
cp config.example.yaml config.yaml
vim config.yaml
```

填写：
```yaml
llm:
  api_key: "sk-xxxxxxxxxxxxx"     # 你的真实 API Key
  base_url: "https://dashscope.aliyuncs.com/compatible-mode/v1"
  model: "qwen-plus"
```

> 支持的 LLM 服务商：阿里云百炼（Qwen）、DeepSeek、以及任何兼容 OpenAI `/v1/chat/completions` 协议的服务。

**第五步：对接 OpenClaw**

将 `skills/` 目录注册为 OpenClaw 的 Skill 目录：
```bash
openclaw skills register /opt/ddtalk/skills
```

将 `prompts/system_prompt.md` 设置为 OpenClaw Agent 的系统提示词：
```bash
openclaw config
# 菜单选择 → Agent → System Prompt → 粘贴 prompts/system_prompt.md 的内容
```

**第六步：对接钉钉机器人**

按 `技术说明.md` 完成钉钉开放平台配置：
1. 创建企业内部机器人应用
2. 获取 Client ID / Client Secret
3. 添加机器人能力（Stream 模式）
4. 开通消息权限
5. 发布应用版本

然后回到 OpenClaw 配置钉钉通道参数：
```bash
openclaw config → Channels → DingTalk
```

**第七步：启动服务**
```bash
pm2 start "openclaw start" --name ddtalk
pm2 save
```

---

### 配置说明

| 配置方式 | 优先级 | 适用场景 |
|---------|--------|---------|
| `config.yaml` | 最高 | 部署环境 |
| 环境变量 | 次高 | CI/CD、Docker |
| 默认值 | 最低 | 本地开发 |

**环境变量：**
```bash
export DDTALK_LLM_KEY="sk-xxx"
export DDTALK_LLM_URL="https://dashscope.aliyuncs.com/compatible-mode/v1"
export DDTALK_LLM_MODEL="qwen-plus"
export DDTALK_DINGTALK_MODE="openclaw"
```

**安全提醒：**
- `config.yaml` 已加入 `.gitignore`，不会被提交
- 不要在代码中硬编码密钥
- 环境变量方式适合 Docker / Systemd 部署

---

## 使用指南

### 命令行测试模式

启动后进入交互界面，模拟钉钉用户对话：

```
==================================================
  AI 会议室预约助手 — 命令行测试模式
==================================================
  LLM 状态: 本地模式（未检测到 LLM API Key）
  当前模拟用户: 张三 (user001)
  输入 'help' 查看帮助, 'quit' 退出
==================================================

[张三] > 帮我约明天下午 330

✅ 预约成功！信电楼330 | 2026-07-15 14:00-18:00 | ID: 1001

[张三] > 我的预约

📋 您当前有 1 个有效预约：
  1. 信电楼330 | 2026-07-15 14:00-18:00 | ID: 1001
如需取消某个预约，请告诉我预约ID。

[张三] > 取消预约 1001

✅ 取消成功！信电楼330 | 2026-07-15 14:00-18:00 | ID: 1001 已取消
```

**CLI 内置命令：**

| 命令 | 功能 |
|------|------|
| `help` | 显示帮助 |
| `users` | 切换模拟用户（张三/李四/王五） |
| `config` | 查看当前配置状态 |
| `quit` | 退出 |

---

### 钉钉群使用

在已接入机器人的钉钉群中，@机器人 即可使用：

#### 1. 预约会议室
```
@预约助手 帮我约明天下午 330
```
→ 返回：预约成功信息（房间、时段、预约ID）

#### 2. 查询空闲房间
```
@预约助手 现在有哪些空房间？
```
→ 返回：当前空闲会议室列表（房间名、容量、设备）

#### 3. 预约总览
```
@预约助手 明天下午各会议室的预约情况
```
→ 返回：所有房间占用/空闲状态一览

#### 4. 冲突推荐
```
@预约助手 明天下午 330
# 假设 330 已被占用
```
→ 返回：330已满，推荐容量相近的替代房间

#### 5. 查询我的预约
```
@预约助手 查看我的预约
```
→ 返回：个人有效预约列表

#### 6. 取消预约
```
@预约助手 取消预约 1001
```
→ 返回：取消确认

---

### 支持的表达方式

#### 时间表达
| 用户说 | 系统解析 |
|--------|---------|
| 明天下午 | 明天 14:00-18:00 |
| 后天上午 | 后天 08:00-12:00 |
| 傍晚 | 今天 18:00-21:00 |
| 下周一 | 下周对应日期的默认时段 |
| 2026-07-20 | 指定日期的默认时段 |

#### 时段映射
| 中文 | 时段 |
|------|------|
| 上午 | 08:00-12:00 |
| 中午 | 12:00-14:00 |
| 下午 | 14:00-18:00 |
| 傍晚 | 18:00-21:00 |
| 晚上 | 19:00-22:00 |

#### 房间名称
- 完整名称：`信电楼330`、`理学院A201`
- 房间号：`330`、`317`
- 系统支持模糊匹配，输入 `330` 可以匹配到 `信电楼330`

---

## 项目结构

```
ddtalk/
├── interfaces/                  # 接口层
│   ├── config.py                #   配置管理（YAML + 环境变量）
│   ├── llm_client.py            #   LLM API 客户端（OpenAI 兼容协议）
│   └── dingtalk_handler.py      #   钉钉消息解析 + 回复格式化
├── skills/                      # 业务逻辑层
│   ├── db_manager.py            #   数据库连接 + 初始化
│   ├── time_parser.py           #   模糊时间 → 标准日期
│   ├── room_query.py            #   空闲查询 + 预约总览
│   ├── booking.py               #   预约 + 冲突检测 + 推荐
│   └── cancellation.py          #   取消预约 + 权限检查
├── prompts/                     # LLM 提示词
│   ├── system_prompt.md         #   系统角色定义
│   ├── intent_classify.md       #   意图分类规则
│   └── response_format.md       #   回复格式模板
├── cli/
│   └── test_shell.py            # 命令行测试入口
├── db/
│   ├── schema.sql               # 建表 SQL
│   └── seed_data.sql            # 测试种子数据（8 个会议室）
├── tests/                       # 测试（91 个用例）
│   ├── test_time_parser.py      #   时间解析（13 tests）
│   ├── test_room_query.py       #   房间查询（7 tests）
│   ├── test_booking.py          #   预约模块（8 tests）
│   ├── test_cancellation.py     #   取消管理（6 tests）
│   ├── test_scenarios.py        #   集成测试（19 tests）
│   ├── test_config.py           #   配置模块（8 tests）
│   ├── test_llm_client.py       #   LLM 客户端（15 tests）
│   └── test_dingtalk_handler.py #   钉钉处理（15 tests）
├── config.example.yaml          # 配置模板（可提交）
├── config.yaml                  # 真实配置（gitignore）
├── requirements.txt             # 依赖（pytest）
├── 项目说明.md                  # 项目流程说明
├── AI 会议室预约助手.md          # 需求文档
├── 技术说明.md                  # OpenClaw + 钉钉部署教程
└── docs/
    └── 开发记录.md              # Vibe Coding 开发记录
```

---

## 运行测试

```bash
# 运行全部测试
python -m pytest tests/ -v

# 运行指定模块测试
python -m pytest tests/test_booking.py -v

# 生成测试报告
python -m pytest tests/ -v --tb=short | tee test_report.txt
```

当前测试：**91 passed，0 failed，100% 通过率**

---

## 技术架构

```
┌─────────────────────────────────────────┐
│              钉钉群 @机器人               │
└────────────────┬────────────────────────┘
                 │
┌────────────────┴────────────────────────┐
│         OpenClaw (小龙虾 Agent)           │
│  ┌──────────┐  ┌──────────┐              │
│  │ 钉钉通道  │  │ LLM 调用  │              │
│  └──────────┘  └──────────┘              │
└────────────────┬────────────────────────┘
                 │
┌────────────────┴────────────────────────┐
│           interfaces/（接口层）           │
│  ┌──────────────┐ ┌──────────────────┐  │
│  │ llm_client   │ │ dingtalk_handler  │  │
│  │ 意图分类     │ │ 消息解析+回复     │  │
│  └──────────────┘ └──────────────────┘  │
└────────────────┬────────────────────────┘
                 │
┌────────────────┴────────────────────────┐
│            skills/（业务逻辑层）          │
│  booking │ query │ cancellation │ time  │
└────────────────┬────────────────────────┘
                 │
┌────────────────┴────────────────────────┐
│            SQLite（数据层）              │
│       rooms 表 + reservations 表         │
└─────────────────────────────────────────┘
```

**数据流：** 用户 @机器人 → OpenClaw 接收 → LLM 意图分类 → 调用 Skill → SQLite 读写 → 结果格式化 → 返回钉钉群

**技术栈：** Python 3.10+ / SQLite / OpenAI 兼容 LLM API / OpenClaw
