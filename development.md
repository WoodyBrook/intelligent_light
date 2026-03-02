# Project Animus - 开发规范文档

> **版本**: v1.0  
> **状态**: Active  
> **最后更新**: 2026-01-12  
> **适用范围**: 本文档是 AI Agent 和开发者的核心参考，贯穿整个开发流程。

---

## 目录

1. [代码风格规范](#1-代码风格规范)
2. [架构原则](#2-架构原则)
3. [文件/目录结构规范](#3-文件目录结构规范)
4. [测试规范](#4-测试规范)
5. [文档编写规范](#5-文档编写规范)
6. [开发流程](#6-开发流程)
7. [反模式 (Anti-Patterns)](#7-反模式-anti-patterns)
8. [代码审查清单](#8-代码审查清单)

---

## 1. 代码风格规范

### 1.1 命名约定

#### 文件命名
| 类型 | 规范 | 示例 |
|:---|:---|:---|
| Python 模块 | snake_case | `intimacy_manager.py`, `state_manager.py` |
| 测试文件 | `test_` 前缀 | `test_intimacy_manager.py` |
| 配置文件 | snake_case | `prompts.py`, `config.py` |
| 文档文件 | 大写或 snake_case | `README.md`, `spec_intimacy.md` |

#### 函数/方法命名
```python
# ✅ 正确：使用 snake_case，动词开头
def update_intimacy(delta: float, reason: str) -> Dict[str, Any]:
    """更新亲密度"""
    pass

def get_current_state() -> Dict[str, Any]:
    """获取当前状态"""
    pass

def calculate_daily_bonus(presence_duration: float) -> float:
    """计算每日陪伴奖励"""
    pass

# ❌ 错误：驼峰命名或无动词
def IntimacyUpdate():  # 驼峰 + 无动词
    pass
```

#### 类命名
```python
# ✅ 正确：使用 PascalCase
class IntimacyManager:
    """亲密度管理器"""
    pass

class ConflictHandler:
    """冲突处理器"""
    pass

class UserProfile(BaseModel):
    """用户画像"""
    pass
```

#### 变量命名
```python
# ✅ 正确：使用 snake_case，语义清晰
intimacy_level: float = 30.0
daily_touch_count: int = 0
cooldown_until: Optional[float] = None

# ✅ 正确：常量使用全大写 + 下划线
MAX_INTIMACY_LEVEL = 100.0
DEFAULT_COOLDOWN_SECONDS = 300
AVAILABLE_TOOLS = ["weather_tool", "news_tool"]

# ❌ 错误：缩写或无意义命名
il = 30.0  # 不清晰
tmp = None  # 无意义
```

### 1.2 格式规范

#### 缩进与行长
- **缩进**: 4 空格（不使用 Tab）
- **行长**: 最大 100 字符（建议 80）
- **空行**: 类之间 2 空行，方法之间 1 空行

#### Import 顺序
```python
# 1. 标准库
import time
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, date

# 2. 第三方库
from pydantic import BaseModel, Field
from langchain_core.tools import tool
from langgraph.graph import StateGraph

# 3. 本地模块
from src.state import LampState, UserProfile
from src.memory_manager import MemoryManager
from config.prompts import get_system_prompt
```

#### 类型标注
```python
# ✅ 正确：完整的类型标注
def update_intimacy(
    self, 
    delta: float, 
    reason: str
) -> Dict[str, Any]:
    """更新亲密度"""
    pass

# ✅ 正确：使用 Optional 表示可空
def get_memory(
    self, 
    query: str, 
    limit: Optional[int] = None
) -> List[Dict[str, Any]]:
    pass
```

### 1.3 注释规范

#### Docstring 格式（Google Style）
```python
def update_intimacy(self, delta: float, reason: str) -> Dict[str, Any]:
    """
    更新亲密度
    
    Args:
        delta: 变化量（可为正负）
        reason: 原因（"touch", "praise", "conflict_L1", etc.）
    
    Returns:
        {
            "intimacy_level": float,
            "intimacy_rank": str,
            "delta": float,
            "reason": str,
            "rank_changed": bool
        }
    
    Raises:
        ValueError: 当 reason 为空时
    
    Example:
        >>> manager.update_intimacy(0.5, "touch")
        {"intimacy_level": 30.5, "intimacy_rank": "stranger", ...}
    """
    pass
```

#### 行内注释
```python
# ✅ 正确：解释"为什么"而非"是什么"
# 限制历史记录长度，防止内存膨胀
if len(self.intimacy_history) > 100:
    self.intimacy_history = self.intimacy_history[-100:]

# L3 冒犯需要最小等待时间，避免"暴力-道歉-立刻恢复"的纵容感
if offense_level == "L3" and elapsed < self.REPAIR_MIN_WAIT:
    return False

# ❌ 错误：描述显而易见的内容
# 加 1（这是废话）
count = count + 1
```

---

## 2. 架构原则

### 2.1 状态管理规则 (LangGraph 模式)

#### TypedDict 定义
所有状态 schema 必须在 `state.py` 中使用 `TypedDict` 定义：

```python
from typing import TypedDict, Optional, List, Dict, Any, Annotated
import operator

class LampState(TypedDict):
    """台灯智能体的核心状态定义"""
    
    # --- 输入数据 ---
    user_input: Optional[str]
    sensor_data: Dict[str, Any]
    
    # --- 亲密度系统 ---
    intimacy_level: float                # 0-100，初始30.0
    intimacy_rank: str                   # "stranger|acquaintance|friend|soulmate"
    
    # --- 历史（特殊：追加模式）---
    history: Annotated[List[Any], operator.add]
```

#### 不可变性原则
```python
# ✅ 正确：节点返回仅包含需要更新的字段
def evaluator_node(state: LampState) -> Dict[str, Any]:
    # 只返回需要变化的字段，LangGraph 自动合并
    return {"current_mood": "sleepy"}

# ❌ 错误：直接修改并返回完整 state
def evaluator_node(state: LampState) -> LampState:
    state["current_mood"] = "sleepy"  # 直接修改
    return state  # 返回完整对象
```

#### 状态持久化
关键状态变更必须通过 `StateManager.save_state()` 持久化：

```python
# ✅ 正确：使用 StateManager 持久化
state_manager = StateManager()
state_manager.save_state({
    "intimacy_level": new_level,
    "intimacy_rank": new_rank
})

# ❌ 错误：直接修改 state 而不持久化
state["intimacy_level"] = new_level  # 重启后丢失
```

### 2.2 亲密度系统规则

**必须使用 `IntimacyManager`** 处理所有亲密度变更：

```python
# ✅ 正确：通过 IntimacyManager 更新
intimacy_manager = IntimacyManager()
result = intimacy_manager.update_intimacy(delta=0.5, reason="touch")
# 然后通过 StateManager 持久化
state_manager.save_state(result)

# ❌ 错误：直接修改 state 中的亲密度
state["intimacy_level"] = state["intimacy_level"] + 0.5  # 绕过管理器
```

### 2.3 System Prompt 规则

**绝对禁止**在 `nodes.py` 中硬编码 System Prompt：

```python
# ✅ 正确：从 config/prompts.py 动态加载
from config.prompts import get_system_prompt

system_prompt = get_system_prompt(
    intimacy_level=state["intimacy_level"],
    intimacy_rank=state["intimacy_rank"],
    conflict_state=state.get("conflict_state"),
    focus_mode=state.get("focus_mode", False),
    user_profile=state.get("user_profile", {})
)

# ❌ 错误：硬编码 prompt
system_prompt = "你是一个温柔的猫咪助手..."  # 禁止
```

### 2.4 上下文工程规则

**禁止简单截断**对话历史：

```python
# ✅ 正确：使用 ContextManager 压缩
from src.context_manager import ContextManager

context_manager = ContextManager()
compressed_history = context_manager.compress_history(
    history=state["history"],
    max_chars=2000
)

# ❌ 错误：简单截断
history = state["history"][-3:]  # 禁止
```

### 2.5 错误处理策略

#### 分级处理
```python
# INFO: 正常操作
print(f"   🗜️  压缩对话历史: {len(original)} → {len(compressed)} 字符")

# WARNING: 可恢复问题
try:
    compressed = llm_compress(history)
except LLMError:
    print(f"   ⚠️  LLM 压缩失败，使用简单摘要")
    compressed = simple_summary(history)  # 降级方案

# ERROR: 关键故障
try:
    result = db.query(query)
except DBError as e:
    print(f"   ❌ 数据库查询失败: {e}")
    return []  # 返回空结果而非崩溃
```

#### 降级方案
| 场景 | 降级方案 |
|:---|:---|
| LLM 压缩失败 | 使用 `_simple_summary()` |
| 向量检索失败 | 返回空 context，继续对话 |
| 状态持久化失败 | 记录日志，内存保留 |

### 2.6 模块职责边界

| 模块 | 职责 | 禁止 |
|:---|:---|:---|
| `nodes.py` | 节点逻辑胶水层 | 直接操作数据库/硬编码 prompt |
| `intimacy_manager.py` | 亲密度计算与等级管理 | 直接调用 LLM |
| `memory_manager.py` | 记忆检索与存储 | 修改亲密度 |
| `state_manager.py` | 状态持久化 | 业务逻辑判断 |
| `context_manager.py` | 上下文压缩与格式化 | 直接修改 state |
| `config/prompts.py` | 动态 prompt 生成 | 硬编码用户数据 |

---

## 3. 文件/目录结构规范

### 3.1 标准目录布局

```
Neko_light/
├── main.py                      # 入口点 & 事件循环
├── development.md               # 开发规范（本文档）
├── README.md                    # 项目说明
├── requirements.txt             # 依赖清单
├── pyrightconfig.json           # 类型检查配置
│
├── src/                         # 核心业务代码
│   ├── __init__.py
│   ├── graph.py                 # LangGraph 图定义
│   ├── nodes.py                 # 图节点（逻辑胶水层）
│   ├── state.py                 # 状态类型定义
│   ├── state_manager.py         # 状态持久化
│   ├── intimacy_manager.py      # 亲密度系统
│   ├── conflict_handler.py      # 冲突处理
│   ├── focus_mode_manager.py    # 专注模式
│   ├── memory_manager.py        # 记忆管理（RAG）
│   ├── context_manager.py       # 上下文工程
│   ├── event_manager.py         # 事件调度
│   ├── reflex_router.py         # 反射路由
│   └── tools.py                 # 工具定义
│
├── config/                      # 配置文件
│   ├── __init__.py
│   └── prompts.py               # 动态 Prompt 模板
│
├── demo/                        # Streamlit 演示
│   ├── app.py                   # 主 UI
│   ├── utils.py                 # DemoRunner
│   └── scenarios.py             # 测试场景
│
├── docs/                        # 文档
│   ├── prd/                     # 产品需求文档
│   │   ├── prd0.md
│   │   └── Prd1_5.md
│   ├── specs/                   # 技术规格文档
│   │   ├── SPEC_TEMPLATE.md     # Spec 模板
│   │   └── spec_intimacy.md     # 亲密度模块 Spec
│   ├── architecture/            # 架构设计
│   ├── implementation/          # 实现记录
│   ├── guides/                  # 使用指南
│   └── summaries/               # 阶段总结
│
├── tests/                       # 测试套件
│   ├── __init__.py
│   ├── unit/                    # 单元测试
│   │   ├── test_intimacy_manager.py
│   │   └── test_context_manager.py
│   ├── integration/             # 集成测试
│   └── run_tests.py             # 测试入口
│
├── scripts/                     # 工具脚本
│   ├── diagnose_weather.py
│   └── test_api_latency.py
│
└── archived/                    # 已废弃代码（勿引用）
```

### 3.2 文件命名规则

| 类型 | 命名规则 | 示例 |
|:---|:---|:---|
| Python 模块 | `snake_case.py` | `intimacy_manager.py` |
| 测试文件 | `test_<module>.py` | `test_intimacy_manager.py` |
| Spec 文档 | `spec_<module>.md` | `spec_intimacy.md` |
| 实现记录 | `<FEATURE>_IMPLEMENTATION.md` | `COMPRESSION_IMPLEMENTATION.md` |
| 阶段总结 | `<PHASE>_SUMMARY.md` | `PHASE2_COMPLETION_SUMMARY.md` |

### 3.3 模块职责边界

新增模块时，必须明确其职责边界：

```python
# src/new_module.py

"""
新模块名称

职责：
- 负责 XXX
- 管理 YYY

依赖：
- state.py（状态定义）
- memory_manager.py（记忆检索）

被调用方：
- nodes.py 中的 xxx_node
"""
```

---

## 4. 测试规范

### 4.1 单元测试

#### 必须覆盖的模块
- `IntimacyManager`
- `ConflictHandler`
- `ContextManager`
- `FocusModeManager`

#### 文件路径
```
tests/
├── unit/
│   ├── test_intimacy_manager.py
│   ├── test_conflict_handler.py
│   └── test_context_manager.py
└── test_*.py  # 根目录也接受
```

#### Mock 策略
```python
import unittest
from unittest.mock import Mock, patch

class TestIntimacyManager(unittest.TestCase):
    
    def setUp(self):
        """每个测试前初始化"""
        self.manager = IntimacyManager()
        self.manager.intimacy_level = 30.0  # 重置
    
    @patch('src.memory_manager.ChromaDB')
    def test_with_mocked_db(self, mock_db):
        """Mock ChromaDB 交互"""
        mock_db.query.return_value = []
        # 测试逻辑...
    
    @patch('src.nodes.llm_call')
    def test_with_mocked_llm(self, mock_llm):
        """Mock LLM 调用"""
        mock_llm.return_value = {"content": "测试回复"}
        # 测试逻辑...
```

### 4.2 集成测试

```python
# tests/integration/test_conversation_flow.py

def test_full_conversation_with_intimacy():
    """测试完整对话流（含亲密度变化）"""
    runner = DemoRunner()
    
    # 模拟多轮对话
    runner.process_input("你好")
    runner.process_input("你真可爱")  # 触发 praise +1
    
    # 验证亲密度变化
    assert runner.state["intimacy_level"] > 30.0
```

### 4.3 测试命名规范

```python
# ✅ 正确：描述测试场景
def test_update_intimacy_touch_increases_level():
    """抚摸应增加亲密度"""
    pass

def test_daily_touch_limit_prevents_overflow():
    """每日抚摸上限应阻止过度增加"""
    pass

# ❌ 错误：无意义命名
def test_1():
    pass

def test_function():
    pass
```

---

## 5. 文档编写规范

### 5.1 PRD 格式标准

参考 `docs/prd/Prd1_5.md`：

- **文档头**: 版本号、状态、日期
- **目录**: 使用 Markdown 目录
- **功能编号**: 使用唯一 ID（如 `F-01`, `E-01`, `M-01`）
- **验收标准**: 每个功能必须有明确的验收标准

### 5.2 Spec 文档格式标准

参考 `docs/specs/SPEC_TEMPLATE.md`：

```markdown
# Spec: [模块名称]

## Meta
- PRD Reference: @PRD: E-01, E-02
- Module: `xxx.py`
- Status: draft | in_progress | completed
- Last Updated: YYYY-MM-DD

## 1. Task Definition
## 2. Context
## 3. Interface
## 4. Business Logic
## 5. Error Handling
## 6. Test Cases
## 7. Implementation Notes
```

### 5.3 版本记录规范

```markdown
### 版本历史

| 版本 | 日期 | 变更说明 |
|:---|:---|:---|
| v1.0 | 2026-01-12 | 初始版本 |
| v1.1 | 2026-01-15 | 添加 XXX 功能 |
```

---

## 6. 开发流程

### 6.1 分支策略

```
main
├── feature/intimacy-system     # 新功能
├── bugfix/cooldown-timer       # Bug 修复
└── release/v1.0                # 发布版本
```

#### 分支命名
| 类型 | 格式 | 示例 |
|:---|:---|:---|
| 功能 | `feature/<name>` | `feature/focus-mode` |
| 修复 | `bugfix/<issue>` | `bugfix/intimacy-overflow` |
| 发布 | `release/<version>` | `release/v1.5` |

### 6.2 Commit 规范

```bash
# 格式：<type>(<scope>): <subject>

# ✅ 正确示例
feat(intimacy): add daily touch limit
fix(cooldown): correct timer calculation
docs(spec): add intimacy spec document
refactor(context): optimize compression logic
test(intimacy): add boundary test cases

# ❌ 错误示例
update code  # 无类型，描述模糊
fix  # 无作用域，无描述
```

#### Type 类型
| Type | 描述 |
|:---|:---|
| `feat` | 新功能 |
| `fix` | Bug 修复 |
| `docs` | 文档更新 |
| `refactor` | 重构（无功能变化） |
| `test` | 测试相关 |
| `chore` | 构建/工具/依赖 |

### 6.3 PR 规范

#### 标题格式
```
[Type] 简短描述

示例：
[Feature] 添加亲密度每日上限功能
[Bugfix] 修复冷却计时器逻辑
```

#### 描述模板
```markdown
## 变更内容
- 描述具体变更

## 关联 PRD/Spec
- @PRD: E-01, E-02
- @Spec: spec_intimacy.md

## 测试验证
- [ ] 单元测试通过
- [ ] 集成测试通过
- [ ] Demo 验证通过

## 截图/日志（可选）
```

### 6.4 开发工作流

1. **阅读 Spec/PRD**: 理解需求
2. **创建分支**: `git checkout -b feature/xxx`
3. **增量开发**:
   - Step 1: 实现核心函数
   - Step 2: 集成到节点
   - Step 3: 添加测试
4. **更新文档**: 更新 Spec 状态
5. **提交 PR**: 填写 PR 模板
6. **Code Review**: 通过审查清单
7. **合并**: Squash merge to main

---

## 7. 反模式 (Anti-Patterns)

### ❌ 禁止行为

| 反模式 | 正确做法 |
|:---|:---|
| 硬编码对话历史截断 `history[-3:]` | 使用 `ContextManager` 压缩 |
| 直接修改 `state["intimacy_level"]` | 使用 `IntimacyManager.update_intimacy()` |
| 在 `nodes.py` 硬编码 System Prompt | 从 `config/prompts.py` 加载 |
| 保存 assistant 回复作为用户偏好 | 只从 `user_input` 提取偏好 |
| 跳过冲突检测直接保存 Profile | 使用 `MemoryManager.detect_and_resolve_conflicts()` |
| 忽略压缩失败（无降级方案） | 使用 `_simple_summary()` 降级 |
| 承诺物理能力（泡咖啡、开门） | 提供情感陪伴或数字替代 |

### 示例对比

```python
# ❌ 反模式：直接截断历史
def get_context(state):
    return state["history"][-3:]  # 丢失重要上下文

# ✅ 正确：使用压缩
def get_context(state):
    return context_manager.compress_history(
        history=state["history"],
        max_chars=2000
    )
```

```python
# ❌ 反模式：直接修改亲密度
def handle_touch(state):
    state["intimacy_level"] += 0.5  # 绕过管理器
    return state

# ✅ 正确：使用管理器
def handle_touch(state):
    result = intimacy_manager.update_intimacy(0.5, "touch")
    state_manager.save_state(result)
    return {"intimacy_level": result["intimacy_level"]}
```

---

## 8. 代码审查清单

### 提交前自查

- [ ] **上下文工程**: 使用压缩而非截断
- [ ] **用户 Profile 冲突**: 检测并解决
- [ ] **亲密度持久化**: 变更已保存到磁盘
- [ ] **LLM Prompt**: 包含必要上下文（亲密度、冲突、专注模式）
- [ ] **错误处理**: 包含降级方案（不会崩溃）
- [ ] **测试覆盖**: 新逻辑有单元测试
- [ ] **Plan 状态**: 已标记完成的任务
- [ ] **物理能力**: 无能力幻觉（不承诺无法做到的事）

### 审查者检查

- [ ] 代码风格符合规范
- [ ] 类型标注完整
- [ ] Docstring 清晰
- [ ] 无硬编码魔法值
- [ ] 错误处理合理
- [ ] 测试用例充分
- [ ] 文档已更新

---

## 附录

### A. 相关文档

- **PRD**: `docs/prd/Prd1_5.md`
- **Spec 模板**: `docs/specs/SPEC_TEMPLATE.md`
- **架构设计**: `docs/architecture/architecture_design.md`

### B. 工具推荐

| 工具 | 用途 |
|:---|:---|
| `pytest` | 单元测试 |
| `pyright` | 类型检查 |
| `black` | 代码格式化 |
| `ruff` | Linting |

### C. 参考资料

- [LangGraph 官方文档](https://python.langchain.com/docs/langgraph)
- [Pydantic v2 文档](https://docs.pydantic.dev/)
- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)

---

**文档版本**: v1.0  
**最后更新**: 2026-01-12  
**维护者**: Project Animus Team
