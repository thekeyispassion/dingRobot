-- AI 会议室预约助手 — 测试种子数据

-- 8 个会议室，分布在 2 栋楼
INSERT OR IGNORE INTO rooms (id, name, building, floor, capacity, facilities, status, description) VALUES
(1, '信电楼330', '信电楼', 3, 30, '投影仪,白板,视频会议', 'available', '中型会议室'),
(2, '信电楼317', '信电楼', 3, 20, '投影仪,白板', 'available', '小型会议室'),
(3, '信电楼212', '信电楼', 2, 10, '白板', 'available', '小型讨论室'),
(4, '信电楼501', '信电楼', 5, 50, '投影仪,白板,视频会议,音响', 'available', '大型报告厅'),
(5, '信电楼108', '信电楼', 1, 15, '投影仪', 'available', '小型会议室'),
(6, '理学院A201', '理学院', 2, 25, '投影仪,白板,视频会议', 'available', '中型会议室'),
(7, '理学院A305', '理学院', 3, 40, '投影仪,白板,视频会议,音响', 'available', '大型会议室'),
(8, '理学院B102', '理学院', 1, 60, '投影仪,白板,视频会议,音响,录音', 'available', '学术报告厅');

-- 2 条示例预约（用于测试冲突检测，使用远期日期避免过期）
INSERT OR IGNORE INTO reservations (id, room_id, user_id, user_name, date, start_time, end_time, status, created_at) VALUES
(1, 1, 'user002', '李四', '2026-12-15', '14:00', '16:00', 'active', '2026-07-13T10:00:00'),
(2, 3, 'user003', '王五', '2026-12-15', '09:00', '11:00', 'active', '2026-07-13T09:00:00');

-- 管理员（张三 为默认管理员）
INSERT OR IGNORE INTO admins (id, user_id, user_name, role, created_at) VALUES
(1, 'user001', '张三', 'admin', '2026-07-13T00:00:00');
