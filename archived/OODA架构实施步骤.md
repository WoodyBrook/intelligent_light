# OODA 架构实施步骤

本文档详细说明实现 OODA（观察-调整-决策-行动）架构需要修改和新增的代码。

---

## 📋 总体架构变化

### 当前架构（V1.0）
- **模式**：被动响应（Request-Response）
- **流程**：单次运行，线性执行
- **入口**：`main.py` 直接调用 `app.invoke()`

### 目标架构（V2.0 - OODA）
- **模式**：事件驱动（Event-Driven）
- **流程**：无限循环，后台常驻
- **入口**：事件循环 + 内部状态驱动

---

## 🔧 需要修改的已有文件

### 1. `state.py` - 状态定义扩展

**修改内容**：
- [ ] 新增 `user_profile: Dict[str, Any]` 字段
  - 存储静态用户画像（姓名、城市等）
  
- [ ] 新增 `internal_drives: Dict[str, Any]` 字段
  - 包含：`boredom` (0-100), `energy` (0-100), `last_interaction_time` (float), `absence_duration` (float)
  
- [ ] 新增 `memory_context: Optional[str]` 字段
  - 存放 RAG 检索回来的用户历史偏好
  
- [ ] 新增 `event_type: Optional[str]` 字段
  - 标识事件来源：`"user_input"`, `"timer"`, `"sensor"`, `"internal_drive"`
  
- [ ] 新增 `proactive_expression: Optional[str]` 字段
  - 存储主动行为的表达内容
  
- [ ] 新增 `user_preferences: Dict[str, Any]` 字段
  - 存储用户偏好设置（主动行为开关、勿扰时间等）
  
- [ ] 新增 `context_signals: Dict[str, Any]` 字段
  - 存储当前上下文信号（时间、活动状态等）
  
- [ ] 升级 `history` 字段
  - 确保兼容 LangChain 的 `BaseMessage` 列表
  - 支持 `ToolMessage` 类型

**修改位置**：
```python
# 在 LampState 类中添加新字段
class LampState(TypedDict):
    # ... 现有字段保持不变 ...
    
    # 新增字段
    user_profile: Dict[str, Any]
    internal_drives: Dict[str, Any]
    memory_context: Optional[str]
    event_type: Optional[str]
    proactive_expression: Optional[str]
    user_preferences: Dict[str, Any]
    context_signals: Dict[str, Any]
```

---

### 2. `nodes.py` - 节点函数扩展和升级

#### 2.1 新增节点函数

**需要新增的函数**：

1. **`evaluator_node(state: LampState) -> Dict`**
   - **功能**：全局评估器，作为图的入口
   - **逻辑**：
     - 判断事件来源（用户输入/定时器/传感器/内部驱动）
     - 如果是定时器且无事发生，返回 `{"should_proceed": False}`
     - 如果是 `boredom > 80`，生成主动搭讪意图
     - 如果是用户输入，标记为 `event_type="user_input"`
   - **返回**：`{"should_proceed": bool, "event_type": str, "user_input": Optional[str]}`

2. **`memory_loader_node(state: LampState) -> Dict`**
   - **功能**：记忆读取和查询重写
   - **逻辑**：
     - 如果 `user_input` 存在，进行 Query Rewrite（用 LLM 将用户输入转为检索查询）
     - 从 `user_memory` 集合检索相关记忆
     - 从 `action_library` 集合检索相关动作
     - 将检索结果合并到 `memory_context`
   - **返回**：`{"memory_context": str}`

3. **`timing_evaluator_node(state: LampState) -> Dict`**（可选，解决缺点1）
   - **功能**：时机评估，判断是否适合主动交互
   - **逻辑**：检查冷却期、勿扰时间、用户反馈历史等
   - **返回**：`{"should_proceed": bool, "proactive_level": str}`

4. **`expression_translator_node(state: LampState) -> Dict`**（可选，解决缺点4）
   - **功能**：将内部状态转换为正向表达
   - **逻辑**：将 `boredom`、`absence_duration` 等转换为"好想你啊"等正向表达
   - **返回**：`{"proactive_expression": str}`

5. **`tool_node(state: LampState) -> Dict`**（可选）
   - **功能**：工具调用节点
   - **逻辑**：如果需要调用外部 API（天气、新闻等），在这里处理
   - **返回**：工具调用结果

