# Spec: [模块名称]

> **使用说明**: 复制此模板并填写具体内容。删除本说明块和所有 `<!-- 注释 -->`。

---

## Meta

| 属性 | 值 |
|:---|:---|
| **PRD Reference** | @PRD: E-XX, E-YY |
| **Module** | `src/xxx.py` |
| **Status** | `draft` \| `in_progress` \| `completed` |
| **Created** | YYYY-MM-DD |
| **Last Updated** | YYYY-MM-DD |
| **Author** | @Author |

---

## 1. Task Definition

### 1.1 目标

<!-- 一句话描述这个模块要解决什么问题 -->

**核心目标**: 

### 1.2 触发条件

<!-- 什么情况下会调用这个模块 -->

| 触发场景 | 描述 |
|:---|:---|
| 场景 1 | 描述 |
| 场景 2 | 描述 |

### 1.3 非目标 (Out of Scope)

<!-- 明确列出本模块不负责的内容 -->

- 不负责 XXX
- 不处理 YYY

---

## 2. Context

### 2.1 前置依赖

<!-- 列出本模块依赖的其他模块或外部服务 -->

| 依赖项 | 类型 | 描述 |
|:---|:---|:---|
| `state.py` | 内部模块 | 状态类型定义 |
| `StateManager` | 内部类 | 状态持久化 |
| ChromaDB | 外部服务 | 向量数据库 |

### 2.2 调用方

<!-- 列出哪些模块/节点会调用本模块 -->

| 调用方 | 场景 |
|:---|:---|
| `nodes.py: xxx_node` | 描述场景 |
| `graph.py` | 描述场景 |

### 2.3 数据流

<!-- 可选：描述数据如何流经本模块 -->

```
输入 → [本模块处理] → 输出
         ↓
      [副作用：持久化/日志]
```

---

## 3. Interface

### 3.1 Input

<!-- 描述输入数据结构 -->

```python
# 主要输入参数
{
    "field_name": type,      # 描述
    "optional_field": Optional[type]  # 可选，描述
}
```

**示例**:
```python
{
    "delta": 0.5,           # 亲密度变化量
    "reason": "touch"       # 变化原因
}
```

### 3.2 Output

<!-- 描述输出数据结构 -->

```python
# 返回值结构
{
    "field_name": type,      # 描述
    "status": str            # 状态码
}
```

**示例**:
```python
{
    "intimacy_level": 30.5,
    "intimacy_rank": "stranger",
    "delta": 0.5,
    "reason": "touch",
    "rank_changed": False
}
```

### 3.3 Public Methods

<!-- 列出所有公开方法的签名和描述 -->

```python
class ModuleName:
    """模块描述"""
    
    def method_name(
        self, 
        param1: Type1, 
        param2: Optional[Type2] = None
    ) -> ReturnType:
        """
        方法描述
        
        Args:
            param1: 参数1描述
            param2: 参数2描述（可选）
        
        Returns:
            返回值描述
        
        Raises:
            ErrorType: 错误条件
        """
        pass
    
    def another_method(self) -> Dict[str, Any]:
        """获取当前状态"""
        pass
```

### 3.4 State Fields

<!-- 如果模块影响 LampState，列出相关字段 -->

| 字段名 | 类型 | 描述 |
|:---|:---|:---|
| `xxx_field` | `float` | 描述 |
| `yyy_status` | `Optional[str]` | 描述 |

---

## 4. Business Logic

### 4.1 核心规则

<!-- 列出业务规则，使用编号 -->

1. **规则一**: 描述
2. **规则二**: 描述
3. **规则三**: 描述

### 4.2 决策流程

<!-- 使用伪代码或流程图描述核心逻辑 -->

```
开始
  ↓
[检查条件 A]
  ├─ 是 → [执行动作 1]
  └─ 否 → [检查条件 B]
              ├─ 是 → [执行动作 2]
              └─ 否 → [默认处理]
  ↓
结束
```

**伪代码**:
```python
def process(input):
    if condition_a:
        return action_1()
    elif condition_b:
        return action_2()
    else:
        return default_action()
```

### 4.3 边界情况

