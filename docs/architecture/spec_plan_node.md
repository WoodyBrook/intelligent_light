# Plan Node 技术规格文档

## 文档信息

| 项目 | 内容 |
| :--- | :--- |
| **项目名称** | Project Animus - Plan Node |
| **文档版本** | v1.1 |
| **创建日期** | 2025-12-24 |
| **更新日期** | 2026-01-07 |
| **开发策略** | 新增节点，集成到现有 OODA 工作流 |
| **参考文档** | `Prd1_4.md`, `architecture_design.md`, `spec_coding_v1.md` |
| **变更记录** | v1.1: 修正图结构集成、明确职责边界、添加 Tool/ContextManager 集成 |

---

## 1. 功能概述

### 1.1 核心目标

Plan Node（规划节点）是 Animus 智能体实现 **Agentic AI 核心循环**中的 "Plan" 阶段的关键组件。它位于 `router_node` 之后、`reasoning_node` 之前，负责：

1. **任务分析**：分析用户意图的复杂度和执行需求
2. **计划制定**：生成结构化的执行计划（步骤列表、工具需求、预期结果）
3. **计划验证**：验证计划的可行性和完整性
4. **计划优化**：根据上下文信息优化执行顺序

> **设计决策**：Plan Node 放置在 `reasoning_node` 之前而非之后，原因是：
> - 先规划再执行，符合人类认知流程
> - 避免 reasoning_node 重复分析任务结构
> - 为 reasoning_node 提供清晰的执行上下文

### 1.2 设计理念

Plan Node 的设计遵循 Jensen Huang 提出的 Agentic AI 架构理念：

- **Reason（推理）**：`reasoning_node` 理解用户需求
- **Plan（规划）**：`plan_node` 制定执行步骤 ← **本节点**
- **Tool Use（工具使用）**：`tool_node` 执行具体工具
- **Critique（反思）**：未来实现，评估执行结果

### 1.3 使用场景

Plan Node 在以下场景中发挥作用：

1. **多步骤任务**：用户请求需要多个工具或多次交互才能完成
   - 示例："帮我查一下北京的天气，然后推荐一首适合的歌"
   - 计划：步骤1（查天气）→ 步骤2（根据天气推荐音乐）

2. **条件执行任务**：需要根据中间结果决定后续步骤
   - 示例："如果今天下雨，提醒我带伞；如果晴天，推荐户外活动"
   - 计划：步骤1（查天气）→ 条件分支 → 步骤2A/2B

3. **复杂查询任务**：需要组合多个工具或数据源
   - 示例："查一下我今天的日程，然后告诉我需要准备什么"
   - 计划：步骤1（查日程）→ 步骤2（分析准备事项）→ 步骤3（生成提醒）

4. **简单任务跳过**：对于简单任务（单工具调用），可以跳过规划直接执行
   - 示例："今天天气怎么样？" → 直接调用天气工具，无需规划

---

## 2. 技术规格

### 2.1 节点位置

Plan Node 插入到现有工作流中：

**当前工作流**（graph.py 实际代码）：
```
evaluator → memory_loader → perception → router → {
    "reflex": reflex → guard → execution,
    "reasoning": reasoning → guard → execution,
    "direct_output": execution
}
tool_node → reasoning (工具调用循环，当前未激活)
```

**目标工作流**（Plan Node 插入后）：
```
evaluator → memory_loader → perception → router → {
    "reflex": reflex → guard → execution,
    "reasoning": plan → reasoning → guard → execution,  # Plan Node 在 reasoning 之前
    "direct_output": execution
}

# 工具调用循环（激活）
reasoning → tool_node (当 need_tool=true)
tool_node → plan (返回规划节点，继续执行下一步)
```

**节点职责链**：
```
router → plan_node → reasoning_node → tool_node → plan_node (循环)
   │         │              │              │
   │         │              │              └── 执行单个工具调用
   │         │              └── 生成单步回复/处理工具结果
   │         └── 分解多步骤任务，生成执行计划
   └── 路由决策（reflex/reasoning/ignore）
```

### 2.2 输入输出

#### 输入（从 state 中读取）

```python
{
    "user_input": str,                     # 用户输入
    "memory_context": Dict,                # 记忆上下文（来自 memory_loader_node）
    "history": List,                       # 对话历史（注意：字段名是 history，不是 conversation_history）
    "intent_route": str,                   # 路由决策（应为 "reasoning"）
    "current_hardware_state": Dict,        # 当前硬件状态
    "intimacy_level": float,               # 亲密度等级
    "conflict_state": Optional[Dict],      # 冲突状态
    "focus_mode": bool,                    # 专注模式
    
    # 工具循环时额外输入
    "tool_results": Optional[List],        # 上一步工具执行结果（循环时）
    "execution_plan": Optional[Dict],      # 当前执行计划（循环时）
}
```

