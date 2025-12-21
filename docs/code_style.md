# Python Music Player Code Guidelines

This document defines the project's code style guidelines. All new and refactored code should follow these standards.
The code style should remain concise, avoiding over-engineering while maintaining good project standards and low coupling.

## 1. Import Guidelines

### 1.1 Import Order

Organize import statements in the following order, with a blank line between each group:

```python
# 1. Standard library
import os
import sys
import logging
from typing import List, Optional, Dict

# 2. Third-party libraries
from PyQt6.QtWidgets import QWidget
import yaml

# 3. Local modules
from core.database import DatabaseManager
from models.track import Track
```

### 1.2 Prohibit the use of sys.path.insert

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

> **Note**: The project uniformely sets `PYTHONPATH` through `main.py`, so there is no need to manually add paths in each module.

---

## 2. Logging Guidelines

### 2.1 Use the logging module

Each module defines a logger at the beginning of the file:

```python
import logging

logger = logging.getLogger(__name__)
```

### 2.2 Log Levels

| Level | Usage |
|------|------|
| `DEBUG` | Debug information (e.g., metadata parsing details) |
| `INFO` | Normal operations (e.g., scan start/completion) |
| `WARNING` | Recoverable errors (e.g., failed to add a single track) |
| `ERROR` | Severe errors (e.g., database connection failure) |

---

## 3. Type Hints

### 3.1 Function Signatures

All public methods must have type hints:

```python
def get_track(self, track_id: str) -> Optional[Track]:
    """Get a single track"""
    ...
```

### 3.2 Complex Types

Use the `typing` module:

```python
from typing import List, Dict, Optional, Callable

def scan(self, directories: List[str], 
         callback: Optional[Callable[[int, int, str], None]] = None) -> int:
    ...
```

---

## 4. Docstring

### 4.1 Module Level

Every file beginning:

```python
"""
Media Library Service Module

Manages scanning, indexing, and search functionality for the media library.
"""
```

### 4.2 Class Level

```python
class LibraryService:
    """
    Media Library Service
    
    Provides scanning, indexing, and search functionality for the media library.
    """
```

### 4.3 Method Level

Complex methods use the full format:

```python
def scan(self, directories: List[str]) -> int:
    """
    Scan directories
    
    Args:
        directories: List of directories
        
    Returns:
        int: Number of tracks scanned
    """
```

Simple methods can use a single line:

```python
def stop_scan(self) -> None:
    """Stop scanning"""
    self._stop_scan.set()
```

---

## 5. Naming Conventions

| Type | Style | Example |
|------|------|------|
| Module | snake_case | `library_service.py` |
| Class | PascalCase | `LibraryService` |
| Function/Method | snake_case | `get_all_tracks` |
| Variable | snake_case | `track_count` |
| Constant | UPPER_SNAKE | `SUPPORTED_FORMATS` |
| Private Member | _prefix | `_db`, `_event_bus` |

---

## 6. Code Organization

### 6.1 Class Structure Order

```python
class MyClass:
    # 1. Class Constants
    CONSTANT = "value"
    
    # 2. __init__
    def __init__(self):
        ...
    
    # 3. Public properties (@property)
    @property
    def name(self) -> str:
        ...
    
    # 4. Public methods
    def do_something(self):
        ...
    
    # 5. Private methods
    def _internal_helper(self):
        ...
```

### 6.2 File Length

* Single files should generally not exceed **600 lines**.
* When exceeded, split functional modules (e.g., move core logic of `LibraryService` to specialized scanners or parsers).
* Maintain low coupling between modules using event-driven communication (EventBus).

---

## 7. Exception Handling

### 7.1 Basic Pattern

```python
try:
    result = risky_operation()
except SpecificError as e:
    logger.warning("Operation failed: %s", e)
    return default_value
```

### 7.2 Avoid bare except

❌ **不推荐**:

```python
except:
    pass
```

✅ **推荐**:

```python
except Exception as e:
    logger.debug("Ignored error: %s", e)
```
