# Python Music Player 代码规范

本文档定义项目的代码风格规范，所有新代码和重构代码都应遵循这些规范。
代码风格在保持良好的项目规范和低耦合性下，保持简洁，避免过度设计。

## 1. 导入规范

### 1.1 导入顺序

按以下顺序组织导入语句，每组之间空一行：

```python
# 1. 标准库
import os
import sys
import logging
from typing import List, Optional, Dict

# 2. 第三方库
from PyQt6.QtWidgets import QWidget
import yaml

# 3. 本地模块
from core.database import DatabaseManager
from models.track import Track
```

### 1.2 禁止使用 sys.path.insert

❌ **不推荐**:

```python
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from core.database import DatabaseManager
```

✅ **推荐**:

```python
from core.database import DatabaseManager
```

> **说明**: 项目通过 `main.py` 统一设置 `PYTHONPATH`，无需在各模块中手动添加路径。

---

## 2. 日志规范

### 2.1 使用 logging 模块

每个模块在文件开头定义 logger:

```python
import logging

logger = logging.getLogger(__name__)
```

### 2.2 日志级别

| 级别 | 用途 |
|------|------|
| `DEBUG` | 调试信息（如元数据解析细节） |
| `INFO` | 正常操作（如扫描开始/完成） |
| `WARNING` | 可恢复错误（如单曲添加失败） |
| `ERROR` | 严重错误（如数据库连接失败） |

---

## 3. 类型提示

### 3.1 函数签名

所有公开方法必须有类型提示:

```python
def get_track(self, track_id: str) -> Optional[Track]:
    """获取单个曲目"""
    ...
```

### 3.2 复杂类型

使用 `typing` 模块:

```python
from typing import List, Dict, Optional, Callable

def scan(self, directories: List[str], 
         callback: Optional[Callable[[int, int, str], None]] = None) -> int:
    ...
```

---

## 4. 文档字符串 (Docstring)

### 4.1 模块级

每个文件开头:

```python
"""
媒体库服务模块

管理媒体库的扫描、索引和搜索功能。
"""
```

### 4.2 类级

```python
class LibraryService:
    """
    媒体库服务
    
    提供媒体库的扫描、索引和搜索功能。
    """
```

### 4.3 方法级

复杂方法使用完整格式:

```python
def scan(self, directories: List[str]) -> int:
    """
    扫描目录
    
    Args:
        directories: 目录列表
        
    Returns:
        int: 扫描到的曲目数量
    """
```

简单方法可使用单行:

```python
def stop_scan(self) -> None:
    """停止扫描"""
    self._stop_scan.set()
```

---

## 5. 命名规范

| 类型 | 风格 | 示例 |
|------|------|------|
| 模块 | snake_case | `library_service.py` |
| 类 | PascalCase | `LibraryService` |
| 函数/方法 | snake_case | `get_all_tracks` |
| 变量 | snake_case | `track_count` |
| 常量 | UPPER_SNAKE | `SUPPORTED_FORMATS` |
| 私有成员 | _前缀 | `_db`, `_event_bus` |

---

## 6. 代码组织

### 6.1 类结构顺序

```python
class MyClass:
    # 1. 类常量
    CONSTANT = "value"
    
    # 2. __init__
    def __init__(self):
        ...
    
    # 3. 公开属性 (@property)
    @property
    def name(self) -> str:
        ...
    
    # 4. 公开方法
    def do_something(self):
        ...
    
    # 5. 私有方法
    def _internal_helper(self):
        ...
```

### 6.2 文件长度

- 单个文件不超过 **600 行**
- 超过时考虑拆分功能模块

---

## 7. 异常处理

### 7.1 基本模式

```python
try:
    result = risky_operation()
except SpecificError as e:
    logger.warning("操作失败: %s", e)
    return default_value
```

### 7.2 避免空 except

❌ **不推荐**:

```python
except:
    pass
```

✅ **推荐**:

```python
except Exception as e:
    logger.debug("忽略的错误: %s", e)
```