#### 2.2 升级现有节点函数

**需要修改的函数**：

1. **`perception_node`**
   - **当前**：锁死兴奋状态
   - **升级后**：
     - 读取 `internal_drives` 中的状态
     - 更新 `context_signals`（当前时间、用户活动状态等）
     - 计算 `absence_duration`（用户离开时长）

2. **`router_node`**
   - **当前**：基于简单规则分流
   - **升级后**：
     - 使用 Function Calling (Structured Output) 进行精确分类
     - 支持三种路由：`"reflex"`, `"reasoning"`, `"ignore"`
     - 考虑 `memory_context` 和 `event_type`

3. **`reasoning_node`**
   - **当前**：直接使用 `user_input` 调用 LLM
   - **升级后**：
     - 如果 `memory_context` 存在，将其注入 System Prompt
     - 支持 Query Expansion（已在 `memory_loader_node` 中处理）
     - 考虑 `user_profile` 进行个性化回复

4. **`execution_node`**
   - **当前**：仅模拟硬件调用
   - **升级后**：
     - 执行硬件控制
     - **记忆写入**：分析 LLM 回复，提取用户新喜好，存入 `user_memory` 集合
     - **状态更新**：更新 `internal_drives`（重置 `boredom`，更新 `last_interaction_time`）
     - **反馈循环**：为下一次循环准备状态

**修改位置**：
```python
# 在 nodes.py 文件末尾或适当位置添加新函数
# 修改现有函数内部逻辑
```

---

### 3. `graph.py` - 工作流图重构

**修改内容**：

- [ ] **修改入口点**
  - 从 `perception` 改为 `evaluator`
  
- [ ] **注册新节点**
  - 添加 `evaluator` 节点
  - 添加 `memory_loader` 节点
  - 添加 `timing_evaluator` 节点（可选）
  - 添加 `expression_translator` 节点（可选）
  - 添加 `tool_node` 节点（可选）

- [ ] **重构连接边**
  - `START` -> `evaluator`
  - `evaluator` -> `timing_evaluator`（可选，如果实现缺点1解决方案）
  - `timing_evaluator` -> `memory_loader` 或 `evaluator` -> `memory_loader`
  - `memory_loader` -> `router`
  - `router` -> `reflex` 或 `reasoning`（条件边）
  - `reasoning` <-> `tool_node`（循环边，如果实现工具调用）
  - `reflex` -> `guard`
  - `reasoning` -> `guard`
  - `guard` -> `execution`
  - `execution` -> `END`（或循环回 `evaluator` 实现无限循环）

- [ ] **添加条件路由函数**
  - `should_proceed_decision(state)` - 判断是否继续
  - `route_decision(state)` - 路由决策（保持现有）

**修改位置**：
```python
# 在 build_graph() 函数中
def build_graph():
    workflow = StateGraph(LampState)
    
    # 注册所有节点（包括新增的）
    workflow.add_node("evaluator", evaluator_node)
    workflow.add_node("memory_loader", memory_loader_node)
    # ... 其他节点 ...
    
    # 修改入口和连接
    workflow.set_entry_point("evaluator")
    # ... 重新连接所有边 ...
```

---

### 4. `main.py` - 改为事件驱动循环

**修改内容**：

- [ ] **移除**：现有的示例代码（两个 `app.invoke()` 调用）

- [ ] **新增**：事件循环结构
  - 导入事件管理器模块
  - 初始化状态（包含 `internal_drives` 等新字段）
  - 实现 `while True` 循环
  - 在循环中：
    1. 获取事件（用户输入/定时器/传感器）
    2. 更新内部状态（无聊度递增、计算离开时长等）
    3. 判断是否需要触发工作流
    4. 调用 `app.invoke()` 执行工作流
    5. 更新状态（为下一次循环准备）
    6. 休眠（防止 CPU 占用过高）

**修改位置**：
```python
# 完全重写 main() 函数
def main():
    app = build_graph()
    
    # 初始化状态
    current_state = initialize_state()
    
    # 事件循环
    while True:
        # 1. 获取事件
        # 2. 更新内部状态
        # 3. 判断是否触发
        # 4. 执行工作流
        # 5. 更新状态
        # 6. 休眠
```

---

## ➕ 需要新增的文件和代码

