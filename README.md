# 智能台灯系统 (Neko-Light)

一个基于 LangGraph 和 LangChain 构建的智能台灯系统，使用 RAG（检索增强生成）技术实现智能对话和动作控制。

## 📋 项目简介

本项目实现了一个具有"温柔坚定"性格的智能台灯，能够：
- 感知用户输入（文本/传感器数据）
- 通过路由节点决定使用快速反射或深度推理
- 使用 RAG 技术从动作库中检索相关动作
- 通过 LLM 生成个性化的语音回复和动作计划
- 执行硬件控制指令（电机、灯光、声音）

## 🏗️ 架构设计

### 工作流程图

```
感知节点 (Perception)
    ↓
路由节点 (Router)
    ↓
    ├─→ 反射节点 (Reflex) ──┐
    │                        │
    └─→ 推理节点 (Reasoning) ─┘
                            ↓
                    安全卫士节点 (Action Guard)
                            ↓
                    执行节点 (Execution)
                            ↓
                           END
```

### 目录结构

```
Neko_light/
├── src/                    # 核心源代码
│   ├── main.py            # 主程序入口
│   ├── nodes.py           # 图节点实现
│   ├── graph.py           # 工作流图定义
│   ├── state.py           # 状态定义
│   ├── memory_manager.py  # 记忆管理
│   ├── context_manager.py # 上下文管理
│   ├── state_manager.py   # 状态管理
│   ├── intimacy_manager.py # 亲密度管理
│   ├── conflict_handler.py # 冲突处理
│   ├── focus_mode_manager.py # 专注模式
│   ├── reflex_router.py   # 反射路由
│   ├── event_manager.py    # 事件管理
│   ├── mcp_manager.py     # MCP 管理
│   ├── tool_documentation.py # 工具文档
│   ├── tools.py           # 工具定义
│   └── ...                # 其他模块
├── config/                # 配置文件
│   └── prompts.py         # 提示词配置
├── docs/                  # 文档目录
│   ├── prd/               # 产品需求文档
│   ├── architecture/      # 架构文档
│   ├── implementation/    # 实现文档
│   ├── guides/            # 使用指南
│   ├── plans/             # 计划文档
│   └── summaries/         # 总结文档
├── tests/                 # 测试目录
├── demo/                  # 演示应用
├── data/                  # 数据目录
│   ├── chroma_db_actions/ # 向量数据库
│   └── lamp_state.json    # 状态文件
└── main.py                # 项目入口（调用 src/main.py）
```

### 核心组件

1. **src/state.py** - 状态定义
   - `LampState`: 定义台灯智能体的完整状态结构
   - 包含用户输入、传感器数据、能量等级、情绪状态、动作计划等

2. **src/nodes.py** - 节点实现
   - `perception_node`: 感知节点，处理传感器数据
   - `router_node`: 路由节点，决定使用反射还是推理路径
   - `reflex_node`: 反射节点，快速硬编码响应
   - `reasoning_node`: 推理节点，使用 RAG + LLM 生成响应
   - `action_guard_node`: 安全卫士，修饰和验证动作计划
   - `execution_node`: 执行节点，模拟硬件调用

3. **src/graph.py** - 工作流图
   - 使用 LangGraph 构建状态图
   - 定义节点之间的连接和条件路由

## 🚀 快速开始

### 环境要求

- Python 3.8+
- OpenAI API Key

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置

1. **API Key 设置**（必需）：

   推荐使用环境变量设置 API Key（安全）：

   ```bash
   export VOLCENGINE_API_KEY="your-actual-api-key"
   ```

   或者在代码中设置（仅用于测试，不要提交到版本控制）：

   ```python
   import os
   os.environ["VOLCENGINE_API_KEY"] = "your-actual-api-key"
   ```

   或者创建 `.env` 文件：

   ```bash
   cp env-example.txt .env
   # 然后编辑 .env 文件，填入你的实际 API Key
   ```

   或者直接创建：

   ```bash
   echo "VOLCENGINE_API_KEY=your-actual-api-key" > .env
   ```

   **⚠️ 安全警告**：不要将真实的 API Key 提交到 GitHub 或分享给他人！

2. 向量数据库路径（默认：`./data/chroma_db_actions`）

### 运行程序

