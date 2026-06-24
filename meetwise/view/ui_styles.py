# -*- coding: utf-8 -*-
"""
UI 样式模块
定义全局深色主题 QSS 样式表，配色以深蓝、黑、紫为主
"""

# 配色常量
class Colors:
    BG_DARKEST = "#0a0e1a"       # 最深背景
    BG_DARK = "#111827"           # 面板背景
    BG_CARD = "#1a1f36"           # 卡片/气泡背景
    BG_HOVER = "#252b45"          # 悬停背景
    BG_SELECTED = "#2d3561"       # 选中背景

    ACCENT_PURPLE = "#7c3aed"     # 主强调色（紫）
    ACCENT_INDIGO = "#6366f1"     # 次强调色（靛蓝）
    ACCENT_LIGHT = "#8b5cf6"      # 亮紫色（高亮）

    TEXT_PRIMARY = "#e2e8f0"      # 主文字
    TEXT_SECONDARY = "#94a3b8"    # 次要文字
    TEXT_MUTED = "#64748b"        # 灰色文字

    BUBBLE_SELF = "#1e1b4b"       # 自己的气泡（深紫蓝）
    BUBBLE_OTHER = "#172554"      # 他人的气泡（深蓝）
    BUBBLE_STRANGER = "#1c1917"   # 陌生人气泡（深褐黑）

    BORDER = "#2a2f45"            # 边框色
    DANGER = "#ef4444"            # 危险操作（红色）
    SUCCESS = "#22c55e"           # 成功状态（绿色）
    RECORDING_RED = "#ef4444"     # 录音指示（红色闪烁）