#### 输出（更新到 state）

```python
{
    "execution_plan": Dict,                # 执行计划（新增字段）
    "plan_status": str,                    # 计划状态："created" | "skipped" | "failed" | "executing" | "completed"
    "plan_skip_reason": Optional[str],     # 跳过原因（如果跳过）
    "current_step_index": int,             # 当前执行步骤索引
    "tool_calls": Optional[List],          # 当前步骤需要的工具调用（转换后的格式）
    "monologue": str,                      # 规划过程的内心独白
}
```

### 2.3 执行计划结构

```python
execution_plan = {
    "plan_id": str,                        # 计划唯一标识
    "created_at": float,                   # 创建时间戳
    "complexity": str,                     # 复杂度："simple" | "moderate" | "complex"
    "steps": List[Dict],                   # 执行步骤列表
    "current_step": int,                   # 当前执行步骤索引（从0开始）
    "total_steps": int,                    # 总步骤数
    "required_tools": List[str],           # 需要的工具列表
    "estimated_time": float,               # 预估执行时间（秒）
    "can_skip": bool,                      # 是否可以跳过规划（简单任务）
}

# 步骤结构
step = {
    "step_id": int,                        # 步骤序号（从1开始）
    "description": str,                    # 步骤描述
    "action_type": str,                    # 动作类型："tool_call" | "llm_reasoning" | "condition_check"
    "tool_name": Optional[str],            # 工具名称（如果是工具调用）
    "tool_args": Optional[Dict],           # 工具参数
    "expected_output": str,                # 预期输出描述
    "depends_on": List[int],               # 依赖的步骤ID（用于并行执行）
    "condition": Optional[str],            # 条件表达式（用于条件分支）
}
```

---

## 3. 节点职责边界

为避免与现有节点职责重叠，明确各节点的职责划分：

### 3.1 职责对比表

| 节点 | 职责 | 输入 | 输出 |
|:---|:---|:---|:---|
| **router_node** | 快速意图分类（reflex/reasoning/ignore） | user_input, sensor_data | intent_route |
| **plan_node** | 多步骤任务分解，生成执行计划 | user_input, memory_context | execution_plan, tool_calls |
| **reasoning_node** | 单步骤 LLM 推理，生成回复 | user_input, execution_plan, tool_results | voice_content, action_plan |
| **tool_node** | 执行单个工具调用 | tool_calls | tool_results |

### 3.2 职责边界规则

**Plan Node 负责（DO）**：
- ✅ 分析任务是否需要多个步骤
- ✅ 识别任务中的条件逻辑（"如果...则..."）
- ✅ 分解任务为有序步骤列表
- ✅ 将步骤中的工具需求转换为 `tool_calls` 格式
- ✅ 跟踪多步骤任务的执行进度

**Plan Node 不负责（DON'T）**：
- ❌ 生成用户回复（由 reasoning_node 负责）
- ❌ 执行工具调用（由 tool_node 负责）
- ❌ 意图分类（由 router_node 负责）
- ❌ 冲突检测和亲密度更新（由 reasoning_node 负责）

### 3.3 与现有 reasoning_node 的协作

**改造前**（reasoning_node 承担过多职责）：
```python
# 旧版 reasoning_node 内部逻辑
def reasoning_node(state):
    # 1. 任务分析（应该由 plan_node 做）
    # 2. 工具调用检测（应该由 plan_node 做）
    # 3. LLM 推理
    # 4. 生成回复
    # 5. 冲突检测
```

**改造后**（职责分离）：
```python
# plan_node：任务分解
def plan_node(state):
    # 1. 任务复杂度分析
    # 2. 生成执行计划
    # 3. 转换工具调用格式
    return {"execution_plan": ..., "tool_calls": ...}

# reasoning_node：单步骤执行
def reasoning_node(state):
    # 1. 读取当前步骤（从 execution_plan）
    # 2. 基于工具结果生成回复
    # 3. 冲突检测和亲密度更新
    return {"voice_content": ..., "action_plan": ...}
```

### 3.4 简单任务快速路径

对于简单任务（单工具调用或纯对话），Plan Node 应快速跳过：

