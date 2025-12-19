"""
Python Music Player - 主入口

一个高质量的本地音乐播放器应用。
"""

import sys
import os

# 添加src到路径
src_path = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, src_path)

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt


def main():
    """应用程序入口"""
    # 启用高DPI缩放
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    
    app = QApplication(sys.argv)
    app.setApplicationName("Python Music Player")
    app.setApplicationVersion("1.0.0")
    
    # 创建依赖容器（组合根）
    from app.container_factory import AppContainerFactory
    container = AppContainerFactory.create(use_qt_dispatcher=True)
    
    # 导入主窗口（延迟导入避免循环依赖）
    from ui.main_window import MainWindow
    
    window = MainWindow(container)
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

