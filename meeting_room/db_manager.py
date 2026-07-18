"""数据库管理器 — 连接、建表、种子数据"""

import sqlite3
import os

DEFAULT_DB_PATH = "db/meeting_rooms.db"


def _get_base_dir() -> str:
    """获取项目根目录（skills/ 的上级目录）"""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _resolve_path(db_path: str = None) -> str:
    """将相对路径转换为基于项目根目录的绝对路径"""
    if db_path is None:
        db_path = DEFAULT_DB_PATH
    if not os.path.isabs(db_path):
        db_path = os.path.join(_get_base_dir(), db_path)
    return db_path


def get_connection(db_path: str = None) -> sqlite3.Connection:
    """获取数据库连接"""
    path = _resolve_path(db_path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _read_sql_file(filename: str) -> str:
    """读取 db/ 目录下的 SQL 文件"""
    base_dir = _get_base_dir()
    filepath = os.path.join(base_dir, "db", filename)
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()


def init_db(db_path: str = None) -> None:
    """初始化数据库 — 执行 schema.sql 建表"""
    conn = get_connection(db_path)
    try:
        sql = _read_sql_file("schema.sql")
        conn.executescript(sql)
        conn.commit()
    finally:
        conn.close()


def seed_data(db_path: str = None) -> None:
    """插入种子数据 — 执行 seed_data.sql"""
    conn = get_connection(db_path)
    try:
        sql = _read_sql_file("seed_data.sql")
        conn.executescript(sql)
        conn.commit()
    finally:
        conn.close()
