# 意图分类提示词

## 说明

根据用户的自然语言输入，判断其意图并提取结构化参数。

## 意图类别

### 1. book — 预约房间

**触发关键词：** 约、定、订、预约、帮我订、帮我约、book、预定、预订

**需要提取的参数：**
- room_name: 房间号或房间名（如 "330"、"信电楼317"）
- date: 日期 YYYY-MM-DD
- start_time: 开始时间 HH:MM
- end_time: 结束时间 HH:MM

**示例：**
| 用户输入 | 提取结果 |
|---------|---------|
| "帮我约明天下午 330" | intent=book, room_name="330", date=<明天>, start_time="14:00", end_time="18:00" |
| "预约下周一上午信电楼501" | intent=book, room_name="信电楼501", date=<下周一>, start_time="08:00", end_time="12:00" |
| "定一个今天下午2点的会议室" | intent=book, room_name=null（需追问）, date=<今天>, start_time="14:00", end_time="18:00" |

### 2. query_available — 查询空闲

**触发关键词：** 空房间、空闲、有哪些、哪些空着、空的、可用的

**需要提取的参数：**
- date: 日期（默认今天）
- start_time: 开始时间
- end_time: 结束时间

**示例：**
| 用户输入 | 提取结果 |
|---------|---------|
| "现在有哪些空房间？" | intent=query_available, date=<今天>, start_time=<现在>, end_time=<当前时段结束> |
| "明天下午有哪些会议室空着？" | intent=query_available, date=<明天>, start_time="14:00", end_time="18:00" |

### 3. query_overview — 预约总览

**触发关键词：** 预约情况、占用情况、都谁约了、全部预约、一览、总览

**需要提取的参数：**
- date: 日期
- start_time: 开始时间
- end_time: 结束时间

**示例：**
| 用户输入 | 提取结果 |
|---------|---------|
| "明天下午各会议室的预约情况" | intent=query_overview, date=<明天>, start_time="14:00", end_time="18:00" |
| "今天330都谁约了？" | intent=query_overview, date=<今天>, room_name="330" |

### 4. query_my — 查询我的预约

**触发关键词：** 我的预约、我约了、我订了、我的记录、我有哪些

**需要提取的参数：**
- user_id: 从钉钉消息中获取

**示例：**
| 用户输入 | 提取结果 |
|---------|---------|
| "我有哪些预约？" | intent=query_my |
| "看看我的预约记录" | intent=query_my |

### 5. cancel — 取消预约

**触发关键词：** 取消、退订、不要了、删掉、撤销

**需要提取的参数：**
- reservation_id: 预约号（如有）
- user_id: 从钉钉消息中获取

**示例：**
| 用户输入 | 提取结果 |
|---------|---------|
| "取消 ID 为 1001 的预约" | intent=cancel, reservation_id=1001 |
| "帮我把明天下午330的预约取消" | intent=cancel, room_name="330", date=<明天>, start_time="14:00"（需查找对应预约ID） |
| "不想要了，取消" | intent=cancel, reservation_id=null（需追问是哪个预约） |

## 未知意图

如果无法匹配以上任何类别，返回 `intent=unknown`，后续回复应引导用户重新描述需求。
