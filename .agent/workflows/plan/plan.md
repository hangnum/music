---
description: 生成复杂任务的结构化计划。当用户需要规划、创建或管理计划文件时使用。
---

# 计划工作流

为复杂编码任务创建结构化计划，可选保存到 `.gemini/plans/` 目录。

---

## 核心规则

- 计划目录: `~/.gemini/plans/` (如 GEMINI_HOME 设置则为 `$GEMINI_HOME/plans/`)
- 仅读取代码库，不修改；只写入计划目录
- 磁盘计划需要 frontmatter：`name` 和 `description`
- 聊天草稿省略 frontmatter，从 `# Plan` 开始

---

## 任务类型

| 操作 | 说明 |
|------|------|
| 创建 | 扫描代码库 → 选择模板 → 起草 → 保存 |
| 列出 | 使用 `scripts/list_plans.py` 查看摘要 |
| 读取 | 加载并展示完整内容 |
| 更新 | 修订内容，保持 frontmatter |
| 删除 | 确认后删除文件 |

---

## 创建流程

1. **快速扫描**: 读取 README.md、docs/、ARCHITECTURE.md
2. **提问**: 最多 1-2 个问题，优先选择题
3. **识别**: 范围、约束、数据模型/API 影响
4. **起草**: 选择实现计划或概览模板
5. **输出**: 仅展示正文（无 frontmatter）
6. **确认**: 询问用户：修改 / 实现 / 保存

---

## 脚本使用

// turbo
创建计划：

```bash
python .agent/workflows/plan/scripts/create_plan.py \
  --name my-feature-plan \
  --description "实现某功能的计划" \
  --body-file /tmp/plan-body.md
```

// turbo
列出计划：

```bash
python .agent/workflows/plan/scripts/list_plans.py --query "feature"
```

---

## 计划文件格式

### Frontmatter (仅保存时)

```yaml
---
name: <plan-name>
description: <一行摘要>
---
```

### 实现计划模板

```markdown
# Plan

<1-3 句话：意图、范围、方法>

## Requirements
- <需求 1>
- <需求 2>

## Scope
- In: <包含>
- Out: <排除>

## Files and entry points
- <文件/模块 1>
- <文件/模块 2>

## Data model / API changes
- <如适用，描述 schema 或契约变更>

## Action items
[ ] <步骤 1>
[ ] <步骤 2>
[ ] <步骤 3>

## Testing and validation
- <测试命令或验证步骤>

## Risks and edge cases
- <风险 1>
- <风险 2>

## Open questions
- <问题 1>
```

### 概览计划模板

```markdown
# Plan

<1-3 句话：概览意图和范围>

## Overview
<高层次描述系统、流程或架构>

## Diagrams
<Mermaid 图或文本图>

## Key file references
- <文件 1>
- <文件 2>

## Current status
- <当前状态与待办>

## Action items
- None (仅概览)
```

---

## 写作指南

- 以 1 段简短描述开始
- 行动项使用动词开头，按顺序排列
- 根据复杂度调整项数：简单 1-2，复杂最多 10
- 避免模糊步骤和代码片段
- 始终包含测试/验证和风险/边缘情况
