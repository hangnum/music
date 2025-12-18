"""
测试配置文件

统一设置 Python 路径，避免在各测试文件中使用 sys.path.insert。
提供 PyQt6 测试所需的 QApplication fixture。
"""

import sys
from pathlib import Path

import pytest

# 将 src 目录添加到 Python 路径
src_path = Path(__file__).parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))


@pytest.fixture(scope="session")
def qapp():
    """
    Create QApplication for all tests.
    
    Uses session scope to avoid creating multiple QApplication instances.
    """
    from PyQt6.QtWidgets import QApplication
    
    # 检查是否已存在 QApplication 实例
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app
