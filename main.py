# -*- coding: utf-8 -*-
"""
智会 MeetWise - AI 会议纪要生成器
程序入口文件
"""

import sys
import os
import logging

# 配置日志：控制台显示 WARNING 及以上，文件保留详细日志
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.WARNING)
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

file_handler = logging.FileHandler('meetwise.log', encoding='utf-8')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

logger.addHandler(console_handler)
logger.addHandler(file_handler)

# 确保项目根目录在 Python 路径中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    """主函数"""
    os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"

    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import Qt

    app = QApplication(sys.argv)
    app.setApplicationName("智会 MeetWise")
    app.setOrganizationName("MeetWise")

    def exception_hook(exctype, value, traceback):
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

    from meetwise.view.main_window import MainWindow
    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
