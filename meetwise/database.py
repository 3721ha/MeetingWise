# -*- coding: utf-8 -*-
"""
数据库管理模块
负责 SQLite 数据库的创建、连接和所有 CRUD 操作
表结构：meetings / utterances / summaries / chat_history / voiceprints
"""

import sqlite3
import os
import numpy as np
from datetime import datetime


class Database:
    """SQLite 数据库管理器"""

    def __init__(self, db_path="data/meetwise.db"):
        """初始化数据库，自动建表"""
        self._db_path = db_path
        self._init_db()

    def _get_conn(self):
        """获取数据库连接"""
        conn = sqlite3.connect(self._db_path)
        conn.execute("PRAGMA foreign_keys = ON")  # 启用外键约束
        return conn

    def _init_db(self):
        """创建所有数据表"""
        conn = self._get_conn()
        cursor = conn.cursor()

        # 会议表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS meetings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT,
                status TEXT DEFAULT 'recording',
                recording_path TEXT
            )
        """)

        # 发言记录表（转写文本）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS utterances (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                meeting_id INTEGER NOT NULL,
                speaker TEXT NOT NULL,
                speaker_id TEXT,
                text TEXT NOT NULL,
                timestamp REAL NOT NULL,
                audio_start REAL NOT NULL DEFAULT 0,
                audio_end REAL NOT NULL DEFAULT 0,
                FOREIGN KEY (meeting_id) REFERENCES meetings(id) ON DELETE CASCADE
            )
        """)

        # 会议摘要表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS summaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                meeting_id INTEGER NOT NULL UNIQUE,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (meeting_id) REFERENCES meetings(id) ON DELETE CASCADE
            )
        """)

        # AI 对话历史表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                meeting_id INTEGER NOT NULL,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (meeting_id) REFERENCES meetings(id) ON DELETE CASCADE
            )
        """)

        # 声纹注册表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS voiceprints (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                embedding_path TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

        conn.commit()
        conn.close()

    # ==================== 会议管理 ====================

    def create_meeting(self, title=None):
        """创建新会议，返回会议ID"""
        if title is None:
            title = f"会议 {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        now = datetime.now().isoformat()
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO meetings (title, start_time, status) VALUES (?, ?, 'recording')",
            (title, now)
        )
        meeting_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return meeting_id

    def end_meeting(self, meeting_id, recording_path=None):
        """结束会议，更新状态和录音路径"""
        now = datetime.now().isoformat()
        conn = self._get_conn()
        conn.execute(
            "UPDATE meetings SET status='ended', end_time=?, recording_path=? WHERE id=?",
            (now, recording_path, meeting_id)
        )
        conn.commit()
        conn.close()

    def get_all_meetings(self):
        """获取所有会议列表（按时间倒序）"""
        conn = self._get_conn()
        cursor = conn.execute(
            "SELECT id, title, start_time, end_time, status, recording_path FROM meetings ORDER BY start_time DESC"
        )
        rows = cursor.fetchall()
        conn.close()
        return [
            {
                "id": r[0], "title": r[1], "start_time": r[2],
                "end_time": r[3], "status": r[4], "recording_path": r[5]
            }
            for r in rows
        ]

    def search_meetings(self, keyword):
        """根据关键词搜索会议（匹配标题）"""
        conn = self._get_conn()
        cursor = conn.execute(
            "SELECT id, title, start_time, end_time, status, recording_path FROM meetings WHERE title LIKE ? ORDER BY start_time DESC",
            (f"%{keyword}%",)
        )
        rows = cursor.fetchall()
        conn.close()
        return [
            {
                "id": r[0], "title": r[1], "start_time": r[2],
                "end_time": r[3], "status": r[4], "recording_path": r[5]
            }
            for r in rows
        ]

    def get_meeting(self, meeting_id):
        """获取单个会议信息"""
        conn = self._get_conn()
        cursor = conn.execute(
            "SELECT id, title, start_time, end_time, status, recording_path FROM meetings WHERE id=?",
            (meeting_id,)
        )
        row = cursor.fetchone()
        conn.close()
        if row:
            return {
                "id": row[0], "title": row[1], "start_time": row[2],
                "end_time": row[3], "status": row[4], "recording_path": row[5]
            }
        return None

    def delete_meeting(self, meeting_id):
        """删除会议及其所有关联数据（级联删除）"""
        conn = self._get_conn()
        conn.execute("DELETE FROM chat_history WHERE meeting_id=?", (meeting_id,))
        conn.execute("DELETE FROM summaries WHERE meeting_id=?", (meeting_id,))
        conn.execute("DELETE FROM utterances WHERE meeting_id=?", (meeting_id,))
        conn.execute("DELETE FROM meetings WHERE id=?", (meeting_id,))
        conn.commit()
        conn.close()

    def update_meeting_title(self, meeting_id, title):
        """更新会议标题"""
        conn = self._get_conn()
        conn.execute("UPDATE meetings SET title=? WHERE id=?", (title, meeting_id))
        conn.commit()
        conn.close()

    # ==================== 发言记录 ====================

    def save_utterance(self, meeting_id, speaker, text, timestamp, audio_start=0, audio_end=0, speaker_id=None):
        """保存一条发言记录"""
        conn = self._get_conn()
        conn.execute(
            """INSERT INTO utterances 
               (meeting_id, speaker, speaker_id, text, timestamp, audio_start, audio_end) 
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (meeting_id, speaker, speaker_id, text, timestamp, audio_start, audio_end)
        )
        conn.commit()
        conn.close()

    def get_utterances(self, meeting_id):
        """获取会议的所有发言记录"""
        conn = self._get_conn()
        cursor = conn.execute(
            """SELECT id, meeting_id, speaker, speaker_id, text, timestamp, audio_start, audio_end 
               FROM utterances WHERE meeting_id=? ORDER BY timestamp ASC""",
            (meeting_id,)
        )
        rows = cursor.fetchall()
        conn.close()
        return [
            {
                "id": r[0], "meeting_id": r[1], "speaker": r[2], "speaker_id": r[3],
                "text": r[4], "timestamp": r[5], "audio_start": r[6], "audio_end": r[7]
            }
            for r in rows
        ]

    def update_speaker_name(self, old_name, new_name):
        """更新所有会议中某个发言人的名称（用于陌生人重命名）"""
        conn = self._get_conn()
        conn.execute("UPDATE utterances SET speaker=? WHERE speaker=?", (new_name, old_name))
        conn.commit()
        conn.close()

    def get_full_transcript(self, meeting_id):
        """获取会议的完整转写文本（用于发送给 AI）"""
        utterances = self.get_utterances(meeting_id)
        lines = [f"{u['speaker']}：{u['text']}" for u in utterances]
        return "\n".join(lines)

    # ==================== 摘要管理 ====================

    def save_summary(self, meeting_id, content):
        """保存会议摘要（如果已有则更新）"""
        now = datetime.now().isoformat()
        conn = self._get_conn()
        # 检查是否已有摘要
        cursor = conn.execute("SELECT id FROM summaries WHERE meeting_id=?", (meeting_id,))
        existing = cursor.fetchone()
        if existing:
            conn.execute(
                "UPDATE summaries SET content=?, created_at=? WHERE meeting_id=?",
                (content, now, meeting_id)
            )
        else:
            conn.execute(
                "INSERT INTO summaries (meeting_id, content, created_at) VALUES (?, ?, ?)",
                (meeting_id, content, now)
            )
        conn.commit()
        conn.close()

    def get_summary(self, meeting_id):
        """获取会议摘要"""
        conn = self._get_conn()
        cursor = conn.execute(
            "SELECT content, created_at FROM summaries WHERE meeting_id=?", (meeting_id,)
        )
        row = cursor.fetchone()
        conn.close()
        if row:
            return {"content": row[0], "created_at": row[1]}
        return None

    # ==================== 对话历史 ====================

    def save_chat(self, meeting_id, question, answer):
        """保存一轮 AI 对话"""
        now = datetime.now().isoformat()
        conn = self._get_conn()
        conn.execute(
            "INSERT INTO chat_history (meeting_id, question, answer, created_at) VALUES (?, ?, ?, ?)",
            (meeting_id, question, answer, now)
        )
        conn.commit()
        conn.close()

    def get_chats(self, meeting_id):
        """获取会议的所有对话记录"""
        conn = self._get_conn()
        cursor = conn.execute(
            "SELECT id, question, answer, created_at FROM chat_history WHERE meeting_id=? ORDER BY created_at ASC",
            (meeting_id,)
        )
        rows = cursor.fetchall()
        conn.close()
        return [
            {"id": r[0], "question": r[1], "answer": r[2], "created_at": r[3]}
            for r in rows
        ]

    # ==================== 声纹管理 ====================

    def save_voiceprint(self, name, embedding_np, voiceprint_dir="voiceprints"):
        """保存声纹：将 numpy 向量保存为文件，路径写入数据库"""
        os.makedirs(voiceprint_dir, exist_ok=True)
        file_path = os.path.join(voiceprint_dir, f"{name}.npy")
        np.save(file_path, embedding_np)

        now = datetime.now().isoformat()
        conn = self._get_conn()
        conn.execute(
            "INSERT OR REPLACE INTO voiceprints (name, embedding_path, created_at) VALUES (?, ?, ?)",
            (name, file_path, now)
        )
        conn.commit()
        conn.close()

    def get_all_voiceprints(self):
        """获取所有已注册声纹 {name: embedding_array}"""
        conn = self._get_conn()
        cursor = conn.execute("SELECT name, embedding_path FROM voiceprints")
        rows = cursor.fetchall()
        conn.close()

        voiceprints = {}
        for name, path in rows:
            if os.path.exists(path):
                voiceprints[name] = np.load(path)
        return voiceprints

    def get_voiceprint_names(self):
        """获取所有已注册的声纹名称列表"""
        conn = self._get_conn()
        cursor = conn.execute("SELECT name, created_at FROM voiceprints ORDER BY created_at DESC")
        rows = cursor.fetchall()
        conn.close()
        return [{"name": r[0], "created_at": r[1]} for r in rows]

    def delete_voiceprint(self, name, voiceprint_dir="voiceprints"):
        """删除声纹注册（同时删除 .npy 文件）"""
        conn = self._get_conn()
        cursor = conn.execute("SELECT embedding_path FROM voiceprints WHERE name=?", (name,))
        row = cursor.fetchone()
        conn.execute("DELETE FROM voiceprints WHERE name=?", (name,))
        conn.commit()
        conn.close()

        # 删除文件
        if row and os.path.exists(row[0]):
            os.remove(row[0])
