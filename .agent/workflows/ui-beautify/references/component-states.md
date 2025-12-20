# 组件状态详细示例

本文档提供各类 UI 组件的状态实现示例。

---

## 按钮类型

### 1. Primary Button (主要操作)

用于：保存、确认、提交等主要操作

```python
# Python 应用样式
from ui.styles.theme_manager import ThemeManager

save_btn = QPushButton("保存")
save_btn.setStyleSheet(ThemeManager.get_primary_button_style())
```

```css
/* QSS 完整定义 */
QPushButton#primaryButton {
    background-color: #3FB7A6;
    color: #FFFFFF;
    font-weight: 600;
    border: 1px solid #2FA191;
    padding: 8px 20px;
    border-radius: 8px;
}

QPushButton#primaryButton:hover {
    background-color: #5BC0B0;
    border-color: #3FB7A6;
}

QPushButton#primaryButton:pressed {
    background-color: #24877A;
}

QPushButton#primaryButton:disabled {
    background-color: #1E2633;
    color: #5E6775;
    border-color: transparent;
}

QPushButton#primaryButton:focus {
    border: 2px solid #3FB7A6;
}
```

### 2. Secondary Button (次要操作)

用于：取消、返回等次要操作

```css
QPushButton {
    background-color: transparent;
    border: 1px solid #202838;
    border-radius: 8px;
    padding: 6px 12px;
    color: #E6E8EC;
    font-weight: 500;
}

QPushButton:hover {
    background-color: #18202C;
    border-color: #2B3547;
}

QPushButton:pressed {
    background-color: #1C2734;
    color: #D2D8E1;
}

QPushButton:disabled {
    color: #5E6775;
    background-color: transparent;
    border-color: transparent;
}
```

### 3. Ghost Button (幽灵按钮)

用于：工具栏、控制按钮等

```css
QPushButton#controlButton {
    border-radius: 6px;
    padding: 8px;
    background-color: transparent;
    border: 1px solid transparent;
}

QPushButton#controlButton:hover {
    background-color: #1D2633;
    border-color: #2A3446;
}

QPushButton#controlButton:checked {
    color: #3FB7A6;
    background-color: rgba(63, 183, 166, 0.16);
}
```

### 4. Icon Button (图标按钮)

用于：播放/暂停等核心操作

```css
/* 圆形播放按钮 */
QPushButton#PlayPauseButton {
    background-color: #3FB7A6;
    color: #ffffff;
    border-radius: 24px; /* 48px 固定尺寸的一半 */
    padding: 0px;
    border: 1px solid #2FA191;
    min-width: 48px;
    min-height: 48px;
    max-width: 48px;
    max-height: 48px;
}

QPushButton#PlayPauseButton:hover {
    background-color: #5BC0B0;
}

QPushButton#PlayPauseButton:pressed {
    background-color: #24877A;
}
```

---

## 输入控件

### 1. Text Input (文本输入框)

```css
QLineEdit {
    background-color: #141923;
    border: 1px solid #263041;
    border-radius: 8px;
    padding: 8px 12px;
    color: #ffffff;
    selection-background-color: #3FB7A6;
}

QLineEdit:focus {
    border: 1px solid #3FB7A6;
    background-color: #18202B;
}

QLineEdit:disabled {
    background-color: #0E1116;
    color: #5E6775;
    border-color: #1E2633;
}

QLineEdit::placeholder {
    color: #5E6775;
}
```

### 2. Text Area (多行文本)

```css
QTextEdit, QPlainTextEdit {
    background-color: #141923;
    border: 1px solid #263041;
    border-radius: 8px;
    padding: 8px 12px;
    color: #ffffff;
    selection-background-color: #3FB7A6;
}

QTextEdit:focus, QPlainTextEdit:focus {
    border: 1px solid #3FB7A6;
}
```

### 3. Combo Box (下拉选择)

