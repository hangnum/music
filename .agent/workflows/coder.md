---
description: Python 编码工作流。当需要实现新功能、编写代码、添加测试或修改现有实现时使用。
---

# Python 编码工作流

结构化的编码流程，确保代码质量和文档完整性。

---

## 阶段概览

```
需求分析 → 文档阅读 → 计划制定 → 代码实现 → 测试编写 → 文档更新
```

---

## 阶段 1: 需求深度分析

在编写任何代码之前，进行序列化思考：

### 分析框架

```markdown
## 需求拆解

### 1. 核心目标
[用户想要达成什么？]

### 2. 输入与输出
- 输入: [函数/API 接收什么？]
- 输出: [期望的结果是什么？]

### 3. 约束条件
- 技术约束: [必须使用的技术栈、兼容性要求]
- 业务约束: [性能要求、安全要求]

### 4. 影响范围
- 需要修改的文件: [列表]
- 可能影响的现有功能: [列表]

### 5. 边界情况
[需要处理的异常和边界情况]
```

---

## 阶段 2: 阅读项目文档

// turbo

根据需求类型，阅读相关文档：

| 需求类型 | 必读文档 |
|---------|---------|
| 新功能 | `docs/architecture.md`, `docs/technical_design.md` |
| API 变更 | `docs/api.md` |
| 编码实现 | `docs/code_style.md` |
| 构建打包 | `docs/build.md` |

```bash
# 列出所有文档
ls docs/
```

### 关键文档

- **架构设计**: `docs/architecture.md` - 分层架构、组件职责
- **技术设计**: `docs/technical_design.md` - 详细实现方案
- **代码规范**: `docs/code_style.md` - 命名、类型提示、错误处理
- **API 文档**: `docs/api.md` - 公共接口定义

---

## 阶段 3: 制定执行计划

### 计划模板

```markdown
## 执行计划

### 目标
[简述要实现的功能]

### 文件变更

| 文件 | 操作 | 说明 |
|------|------|------|
| `path/to/file.py` | 新建/修改 | [变更内容] |

### 实现步骤

1. [ ] [步骤 1]
2. [ ] [步骤 2]
3. [ ] [步骤 3]

### 依赖关系
[步骤之间的依赖，哪些可以并行]

### 验证标准
[如何验证实现正确]
```

---

## 阶段 4: 代码实现

### 实现原则

1. **谨慎**: 每个变更都要考虑影响范围
2. **简洁**: 代码应该简单直接，避免过度设计
3. **渐进**: 分小步骤实现，每步可验证

### 编码规范检查

实现时遵循 `docs/code_style.md`:

- [ ] 使用 `from __future__ import annotations`
- [ ] 完整的类型提示
- [ ] 模块级 logger: `logger = logging.getLogger(__name__)`
- [ ] 函数 docstring (Google 风格)
- [ ] 异常使用自定义类型

### 架构层级遵循

```
UI (src/ui/) → Service (src/services/) → Core (src/core/) → Data (src/models/)
```

- UI 层只调用 Service 层
- Service 层编排业务逻辑
- Core 层提供基础能力
- 使用 EventBus 进行跨层通信

---

## 阶段 5: 测试编写

### 测试决策

完成实现后评估是否需要测试：

| 情况 | 需要测试 |
|------|---------|
| 新增公共 API / Service 方法 | ✅ 是 |
| 修改核心业务逻辑 | ✅ 是 |
| 修复重要 Bug | ✅ 是 |
| 简单配置变更 | ❌ 否 |
| 纯 UI 样式调整 | ❌ 否 |

### 测试规范

测试文件放置：`tests/` 目录，与源码结构对应

```python
# tests/test_<module>.py
import pytest
from src.services.my_service import MyService

class TestMyService:
    """MyService 测试套件"""
    
    def test_basic_functionality(self):
        """测试基本功能"""
        # Arrange
        service = MyService()
        
        # Act
        result = service.do_something()
        
        # Assert
        assert result == expected
```

// turbo

### 运行测试

```bash
python -m pytest tests/ -v
```

// turbo

运行特定测试：

```bash
python -m pytest tests/test_module.py -v
```

---

## 阶段 6: 文档更新

### 需要更新的文档

| 变更类型 | 更新文档 |
|---------|---------|
| 新增 API / 公共方法 | `docs/api.md` |
| 架构变更 | `docs/architecture.md` |
| 新功能 / 模块 | `docs/technical_design.md` |
| 新依赖 / 配置 | `GEMINI.md` |

### 更新原则

- 保持文档与代码同步
- 描述 "是什么" 和 "为什么"
- 提供使用示例

---

## 快速检查清单

实现完成后确认：

- [ ] 需求分析完整，边界情况已考虑
- [ ] 代码遵循架构分层
- [ ] 类型提示完整
- [ ] 错误处理恰当
- [ ] 必要的测试已编写
- [ ] 测试全部通过
- [ ] 相关文档已更新
