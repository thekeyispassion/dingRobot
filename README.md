# AI 会议室预约助手

> 一句话，约一间房。不用找管理员，不用填表单，在钉钉群里 @机器人 说句话就行。

基于 OpenClaw 框架的智能会议室预约系统，以钉钉群机器人形态运行。师生通过 @机器人 + 自然语言即可完成会议室查询、预约、取消等操作。

---

## 目录

- [快速开始](#快速开始)
- [部署指南](#部署指南)
  - [本地开发环境](#本地开发环境)
  - [云服务器部署](#云服务器部署)
- [使用指南](#使用指南)
  - [命令行测试模式](#命令行测试模式)
  - [钉钉群使用](#钉钉群使用)
  - [支持的表达方式](#支持的表达方式)
- [项目结构](#项目结构)
- [运行测试](#运行测试)
- [技术架构](#技术架构)
- [OpenClaw 配置说明](#openclaw-配置说明)

---

## 快速开始

```bash
# 1. 克隆项目
git clone <repo-url> && cd ddtalk

# 2. 创建虚拟环境
python3 -m venv myven && source myven/bin/activate

# 3. 安装依赖
pip install -r requirements-dev.txt  # 仅开发测试需要

# 4. 启动命令行测试
python tests/test_shell.py
```

---

## 部署指南

### 本地开发环境

**前置条件：** Python 3.10+

```bash
# 安装依赖
pip install -r requirements-dev.txt  # 仅开发测试需要

# 初始化数据库（含种子数据：8 个会议室 + 2 条示例预约）
python -c "
from meeting_room.db_manager import init_db, seed_data
init_db()
seed_data()
print('数据库初始化完成')
"
```

**启动命令行交互：**
```bash
python tests/test_shell.py
```


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
cd /opt/ding-robot
# 生产环境无需安装任何依赖——项目仅使用 Python 标准库
```

**第三步：初始化数据库**
```bash
python -c "from meeting_room.db_manager import init_db, seed_data; init_db(); seed_data()"
```

**第四步：注册 Skill 到 OpenClaw**

项目根目录的 `SKILL.md` 是 OpenClaw 技能的"说明书"——它告诉 OpenClaw 的 AI：

- 有哪些操作可用（查询空闲、预约、取消、总览、个人查询、时间解析）
- 每个操作对应的 Python 命令（精确到参数）
- 学院有哪些会议室（容量、设备）
- 回复风格和注意事项

**注册方式：** 将项目目录软链接到 OpenClaw 的 skills 目录：

```bash
ln -s /opt/ding-robot/meeting_room /home/user/.openclaw/workspace/skills/meeting-room
openclaw skills reload
```

OpenClaw 启动后会自动读取 `SKILL.md`。之后用户在钉钉群 @机器人 时：

```
用户: @机器人 帮我约明天下午 330
       ↓
OpenClaw AI 读取 SKILL.md → 理解意图 → 判断需要"预约会议室"
       ↓
执行: cd /opt/ding-robot && python -c "from meeting_room.booking import book_room; ..."
       ↓
返回 JSON 结果 → AI 根据 SKILL.md 的回复风格格式化 → 回复钉钉群
```

> **注意：** OpenClaw 的 AI 本身就是最强的意图理解器——它读取 SKILL.md 后直接判断用户意图并执行对应命令，不需要项目里再调一个外部 LLM 做意图分类。CLI 测试模式下使用内置关键词匹配作为简易替代。

**第五步：对接钉钉机器人**

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

**第六步：启动服务**
```bash
pm2 start "openclaw start" --name ddtalk
pm2 save
```

---

## 使用指南

### 命令行测试模式

启动后进入交互界面，模拟钉钉用户对话：

```
==================================================
  AI 会议室预约助手 — 命令行测试模式
==================================================
  意图分类: 关键词匹配（生产环境由 OpenClaw AI 替代）
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
├── meeting_room/                # 会议室预约 Skill
│   ├── SKILL.md                 #   工具手册——7 个操作的命令+参数+返回值
│   ├── SOUL.md                  #   说话风格——10 种场景指南+emoji 规范
│   ├── MEMORY.md                #   身份约束——防注入、必须查数据库
│   ├── db_manager.py            #   数据库连接 + 初始化
│   ├── time_parser.py           #   模糊时间 → 标准日期
│   ├── room_query.py            #   空闲查询 + 今日状态 + 日程
│   ├── booking.py               #   预约 + 冲突检测 + 推荐
│   └── cancellation.py          #   取消预约 + 权限检查
├── tests/                       # 测试 + CLI + 验证（57 个用例）
│   ├── test_shell.py            #   命令行测试入口
│   ├── verify.py                #   一键验证脚本
│   ├── test_time_parser.py      #   时间解析（13 tests）
│   ├── test_room_query.py       #   房间查询（11 tests）
│   ├── test_booking.py          #   预约模块（8 tests）
│   ├── test_cancellation.py     #   取消管理（6 tests）
│   └── test_scenarios.py        #   集成测试（19 tests）
├── db/
│   ├── schema.sql               # 建表 SQL
│   └── seed_data.sql            # 测试种子数据（8 个会议室）
├── requirements.txt             # 生产依赖（无，纯标准库）
└── requirements-dev.txt         # 开发依赖（pytest）
```

---

## 运行测试

### 一键验证

```bash
python tests/verify.py
```

运行 4 层检验：数据库初始化 → 自动化测试 → CLI 功能测试 → LLM 配置检查。

### 手动运行

```bash
# 运行全部测试
python -m pytest tests/ -v

# 运行指定模块
python -m pytest tests/test_booking.py -v

# 生成测试报告
python -m pytest tests/ -v --tb=short | tee test_report.txt
```

### 测试模块说明

当前共 **57 个测试用例，100% 通过率**，按模块分布：

#### 业务逻辑层测试

| 模块 | 文件 | 用例数 | 测试内容 |
|------|------|--------|---------|
| 时间解析 | `test_time_parser.py` | 13 | 时段映射、今天/明天/后天、上午/下午/傍晚、下周一、空输入、乱码输入、房间号干扰 |
| 房间查询 | `test_room_query.py` | 11 | 空闲查询（空时段/冲突/重叠/边界）、今日实时状态（当前占用+后续预约）、预约日程（时间线+空日）、模糊查找房间 |
| 预约核心 | `test_booking.py` | 8 | 正常预约、冲突检测+推荐、不存在房间、过去日期、时间倒置、相邻时段不互斥、推荐排序、全部满房 |
| 取消管理 | `test_cancellation.py` | 6 | 查我的预约、无预约用户、取消自己的、取消别人的（权限拒绝）、取消不存在的、重复取消 |
| 集成测试 | `test_scenarios.py` | 19 | TC01-TC19：端到端覆盖基础预约(3)、空闲查询(2)、总览(1)、模糊时间(3)、冲突推荐(2)、个人管理(3)、边界情况(3)、额外边界(2) |

#### 测试命名规范

所有集成测试使用 TC 编号（TC01-TC19），方法名包含编号和场景描述，方便在测试报告中快速定位：

```
tests/test_scenarios.py::TestBasicBooking::test_tc01_book_available_room_success
tests/test_scenarios.py::TestBoundaryCases::test_tc17_reverse_time_range
```

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
│  │ → 直接执行 Python 命令            │   │
│  └──────────────────────────────────┘   │
└────────────────┬────────────────────────┘
                 │
┌────────────────┴────────────────────────┐
│            meeting_room/（业务逻辑层）          │
│  booking │ query │ cancellation │ time  │
└────────────────┬────────────────────────┘
                 │
┌────────────────┴────────────────────────┐
│            SQLite（数据层）              │
│       rooms 表 + reservations 表         │
└─────────────────────────────────────────┘
```

**OpenClaw 配置：** MEMORY.md（身份约束，永不丢失）→ SOUL.md（说话风格）→ SKILL.md（工具手册）。越核心越小，越不易被截断。

**数据流：** 用户 @机器人 → OpenClaw AI 读 SKILL.md 理解意图 → 直接执行 Python 命令 → Skill 操作 SQLite → JSON 结果 → AI 格式化 → 返回钉钉群

**技术栈：** Python 3.10+ / SQLite / OpenClaw / 钉钉机器人

---

## OpenClaw 配置说明

项目使用三层文件配置 OpenClaw，各司其职：

| 文件 | 大小 | 职责 | 被截风险 |
|------|------|------|---------|
| `MEMORY.md` | ~40 行 | 身份定义 + 核心约束（"你是会议室助手，必须查数据库"） | 几乎为零 |
| `SOUL.md` | ~60 行 | 说话风格（10 种场景指南 + 回复语气 + emoji 规范） | 低 |
| `SKILL.md` | ~110 行 | 工具手册（7 个操作的命令模板 + 参数 + 返回值） | 中 |

**为什么拆成三个文件？**

1. **上下文超限安全** — 会话长了 SKILL.md 可能被截断，但 MEMORY.md 只有几行，几乎不会被截。即使忘了怎么操作，至少知道不能编造数据
2. **身份持久性** — MEMORY.md 定义"你是谁"，跨会话生效；SKILL.md 只是"工具说明书"
3. **关注点分离** — 改说话风格只改 SOUL.md，改命令只改 SKILL.md，互不干扰

**部署：** 三个文件放在项目根目录，OpenClaw 自动加载。软链接到 skills 目录后即可使用：

```bash
ln -s /opt/ding-robot/meeting_room ~/.openclaw/workspace/skills/meeting-room
openclaw skills reload
```
