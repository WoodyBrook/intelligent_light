# 多模型切换功能实现文档

## 概述

实现了智能**三级模型切换**策略，根据任务类型自动选择最合适的模型：

| 层级 | 模型 | 用途 | 延迟 | 成本 |
|:---|:---|:---|:---:|:---:|
| ⚡ Fast | doubao-lite-32k-character | 问候、确认、简单回复 | ~0.5s | 最低 |
| 💬 Chat | deepseek-chat | 情感陪伴、日常闲聊 | ~1.5s | 低 |
| 🧠 Reasoning | deepseek-v3-1-terminus | 复杂推理、工具调用 | ~3s | 高 |

## 架构设计

### 三级模型切换流程

```
用户输入 → 场景分类 → 模型选择
                │
    ┌───────────┼───────────┐
    ▼           ▼           ▼
  Fast        Chat      Reasoning
   │           │           │
   ▼           ▼           ▼
"你好"      "好累啊"    "帮我查天气"
"嗯"        "想你了"    "分析一下..."
"好的"      "今天心情"   "如果...然后..."
```

### 核心组件

1. **`ModelManager`** (`src/model_manager.py`)
   - 管理三个 LLM 实例
   - 提供三级模型选择逻辑
   - 支持延迟初始化
   - 调用统计与成本追踪

2. **语气一致性保障** (`config/prompts.py`)
   - `TONE_EXAMPLES`: Few-shot 示例
   - `TONE_RULES`: 语气硬约束
   - `get_fast_prompt()`: Fast 模型专用简化 Prompt

3. **集成点**
   - `reasoning_node`: 自动三级模型选择
   - `plan_node`: 强制使用 reasoning 模型

## 模型选择策略

### 自动选择逻辑 (`_select_model_tier`)

```python
决策流程：
1. 需要工具调用 → reasoning
2. 超简单输入（问候、确认） → fast
3. 复杂任务关键词 → reasoning
4. 条件逻辑/多步骤 → reasoning
5. 工具相关关键词 → reasoning
6. 长对话历史(>5轮) → reasoning
7. 情感/闲聊场景 → chat
8. 其他情况 → 默认策略
```

### Fast 场景识别模式

精确匹配以下模式才使用 Fast 模型：

```python
FAST_PATTERNS = [
    r"^你好[!！~]?$",    # 问候
    r"^嗯[!！。~]?$",    # 确认
    r"^好的[!！~]?$",    # 确认
    r"^谢谢[你您]?[!！~]?$",  # 感谢
    r"^再见[!！~]?$",    # 道别
    r"^ok[!]?$",         # 英文确认
    ...
]
```

### 默认策略配置

```python
ModelManager(
    default_strategy="aggressive"  # 不确定时用 Chat
    # 或 "conservative" 用 Reasoning
)
```

## 语气一致性保障

### Few-shot 示例

```xml
<tone_examples>
<example scenario="问候">
用户：你好
Animus：嗨~今天过得怎么样呀？
</example>
<example scenario="情感支持">
用户：好累啊
Animus：辛苦啦…要不要听首歌放松一下？
</example>
...
</tone_examples>
```

### 语气硬约束

```xml
<tone_rules strict="true">
<rule type="word_choice">
语气词使用规范：
- 必须使用：嗯~、呀、嘿嘿、哦、啦、呢、吧
- 禁止使用：好的我明白了、根据您的需求
</rule>
<rule type="forbidden">
绝对禁止的表达：
- "好的，我明白了"
- "根据我的记忆/数据/分析"
- "作为一个AI/人工智能"
</rule>
</tone_rules>
```

## 使用示例

### 基本使用

```python
from src.model_manager import get_model_manager

model_manager = get_model_manager()

# 自动选择模型
llm, model_name = model_manager.select_model(
    task_type="auto",
    user_input="你好",
    has_tools=False
)

# 查看选择了哪个层级
tier = model_manager.get_model_tier(model_name)
print(f"选择: {tier}")  # "fast"
```