```css
QComboBox {
    background-color: #141923;
    border: 1px solid #263041;
    border-radius: 8px;
    padding: 6px 12px;
    color: #E6E8EC;
}

QComboBox:hover {
    border-color: #3FB7A6;
}

QComboBox::drop-down {
    border: none;
    width: 24px;
}

QComboBox::down-arrow {
    /* 使用自定义图标 */
}

QComboBox QAbstractItemView {
    background-color: #151B26;
    border: 1px solid #253043;
    selection-background-color: #3FB7A6;
}
```

---

## 滑块控件

### Horizontal Slider (水平滑块)

用于：音量控制、进度条

```css
QSlider::groove:horizontal {
    border: none;
    height: 4px;
    background: #252E3B;
    border-radius: 2px;
}

QSlider::sub-page:horizontal {
    background: #3FB7A6;
    border-radius: 2px;
}

QSlider::handle:horizontal {
    background: #E6E8EC;
    border: none;
    width: 12px;
    height: 12px;
    margin: -4px 0;
    border-radius: 6px;
}

QSlider::handle:horizontal:hover {
    background: #FFFFFF;
    width: 14px;
    height: 14px;
    margin: -5px 0;
}

QSlider::handle:horizontal:pressed {
    background: #3FB7A6;
}
```

---

## 列表与表格

### List Widget

```css
QListWidget {
    background-color: #0E1116;
    border: none;
    outline: none;
}

QListWidget::item {
    padding: 8px 12px;
    border-radius: 8px;
    margin: 2px 4px;
}

QListWidget::item:hover {
    background-color: #18202C;
}

QListWidget::item:selected {
    background-color: rgba(63, 183, 166, 0.16);
    color: #DFF6F3;
}

QListWidget::item:selected:active {
    background-color: rgba(63, 183, 166, 0.20);
}
```

### Table Widget

```css
QTableView {
    background-color: #0E1116;
    border: none;
    gridline-color: transparent;
}

QTableView::item {
    padding: 6px 12px;
    border-bottom: 1px solid #18202C;
    color: #E6E8EC;
}

QTableView::item:hover {
    background-color: #18202C;
}

QTableView::item:selected {
    background-color: rgba(63, 183, 166, 0.18);
    color: #DFF6F3;
}

QHeaderView::section {
    background-color: #0E1116;
    color: #9AA2AF;
    padding: 8px 12px;
    border: none;
    border-bottom: 1px solid #1E2633;
    font-weight: 600;
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}
```

---

## 导航组件

### Sidebar Button

```css
QWidget#sidebar QPushButton {
    text-align: left;
    padding: 10px 16px;
    border: none;
    color: #A1A8B3;
    font-weight: 500;
    margin: 2px 8px;
    border-radius: 8px;
    font-size: 14px;
}

QWidget#sidebar QPushButton:hover {
    background-color: #1B2432;
    color: #ffffff;
}

QWidget#sidebar QPushButton:checked {
    background-color: #1C2A33;
    color: #DFF6F3;
    border-left: 3px solid #3FB7A6;
    font-weight: 600;
}
```

### Tab Bar

```css
QTabBar::tab {
    background-color: transparent;
    padding: 8px 16px;
    color: #9AA2AF;
    border-bottom: 2px solid transparent;
}

QTabBar::tab:hover {
    color: #E6E8EC;
}

QTabBar::tab:selected {
    color: #3FB7A6;
    border-bottom: 2px solid #3FB7A6;
}
```

---

## Python 代码示例

### 应用完整主题

```python
from PyQt6.QtWidgets import QApplication
from ui.styles.theme_manager import ThemeManager

app = QApplication([])
app.setStyleSheet(ThemeManager.get_global_stylesheet())
```

### 设置组件 ObjectName

```python
# 为样式选择器设置 objectName
play_btn = QPushButton()
play_btn.setObjectName("PlayPauseButton")

sidebar = QWidget()
sidebar.setObjectName("sidebar")

primary_btn = QPushButton("确认")
primary_btn.setObjectName("primaryButton")
```

### 动态更新样式

```python
# 根据状态切换样式
def update_button_state(button, is_active):
    if is_active:
        button.setProperty("active", True)
    else:
        button.setProperty("active", False)
    
    # 强制刷新样式
    button.style().unpolish(button)
    button.style().polish(button)
```
