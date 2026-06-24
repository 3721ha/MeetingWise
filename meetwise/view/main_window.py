# -*- coding: utf-8 -*-
"""
主窗口模块
包含主界面布局、所有 UI 组件、交互逻辑和线程管理
"""

import os
import time
import numpy as np
import sounddevice as sd
import soundfile as sf
from datetime import datetime

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QListWidget, QListWidgetItem, QLabel, QPushButton, QTextEdit,
    QLineEdit, QScrollArea, QFrame, QDialog, QInputDialog,
    QMessageBox, QMenu, QSizePolicy, QSpacerItem
)
from PySide6.QtCore import Qt, QTimer, QThread, Signal
from PySide6.QtGui import QFont, QIcon, QCursor

from meetwise.utils.config_manager import ConfigManager
from meetwise.database import Database
from meetwise.services.whisper_client import WhisperClient
from meetwise.services.speaker_recognizer import SpeakerRecognizer
from meetwise.services.llm_client import LLMClient
from meetwise.services.voiceprint_manager import VoiceprintManager
from meetwise.services.realtime_transcriber import RealtimeTranscriber
from meetwise.view.ui_styles import DARK_STYLE, Colors, get_bubble_style


class ModelLoaderThread(QThread):
    """后台模型加载线程"""
    finished = Signal()

    def __init__(self, whisper, recognizer):
        super().__init__()
        self._whisper = whisper
        self._recognizer = recognizer

    def run(self):
        """加载所有模型"""
        try:
            if not self._whisper.is_loaded():
                self._whisper.load_model()
            if not self._recognizer.is_loaded():
                self._recognizer.load_model()
        except Exception as e:
            print(f"[ModelLoaderThread] 模型加载失败: {e}")
        finally:
            self.finished.emit()