```python
# 简单任务检测规则
SIMPLE_TASK_RULES = [
    # 无工具需求的纯对话
    lambda state: not _needs_tool(state["user_input"]),
    # 单一明确的工具调用（如"北京天气"）
    lambda state: _is_single_tool_task(state["user_input"]),
]

def plan_node(state):
    # 快速路径：简单任务直接跳过
    if any(rule(state) for rule in SIMPLE_TASK_RULES):
        return {
            "plan_status": "skipped",
            "plan_skip_reason": "simple_task"
        }
    # ... 复杂任务规划逻辑
```

---

## 4. 接口定义

### 4.1 状态字段扩展（state.py）

```python
class LampState(TypedDict):
    # ... 现有字段保持不变 ...
    
    # === Plan Node 新增字段 ===
    execution_plan: Optional[Dict[str, Any]]  # 执行计划
    plan_status: Optional[str]                # 计划状态
    plan_skip_reason: Optional[str]           # 跳过规划的原因（如果跳过）
```

### 4.2 Plan Node 函数签名（nodes.py）

```python
def plan_node(state: LampState) -> Dict[str, Any]:
    """
    规划节点：分析任务复杂度，制定执行计划
    
    Args:
        state: 当前状态，包含用户输入、记忆上下文、工具调用需求等
    
    Returns:
        更新后的状态字典，包含 execution_plan 和 plan_status
    """
    pass
```

### 4.3 计划生成器接口（可选，未来可提取为独立模块）

```python
class PlanGenerator:
    """计划生成器（可选，未来可提取为独立模块）"""
    
    def analyze_complexity(self, user_input: str, tool_calls: List) -> str:
        """
        分析任务复杂度
        
        Returns:
            "simple": 单工具调用，可跳过规划
            "moderate": 2-3个步骤，需要简单规划
            "complex": 4+步骤或条件分支，需要详细规划
        """
        pass
    
    def generate_plan(self, user_input: str, context: Dict) -> Dict:
        """
        生成执行计划
        
        Args:
            user_input: 用户输入
            context: 上下文信息（记忆、对话历史、工具需求）
        
        Returns:
            执行计划字典
        """
        pass
    
    def validate_plan(self, plan: Dict) -> Tuple[bool, Optional[str]]:
        """
        验证计划的有效性
        
        Returns:
            (is_valid, error_message)
        """
        pass
```

---

## 5. 工作流集成

### 5.1 图结构修改（graph.py）

**基于现有代码的修改方案**：

```python
def build_graph():
    """构建 OODA 架构工作流图"""
    workflow = StateGraph(LampState)
    
    # === 注册所有节点 ===
    workflow.add_node("evaluator", evaluator_node)
    workflow.add_node("memory_loader", memory_loader_node)
    workflow.add_node("perception", perception_node)
    workflow.add_node("router", router_node)
    workflow.add_node("reflex", reflex_node)
    workflow.add_node("plan", plan_node)              # 新增：规划节点
    workflow.add_node("reasoning", reasoning_node)
    workflow.add_node("tool_node", tool_node)
    workflow.add_node("guard", action_guard_node)
    workflow.add_node("execution", execution_node)
    
    # === 设置连接边 ===

    # 1. 入口：评估器
    workflow.set_entry_point("evaluator")

    # 2. 评估器 → 记忆加载器（条件分支）
    workflow.add_conditional_edges(
        "evaluator",
        should_proceed_decision,
        {
            "proceed": "memory_loader",
            "skip": END
        }
    )

    # 3. 记忆加载器 → 感知节点
    workflow.add_edge("memory_loader", "perception")

    # 4. 感知节点 → 路由节点
    workflow.add_edge("perception", "router")

    # 5. 路由节点 → 三路分支
    workflow.add_conditional_edges(
        "router",
        route_decision,
        {
            "reflex": "reflex",
            "reasoning": "plan",           # 修改：reasoning 路径先走 plan
            "direct_output": "execution",
            "ignore": END
        }
    )

    # 6. 规划节点 → 条件分支（新增）
    workflow.add_conditional_edges(
        "plan",
        plan_decision,
        {
            "need_tool": "reasoning",      # 需要工具：先推理再调用工具
            "no_tool": "reasoning",        # 不需要工具：直接推理
            "skipped": "reasoning",        # 简单任务：跳过规划，直接推理
        }
    )

    # 7. 推理节点 → 条件分支（激活工具调用循环）
    workflow.add_conditional_edges(
        "reasoning",
        reasoning_decision,                # 新增决策函数
        {
            "tool_call": "tool_node",      # 需要调用工具
            "complete": "guard",           # 推理完成，进入守卫
        }
    )

    # 8. 工具节点 → 规划节点（循环：返回规划节点执行下一步）
    workflow.add_edge("tool_node", "plan")

    # 9. 其他连接
    workflow.add_edge("reflex", "guard")
    workflow.add_edge("guard", "execution")
    workflow.add_edge("execution", END)

    print("🔄 OODA 工作流图构建完成（含 Plan Node）")
    return workflow.compile()
```