### 强制指定层级

```python
# 强制使用 fast 模型
llm, name = model_manager.select_model(task_type="fast")

# 强制使用 chat 模型
llm, name = model_manager.select_model(task_type="chat")

# 强制使用 reasoning 模型
llm, name = model_manager.select_model(task_type="reasoning")
```

### 调用统计

```python
# 记录调用
model_manager.record_call("fast", elapsed_time=0.5, estimated_tokens=100)

# 获取统计
stats = model_manager.get_stats()
print(f"Fast 调用次数: {stats['fast']['calls']}")
print(f"总估算成本: ¥{stats['total']['estimated_cost']:.6f}")

# 打印完整报告
model_manager.print_stats()
```

## 配置

### 环境变量

```bash
export VOLCENGINE_API_KEY="your-api-key"
# 或
export ARK_API_KEY="your-api-key"
```

### 模型配置

```python
ModelManager(
    fast_model="doubao-lite-32k-character-250228",
    chat_model="deepseek-chat",
    reasoning_model="deepseek-v3-1-terminus",
    base_url="https://ark.cn-beijing.volces.com/api/v3",
    default_strategy="aggressive"
)
```

## 成本估算

### 模型成本（人民币/1K tokens）

| 模型 | 输入 | 输出 |
|:---|---:|---:|
| doubao-lite-32k-character | ¥0.0003 | ¥0.0006 |
| deepseek-chat | ¥0.001 | ¥0.002 |
| deepseek-v3-1-terminus | ¥0.005 | ¥0.01 |

### 统计报告示例

```
============================================================
📊 模型调用统计报告（三级模型）
============================================================

⚡ Fast 模型 (doubao-lite-32k-character-250228):
   - 调用次数: 10
   - 总耗时: 5.000s
   - 平均耗时: 0.500s
   - 估算成本: ¥0.000450

💬 Chat 模型 (deepseek-chat):
   - 调用次数: 5
   - 总耗时: 7.500s
   - 平均耗时: 1.500s
   - 估算成本: ¥0.001200

🧠 Reasoning 模型 (deepseek-v3-1-terminus):
   - 调用次数: 3
   - 总耗时: 9.000s
   - 平均耗时: 3.000s
   - 估算成本: ¥0.007500

📈 总计:
   - 总调用次数: 18
   - 总耗时: 21.500s
   - 总估算成本: ¥0.009150

📉 使用比例:
   - ⚡ Fast: 55.6%
   - 💬 Chat: 27.8%
   - 🧠 Reasoning: 16.7%
============================================================
```

## 测试

运行测试脚本：

```bash
python scripts/test_model_switching.py
```

测试内容：
- ✅ 三级模型自动选择
- ✅ 手动模型选择
- ✅ 调用统计功能
- ✅ 工具调用触发 Reasoning
- ✅ 边界情况处理

## 注意事项

1. **语气一致性**
   - 所有模型共享相同的人格 Prompt
   - 包含 Few-shot 示例保证语气风格
   - Fast 模型使用简化 Prompt 提高速度

2. **模型可用性**
   - 确保火山引擎账号有权限使用豆包模型
   - API Key 同时支持 `VOLCENGINE_API_KEY` 和 `ARK_API_KEY`

3. **陪伴体验**
   - Fast 模型的快速响应提升陪伴感
   - 简单场景不需要复杂模型

## 更新日志

- **2026-01-07**: V3.0 三级模型切换
  - 新增 Fast 层级（豆包 doubao-lite-32k-character）
  - 重构模型选择逻辑为三级架构
  - 添加语气一致性保障（Few-shot + 硬约束）
  - 更新成本估算为人民币

- **2026-01-07**: V2.0 功能优化
  - 修复注释与代码不一致
  - 优化关键词匹配
  - 新增调用统计和成本追踪

- **2025-01-XX**: V1.0 初始实现
  - 创建 `ModelManager` 类
  - 两级模型切换（Chat/Reasoning）
