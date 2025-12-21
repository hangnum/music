---
description: 项目严格全面分析工作流。当需要基于文档对项目进行全功能查验、寻找Bug/冗余/性能/设计问题，并制定详细并行/串行计划时使用。
---

# 项目全面审计工作流 (Project Audit)

本工作流通过严格对照项目文档，对代码库进行全方位深度审计。

---

## 上下文管理设计 (Context Management)

### Artifact 目录结构

所有审计产物存放在 `<brain>/<conversation-id>/` 下：

```text
<brain>/<conversation-id>/
├── task.md                 # 任务进度跟踪
├── audit_plan.md           # 阶段一产出：审计计划
├── audit_state.md          # 状态文件：跨阶段上下文
├── findings/               # 阶段二产出：各模块发现
│   ├── core_findings.md
│   ├── services_findings.md
│   └── ui_findings.md
└── audit_report.md         # 阶段四产出：最终报告
```

### 状态文件 (audit_state.md)

此文件是**上下文中枢**，在各阶段间传递关键信息。Agent 在每个阶段结束时更新，下一阶段开始时读取。

```markdown
# Audit State

## Phase: [PLANNING | EXECUTION | ANALYSIS | REPORTING]

## Documentation Summary
<!-- 阶段一填写：文档要点摘要，供后续阶段快速回顾 -->
- architecture.md: [核心架构要点]
- api.md: [API 设计要点]

## Module Registry
<!-- 阶段一填写：模块与文档的映射关系 -->
| Module | Related Docs | Execution Mode | Status |
|--------|--------------|----------------|--------|
| src/core/ | architecture.md | Serial | Pending |
| src/services/ | api.md | Serial | Pending |
| src/ui/ | - | Parallel | Pending |

## Findings Index
<!-- 阶段二更新：已发现问题的快速索引 -->
- [Critical] PlayerService: ...
- [Design] EventBus: ...

## Pending Actions
<!-- 跨阶段待办事项 -->
- [ ] 验证 XXX 模块的边界情况
```

### 上下文流转规则

| 阶段 | 输入 | 输出 | 更新 audit_state.md |
|------|------|------|---------------------|
| Planning | `docs/*` | `audit_plan.md` | 初始化 Phase, Documentation Summary, Module Registry |
| Execution | `audit_plan.md`, `audit_state.md` | `findings/*.md` | 更新 Module Status, Findings Index |
| Analysis | `audit_state.md`, codebase | 补充 findings | 更新 Pending Actions |
| Reporting | `audit_state.md`, `findings/*` | `audit_report.md` | 标记 Phase = COMPLETE |

---

## 阶段一：文档研读与计划制定 (Planning)

**目标**：建立文档-代码映射，制定可执行的审计计划。

### 步骤

1. **扫描文档目录**

   ```bash
   ls -la docs/
   ```

2. **阅读核心文档** (使用 `view_file`)
   - `docs/architecture.md` - 架构设计
   - `docs/api.md` - API 规范
   - `docs/code_style.md` - 代码规范 (作为审计标准)
   - 其他功能性文档

3. **创建 `audit_state.md`**
   - 初始化 `Phase: PLANNING`
   - 填写 `Documentation Summary`：提炼每个文档的核心要点（2-3 句话）
   - 填写 `Module Registry`：列出所有模块、关联文档、执行模式

4. **创建 `audit_plan.md`**
   包含以下章节：

   ```markdown
   # Audit Plan

   ## Scope
   [审计范围边界]

   ## Audit Dimensions
   - Functional Consistency
   - Code Quality (DRY, Dead Code)
   - Potential Bugs
   - Performance
   - Design Violations

   ## Execution Strategy

   ### Parallel Tasks
   <!-- 可并行执行的独立模块 -->
   | Task ID | Module | Description |
   |---------|--------|-------------|
   | P1 | src/ui/widgets/ | UI 组件审计 |
   | P2 | src/models/ | 数据模型审计 |

   ### Serial Tasks
   <!-- 需串行执行的有依赖模块，按执行顺序排列 -->
   | Order | Task ID | Module | Depends On |
   |-------|---------|--------|------------|
   | 1 | S1 | src/core/ | - |
   | 2 | S2 | src/services/ | S1 |
   | 3 | S3 | src/app/ | S1, S2 |
   ```