### 1. `event_manager.py` - 事件管理器（新建文件）

**功能**：管理各种事件源

**需要实现**：

- [ ] **`EventManager` 类**
  - `get_event()` - 获取事件（用户输入/定时器/传感器）
  - `register_timer(callback, interval)` - 注册定时器
  - `register_sensor(sensor_type, callback)` - 注册传感器
  - `get_user_input()` - 获取用户输入（非阻塞）

- [ ] **事件类型定义**
  - `UserInputEvent`
  - `TimerEvent`
  - `SensorEvent`
  - `InternalDriveEvent`

**文件位置**：`/Users/JiajunFei/Documents/开普勒/event_manager.py`

**代码结构**：
```python
# event_manager.py
from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime
import threading
import queue

@dataclass
class Event:
    type: str  # "user_input", "timer", "sensor", "internal_drive"
    data: Dict[str, Any]
    timestamp: float

class EventManager:
    def __init__(self):
        self.event_queue = queue.Queue()
        # ... 初始化 ...
    
    def get_event(self) -> Optional[Event]:
        # 非阻塞获取事件
        pass
    
    # ... 其他方法 ...
```

---

### 2. `memory_manager.py` - 记忆系统管理（新建文件）

**功能**：管理向量数据库和记忆操作

**需要实现**：

- [ ] **`MemoryManager` 类**
  - `__init__()` - 初始化两个向量数据库集合
    - `action_library` - 动作库（已存在，需要启用）
    - `user_memory` - 用户记忆（新建）
  
  - `query_rewrite(user_input: str) -> str` - Query Rewrite
    - 使用 LLM 将用户输入转为检索查询
  
  - `retrieve_user_memory(query: str, k: int = 3) -> List[Document]` - 检索用户记忆
  
  - `retrieve_action_library(query: str, k: int = 2) -> List[Document]` - 检索动作库
  
  - `save_user_memory(content: str, metadata: Dict)` - 保存用户记忆
    - 添加时间戳、分类标签等元数据
  
  - `extract_user_preference(llm_response: str) -> Optional[Dict]` - 从 LLM 回复中提取用户偏好

**文件位置**：`/Users/JiajunFei/Documents/开普勒/memory_manager.py`

**代码结构**：
```python
# memory_manager.py
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document
from typing import List, Dict, Optional

class MemoryManager:
    def __init__(self, db_path: str = "./chroma_db_actions"):
        # 初始化 embeddings
        # 初始化 action_library 集合
        # 初始化 user_memory 集合
        pass
    
    def query_rewrite(self, user_input: str) -> str:
        # 使用 LLM 进行查询重写
        pass
    
    # ... 其他方法 ...
```

---

### 3. `state_manager.py` - 状态管理（新建文件，可选）

**功能**：管理内部状态更新和持久化

**需要实现**：

- [ ] **`StateManager` 类**
  - `update_internal_state(state: LampState) -> LampState` - 更新内部状态
    - 递增 `boredom`（随时间增长）
    - 计算 `absence_duration`（用户离开时长）
    - 更新 `last_interaction_time`
  
  - `initialize_state() -> LampState` - 初始化状态
    - 设置默认值
    - 加载持久化状态（如果存在）
  
  - `save_state(state: LampState)` - 保存状态（可选，持久化）
  
  - `load_state() -> Optional[LampState]` - 加载状态（可选，持久化）

**文件位置**：`/Users/JiajunFei/Documents/开普勒/state_manager.py`

**代码结构**：
```python
# state_manager.py
from state import LampState
from typing import Optional
import time
import json

class StateManager:
    def __init__(self):
        pass
    
    def update_internal_state(self, state: LampState) -> LampState:
        # 更新内部驱动力
        internal = state.get("internal_drives", {})
        current_time = time.time()
        
        # 计算离开时长
        last_interaction = internal.get("last_interaction_time", current_time)
        absence_duration = current_time - last_interaction
        
        # 递增无聊度（例如：每分钟 +1，最高 100）
        boredom = internal.get("boredom", 0)
        boredom_increase = int(absence_duration / 60)  # 每分钟 +1
        boredom = min(boredom + boredom_increase, 100)
        
        # 更新状态
        internal["boredom"] = boredom
        internal["absence_duration"] = absence_duration
        
        return {**state, "internal_drives": internal}
    
    # ... 其他方法 ...
```