### 5.2 决策函数

```python
def plan_decision(state: LampState) -> str:
    """
    规划节点后的路由决策
    
    Returns:
        "need_tool": 计划包含工具调用步骤
        "no_tool": 计划不需要工具（纯 LLM 推理）
        "skipped": 简单任务，跳过规划
    """
    plan_status = state.get("plan_status")
    
    # 简单任务跳过
    if plan_status == "skipped":
        return "skipped"
    
    # 检查计划中是否有工具调用
    execution_plan = state.get("execution_plan", {})
    required_tools = execution_plan.get("required_tools", [])
    
    if required_tools:
        return "need_tool"
    return "no_tool"


def reasoning_decision(state: LampState) -> str:
    """
    推理节点后的路由决策
    
    Returns:
        "tool_call": 当前步骤需要调用工具
        "complete": 推理完成，无需工具
    """
    # 检查是否有待执行的工具调用
    tool_calls = state.get("tool_calls", [])
    if tool_calls:
        return "tool_call"
    return "complete"
```

### 5.3 工作流执行示例

**简单任务流程**（无工具）：
```
用户: "你好"
→ router (reasoning) → plan (skipped) → reasoning → guard → execution
```

**单工具任务流程**：
```
用户: "北京天气"
→ router (reasoning) → plan (need_tool) → reasoning (tool_call) 
→ tool_node → plan (completed) → reasoning (complete) → guard → execution
```

**多步骤任务流程**：
```
用户: "查北京天气，然后推荐歌曲"
→ router (reasoning) → plan (need_tool, 2 steps)
→ reasoning (step 1: tool_call) → tool_node (weather)
→ plan (step 2: no_tool) → reasoning (step 2: complete)
→ guard → execution
```

---

## 6. 与现有系统集成

### 6.1 与 Tool 系统集成

#### 6.1.1 tool_calls 格式转换

现有 `tool_node` 期望的输入格式（来自 `state["tool_calls"]`）：

```python
# 现有 tool_node 期望的格式
tool_calls = [
    {
        "id": "call_xxx",           # 可选，工具调用ID
        "name": "weather_tool",     # 工具名称
        "args": {"city": "北京"}    # 工具参数
    }
]
```

Plan Node 需要将 `execution_plan.steps` 转换为此格式：

```python
def _convert_step_to_tool_call(step: Dict) -> Optional[Dict]:
    """
    将执行计划步骤转换为 tool_calls 格式
    
    Args:
        step: execution_plan 中的单个步骤
    
    Returns:
        tool_call 字典，或 None（如果不是工具调用步骤）
    """
    if step.get("action_type") != "tool_call":
        return None
    
    return {
        "id": f"plan_step_{step['step_id']}",
        "name": step["tool_name"],
        "args": step.get("tool_args", {})
    }


def plan_node(state: LampState) -> Dict[str, Any]:
    # ... 生成 execution_plan ...
    
    # 获取当前步骤
    current_step_index = state.get("current_step_index", 0)
    steps = execution_plan.get("steps", [])
    
    if current_step_index < len(steps):
        current_step = steps[current_step_index]
        tool_call = _convert_step_to_tool_call(current_step)
        
        return {
            "execution_plan": execution_plan,
            "plan_status": "executing",
            "current_step_index": current_step_index,
            "tool_calls": [tool_call] if tool_call else [],
            # ...
        }
```

#### 6.1.2 工具结果处理

当 `tool_node` 执行完毕后，结果存储在 `state["tool_results"]` 中。Plan Node 需要：

1. 读取工具结果
2. 更新当前步骤状态
3. 决定下一步（继续执行 / 完成 / 条件分支）

