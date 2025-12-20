---
description: UI 美化与品牌视觉设计工作流。当需要美化界面、应用设计系统、创建现代化 UI 组件、生成图标或进行品牌化设计时使用。
---

# UI 美化工作流

本工作流为 PyQt6 音乐播放器提供完整的 UI 美化指南，包含品牌审美标准、设计系统和组件模板。

---

## 第一部分：品牌视觉识别

### 品牌概述

| 属性 | 值 |
|------|-----|
| **主题名称** | Deep Ocean 2025 |
| **设计风格** | 现代深色、专业、沉浸式 |
| **品牌调性** | 高端、精致、专注内容 |
| **目标用户** | 追求高品质音乐体验的用户 |

### 核心色板

#### 主色 (Teal Accent)

```
品牌主色        #3FB7A6    RGB(63, 183, 166)    用于主要操作按钮、进度条、选中状态
主色 Hover      #5BC0B0    RGB(91, 192, 176)    悬停状态
主色 Active     #24877A    RGB(36, 135, 122)    按下状态
主色边框        #2FA191    RGB(47, 161, 145)    按钮边框
```

#### 深色背景

```
最深背景        #0E1116    RGB(14, 17, 22)      主背景
表面/卡片       #111620    RGB(17, 22, 32)      侧边栏
次级表面        #141923    RGB(20, 25, 35)      输入框背景
悬停表面        #18202C    RGB(24, 32, 44)      列表悬停
边框/分隔符    #1E2633    RGB(30, 38, 51)      分隔线
```

#### 文本色

```
主要文本        #E6E8EC    RGB(230, 232, 236)   标题、正文
次级文本        #9AA2AF    RGB(154, 162, 175)   标签、提示
禁用文本        #5E6775    RGB(94, 103, 117)    禁用状态
高亮文本        #DFF6F3    RGB(223, 246, 243)   选中项文本
```

### 排版规范

**字体系列**: `"Segoe UI Variable", "Segoe UI", "Microsoft YaHei", sans-serif`

| 级别 | 大小 | 权重 | 用途 |
|------|------|------|------|
| Display | 28px | 700 | 页面标题 |
| H1 | 24px | 600 | 区域标题 |
| H2 | 18px | 600 | 卡片标题 |
| Body | 14px | 400 | 正文内容 |
| Caption | 12px | 400 | 辅助说明 |
| Mini | 11px | 600 | 分类标签 |

### 间距系统 (4px 基准)

| Token | 值 | 用途 |
|-------|-----|------|
| `xs` | 4px | 紧凑元素内间距 |
| `sm` | 8px | 按钮 padding、图标间距 |
| `md` | 12px | 卡片内间距 |
| `lg` | 16px | 区域间距 |
| `xl` | 24px | 主要分隔 |
| `2xl` | 32px | 页面边距 |

### 圆角规范

| Token | 值 | 用途 |
|-------|-----|------|
| `sm` | 4px | 提示框、小标签 |
| `md` | 8px | 按钮、输入框、菜单项 |
| `lg` | 12px | 卡片、对话框 |
| `full` | 50% | 圆形按钮 (如播放按钮) |

---

## 第二部分：组件状态规范

每个交互组件必须实现 **5 种视觉状态**：

### 状态定义

| 状态 | 说明 | 视觉变化 |
|------|------|---------|
| Default | 初始状态 | 基准样式 |
| Hover | 鼠标悬停 | 背景变亮、边框强调 |
| Pressed | 按下 | 背景变暗 |
| Focus | 键盘焦点 | 品牌色边框 |
| Disabled | 禁用 | 透明度降低、灰色 |

### 按钮状态示例

详见 [references/component-states.md](references/component-states.md)

---

## 第三部分：美化检查清单

在进行 UI 美化时，按照以下清单逐项检查：

### 1. 颜色一致性

- [ ] 所有硬编码颜色值替换为 `DesignTokens` 或 CSS 变量
- [ ] 使用 `ThemeManager` 方法获取组件样式
- [ ] 检查黑暗模式下的对比度 (WCAG AA 标准)

### 2. 组件状态

- [ ] 5 种交互状态全部实现
- [ ] 状态过渡平滑 (使用 transition 属性)
- [ ] 禁用状态视觉明确

### 3. 间距与对齐

- [ ] 使用 8px 或 4px 基准的间距值
- [ ] 元素对齐检查 (左对齐/居中)
- [ ] 响应式布局处理

### 4. 排版

- [ ] 字体系列统一
- [ ] 字号层级合理
- [ ] 行高舒适 (1.4-1.6)

### 5. 视觉增强

- [ ] 适当使用圆角
- [ ] 分隔线/边框颜色协调
- [ ] 滚动条样式定制

---

## 第四部分：常用样式模板

### 主要操作按钮 (Primary Button)

```python
from ui.styles.theme_manager import ThemeManager

# 应用主按钮样式
button.setStyleSheet(ThemeManager.get_primary_button_style())
button.setObjectName("primaryButton")
```

### 侧边栏导航按钮

```python
button.setStyleSheet(ThemeManager.get_sidebar_button_style())
button.setCheckable(True)  # 支持选中状态
```

### 播放/暂停按钮 (Hero Button)

```python
play_btn.setObjectName("PlayPauseButton")
play_btn.setFixedSize(48, 48)
# 样式已在 dark_theme.qss 中定义
```

### 控制按钮 (图标按钮)

```python
ctrl_btn.setObjectName("controlButton")
# hover/checked 状态自动应用
```

---

## 第五部分：图标生成

### 使用脚本生成 SVG 图标

// turbo

```bash
python .agent/workflows/ui-beautify/scripts/generate_icon.py --name "settings" --type "cog"
```

详见 [scripts/generate_icon.py](scripts/generate_icon.py) 了解支持的图标类型。

### 图标规范

| 属性 | 值 |
|------|-----|
| 尺寸 | 24x24px (默认) |
| 线宽 | 2px |
| 颜色 | `currentColor` (继承父元素) |
| 格式 | SVG |

---

## 第六部分：样式验证

### 运行样式检查脚本

// turbo

```bash
python .agent/workflows/ui-beautify/scripts/style_checker.py src/ui/
```

该脚本检查：

- 硬编码颜色值
- 未使用 DesignTokens 的样式
- 缺失的组件状态

---

## 第七部分：相关文档

| 文档 | 说明 |
|------|------|
| [references/brand-aesthetic.md](references/brand-aesthetic.md) | 完整品牌审美指南 |
| [references/component-states.md](references/component-states.md) | 组件状态详细示例 |
| [references/qss-patterns.md](references/qss-patterns.md) | QSS 样式模式参考 |

---

## 审查清单

美化完成后检查：

- [ ] 使用 `DesignTokens` 和 `ThemeManager`
- [ ] 无硬编码 RGB/Hex 颜色值
- [ ] 所有交互状态实现完整
- [ ] 组件设置了 `objectName` 以便样式选择
- [ ] 代码通过 `style_checker.py` 检查
