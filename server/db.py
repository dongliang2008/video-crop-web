# -*- coding: utf-8 -*-
"""SQLite 数据层：项目 / 水印区域 / 时间段 / 任务。纯本地离线。"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / 'data' / 'videocrop.db'

SCHEMA = """
CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    src_path TEXT NOT NULL,
    src_w INTEGER, src_h INTEGER,
    src_duration REAL, src_fps REAL,
    crop_x INTEGER, crop_y INTEGER, crop_w INTEGER, crop_h INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS watermark_regions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    x INTEGER, y INTEGER, width INTEGER, height INTEGER,
    blur_sigma REAL DEFAULT 30
);
CREATE TABLE IF NOT EXISTS segments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    seg_index INTEGER NOT NULL,
    frame_start INTEGER, frame_end INTEGER,
    start_time REAL NOT NULL, end_time REAL NOT NULL,
    direction TEXT DEFAULT 'both'
);
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    segment_id INTEGER NOT NULL,
    direction TEXT NOT NULL,
    state TEXT DEFAULT 'PENDING',
    progress REAL DEFAULT 0,
    preview_path TEXT,
    preview_approved INTEGER DEFAULT 0,
    output_path TEXT,
    error TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


def get_conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA journal_mode=WAL')
    return conn


def init_db():
    conn = get_conn()
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()


def row_to_dict(row):
    return dict(row) if row is not None else None