```python
def plan_node(state: LampState) -> Dict[str, Any]:
    # 检查是否是工具调用循环返回
    tool_results = state.get("tool_results", [])
    execution_plan = state.get("execution_plan")
    
    if tool_results and execution_plan:
        # 这是从 tool_node 返回的循环
        current_step_index = state.get("current_step_index", 0)
        
        # 保存工具结果到步骤中
        execution_plan["steps"][current_step_index]["result"] = tool_results[-1]
        
        # 移动到下一步
        next_step_index = current_step_index + 1
        
        if next_step_index >= len(execution_plan["steps"]):
            # 计划执行完毕
            return {
                "execution_plan": execution_plan,
                "plan_status": "completed",
                "current_step_index": next_step_index,
                "tool_calls": [],  # 清空工具调用
            }
        else:
            # 继续执行下一步
            next_step = execution_plan["steps"][next_step_index]
            tool_call = _convert_step_to_tool_call(next_step)
            return {
                "execution_plan": execution_plan,
                "plan_status": "executing",
                "current_step_index": next_step_index,
                "tool_calls": [tool_call] if tool_call else [],
            }
    
    # ... 首次规划逻辑 ...
```

#### 6.1.3 可用工具列表

Plan Node 需要知道可用工具列表以验证计划。从 `tools.py` 获取：

```python
from src.tools import AVAILABLE_TOOLS, TOOL_DESCRIPTIONS

def validate_plan(plan: Dict) -> Tuple[bool, Optional[str]]:
    """验证计划中的工具名称是否有效"""
    available_tool_names = [t.name for t in AVAILABLE_TOOLS]
    
    for step in plan.get("steps", []):
        if step.get("action_type") == "tool_call":
            tool_name = step.get("tool_name")
            if tool_name not in available_tool_names:
                return False, f"未知工具: {tool_name}"
    
    return True, None
```

### 6.2 与 ContextManager 集成

Plan Node 应复用现有的 `ContextManager` 进行上下文处理，保持一致性。

#### 6.2.1 对话历史压缩

```python
from src.context_manager import get_context_manager

def plan_node(state: LampState) -> Dict[str, Any]:
    context_manager = get_context_manager()
    
    # 获取对话历史
    conversation_history = state.get("history", [])
    
    # 压缩对话历史（复用现有逻辑）
    compression_result = context_manager.compress_conversation_history(conversation_history)
    formatted_history = context_manager.format_compressed_history(compression_result)
    
    if compression_result["compressed"]:
        print(f"   📊 Plan Node 压缩对话历史: {compression_result['compression_ratio']}")
    
    # 在规划 Prompt 中使用压缩后的历史
    plan_prompt = PLAN_PROMPT_TEMPLATE.format(
        user_input=state["user_input"],
        conversation_history=formatted_history,
        # ...
    )
```

#### 6.2.2 记忆上下文清洗

```python
def plan_node(state: LampState) -> Dict[str, Any]:
    context_manager = get_context_manager()
    memory_context = state.get("memory_context", {})
    
    # 清洗和去重记忆上下文
    if memory_context:
        memory_context = context_manager.clean_memory_context(memory_context)
        
        # 用户画像去重
        user_profile = memory_context.get("user_profile", "")
        if user_profile:
            profile_items = [line.strip()[2:] for line in user_profile.split("\n") 
                           if line.strip().startswith("- ")]
            deduplicated = context_manager.deduplicate_user_profile(profile_items)
            memory_context["user_profile"] = "\n".join([f"- {item}" for item in deduplicated])
```

#### 6.2.3 XML 格式化上下文

```python
def plan_node(state: LampState) -> Dict[str, Any]:
    context_manager = get_context_manager()
    
    # 使用 XML 格式化上下文（与 reasoning_node 保持一致）
    xml_context = context_manager.format_context_with_xml(
        user_profile=user_profile_text,
        recent_memories=recent_memories_list,
        action_patterns=[],  # Plan Node 不需要动作模式
        conversation_history=formatted_history,
        current_state={
            "intimacy_level": state.get("intimacy_level", 30),
            "focus_mode": state.get("focus_mode", False),
            "conflict_state": state.get("conflict_state")
        }
    )
    
    # 构建规划 Prompt
    plan_prompt = f"""
<system_instructions>
你是一个任务规划专家。根据用户输入和上下文，分析任务复杂度并生成执行计划。
</system_instructions>

{xml_context}

<task>
分析以下用户请求，判断复杂度并生成执行计划：
用户输入：{state["user_input"]}
</task>
"""
```

#### 6.2.4 完整集成示例

