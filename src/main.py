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
    
    # === 单实例检测 ===
    from core.single_instance import SingleInstanceManager
    instance_manager = SingleInstanceManager("PythonMusicPlayer")
    
    if instance_manager.is_running():
        # 已有实例运行，发送激活消息并退出
        instance_manager.send_activation_message()
        sys.exit(0)
    
    # 启动本地服务器，监听其他实例的激活请求
    instance_manager.start_server()
    
    # 创建依赖容器（组合根）
    from app.container_factory import AppContainerFactory
    container = AppContainerFactory.create(use_qt_dispatcher=True)
    
    # 导入主窗口（延迟导入避免循环依赖）
    from ui.main_window import MainWindow
    
    window = MainWindow(container)
    
    # 连接激活信号到主窗口
    instance_manager.activation_requested.connect(window.activate_from_external)
    
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

