-- AI 会议室预约助手 — 数据库 Schema

CREATE TABLE IF NOT EXISTS rooms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    building TEXT NOT NULL,
    floor INTEGER NOT NULL,
    capacity INTEGER NOT NULL,
    facilities TEXT DEFAULT '',
    status TEXT DEFAULT 'available',
    description TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS reservations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    room_id INTEGER NOT NULL,
    user_id TEXT NOT NULL,
    user_name TEXT NOT NULL,
    date TEXT NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    status TEXT DEFAULT 'active',
    created_at TEXT NOT NULL,
    FOREIGN KEY (room_id) REFERENCES rooms(id)
);

-- 索引：加速按日期+状态查询预约
CREATE INDEX IF NOT EXISTS idx_reservations_date_status
    ON reservations(date, status);

-- 索引：加速按用户查询
CREATE INDEX IF NOT EXISTS idx_reservations_user
    ON reservations(user_id, status);

-- 管理员表
CREATE TABLE IF NOT EXISTS admins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL UNIQUE,
    user_name TEXT NOT NULL,
    role TEXT DEFAULT 'admin',
    created_at TEXT NOT NULL
);