```python
from src.context_manager import get_context_manager
from src.tools import AVAILABLE_TOOLS, get_tool_descriptions

def plan_node(state: LampState) -> Dict[str, Any]:
    """
    规划节点：分析任务复杂度，制定执行计划
    集成 ContextManager 和 Tool 系统
    """
    print("--- 规划节点 (Plan Node) ---")
    
    # === 1. 获取上下文管理器 ===
    context_manager = get_context_manager()
    
    # === 2. 检查是否是工具调用循环返回 ===
    tool_results = state.get("tool_results", [])
    existing_plan = state.get("execution_plan")
    
    if tool_results and existing_plan:
        # 处理工具结果，更新计划状态
        return _handle_tool_result(state, existing_plan, tool_results)
    
    # === 3. 首次规划：准备上下文 ===
    user_input = state["user_input"]
    conversation_history = state.get("history", [])
    memory_context = state.get("memory_context", {})
    
    # 3.1 压缩对话历史
    compression_result = context_manager.compress_conversation_history(conversation_history)
    formatted_history = context_manager.format_compressed_history(compression_result)
    
    # 3.2 清洗记忆上下文
    if memory_context:
        memory_context = context_manager.clean_memory_context(memory_context)
    
    # 3.3 获取用户画像（去重）
    user_profile_text = _get_deduplicated_profile(memory_context, context_manager)
    
    # === 4. 快速路径：简单任务检测 ===
    if _is_simple_task(user_input, conversation_history):
        print("   ⚡ 简单任务，跳过规划")
        return {
            "execution_plan": None,
            "plan_status": "skipped",
            "plan_skip_reason": "simple_task",
            "tool_calls": [],
        }
    
    # === 5. 复杂任务：生成执行计划 ===
    # 5.1 构建 XML 格式化上下文
    xml_context = context_manager.format_context_with_xml(
        user_profile=user_profile_text,
        recent_memories=memory_context.get("user_memories", [])[:3],
        action_patterns=[],
        conversation_history=formatted_history,
        current_state={
            "intimacy_level": state.get("intimacy_level", 30),
            "focus_mode": state.get("focus_mode", False),
            "conflict_state": state.get("conflict_state")
        }
    )
    
    # 5.2 调用 LLM 生成计划
    plan = _generate_plan_with_llm(user_input, xml_context, get_tool_descriptions())
    
    # 5.3 验证计划
    is_valid, error = validate_plan(plan)
    if not is_valid:
        print(f"   ⚠️ 计划验证失败: {error}，使用降级策略")
        plan = _generate_simple_plan(user_input)
    
    # === 6. 转换第一步的工具调用 ===
    first_step = plan["steps"][0] if plan.get("steps") else None
    tool_calls = []
    if first_step:
        tool_call = _convert_step_to_tool_call(first_step)
        if tool_call:
            tool_calls = [tool_call]
    
    print(f"   ✅ 生成 {len(plan.get('steps', []))} 步执行计划")
    
    return {
        "execution_plan": plan,
        "plan_status": "created",
        "current_step_index": 0,
        "tool_calls": tool_calls,
        "monologue": f"我分析了你的请求，制定了{len(plan.get('steps', []))}步执行计划..."
    }
```

### 6.3 与 Memory 系统集成（RAM/ROM 架构）

Plan Node 应感知 RAM/ROM 记忆架构的变化：

#### 6.3.1 Profile 处理 (RAM)
- **输入**: Plan Node 可直接访问 `state["user_profile"]`（结构化 RAM 数据），无需通过工具查询。
- **规划**: 如果任务涉及用户核心画像（如“我住在哪里”），可以直接生成回答步骤（`llm_reasoning`），而无需生成工具调用。

#### 6.3.2 长期记忆检索 (ROM)
- **工具调用**: 如果任务需要回顾过往经历（如“我上次提到喜欢什么”），Plan Node 应生成 `query_user_memory_tool` 的调用步骤。
- **历史注入**: Plan Node 无需显式传递对话历史给工具，`tool_node` 会自动处理上下文注入。

```python
def plan_node(state: LampState) -> Dict[str, Any]:
    # ...
    user_input = state.get("user_input", "")
    
    # 检查是否需要查阅长期记忆
    memory_keywords = ["记得", "上次", "以前", "说过", "历史"]
    needs_memory_check = any(kw in user_input for kw in memory_keywords)
    
    if needs_memory_check:
        # 在 Prompt 中提示 LLM 可以使用 query_user_memory_tool
        pass
    # ...
```

#### 6.3.3 Profile 更新
- **意图识别**: 如果用户意图是更新核心信息（如“我搬家了”），Plan Node 应生成 `update_profile_tool` 的调用步骤。

---

