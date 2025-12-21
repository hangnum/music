"""
Python Music Player - Main Entry Point

A high-quality local music player application.
"""

import sys
import os

# Add src to path
src_path = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, src_path)

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt


def main():
    """Application entry point"""
    # Enable high DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    
    app = QApplication(sys.argv)
    app.setApplicationName("Python Music Player")
    app.setApplicationVersion("1.0.0")
    
    # === Single Instance Detection ===
    from core.single_instance import SingleInstanceManager
    instance_manager = SingleInstanceManager("PythonMusicPlayer")
    
    if instance_manager.is_running():
        # Existing instance running, send activation message and exit
        instance_manager.send_activation_message()
        sys.exit(0)
    
    # Start local server, listen for activation requests from other instances
    instance_manager.start_server()
    
    # Create dependency container (composition root)
    from app.container_factory import AppContainerFactory
    container = AppContainerFactory.create(use_qt_dispatcher=True)
    
    # Import main window (lazy import to avoid circular dependencies)
    from ui.main_window import MainWindow
    
    window = MainWindow(container)
    
    # Connect activation signal to main window
    instance_manager.activation_requested.connect(window.activate_from_external)
    
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