直接运行主程序：

```bash
python main.py
```

或者运行演示应用：

```bash
cd demo
streamlit run app.py
```

### 运行示例

使用 Python 代码运行工作流：

```python
from src.graph import build_graph
from src.state import LampState

# 构建工作流图
app = build_graph()

# 初始化状态
initial_state: LampState = {
    "user_input": "我累了，需要一些鼓励",
    "sensor_data": {},
    "energy_level": 0,
    "current_mood": "",
    "intent_route": "",
    "action_plan": {},
    "voice_content": None,
    "history": []
}

# 运行工作流
result = app.invoke(initial_state)
print("\n最终结果:", result)
```

## 📦 依赖说明

主要依赖包：

- **langchain-openai**: OpenAI 模型集成
- **langchain-community**: 社区集成（向量数据库等）
- **langchain-core**: LangChain 核心功能
- **langgraph**: 状态图和工作流管理
- **chromadb**: 向量数据库，用于 RAG 检索
- **pydantic**: 数据验证和类型检查

完整依赖列表请查看 `requirements.txt`。

## 🔧 功能详解

### 1. 感知节点 (Perception)

- 处理传感器数据
- 设置初始能量等级和情绪状态
- 当前实现：温柔坚定性格（mood="gentle_firm"）

### 2. 路由节点 (Router)

基于规则决定处理路径：
- **反射路径 (reflex)**: 传感器触发（如触摸）或默认情况
- **推理路径 (reasoning)**: 用户文本输入

### 3. 反射节点 (Reflex)

快速响应，无需 LLM：
- 硬编码的动作计划
- 彩虹灯光、快速闪烁、最大震动
- 无语音回复

### 4. 推理节点 (Reasoning)

使用 RAG + LLM 的深度处理：
1. **RAG 检索**: 从向量数据库中检索相似的动作场景
2. **LLM 生成**: 基于检索结果和用户输入生成个性化回复
3. **结构化输出**: 返回语音内容和动作计划

### 5. 安全卫士节点 (Action Guard)

- 验证和修饰动作计划
- 确保动作计划符合安全规范
- V1: 尊重LLM生成的原始动作计划，不再强制修改

### 6. 执行节点 (Execution)

- 模拟硬件调用
- 输出语音内容和动作计划
- 在实际部署中，这里会调用真实的硬件接口

## 🗄️ 向量数据库

项目使用 ChromaDB 存储动作库，用于 RAG 检索。

### 初始化动作库

你可以通过以下方式向向量数据库添加动作：

```python
from langchain_core.documents import Document
from src.memory_manager import MemoryManager

# 初始化记忆管理器
memory_manager = MemoryManager()

# 添加动作文档
documents = [
    Document(page_content="当用户说累了时，应该播放鼓励的音乐，灯光调成温暖的橙色"),
    Document(page_content="用户触摸时，快速闪烁彩虹灯，震动反馈"),
    # ... 更多动作
]

# 保存到动作库
memory_manager.save_to_action_library(documents)
```

## 🎯 使用场景

1. **快速响应**: 触摸传感器 → 反射节点 → 立即响应
2. **智能对话**: 用户说"我累了" → 推理节点 → RAG 检索 → LLM 生成鼓励回复
3. **个性化交互**: 基于历史对话和动作库，生成符合"温柔坚定"性格的回复

## 🔒 注意事项

1. **API Key 安全**: 不要将 API Key 提交到版本控制系统
2. **向量数据库**: 首次运行会自动创建向量数据库目录
3. **错误处理**: 推理节点包含异常处理，LLM 失败时会返回默认响应

## 📝 扩展建议

1. **添加更多传感器**: 视觉、声音等
2. **增强 RAG**: 添加更多动作场景到向量数据库
3. **持久化状态**: 使用 LangGraph 的检查点功能保存对话历史
4. **硬件集成**: 在 `execution_node` 中连接真实的硬件接口
5. **多模态输入**: 支持图像、音频输入


---

**注意**: 这是一个演示项目，展示了如何使用 LangGraph 和 RAG 技术构建智能硬件控制系统。在实际部署前，请确保：
- 配置正确的 API Key
- 测试所有功能
- 添加适当的错误处理和日志记录
- 考虑安全性和隐私保护