5. **提交审查**
   使用 `notify_user` 提交 `audit_plan.md`，等待用户批准。

---

## 阶段二：执行审计 (Execution)

**目标**：按计划检查代码，记录发现。

### 启动前

1. **读取 `audit_state.md`**，获取 Module Registry 和 Documentation Summary。
2. 更新 `Phase: EXECUTION`。

### 并行任务 (Parallel Tasks)

对于标记为 Parallel 的模块：

- 可使用多个 `view_file` / `codebase_search` 并行阅读。
- 每个模块的发现写入 `findings/<module>_findings.md`。

### 串行任务 (Serial Tasks)

按 Order 顺序执行：

1. 阅读当前模块代码。
2. 对照 `Documentation Summary` 中对应文档的要点进行验证。
3. 记录发现并**立即更新 `audit_state.md` 的 Findings Index**。
4. 完成后将 Module Registry 中的 Status 更新为 `Done`。

### Findings 文件格式

```markdown
# [Module Name] Audit Findings

## Summary
[一句话总结]

## Issues

### [SEV-1: Critical] Issue Title
- **Location**: `file.py:123`
- **Description**: ...
- **Evidence**: `代码片段`
- **Recommendation**: ...

### [SEV-2: Design] Issue Title
...
```

---

## 阶段三：静态分析 (Analysis)

**目标**：使用工具辅助发现遗漏问题。

// turbo

1. **大文件检测**（可能需拆分）

   ```powershell
   # Windows PowerShell
   Get-ChildItem -Path src -Recurse -Filter *.py | ForEach-Object { $_ | Add-Member -NotePropertyName Lines -NotePropertyValue (Get-Content $_.FullName | Measure-Object -Line).Lines -PassThru } | Sort-Object Lines -Descending | Select-Object -First 10 Name, Lines
   ```

// turbo
2. **TODO/FIXME 扫描**

   ```powershell
   Select-String -Path "src\*.py" -Pattern "TODO|FIXME|HACK|XXX" -Recurse
   ```

3. **更新 `audit_state.md`**
   - 将工具发现的问题添加到 `Pending Actions`。

---

## 阶段四：产出报告 (Reporting)

**目标**：整合所有发现，输出最终报告。

### 步骤

1. **读取上下文**
   - `audit_state.md` - 获取 Findings Index
   - `findings/*.md` - 读取详细发现

2. **创建 `audit_report.md`**

   ```markdown
   # Project Audit Report

   **Date**: [日期]
   **Scope**: [审计范围]

   ## Executive Summary
   [一段话概述]

   ## Findings by Severity

   ### Critical (SEV-1)
   [列表]

   ### Design Issues (SEV-2)
   [列表]

   ### Performance (SEV-3)
   [列表]

   ### Code Smells (SEV-4)
   [列表]

   ## Statistics
   | Category | Count |
   |----------|-------|
   | Critical | X |
   | Design | X |
   | Performance | X |
   | Code Smells | X |

   ## Recommendations
   [修复优先级建议]
   ```

3. **更新 `audit_state.md`**
   - 设置 `Phase: COMPLETE`

4. **通知用户**
   使用 `notify_user` 提交 `audit_report.md`。

---

## 验证清单 (Checklist)

- [ ] `audit_state.md` 是否在每个阶段都已更新？
- [ ] 所有 `findings/*.md` 是否使用统一格式？
- [ ] `audit_plan.md` 是否明确区分了 Parallel/Serial 任务？
- [ ] 是否对照文档逐一核验了功能？
- [ ] 是否覆盖了 Bug、冗余、性能、设计四个维度？
