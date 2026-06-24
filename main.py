# -*- coding: utf-8 -*-
"""
智会 MeetWise - AI 会议纪要生成器
程序入口文件
"""

import sys
import os

# 确保项目根目录在 Python 路径中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    """主函数"""
    # 高 DPI 支持（必须在 QApplication 之前设置）
    os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"

    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import Qt

    # 创建应用
    app = QApplication(sys.argv)
    app.setApplicationName("智会 MeetWise")
    app.setOrganizationName("MeetWise")

    # 全局异常处理
    def exception_hook(exctype, value, traceback):
        """全局异常捕获"""
        import traceback as tb
        error_msg = "".join(tb.format_exception(exctype, value, traceback))
        print(f"[全局异常] {error_msg}")
        try:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(None, "程序错误", f"发生未预期的错误：\n{str(value)}")
        except:
            pass
        sys.__excepthook__(exctype, value, traceback)

    sys.excepthook = exception_hook

    # 创建并显示主窗口
    from meetwise.view.main_window import MainWindow
    window = MainWindow()
    window.show()

    # 运行事件循环
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
