---
description: 智能 Git 提交工作流。当需要分析未提交代码变更并生成规范化 commit 消息时使用。
---

# Git 智能提交工作流

分析项目中未提交的代码变更，生成符合 Conventional Commits 规范的提交消息。

---

## 步骤 1: 获取变更概览

// turbo

```bash
git status --porcelain
```

// turbo

```bash
git diff --stat
```

---

## 步骤 2: 获取详细变更

// turbo

```bash
git diff HEAD
```

对于已暂存的变更：

// turbo

```bash
git diff --cached
```

---

## 步骤 3: 分析变更

按以下维度分类变更：

| 类型 | 前缀 | 描述 |
|------|------|------|
| 新功能 | `feat` | 新增功能或模块 |
| 修复 | `fix` | Bug 修复 |
| 重构 | `refactor` | 代码重构，不改变功能 |
| 样式 | `style` | 代码格式、UI 样式调整 |
| 文档 | `docs` | 文档更新 |
| 测试 | `test` | 测试相关 |
| 构建 | `build` | 构建系统或依赖 |
| 杂务 | `chore` | 其他维护性工作 |

### 分析框架

```markdown
## 变更分析

### 主要变更类型
[feat/fix/refactor/style/docs/test/build/chore]

### 变更范围
[受影响的模块/组件]

### 变更摘要
- [变更 1]: [简述]
- [变更 2]: [简述]
- ...

### 关键决策
[为什么这样改？解决什么问题？]
```

---

## 步骤 4: 生成 Commit 消息

### 消息格式

```
<type>: <简短描述> (50 字符以内)

<变更点列表，每行以动词开头>

<可选：详细说明和影响>
```

### 示例

```txt
refactor: implement FFmpeg transcoding for extended audio format support

Add FFmpegTranscoder core module for on-the-fly audio format conversion
Implement MiniaudioEngine fallback strategy with VLC engine support
Add UnsupportedFormatError for graceful format handling
Create comprehensive design token system for UI consistency
Introduce theme manager for centralized styling
Update all UI components to use design tokens
Add transcoding tests and error handling

This enables support for a wider range of audio formats while maintaining
high-quality playback through intelligent transcoding fallbacks.
```

---

## 步骤 5: 暂存并提交

// turbo

暂存所有变更：

```bash
git add -A
```

提交变更（使用生成的消息）：

```bash
git commit -m "<生成的提交消息>"
```

> ⚠️ 对于多行消息，使用 `-m` 多次或交互式编辑。

---

## 提交消息规范

### 标题行

- 使用祈使语气（"Add feature" 而非 "Added feature"）
- 首字母大写
- 不超过 50 字符
- 不以句号结尾

### 正文

- 空一行后开始
- 每行不超过 72 字符
- 解释 **是什么** 和 **为什么**，而非 **怎么做**
- 使用列表项描述多个变更

### 变更点动词

| 动词 | 用于 |
|------|------|
| Add | 新增文件/功能 |
| Remove | 删除文件/功能 |
| Fix | 修复问题 |
| Update | 更新现有功能 |
| Refactor | 重构代码 |
| Improve | 优化/增强 |
| Implement | 实现新功能 |
| Introduce | 引入新概念/模块 |
| Create | 创建新组件 |
| Enhance | 增强功能 |

---

## 快速命令

// turbo

查看最近提交：

```bash
git log --oneline -5
```

// turbo

修改最后一次提交消息：

```bash
git commit --amend
```