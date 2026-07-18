---
name: room-manager
description: 会议室管理——管理员专用。添加、修改、停用/启用会议室。所有操作需管理员权限。
alwaysActive: true
---

# 会议室管理 — 操作手册

## 权限

本技能的所有操作**仅限管理员**使用。每次操作前脚本会自动校验 `admins` 表——非管理员用户会收到权限拒绝提示。

## 环境信息

- 项目根目录: `/opt/ding-robot`
- 数据库路径: `/opt/ding-robot/db/meeting_rooms.db`
- 所有命令从项目根目录执行: `cd /opt/ding-robot`

## 触发规则

| 场景 | 关键词/意图 | 执行操作 |
|------|------------|---------|
| 查看所有会议室 | 全部会议室、列出房间、房间列表、有哪些房间 | `list_rooms` |
| 添加会议室 | 添加、新增、加一间、增加 | `add_room` |
| 修改会议室 | 修改、改一下、更新、调整 | `update_room` |
| 停用会议室 | 停用、禁用、关闭、暂停使用 | `disable_room` |
| 启用会议室 | 启用、恢复、重新开放 | `enable_room` |

> 用户说"修改330"但没有说改什么时，先列出该房间当前信息，再追问具体要改什么。

---

## 可用操作

### 1. 列出所有会议室

```bash
cd /opt/ding-robot && python -c "
import json
from room_manager.room_crud import list_rooms
print(list_rooms())
"
```

**返回：** `{"success": true, "rooms": [{"id": 1, "name": "信电楼330", "building": "信电楼", "floor": 3, "capacity": 30, "facilities": "投影仪,白板,视频会议", "status": "available", "description": "中型会议室"}, ...], "count": 8}`

### 2. 添加会议室

```bash
cd /opt/ding-robot && python -c "
import json
from room_manager.room_crud import add_room
print(add_room('USER_ID', 'NAME', 'BUILDING', FLOOR, CAPACITY, 'FACILITIES', 'DESCRIPTION'))
"
```

**参数：** `USER_ID` 管理员钉钉ID, `NAME` 名称, `BUILDING` 楼栋, `FLOOR` 楼层(整数), `CAPACITY` 容量(整数), `FACILITIES` 设备, `DESCRIPTION` 备注

**权限：** 需管理员

**返回：** `{"success": true, "message": "会议室 'xxx' 添加成功", "room": {...}}`

### 3. 修改会议室

```bash
cd /opt/ding-robot && python -c "
import json
from room_manager.room_crud import update_room
print(update_room('USER_ID', ROOM_ID, name='新名称', capacity=40))
"
```

**参数：** `USER_ID` 管理员钉钉ID, `ROOM_ID` 会议室ID, 关键字参数指定要修改的字段

**可修改字段：** `name`（名称）, `building`（楼栋）, `floor`（楼层）, `capacity`（容量）, `facilities`（设备）, `description`（备注）

**权限：** 需管理员

**不可修改 status——停用/启用用下面的 disable_room / enable_room。**

**返回：** `{"success": true, "message": "会议室 ID:1 修改成功：name → 新名称, capacity → 40"}`

### 4. 停用会议室

```bash
cd /opt/ding-robot && python -c "
import json
from room_manager.room_crud import disable_room
print(disable_room('USER_ID', ROOM_ID))
"
```

**参数：** `USER_ID` 管理员钉钉ID, `ROOM_ID` 会议室ID

**权限：** 需管理员

**停止条件：** 如果该房间有未完成的活跃预约（从今天起），拒绝停用并告知有多少个预约待处理。

**返回：** `{"success": true, "message": "会议室 '信电楼330' 已停用"}`

### 5. 启用会议室

```bash
cd /opt/ding-robot && python -c "
import json
from room_manager.room_crud import enable_room
print(enable_room('USER_ID', ROOM_ID))
"
```

**参数：** `USER_ID` 管理员钉钉ID, `ROOM_ID` 会议室ID

**权限：** 需管理员

**返回：** `{"success": true, "message": "会议室 '信电楼330' 已启用"}`
