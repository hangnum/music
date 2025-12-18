"""
测试配置文件

统一设置 Python 路径，避免在各测试文件中使用 sys.path.insert。
"""

import sys
from pathlib import Path

# 将 src 目录添加到 Python 路径
src_path = Path(__file__).parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))
