---
name: deploy-ai-table
description: Use when deploying to a new channel — creates tables on external platforms (DingTalk AI Table etc.) according to channel-specific configs. Triggers on "deploy AI table", "创建 AI 表格", "初始化钉钉表格".
alwaysActive: true
---

# 通道建表 — 操作手册

## 概述

本地 `data/` markdown 文件是数据主源（git 跟踪，部署即用）。本 Skill 负责在外部通道上创建对应的表结构。

**通用流程 + 通道配置：** SKILL.md 描述标准建表流程，具体字段定义、MCP 工具、创建顺序由各通道配置文件定义。

## 支持的通道

| 通道 | 配置文件 | 用途 |
|------|---------|------|
| 钉钉 AI 表格 | `deploy-ai-table/钉钉AI表格-配置.md` | 在线查看 + 链接分享 |

> 新增通道时，在 `deploy-ai-table/` 下新增配置文件即可。

---

## 工作流

### Step 1: 搜索或创建目标

根据通道配置文件中的「连接方式」，搜索目标是否已存在：

| 搜索结果 | 处理 |
|---------|------|
| 已存在 | 询问用户：清空重建 / 复用已有 / 新建（名称加时间戳后缀） |
| 不存在 | 创建（Base/项目/空间——取决于通道类型） |

### Step 2: 按配置文件创建表

根据配置文件中的「表定义」和「创建顺序」，逐张表创建：

1. 创建 Sheet/Table
2. 按字段列表逐个添加字段（类型、选项、必填）
3. link 字段：确保目标表已先创建

### Step 3: 建表后调整

根据配置文件中的「建表后操作」执行（如调整列顺序）。

### Step 4: 输出结果

```
✅ <通道名> 建表完成

   <目标>: <名称>
   🔗 <链接>

   数据表（N 个）:
     • 表1 — M 字段（备注）
     • 表2 — M 字段（备注）
```

---

## 触发规则

| 场景 | 关键词 | 行为 |
|------|-------|------|
| 新通道部署 | "执行 deploy-ai-table skill"、"创建 AI 表格"、"初始化钉钉表格" | 走完整工作流 |
| 指定通道 | "在钉钉创建表格" | 只走指定通道的配置 |
| 重建 | "重建 AI 表格" | 清空 + 重建 |