## 7. 实现细节

### 7.1 计划生成逻辑

Plan Node 使用 LLM 生成执行计划，流程如下：

1. **复杂度分析**：
   - 检查工具调用数量：0个 → simple，1个 → simple/moderate，2+个 → complex
   - 检查用户输入中的条件关键词（"如果"、"当"、"若"等）→ complex
   - 检查任务描述中的步骤数量 → moderate/complex

2. **计划生成**（使用 LLM）：
   - 如果复杂度为 "simple"，生成简单计划或跳过规划
   - 如果复杂度为 "moderate" 或 "complex"，调用 LLM 生成详细计划

3. **计划验证**：
   - 检查步骤依赖关系（避免循环依赖）
   - 验证工具名称是否在可用工具列表中
   - 检查步骤数量是否合理（不超过10步）

### 7.2 LLM Prompt 设计

```python
PLAN_PROMPT_TEMPLATE = """
你是一个任务规划专家。根据用户输入和可用工具，制定详细的执行计划。

用户输入：{user_input}

可用工具：
{tool_descriptions}

对话历史（最近3轮）：
{conversation_history}

记忆上下文：
{memory_context}

请分析任务复杂度，并生成执行计划。输出格式为 JSON：

{{
    "complexity": "simple|moderate|complex",
    "can_skip": true/false,  // 简单任务可以跳过规划
    "steps": [
        {{
            "step_id": 1,
            "description": "步骤描述",
            "action_type": "tool_call|llm_reasoning|condition_check",
            "tool_name": "工具名称（如果是工具调用）",
            "tool_args": {{"参数": "值"}},
            "expected_output": "预期输出",
            "depends_on": [],  // 依赖的步骤ID
            "condition": null  // 条件表达式（如果有）
        }}
    ],
    "estimated_time": 5.0  // 预估执行时间（秒）
}}
"""
```

### 7.3 错误处理

```python
def plan_node(state: LampState) -> Dict[str, Any]:
    try:
        # 1. 分析复杂度
        complexity = analyze_complexity(state)
        
        # 2. 简单任务跳过规划
        if complexity == "simple" and not has_conditions(state):
            return {
                "execution_plan": None,
                "plan_status": "skipped",
                "plan_skip_reason": "简单任务，无需规划"
            }
        
        # 3. 生成计划
        plan = generate_plan_with_llm(state)
        
        # 4. 验证计划
        is_valid, error = validate_plan(plan)
        if not is_valid:
            # 降级策略：生成简单计划
            plan = generate_simple_plan(state)
        
        return {
            "execution_plan": plan,
            "plan_status": "created",
            "monologue": f"我制定了{len(plan['steps'])}步执行计划..."
        }
        
    except Exception as e:
        # 错误处理：跳过规划，直接执行
        logger.error(f"计划生成失败: {e}")
        return {
            "execution_plan": None,
            "plan_status": "failed",
            "plan_skip_reason": f"计划生成失败: {str(e)}"
        }
```

### 7.4 性能优化

1. **缓存机制**：对于相似的任务，可以缓存计划模板
2. **并行分析**：复杂度分析和计划生成可以并行进行
3. **快速路径**：简单任务（单工具调用）直接跳过 LLM 调用
4. **超时控制**：LLM 调用设置超时（5秒），超时后使用降级策略

---

## 8. 使用示例

### 8.1 简单任务（跳过规划）

**用户输入**："今天北京天气怎么样？"

**Plan Node 输出**：
```python
{
    "execution_plan": None,
    "plan_status": "skipped",
    "plan_skip_reason": "简单任务，无需规划"
}
```

**工作流**：`reasoning → plan → guard → execution`（跳过 tool_node）

### 8.2 中等复杂度任务（简单规划）

**用户输入**："帮我查一下北京的天气，然后推荐一首适合的歌"

**Plan Node 输出**：
```python
{
    "execution_plan": {
        "complexity": "moderate",
        "can_skip": False,
        "steps": [
            {
                "step_id": 1,
                "description": "查询北京天气",
                "action_type": "tool_call",
                "tool_name": "weather_tool",
                "tool_args": {"location": "北京"},
                "expected_output": "天气信息（温度、天气状况）",
                "depends_on": []
            },
            {
                "step_id": 2,
                "description": "根据天气推荐音乐",
                "action_type": "llm_reasoning",
                "tool_name": None,
                "expected_output": "音乐推荐（基于天气情绪）",
                "depends_on": [1]
            }
        ],
        "total_steps": 2,
        "required_tools": ["weather_tool"],
        "estimated_time": 3.0
    },
    "plan_status": "created"
}
```