---

### 4. `tools.py` - 工具定义（新建文件，可选）

**功能**：定义外部工具（天气、新闻等）

**需要实现**：

- [ ] **工具函数定义**
  - `get_weather(city: str) -> str` - 获取天气
  - `get_news(keyword: str) -> str` - 获取新闻
  - 其他工具...

- [ ] **工具注册**
  - 使用 LangChain 的 `@tool` 装饰器
  - 注册到 LangGraph 的 `ToolNode`

**文件位置**：`/Users/JiajunFei/Documents/开普勒/tools.py`

---

## 📝 实施步骤（按顺序）

### 阶段 1：基础架构搭建

1. **修改 `state.py`**
   - 添加所有新字段到 `LampState`
   - 确保类型定义正确

2. **创建 `event_manager.py`**
   - 实现基础的事件管理器
   - 支持用户输入和定时器事件

3. **创建 `state_manager.py`**
   - 实现内部状态更新逻辑
   - 实现状态初始化

4. **修改 `main.py`**
   - 改为事件循环结构
   - 集成事件管理器和状态管理器

### 阶段 2：记忆系统

5. **创建 `memory_manager.py`**
   - 初始化两个向量数据库集合
   - 实现 Query Rewrite
   - 实现记忆检索和保存

6. **在 `nodes.py` 中新增 `memory_loader_node`**
   - 调用 `MemoryManager` 进行记忆检索
   - 将结果写入 `memory_context`

7. **升级 `reasoning_node`**
   - 集成 `memory_context` 到 System Prompt
   - 支持个性化回复

8. **升级 `execution_node`**
   - 实现记忆写入逻辑
   - 调用 `MemoryManager.save_user_memory()`

### 阶段 3：OODA 循环核心

9. **在 `nodes.py` 中新增 `evaluator_node`**
   - 判断事件来源
   - 处理内部驱动触发
   - 生成主动搭讪意图

10. **升级 `perception_node`**
    - 读取和更新 `internal_drives`
    - 更新 `context_signals`

11. **升级 `router_node`**
    - 使用 Function Calling 进行精确分类
    - 支持 `ignore` 路由

12. **修改 `graph.py`**
    - 注册所有新节点
    - 重构连接边
    - 设置 `evaluator` 为入口

### 阶段 4：可选功能

13. **实现缺点1解决方案**（可选）
    - 新增 `timing_evaluator_node`
    - 集成到图中

14. **实现缺点4解决方案**（可选）
    - 新增 `expression_translator_node`
    - 集成到图中

15. **实现工具调用**（可选）
    - 创建 `tools.py`
    - 新增 `tool_node`
    - 集成到 `reasoning` 循环中

### 阶段 5：测试和优化

16. **测试事件循环**
    - 测试用户输入事件
    - 测试定时器事件
    - 测试内部驱动触发

17. **测试记忆系统**
    - 测试记忆检索
    - 测试记忆写入
    - 测试 Query Rewrite

18. **测试主动行为**
    - 测试 `boredom > 80` 触发
    - 测试正向表达生成

19. **性能优化**
    - 优化事件循环频率
    - 优化向量检索性能
    - 添加错误处理和日志

---

## 🔗 依赖关系

```
main.py
  ├── event_manager.py (新建)
  ├── state_manager.py (新建)
  └── graph.py (修改)
       └── nodes.py (修改)
            ├── memory_manager.py (新建)
            └── tools.py (新建，可选)
```

---

## ⚠️ 注意事项

1. **向后兼容**：修改现有节点时，确保不影响现有功能
2. **错误处理**：所有新代码都要有完善的异常处理
3. **性能考虑**：事件循环要有适当的休眠，避免 CPU 占用过高
4. **状态持久化**：考虑是否需要将状态保存到文件，以便重启后恢复
5. **向量数据库**：确保 `user_memory` 集合正确初始化，避免数据混乱

---

## 📊 代码量估算

- **修改文件**：4 个（`state.py`, `nodes.py`, `graph.py`, `main.py`）
- **新建文件**：3-4 个（`event_manager.py`, `memory_manager.py`, `state_manager.py`, `tools.py`）
- **新增代码行数**：约 800-1200 行
- **修改代码行数**：约 200-300 行

---

**文档创建时间**：2024年