# 全局深色主题样式表
DARK_STYLE = """
/* ========== 全局样式 ========== */
QMainWindow {
    background-color: #0a0e1a;
}

QWidget {
    color: #e2e8f0;
    font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
    font-size: 13px;
}

/* ========== 按钮样式 ========== */
QPushButton {
    background-color: #1a1f36;
    color: #e2e8f0;
    border: 1px solid #2a2f45;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 500;
    min-height: 20px;
}

QPushButton:hover {
    background-color: #252b45;
    border-color: #7c3aed;
}

QPushButton:pressed {
    background-color: #7c3aed;
}

QPushButton:disabled {
    background-color: #111827;
    color: #64748b;
    border-color: #1a1f36;
}

/* 主要操作按钮（紫色） */
QPushButton#primaryBtn {
    background-color: #7c3aed;
    border-color: #7c3aed;
    color: white;
}

QPushButton#primaryBtn:hover {
    background-color: #8b5cf6;
}

QPushButton#primaryBtn:pressed {
    background-color: #6d28d9;
}

/* 危险按钮（红色） */
QPushButton#dangerBtn {
    background-color: #991b1b;
    border-color: #ef4444;
    color: #fca5a5;
}

QPushButton#dangerBtn:hover {
    background-color: #b91c1c;
}

/* ========== 输入框样式 ========== */
QLineEdit {
    background-color: #1a1f36;
    color: #e2e8f0;
    border: 1px solid #2a2f45;
    border-radius: 6px;
    padding: 8px 12px;
    selection-background-color: #7c3aed;
}

QLineEdit:focus {
    border-color: #7c3aed;
}

QTextEdit {
    background-color: #1a1f36;
    color: #e2e8f0;
    border: 1px solid #2a2f45;
    border-radius: 6px;
    padding: 8px;
    selection-background-color: #7c3aed;
}

QTextEdit:focus {
    border-color: #7c3aed;
}

/* ========== 列表样式 ========== */
QListWidget {
    background-color: #111827;
    color: #e2e8f0;
    border: 1px solid #2a2f45;
    border-radius: 6px;
    padding: 4px;
    outline: none;
}

QListWidget::item {
    padding: 10px 12px;
    border-radius: 4px;
    margin: 2px 4px;
}

QListWidget::item:hover {
    background-color: #252b45;
}

QListWidget::item:selected {
    background-color: #2d3561;
    border-left: 3px solid #7c3aed;
}

/* ========== 滚动条样式 ========== */
QScrollBar:vertical {
    background-color: #0a0e1a;
    width: 8px;
    border-radius: 4px;
}

QScrollBar::handle:vertical {
    background-color: #2a2f45;
    border-radius: 4px;
    min-height: 30px;
}

QScrollBar::handle:vertical:hover {
    background-color: #7c3aed;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    background-color: #0a0e1a;
    height: 8px;
    border-radius: 4px;
}

QScrollBar::handle:horizontal {
    background-color: #2a2f45;
    border-radius: 4px;
    min-width: 30px;
}

QScrollBar::handle:horizontal:hover {
    background-color: #7c3aed;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}

/* ========== 滚动区域 ========== */
QScrollArea {
    background-color: #0a0e1a;
    border: none;
}

/* ========== 标签页 ========== */
QTabWidget::pane {
    background-color: #111827;
    border: 1px solid #2a2f45;
    border-radius: 6px;
}

QTabBar::tab {
    background-color: #111827;
    color: #94a3b8;
    padding: 8px 16px;
    border: 1px solid #2a2f45;
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    margin-right: 2px;
}

QTabBar::tab:selected {
    background-color: #1a1f36;
    color: #e2e8f0;
    border-bottom: 2px solid #7c3aed;
}

QTabBar::tab:hover {
    background-color: #1a1f36;
    color: #e2e8f0;
}

/* ========== 下拉框 ========== */
QComboBox {
    background-color: #1a1f36;
    color: #e2e8f0;
    border: 1px solid #2a2f45;
    border-radius: 6px;
    padding: 6px 12px;
}

QComboBox:hover {
    border-color: #7c3aed;
}

QComboBox::drop-down {
    border: none;
    width: 24px;
}

QComboBox QAbstractItemView {
    background-color: #1a1f36;
    color: #e2e8f0;
    border: 1px solid #2a2f45;
    selection-background-color: #7c3aed;
}

/* ========== 分组框 ========== */
QGroupBox {
    background-color: #111827;
    border: 1px solid #2a2f45;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 16px;
    font-weight: bold;
}

QGroupBox::title {
    color: #8b5cf6;
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
}

/* ========== 标签 ========== */
QLabel {
    color: #e2e8f0;
    background-color: transparent;
}

QLabel#titleLabel {
    font-size: 18px;
    font-weight: bold;
    color: #e2e8f0;
}

QLabel#subtitleLabel {
    font-size: 14px;
    color: #94a3b8;
}

QLabel#recordingLabel {
    color: #ef4444;
    font-weight: bold;
}

QLabel#timerLabel {
    font-size: 16px;
    font-weight: bold;
    color: #e2e8f0;
    font-family: "Consolas", "Courier New", monospace;
}

/* ========== 对话框 ========== */
QDialog {
    background-color: #111827;
}

QMessageBox {
    background-color: #111827;
}

QMessageBox QLabel {
    color: #e2e8f0;
}

/* ========== 工具提示 ========== */
QToolTip {
    background-color: #1a1f36;
    color: #e2e8f0;
    border: 1px solid #7c3aed;
    border-radius: 4px;
    padding: 4px 8px;
}

/* ========== 进度条 ========== */
QProgressBar {
    background-color: #1a1f36;
    border: 1px solid #2a2f45;
    border-radius: 4px;
    text-align: center;
    color: #e2e8f0;
    height: 8px;
}

QProgressBar::chunk {
    background-color: #7c3aed;
    border-radius: 4px;
}

/* ========== 菜单 ========== */
QMenu {
    background-color: #1a1f36;
    border: 1px solid #2a2f45;
    border-radius: 6px;
    padding: 4px;
}

QMenu::item {
    padding: 8px 24px;
    border-radius: 4px;
}

QMenu::item:selected {
    background-color: #7c3aed;
    color: white;
}

/* ========== 分割线 ========== */
QSplitter::handle {
    background-color: #2a2f45;
    width: 1px;
    height: 1px;
}

/* ========== 自定义气泡样式 ========== */
/* 这些类名在代码中动态设置 objectName */
QFrame#bubbleSelf {
    background-color: #1e1b4b;
    border: 1px solid #3730a3;
    border-radius: 10px;
    padding: 10px 14px;
}

QFrame#bubbleOther {
    background-color: #172554;
    border: 1px solid #1e3a5f;
    border-radius: 10px;
    padding: 10px 14px;
}

QFrame#bubbleStranger {
    background-color: #1c1917;
    border: 1px solid #292524;
    border-radius: 10px;
    padding: 10px 14px;
}

QFrame#bubblePlaying {
    background-color: #2e1065;
    border: 2px solid #8b5cf6;
    border-radius: 10px;
    padding: 10px 14px;
}

QFrame#summaryCard {
    background-color: #111827;
    border: 1px solid #2a2f45;
    border-radius: 8px;
    padding: 12px;
}
"""


def get_bubble_style(speaker_name, is_playing=False):
    """
    根据发言人类型返回气泡样式
    :param speaker_name: 发言人名称
    :param is_playing: 是否正在播放
    :return: QSS 样式字符串
    """
    if is_playing:
        return """
            background-color: #2e1065;
            border: 2px solid #8b5cf6;
            border-radius: 10px;
            padding: 10px 14px;
        """

    # 陌生人样式
    if speaker_name.startswith("陌生人"):
        return """
            background-color: #1c1917;
            border: 1px solid #292524;
            border-radius: 10px;
            padding: 10px 14px;
        """

    # 已注册发言人样式（根据名字哈希选择不同色调）
    hash_val = hash(speaker_name) % 3
    if hash_val == 0:
        return """
            background-color: #1e1b4b;
            border: 1px solid #3730a3;
            border-radius: 10px;
            padding: 10px 14px;
        """
    elif hash_val == 1:
        return """
            background-color: #172554;
            border: 1px solid #1e3a5f;
            border-radius: 10px;
            padding: 10px 14px;
        """
    else:
        return """
            background-color: #1a1f36;
            border: 1px solid #2a2f45;
            border-radius: 10px;
            padding: 10px 14px;
        """
