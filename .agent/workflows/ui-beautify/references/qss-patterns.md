# QSS 样式模式参考

Qt Style Sheets (QSS) 常用模式和最佳实践。

---

## 选择器

```css
QPushButton { }           /* 类型选择 */
QPushButton#saveBtn { }   /* ID 选择 (objectName) */
QDialog QPushButton { }   /* 后代选择 */
```

### 伪状态

```css
QPushButton:hover { }
QPushButton:pressed { }
QPushButton:checked { }
QPushButton:disabled { }
QPushButton:focus { }
```

### 子控件

```css
QComboBox::drop-down { }
QScrollBar::handle { }
QSlider::groove:horizontal { }
QSlider::handle:horizontal { }
QMenu::item { }
```

---

## 常用属性

### 背景

```css
background-color: #0E1116;
background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
    stop:0 #1B2230, stop:1 #0E1116);
```

### 边框

```css
border: 1px solid #263041;
border: none;
border-radius: 8px;
```

### 间距

```css
padding: 8px 12px;
margin: 4px;
```

### 字体

```css
font-family: "Segoe UI";
font-size: 14px;
font-weight: 600;
```

---

## 项目模式

### 使用 DesignTokens

```python
from ui.resources.design_tokens import tokens

style = f"""
QPushButton {{
    background-color: {tokens.PRIMARY_500};
    border-radius: {tokens.RADIUS_MD}px;
}}
"""
```

### 使用 ThemeManager

```python
from ui.styles.theme_manager import ThemeManager
widget.setStyleSheet(ThemeManager.get_primary_button_style())
```

---

## QSS 限制

| CSS 属性 | 替代方案 |
|----------|---------|
| transition | QPropertyAnimation |
| box-shadow | QGraphicsDropShadowEffect |
| opacity | QGraphicsOpacityEffect |

### 强制刷新样式

```python
widget.style().unpolish(widget)
widget.style().polish(widget)
```