<!-- 列出特殊情况及其处理方式 -->

| 情况 | 条件 | 处理方式 |
|:---|:---|:---|
| 边界情况 A | `value < 0` | 设为 0 |
| 边界情况 B | `value > MAX` | 设为 MAX |
| 异常情况 C | 依赖服务不可用 | 使用缓存/默认值 |

### 4.4 状态转换

<!-- 如果涉及状态机，描述状态转换 -->

```
状态 A ─[事件1]→ 状态 B
状态 B ─[事件2]→ 状态 C
状态 C ─[事件3]→ 状态 A
```

---

## 5. Error Handling

### 5.1 错误分类

| 错误类型 | 严重性 | 处理策略 | 降级方案 |
|:---|:---|:---|:---|
| 输入验证失败 | WARNING | 返回错误信息 | 使用默认值 |
| 外部服务超时 | WARNING | 重试 1 次 | 返回缓存数据 |
| 数据库连接失败 | ERROR | 记录日志 | 内存模式运行 |
| 未知异常 | ERROR | 捕获并记录 | 返回安全默认值 |

### 5.2 日志规范

```python
# INFO: 正常操作
print(f"   ✅ 操作成功: {result}")

# WARNING: 可恢复问题
print(f"   ⚠️  警告: {message}")

# ERROR: 关键故障
print(f"   ❌ 错误: {error}")
```

### 5.3 降级策略示例

```python
try:
    result = external_service.call()
except ServiceTimeout:
    print(f"   ⚠️  服务超时，使用缓存")
    result = cache.get_fallback()
except Exception as e:
    print(f"   ❌ 未知错误: {e}")
    result = DEFAULT_VALUE
```

---

## 6. Test Cases

### 6.1 单元测试

<!-- 列出需要的测试用例 -->

- [ ] **test_initial_state**: 验证初始状态正确
- [ ] **test_basic_operation**: 测试基本操作流程
- [ ] **test_boundary_min**: 测试最小边界值
- [ ] **test_boundary_max**: 测试最大边界值
- [ ] **test_error_handling**: 测试错误处理

### 6.2 测试文件路径

```
tests/
├── unit/
│   └── test_module_name.py
└── integration/
    └── test_module_integration.py
```

### 6.3 Mock 需求

| Mock 对象 | 原因 |
|:---|:---|
| `LLM.call()` | 避免真实 API 调用 |
| `ChromaDB.query()` | 隔离数据库依赖 |

### 6.4 示例测试代码

```python
import unittest
from src.module_name import ModuleName

class TestModuleName(unittest.TestCase):
    
    def setUp(self):
        """测试初始化"""
        self.module = ModuleName()
    
    def test_initial_state(self):
        """测试初始状态"""
        self.assertEqual(self.module.value, 0)
    
    def test_basic_operation(self):
        """测试基本操作"""
        result = self.module.operation(param=1)
        self.assertEqual(result["status"], "success")
```

---

## 7. Implementation Notes

### 7.1 开发注意事项

<!-- 开发时需要注意的要点 -->

- ⚠️ 注意事项 1
- ⚠️ 注意事项 2

### 7.2 技术债务

<!-- 已知的技术债务，标注优先级 -->

| 问题 | 优先级 | 描述 |
|:---|:---|:---|
| XXX 需要重构 | P2 | 当前实现不够优雅 |
| YYY 缺少缓存 | P3 | 性能可优化 |

### 7.3 未来优化

<!-- 未来可能的优化方向 -->

- [ ] 优化 1: 描述
- [ ] 优化 2: 描述

### 7.4 相关文档

<!-- 链接到相关文档 -->

- **PRD**: `docs/prd/Prd1_5.md`
- **架构设计**: `docs/architecture/xxx.md`
- **实现记录**: `docs/implementation/XXX_IMPLEMENTATION.md`

---

## 版本历史

| 版本 | 日期 | 变更说明 |
|:---|:---|:---|
| v1.0 | YYYY-MM-DD | 初始版本 |

---

**文档状态**: `draft` | `in_progress` | `completed`  
**最后更新**: YYYY-MM-DD