class MainWindow(QMainWindow):
    """智会 MeetWise 主窗口"""

    def __init__(self):
        super().__init__()

        # 初始化配置
        self._config = ConfigManager()
        self._db = Database(self._config.get("db_path", "data/meetwise.db"))

        # 初始化核心组件
        self._whisper = WhisperClient(self._config.get("whisper_model_size", "base"))
        self._recognizer = SpeakerRecognizer(
            model_name=self._config.get("pyannote_model", "pyannote/embedding"),
            hf_token=self._config.get("hf_token")
        )
        self._llm = LLMClient(
            api_key=self._config.get("glm_api_key"),
            base_url=self._config.get("glm_base_url"),
            model=self._config.get("glm_model")
        )
        self._voiceprint_mgr = VoiceprintManager(self._recognizer, self._db, self._config)

        # 转写引擎（会议开始时创建）
        self._transcriber = None
        self._current_meeting_id = None
        self._closing = False  # 窗口关闭标志

        # 音频播放器
        self._audio_stream = None
        self._playing_bubble = None
        self._play_timer = QTimer()
        self._play_timer.timeout.connect(self._check_playback)

        # 录音计时器
        self._record_timer = QTimer()
        self._record_timer.timeout.connect(self._update_timer_display)
        self._record_start_time = 0

        # 构建 UI
        self._init_ui()
        self._load_meeting_list()

        # 状态栏
        self.statusBar().showMessage("就绪")

        # 后台预加载模型
        self._model_loader = ModelLoaderThread(self._whisper, self._recognizer)
        self._model_loader.finished.connect(lambda: self.statusBar().showMessage("模型加载完成"))
        self._model_loader.start()

    def _init_ui(self):
        """初始化主界面"""
        self.setWindowTitle("智会 MeetWise - AI 会议纪要生成器")
        self.setMinimumSize(1200, 750)
        self.resize(1400, 850)
        self.setStyleSheet(DARK_STYLE)

        # 中心部件
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(8)

        # ===== 顶部工具栏 =====
        toolbar = self._create_toolbar()
        main_layout.addWidget(toolbar)

        # ===== 主内容区（三栏布局）=====
        splitter = QSplitter(Qt.Horizontal)

        # 左侧：会议列表
        left_panel = self._create_left_panel()
        splitter.addWidget(left_panel)

        # 中间：录音控制 + 转写区域
        center_panel = self._create_center_panel()
        splitter.addWidget(center_panel)

        # 右侧：摘要 + AI 对话
        right_panel = self._create_right_panel()
        splitter.addWidget(right_panel)

        # 设置分割比例
        splitter.setSizes([220, 580, 350])
        main_layout.addWidget(splitter, 1)

    def _create_toolbar(self):
        """创建顶部工具栏"""
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BG_DARK};
                border-radius: 8px;
                padding: 8px;
            }}
        """)
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(16, 8, 16, 8)

        # 标题
        title = QLabel("智会 MeetWise")
        title.setObjectName("titleLabel")
        layout.addWidget(title)

        layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Expanding))

        # 声纹管理按钮
        btn_voiceprint = QPushButton("声纹管理")
        btn_voiceprint.clicked.connect(self._open_voiceprint_dialog)
        layout.addWidget(btn_voiceprint)

        # 新建会议按钮
        btn_new_meeting = QPushButton("新建会议")
        btn_new_meeting.setObjectName("primaryBtn")
        btn_new_meeting.clicked.connect(self._start_new_meeting)
        layout.addWidget(btn_new_meeting)

        return frame

    def _create_left_panel(self):
        """创建左侧面板：会议列表"""
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BG_DARK};
                border-radius: 8px;
            }}
        """)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(8, 8, 8, 8)

        # 标题
        label = QLabel("会议列表")
        label.setStyleSheet(f"color: {Colors.ACCENT_LIGHT}; font-weight: bold; font-size: 14px; padding: 4px;")
        layout.addWidget(label)

        # 会议列表
        self._meeting_list = QListWidget()
        self._meeting_list.currentItemChanged.connect(self._on_meeting_selected)
        self._meeting_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self._meeting_list.customContextMenuRequested.connect(self._show_meeting_context_menu)
        layout.addWidget(self._meeting_list)

        return frame

    def _create_center_panel(self):
        """创建中间面板：录音控制 + 转写气泡区"""
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BG_DARKEST};
                border-radius: 8px;
            }}
        """)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # ===== 录音控制区 =====
        control_frame = QFrame()
        control_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BG_DARK};
                border-radius: 6px;
            }}
        """)
        control_layout = QHBoxLayout(control_frame)
        control_layout.setContentsMargins(12, 8, 12, 8)

        # 录音状态指示
        self._recording_dot = QLabel("●")
        self._recording_dot.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: 16px;")
        control_layout.addWidget(self._recording_dot)

        # 录音状态文字
        self._status_label = QLabel("就绪")
        self._status_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 13px;")
        control_layout.addWidget(self._status_label)

        control_layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Expanding))

        # 计时器
        self._timer_label = QLabel("00:00")
        self._timer_label.setObjectName("timerLabel")
        control_layout.addWidget(self._timer_label)

        control_layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Expanding))

        # 控制按钮
        self._btn_start = QPushButton("开始")
        self._btn_start.setObjectName("primaryBtn")
        self._btn_start.setFixedSize(70, 32)
        self._btn_start.clicked.connect(self._on_start_clicked)
        control_layout.addWidget(self._btn_start)

        self._btn_pause = QPushButton("暂停")
        self._btn_pause.setFixedSize(70, 32)
        self._btn_pause.setEnabled(False)
        self._btn_pause.clicked.connect(self._on_pause_clicked)
        control_layout.addWidget(self._btn_pause)

        self._btn_stop = QPushButton("停止")
        self._btn_stop.setFixedSize(70, 32)
        self._btn_stop.setEnabled(False)
        self._btn_stop.clicked.connect(self._on_stop_clicked)
        control_layout.addWidget(self._btn_stop)

        layout.addWidget(control_frame)

        # ===== 转写气泡滚动区域 =====
        self._scroll_area = QScrollArea()
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self._bubble_container = QWidget()
        self._bubble_layout = QVBoxLayout(self._bubble_container)
        self._bubble_layout.setContentsMargins(4, 4, 4, 4)
        self._bubble_layout.setSpacing(6)
        self._bubble_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))

        self._scroll_area.setWidget(self._bubble_container)
        layout.addWidget(self._scroll_area, 1)

        return frame

    def _create_right_panel(self):
        """创建右侧面板：摘要卡片 + AI 对话"""
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BG_DARK};
                border-radius: 8px;
            }}
        """)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # ===== 摘要区域 =====
        summary_label = QLabel("会议摘要")
        summary_label.setStyleSheet(f"color: {Colors.ACCENT_LIGHT}; font-weight: bold; font-size: 14px; padding: 4px;")
        layout.addWidget(summary_label)

        self._summary_text = QTextEdit()
        self._summary_text.setReadOnly(True)
        self._summary_text.setPlaceholderText("点击\"生成摘要\"按钮生成会议摘要...")
        self._summary_text.setStyleSheet(f"""
            QTextEdit {{
                background-color: {Colors.BG_CARD};
                border: 1px solid {Colors.BORDER};
                border-radius: 6px;
                padding: 10px;
                color: {Colors.TEXT_PRIMARY};
            }}
        """)
        layout.addWidget(self._summary_text, 2)

        # 生成摘要按钮
        self._btn_summary = QPushButton("生成摘要")
        self._btn_summary.setObjectName("primaryBtn")
        self._btn_summary.clicked.connect(self._on_generate_summary)
        layout.addWidget(self._btn_summary)

        # ===== AI 对话区域 =====
        chat_label = QLabel("AI 对话")
        chat_label.setStyleSheet(f"color: {Colors.ACCENT_LIGHT}; font-weight: bold; font-size: 14px; padding: 4px; margin-top: 8px;")
        layout.addWidget(chat_label)

        # 对话历史显示
        self._chat_display = QTextEdit()
        self._chat_display.setReadOnly(True)
        self._chat_display.setPlaceholderText("在这里向 AI 提问关于会议内容的问题...")
        self._chat_display.setStyleSheet(f"""
            QTextEdit {{
                background-color: {Colors.BG_CARD};
                border: 1px solid {Colors.BORDER};
                border-radius: 6px;
                padding: 10px;
                color: {Colors.TEXT_PRIMARY};
            }}
        """)
        layout.addWidget(self._chat_display, 3)

        # 输入区
        input_layout = QHBoxLayout()
        self._chat_input = QLineEdit()
        self._chat_input.setPlaceholderText("输入问题...")
        self._chat_input.returnPressed.connect(self._on_send_chat)
        input_layout.addWidget(self._chat_input)

        self._btn_send = QPushButton("发送")
        self._btn_send.setObjectName("primaryBtn")
        self._btn_send.setFixedSize(60, 32)
        self._btn_send.clicked.connect(self._on_send_chat)
        input_layout.addWidget(self._btn_send)

        layout.addLayout(input_layout)

        return frame

    # ==================== 会议列表操作 ====================

    def _load_meeting_list(self):
        """加载会议列表"""
        self._meeting_list.clear()
        meetings = self._db.get_all_meetings()
        for m in meetings:
            status_icon = "●" if m["status"] == "recording" else "○"
            time_str = m["start_time"][:16].replace("T", " ")
            text = f"{status_icon} {m['title']}\n    {time_str}"
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, m["id"])
            self._meeting_list.addItem(item)

    def _on_meeting_selected(self, current, previous):
        """会议列表项被点击"""
        if current is None:
            return
        meeting_id = current.data(Qt.UserRole)
        self._load_meeting_detail(meeting_id)

    def _load_meeting_detail(self, meeting_id):
        """加载会议详情到中间和右侧面板"""
        self._current_meeting_id = meeting_id

        # 清空当前显示
        self._clear_bubbles()
        self._summary_text.clear()
        self._chat_display.clear()

        # 加载转写记录
        utterances = self._db.get_utterances(meeting_id)
        for u in utterances:
            self._add_bubble(u["speaker"], u["text"], u["audio_start"], u["audio_end"], clickable=True)

        # 加载摘要
        summary = self._db.get_summary(meeting_id)
        if summary:
            self._summary_text.setMarkdown(summary["content"])

        # 加载对话历史
        chats = self._db.get_chats(meeting_id)
        for c in chats:
            self._chat_display.append(f"<b style='color:{Colors.ACCENT_LIGHT}'>问：</b>{c['question']}")
            self._chat_display.append(f"<b style='color:{Colors.TEXT_SECONDARY}'>答：</b>{c['answer']}")
            self._chat_display.append("")

    def _show_meeting_context_menu(self, pos):
        """会议列表右键菜单"""
        item = self._meeting_list.itemAt(pos)
        if item is None:
            return

        menu = QMenu()
        delete_action = menu.addAction("删除会议")
        action = menu.exec(self._meeting_list.mapToGlobal(pos))

        if action == delete_action:
            meeting_id = item.data(Qt.UserRole)
            reply = QMessageBox.question(
                self, "确认删除",
                "确定要删除这个会议吗？所有相关数据（转写、摘要、对话记录）都将被删除。",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self._db.delete_meeting(meeting_id)
                self._load_meeting_list()
                self._clear_bubbles()
                self._summary_text.clear()
                self._chat_display.clear()

    # ==================== 会议控制 ====================

    def _start_new_meeting(self):
        """开始新会议"""
        # 如果正在录音，先停止
        if self._transcriber and self._transcriber.state == RealtimeTranscriber.RECORDING:
            self._on_stop_clicked()
            return

        # 创建新会议
        self._current_meeting_id = self._db.create_meeting()
        self._clear_bubbles()
        self._summary_text.clear()
        self._chat_display.clear()

        # 创建转写引擎
        self._transcriber = RealtimeTranscriber(
            self._whisper, self._recognizer, self._db,
            self._current_meeting_id, self._config
        )
        self._transcriber.utterance_ready.connect(self._on_utterance)
        self._transcriber.status_changed.connect(self._on_status_changed)
        self._transcriber.error_occurred.connect(self._on_error)
        self._transcriber.meeting_ended.connect(self._on_meeting_ended)
        self._transcriber.duration_updated.connect(self._on_duration_updated)

        # 启动转写引擎
        self._transcriber.start()

        # 更新 UI 状态
        self._btn_start.setEnabled(False)
        self._btn_pause.setEnabled(True)
        self._btn_stop.setEnabled(True)
        self._recording_dot.setStyleSheet(f"color: {Colors.RECORDING_RED}; font-size: 16px;")
        self._record_start_time = time.time()
        self._record_timer.start(1000)

        self.statusBar().showMessage("会议已开始录音")

    def _on_start_clicked(self):
        self._start_new_meeting()

    def _on_pause_clicked(self):
        if self._transcriber:
            if self._transcriber.state == RealtimeTranscriber.RECORDING:
                self._transcriber.pause()
                self._btn_pause.setText("继续")
                self._recording_dot.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: 16px;")
                self._record_timer.stop()
            elif self._transcriber.state == RealtimeTranscriber.PAUSED:
                self._transcriber.resume()
                self._btn_pause.setText("暂停")
                self._recording_dot.setStyleSheet(f"color: {Colors.RECORDING_RED}; font-size: 16px;")
                self._record_timer.start(1000)

    def _on_stop_clicked(self):
        if self._transcriber:
            self._transcriber.stop()
            self._btn_start.setEnabled(True)
            self._btn_pause.setEnabled(False)
            self._btn_stop.setEnabled(False)
            self._btn_pause.setText("暂停")
            self._recording_dot.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: 16px;")
            self._record_timer.stop()

    def _update_timer_display(self):
        """更新录音计时器显示"""
        elapsed = int(time.time() - self._record_start_time)
        minutes = elapsed // 60
        seconds = elapsed % 60
        self._timer_label.setText(f"{minutes:02d}:{seconds:02d}")

    # ==================== 转写回调 ====================

    def _on_utterance(self, speaker, text, timestamp, audio_start, audio_end):
        """收到新的转写结果（从子线程信号触发）"""
        self._add_bubble(speaker, text, audio_start, audio_end, clickable=True)

    def _on_status_changed(self, status):
        """状态变化"""
        self._status_label.setText(status)
        self.statusBar().showMessage(status)

    def _on_error(self, error):
        """错误处理"""
        QMessageBox.warning(self, "错误", error)
        self.statusBar().showMessage(f"错误: {error}")

    def _on_meeting_ended(self, recording_path):
        """会议结束"""
        self._status_label.setText("会议已结束")
        self._timer_label.setText("00:00")
        self._btn_start.setEnabled(True)
        self._btn_pause.setEnabled(False)
        self._btn_stop.setEnabled(False)
        self._load_meeting_list()
        self.statusBar().showMessage("会议已结束")

    def _on_duration_updated(self, duration):
        """录音时长更新"""
        minutes = int(duration) // 60
        seconds = int(duration) % 60
        self._timer_label.setText(f"{minutes:02d}:{seconds:02d}")

    # ==================== 气泡组件 ====================

    def _add_bubble(self, speaker, text, audio_start=0, audio_end=0, clickable=False):
        """添加一条转写气泡（子线程信号触发，需检查控件存活）"""
        if self._closing:
            return
        try:
            if not hasattr(self, '_bubble_layout') or self._bubble_layout is None:
                return
        except RuntimeError:
            return

        bubble = QFrame()
        bubble.setStyleSheet(get_bubble_style(speaker))
        bubble.setCursor(QCursor(Qt.PointingHandCursor) if clickable else Qt.ArrowCursor)

        bubble_layout = QVBoxLayout(bubble)
        bubble_layout.setContentsMargins(12, 8, 12, 8)
        bubble_layout.setSpacing(2)

        # 发言人名称
        name_label = QLabel(speaker)
        name_color = Colors.ACCENT_LIGHT if not speaker.startswith("陌生人") else Colors.TEXT_SECONDARY
        name_label.setStyleSheet(f"""
            color: {name_color};
            font-weight: bold;
            font-size: 12px;
            background-color: transparent;
        """)
        bubble_layout.addWidget(name_label)

        # 转写文本
        text_label = QLabel(text)
        text_label.setWordWrap(True)
        text_label.setStyleSheet(f"""
            color: {Colors.TEXT_PRIMARY};
            font-size: 13px;
            background-color: transparent;
        """)
        bubble_layout.addWidget(text_label)

        # 存储音频时间信息
        bubble.setProperty("audio_start", audio_start)
        bubble.setProperty("audio_end", audio_end)
        bubble.setProperty("speaker", speaker)

        # 点击播放语音
        if clickable and audio_start > 0:
            bubble.mousePressEvent = lambda event, b=bubble: self._on_bubble_clicked(b)

        # 右键菜单（陌生人可重命名）
        if speaker.startswith("陌生人"):
            bubble.setContextMenuPolicy(Qt.CustomContextMenu)
            bubble.customContextMenuRequested.connect(
                lambda pos, b=bubble, s=speaker: self._show_bubble_context_menu(b, s, pos)
            )

        # 插入到布局中（在 spacer 之前）
        insert_pos = self._bubble_layout.count() - 1
        self._bubble_layout.insertWidget(insert_pos, bubble)

        # 自动滚动到底部
        QTimer.singleShot(50, self._scroll_to_bottom)

    def _clear_bubbles(self):
        """清空所有气泡"""
        try:
            if not hasattr(self, '_bubble_layout') or self._bubble_layout is None:
                return
        except RuntimeError:
            return

        while self._bubble_layout.count() > 1:
            item = self._bubble_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _scroll_to_bottom(self):
        """滚动到底部"""
        scrollbar = self._scroll_area.verticalScrollBar()
        if scrollbar:
            scrollbar.setValue(scrollbar.maximum())

    def _on_bubble_clicked(self, bubble):
        """点击气泡跳转播放"""
        audio_start = bubble.property("audio_start")
        audio_end = bubble.property("audio_end")

        if not self._current_meeting_id or not audio_start:
            return

        # 获取录音文件路径
        meeting = self._db.get_meeting(self._current_meeting_id)
        if not meeting or not meeting.get("recording_path"):
            self.statusBar().showMessage("录音文件不存在，无法播放")
            return

        recording_path = meeting["recording_path"]
        if not os.path.exists(recording_path):
            self.statusBar().showMessage(f"录音文件未找到: {recording_path}")
            return

        # 取消之前的高亮
        if self._playing_bubble:
            self._playing_bubble.setStyleSheet(
                get_bubble_style(self._playing_bubble.property("speaker"))
            )

        # 高亮当前气泡
        bubble.setStyleSheet(get_bubble_style(bubble.property("speaker"), is_playing=True))
        self._playing_bubble = bubble

        # 开始播放
        self._play_audio_segment(recording_path, audio_start, audio_end)

    def _play_audio_segment(self, file_path, start_time, end_time):
        """播放指定时间段的音频"""
        try:
            # 读取音频文件
            audio_data, sample_rate = sf.read(file_path, dtype="float32")

            # 提取指定时间段
            start_sample = int(start_time * sample_rate)
            end_sample = int(end_time * sample_rate)
            segment = audio_data[start_sample:end_sample]

            if len(segment) == 0:
                return

            # 在后台线程播放
            def play():
                try:
                    sd.play(segment, sample_rate)
                    sd.wait()
                    # 播放完毕，取消高亮
                    QTimer.singleShot(0, self._clear_playing_highlight)
                except Exception as e:
                    print(f"[AudioPlayer] 播放失败: {e}")

            import threading
            threading.Thread(target=play, daemon=True).start()

        except Exception as e:
            print(f"[AudioPlayer] 读取音频失败: {e}")

    def _check_playback(self):
        """定时检查音频播放状态，播放结束后清除高亮"""
        try:
            import sounddevice as sd
            if not sd.get_stream().active:
                self._play_timer.stop()
                self._clear_playing_highlight()
        except Exception:
            # 流已关闭或不存在，停止计时器并清除高亮
            self._play_timer.stop()
            self._clear_playing_highlight()

    def _clear_playing_highlight(self):
        """取消播放高亮"""
        if self._playing_bubble:
            self._playing_bubble.setStyleSheet(
                get_bubble_style(self._playing_bubble.property("speaker"))
            )
            self._playing_bubble = None

    def _show_bubble_context_menu(self, bubble, speaker, pos):
        """气泡右键菜单（陌生人重命名）"""
        menu = QMenu()
        rename_action = menu.addAction("重命名")
        action = menu.exec(bubble.mapToGlobal(pos))

        if action == rename_action:
            new_name, ok = QInputDialog.getText(
                self, "重命名陌生人",
                f"为 {speaker} 输入真实姓名：",
                text=""
            )
            if ok and new_name.strip():
                new_name = new_name.strip()
                # 更新数据库
                self._db.update_speaker_name(speaker, new_name)
                # 更新当前 UI 中所有该陌生人的气泡
                self._update_bubble_names(speaker, new_name)
                self.statusBar().showMessage(f"已将 {speaker} 重命名为 {new_name}")

    def _update_bubble_names(self, old_name, new_name):
        """更新所有匹配的气泡显示"""
        for i in range(self._bubble_layout.count()):
            item = self._bubble_layout.itemAt(i)
            if item and item.widget():
                bubble = item.widget()
                if bubble.property("speaker") == old_name:
                    bubble.setProperty("speaker", new_name)
                    # 更新名称标签
                    name_label = bubble.findChild(QLabel)
                    if name_label:
                        name_label.setText(new_name)
                    # 更新样式
                    bubble.setStyleSheet(get_bubble_style(new_name))
                    # 移除右键菜单（不再是陌生人）
                    bubble.setContextMenuPolicy(Qt.NoContextMenu)

    # ==================== 摘要生成 ====================

    def _on_generate_summary(self):
        """生成 AI 摘要"""
        if not self._current_meeting_id:
            QMessageBox.warning(self, "提示", "请先选择或开始一个会议")
            return

        transcript = self._db.get_full_transcript(self._current_meeting_id)
        if not transcript:
            QMessageBox.warning(self, "提示", "暂无转写内容，无法生成摘要")
            return

        self._btn_summary.setEnabled(False)
        self._btn_summary.setText("生成中...")
        self._summary_text.setPlainText("正在生成摘要，请稍候...")

        # 在子线程中调用 API
        def generate():
            result = self._llm.generate_summary(transcript)
            # 回到主线程更新 UI
            QTimer.singleShot(0, lambda: self._on_summary_ready(result))

        import threading
        threading.Thread(target=generate, daemon=True).start()

    def _on_summary_ready(self, summary):
        """摘要生成完成"""
        self._summary_text.setMarkdown(summary)
        self._btn_summary.setEnabled(True)
        self._btn_summary.setText("生成摘要")

        # 保存到数据库
        if self._current_meeting_id:
            self._db.save_summary(self._current_meeting_id, summary)

    # ==================== AI 对话 ====================

    def _on_send_chat(self):
        """发送 AI 对话"""
        question = self._chat_input.text().strip()
        if not question:
            return

        if not self._current_meeting_id:
            QMessageBox.warning(self, "提示", "请先选择或开始一个会议")
            return

        self._chat_input.clear()

        # 显示用户问题
        self._chat_display.append(f"<b style='color:{Colors.ACCENT_LIGHT}'>问：</b>{question}")
        self._chat_display.append("<b style='color:{Colors.TEXT_SECONDARY}'>答：</b>思考中...")
        self._scroll_chat_to_bottom()

        transcript = self._db.get_full_transcript(self._current_meeting_id)
        history = self._db.get_chats(self._current_meeting_id)
        history_list = [{"question": h["question"], "answer": h["answer"]} for h in history]

        # 在子线程中调用 API
        def chat():
            answer = self._llm.chat(transcript, question, history_list)
            QTimer.singleShot(0, lambda: self._on_chat_ready(question, answer))

        import threading
        threading.Thread(target=chat, daemon=True).start()

    def _on_chat_ready(self, question, answer):
        """AI 回答就绪"""
        # 更新最后一条"思考中..."
        cursor = self._chat_display.textCursor()
        cursor.movePosition(cursor.End)
        self._chat_display.setTextCursor(cursor)

        # 重新渲染整个对话区（简单实现）
        chats = self._db.get_chats(self._current_meeting_id)
        self._chat_display.clear()
        for c in chats:
            self._chat_display.append(f"<b style='color:{Colors.ACCENT_LIGHT}'>问：</b>{c['question']}")
            self._chat_display.append(f"<b style='color:{Colors.TEXT_SECONDARY}'>答：</b>{c['answer']}")
            self._chat_display.append("")

        # 追加新的对话
        self._chat_display.append(f"<b style='color:{Colors.ACCENT_LIGHT}'>问：</b>{question}")
        self._chat_display.append(f"<b style='color:{Colors.TEXT_SECONDARY}'>答：</b>{answer}")
        self._chat_display.append("")

        # 保存到数据库
        self._db.save_chat(self._current_meeting_id, question, answer)
        self._scroll_chat_to_bottom()

    def _scroll_chat_to_bottom(self):
        """滚动对话区到底部"""
        scrollbar = self._chat_display.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    # ==================== 声纹管理对话框 ====================

    def _open_voiceprint_dialog(self):
        """打开声纹管理对话框"""
        dialog = VoiceprintDialog(self._voiceprint_mgr, self._recognizer, self)
        dialog.exec()

    # ==================== 关闭事件 ====================

    def closeEvent(self, event):
        """窗口关闭时清理资源"""
        self._closing = True
        if self._transcriber and self._transcriber.isRunning():
            self._transcriber.stop()
            self._transcriber.wait(3000)
        if self._audio_stream:
            sd.stop()
        event.accept()


class VoiceprintDialog(QDialog):
    """声纹注册管理对话框"""

    def __init__(self, voiceprint_mgr, recognizer, parent=None):
        super().__init__(parent)
        self._mgr = voiceprint_mgr
        self._recognizer = recognizer
        self._is_recording = False

        self.setWindowTitle("声纹管理")
        self.setFixedSize(450, 500)
        self.setStyleSheet(DARK_STYLE)
        self._init_ui()
        self._refresh_list()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        # 标题
        title = QLabel("声纹注册")
        title.setObjectName("titleLabel")
        layout.addWidget(title)

        # 姓名输入
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("姓名："))
        self._name_input = QLineEdit()
        self._name_input.setPlaceholderText("输入发言人姓名")
        name_layout.addWidget(self._name_input)
        layout.addLayout(name_layout)

        # 录音控制
        record_layout = QHBoxLayout()

        self._btn_record = QPushButton("开始录音")
        self._btn_record.setObjectName("primaryBtn")
        self._btn_record.clicked.connect(self._toggle_recording)
        record_layout.addWidget(self._btn_record)

        self._btn_register = QPushButton("注册")
        self._btn_register.clicked.connect(self._register)
        self._btn_register.setEnabled(False)
        record_layout.addWidget(self._btn_register)

        layout.addLayout(record_layout)

        # 录音时长显示
        self._record_info = QLabel("请录制 10-30 秒的语音")
        self._record_info.setStyleSheet(f"color: {Colors.TEXT_SECONDARY};")
        layout.addWidget(self._record_info)

        # 录音计时器
        self._record_timer = QTimer()
        self._record_timer.timeout.connect(self._update_record_info)

        # 已注册声纹列表
        list_label = QLabel("已注册声纹")
        list_label.setStyleSheet(f"color: {Colors.ACCENT_LIGHT}; font-weight: bold; margin-top: 8px;")
        layout.addWidget(list_label)

        self._voiceprint_list = QListWidget()
        layout.addWidget(self._voiceprint_list)

        # 删除按钮
        btn_layout = QHBoxLayout()
        btn_layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Expanding))

        self._btn_delete = QPushButton("删除选中")
        self._btn_delete.setObjectName("dangerBtn")
        self._btn_delete.clicked.connect(self._delete_selected)
        btn_layout.addWidget(self._btn_delete)

        layout.addLayout(btn_layout)

    def _toggle_recording(self):
        """切换录音状态"""
        if not self._is_recording:
            name = self._name_input.text().strip()
            if not name:
                QMessageBox.warning(self, "提示", "请先输入姓名")
                return

            self._is_recording = True
            self._btn_record.setText("停止录音")
            self._btn_register.setEnabled(False)
            self._record_info.setText("录音中... 请朗读一段内容（10-30秒）")
            self._record_info.setStyleSheet(f"color: {Colors.RECORDING_RED};")

            self._mgr.start_recording()
            self._record_timer.start(500)
        else:
            self._is_recording = False
            self._record_timer.stop()

            audio_data = self._mgr.stop_recording()
            duration = self._mgr.get_recording_duration() if hasattr(self._mgr, 'get_recording_duration') else 0

            self._btn_record.setText("开始录音")
            self._record_info.setStyleSheet(f"color: {Colors.TEXT_SECONDARY};")

            if audio_data is not None and len(audio_data) > 0:
                self._recorded_audio = audio_data
                self._record_info.setText(f"录音完成（{len(audio_data) / 16000:.1f} 秒），点击\"注册\"保存声纹")
                self._record_info.setStyleSheet(f"color: {Colors.SUCCESS};")
                self._btn_register.setEnabled(True)
            else:
                self._record_info.setText("录音数据为空，请重新录制")
                self._btn_register.setEnabled(False)

    def _update_record_info(self):
        """更新录音时长显示"""
        if self._is_recording:
            duration = len(self._mgr._audio_chunks) * 1024 / self._mgr._sample_rate
            self._record_info.setText(f"录音中... {duration:.1f} 秒（建议 10-30 秒）")

    def _register(self):
        """注册声纹"""
        name = self._name_input.text().strip()
        if not name or not hasattr(self, '_recorded_audio'):
            return

        # 确保模型已加载
        if not self._recognizer.is_loaded():
            self._record_info.setText("模型尚未加载完成，请稍候...")
            return

        success, message = self._mgr.register_voiceprint(name, self._recorded_audio)
        self._record_info.setText(message)

        if success:
            self._record_info.setStyleSheet(f"color: {Colors.SUCCESS};")
            self._name_input.clear()
            self._btn_register.setEnabled(False)
            self._refresh_list()
        else:
            self._record_info.setStyleSheet(f"color: {Colors.DANGER};")

    def _refresh_list(self):
        """刷新声纹列表"""
        self._voiceprint_list.clear()
        voiceprints = self._mgr.list_voiceprints()
        for v in voiceprints:
            time_str = v["created_at"][:16].replace("T", " ")
            item = QListWidgetItem(f"{v['name']}  ({time_str})")
            item.setData(Qt.UserRole, v["name"])
            self._voiceprint_list.addItem(item)

    def _delete_selected(self):
        """删除选中的声纹"""
        item = self._voiceprint_list.currentItem()
        if item is None:
            return

        name = item.data(Qt.UserRole)
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除声纹「{name}」吗？",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            success, message = self._mgr.delete_voiceprint(name)
            self._record_info.setText(message)
            if success:
                self._refresh_list()