### 8.3 复杂任务（详细规划）

**用户输入**："如果今天下雨，提醒我带伞；如果晴天，推荐户外活动，并查一下附近的公园"

**Plan Node 输出**：
```python
{
    "execution_plan": {
        "complexity": "complex",
        "can_skip": False,
        "steps": [
            {
                "step_id": 1,
                "description": "查询今天天气",
                "action_type": "tool_call",
                "tool_name": "weather_tool",
                "tool_args": {"location": "用户所在城市"},
                "expected_output": "天气信息",
                "depends_on": []
            },
            {
                "step_id": 2,
                "description": "判断天气条件",
                "action_type": "condition_check",
                "condition": "weather.condition == 'rain'",
                "expected_output": "布尔值（是否下雨）",
                "depends_on": [1]
            },
            {
                "step_id": 3,
                "description": "提醒带伞（如果下雨）",
                "action_type": "llm_reasoning",
                "condition": "step_2 == true",
                "expected_output": "提醒消息",
                "depends_on": [2]
            },
            {
                "step_id": 4,
                "description": "推荐户外活动并查询公园（如果晴天）",
                "action_type": "tool_call",
                "tool_name": "location_search_tool",
                "tool_args": {"query": "附近公园"},
                "condition": "step_2 == false",
                "expected_output": "公园列表",
                "depends_on": [2]
            }
        ],
        "total_steps": 4,
        "required_tools": ["weather_tool", "location_search_tool"],
        "estimated_time": 5.0
    },
    "plan_status": "created"
}
```

---

## 9. 测试策略

### 9.1 单元测试

```python
def test_plan_node_simple_task():
    """测试简单任务跳过规划"""
    state = {
        "user_input": "今天天气怎么样？",
        "tool_calls": [{"name": "weather_tool"}],
        "intent_route": "reasoning"
    }
    result = plan_node(state)
    assert result["plan_status"] == "skipped"

def test_plan_node_complex_task():
    """测试复杂任务生成计划"""
    state = {
        "user_input": "查天气然后推荐音乐",
        "tool_calls": [{"name": "weather_tool"}],
        "intent_route": "reasoning"
    }
    result = plan_node(state)
    assert result["plan_status"] == "created"
    assert "execution_plan" in result
    assert len(result["execution_plan"]["steps"]) >= 2
```

### 9.2 集成测试

```python
def test_plan_node_integration():
    """测试规划节点在工作流中的集成"""
    # 模拟完整工作流：reasoning → plan → tool_node
    state = create_test_state()
    state = reasoning_node(state)
    state = plan_node(state)
    
    if state["plan_status"] != "skipped":
        assert "execution_plan" in state
        state = tool_node(state)
        # 验证工具执行结果
```

---

## 10. 未来扩展

### 10.1 Critique Node（反思节点）

未来可以添加 Critique Node，在工具执行后评估结果：

```
reasoning → plan → tool_node → critique → {
    "satisfied": reasoning (生成最终回复),
    "unsatisfied": plan (重新规划)
}
```

### 10.2 计划优化

- **动态调整**：根据中间结果动态调整后续步骤
- **并行执行**：识别可以并行执行的步骤
- **计划缓存**：缓存相似任务的计划模板

### 10.3 计划可视化

- 在 Demo UI 中可视化执行计划
- 显示当前执行步骤和进度
- 支持用户查看和修改计划

---

## 11. 验收标准

### 11.1 功能验收

- ✅ 简单任务正确跳过规划
- ✅ 中等复杂度任务生成合理计划
- ✅ 复杂任务生成详细计划（包含条件分支）
- ✅ 计划验证机制正常工作
- ✅ 错误处理完善（降级策略）

### 11.2 性能验收

- ✅ 简单任务规划延迟 < 100ms（规则跳过，无 LLM 调用）
- ✅ 中等复杂度任务规划延迟 < 3s（LLM 调用）
- ✅ 复杂任务规划延迟 < 5s（LLM 调用）

### 11.3 集成验收

- ✅ 工作流集成正确（router → plan → reasoning → tool_node → plan 循环）
- ✅ 与 ContextManager 集成正确（对话压缩、XML 格式化）
- ✅ 与 Tool 系统集成正确（tool_calls 格式转换）
- ✅ 状态字段正确更新
- ✅ 不影响现有功能（reflex 路径、direct_output 路径）

---

**文档结束**

