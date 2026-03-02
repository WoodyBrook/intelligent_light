# 记忆系统增强实现计划

基于 LangGraph Memory 调研结果，为 Neko_light 添加 **Profile 模式增强** 和 **Few-shot Learning (Episodic Memory)** 能力。

## 优先级说明

| 优先级 | 功能 | 状态 |
|--------|------|------|
| **P1** | Profile 模式增强 | 本次实现 |
| **P1** | Few-shot Learning (Episodic Memory) | 本次实现 |
| P2 | Namespace 组织 | 后续迭代 |
| P2 | Procedural 自我反思 | 后续迭代 |

---

## P1-1: Profile 模式增强

### 现状分析

当前系统已有 Profile 模式（[UserProfile](file:///Users/JiajunFei/Documents/%E5%BC%80%E6%99%AE%E5%8B%92/Neko_light/src/state.py#6-43) 类在 [state.py](file:///Users/JiajunFei/Documents/%E5%BC%80%E6%99%AE%E5%8B%92/Neko_light/src/state.py)），但存在以下问题：

1. **字段分散**: 核心偏好只有 `core_preferences: List[str]`，缺少结构化分类
2. **缺少总结机制**: 没有从 Collection 记忆中自动合成 Profile 的能力
3. **未充分使用**: 检索时仍依赖 Collection 模式，Profile 仅作为静态画像

### 目标

1. 扩展 [UserProfile](file:///Users/JiajunFei/Documents/%E5%BC%80%E6%99%AE%E5%8B%92/Neko_light/src/state.py#6-43) 结构，增加分类偏好
2. 添加 Profile 自动合成机制（从 Collection → Profile）
3. 在检索时优先返回 Profile 信息

### Proposed Changes

---

#### [MODIFY] [state.py](file:///Users/JiajunFei/Documents/开普勒/Neko_light/src/state.py)

扩展 [UserProfile](file:///Users/JiajunFei/Documents/%E5%BC%80%E6%99%AE%E5%8B%92/Neko_light/src/state.py#6-43) 类，增加结构化偏好字段：

```python
class UserProfile(BaseModel):
    # ... 现有字段 ...
    
    # === 新增：分类偏好摘要 ===
    preference_summary: Dict[str, List[str]] = {
        "food": [],      # ["喜欢拉面", "不喜欢辣的"]
        "music": [],     # ["喜欢周杰伦"]
        "activity": [],  # ["喜欢散步"]
        "habit": [],     # ["习惯晚睡"]
        "work": [],      # ["工作压力大"]
    }
    
    # === 新增：Profile 合成时间戳 ===
    last_synthesized: float = 0.0  # 上次从 Collection 合成的时间
```

---

#### [MODIFY] [memory_manager.py](file:///Users/JiajunFei/Documents/开普勒/Neko_light/src/memory_manager.py)

**新增方法：`synthesize_profile_from_collection()`**

每日或按需从 Collection 记忆中提取高频偏好，合并到 Profile：

```python
def synthesize_profile_from_collection(self) -> bool:
    """
    从 Collection 记忆中合成 Profile 偏好摘要
    使用 LLM 对相似记忆进行归纳
    """
    # 1. 获取所有偏好类记忆
    # 2. 按 category 分组
    # 3. 使用 LLM 合成每个 category 的摘要
    # 4. 更新 Profile.preference_summary
    pass
```

**修改方法：[retrieve_memory_context()](file:///Users/JiajunFei/Documents/%E5%BC%80%E6%99%AE%E5%8B%92/Neko_light/src/memory_manager.py#297-324)**

优先返回 Profile 摘要，再补充 Collection 细节：

```python
def retrieve_memory_context(...):
    # 1. 先获取 Profile 摘要
    profile = self.load_profile()
    profile_context = self._format_profile_as_context(profile)
    
    # 2. 再获取 Collection 细节（补充）
    collection_memories = self.retrieve_user_memory(query, k=3)
    
    # 3. 合并返回
    return {
        "profile_summary": profile_context,
        "detailed_memories": collection_memories,
        ...
    }
```

---

## P1-2: Few-shot Learning (Episodic Memory)

### 现状分析

当前系统没有 Episodic Memory（情景记忆用于 Few-shot）。无法从成功/失败的交互中学习。

### 目标

1. 创建新的 ChromaDB Collection: `episodes`
2. 在交互成功/失败后自动保存 Episode
3. 检索时查找相似 Episode 作为 Few-shot 示例注入 Prompt

### Proposed Changes

---

#### [MODIFY] [memory_manager.py](file:///Users/JiajunFei/Documents/开普勒/Neko_light/src/memory_manager.py)

**新增 [__init__](file:///Users/JiajunFei/Documents/%E5%BC%80%E6%99%AE%E5%8B%92/Neko_light/src/memory_manager.py#23-85) 中初始化 `episodes` Collection**

```python
def __init__(self, db_path: str = "./data/chroma_db_actions"):
    # ... 现有代码 ...
    
    # 初始化情景记忆集合 (Few-shot Episodes)
    self.episodes_path = os.path.join(db_path, "episodes")
    try:
        self.episodes_store = Chroma(
            collection_name="episodes",
            embedding_function=self.embeddings,
            persist_directory=self.episodes_path
        )
        print("情景记忆集合已加载")
    except Exception as e:
        print(f"[WARN]  情景记忆集合初始化失败: {e}")
        self.episodes_store = None
```

**新增方法：`save_episode()`**

```python
def save_episode(
    self,
    context: str,       # 用户输入的上下文
    action: str,        # Agent 采取的动作
    outcome: str,       # "positive" | "negative" | "neutral"
    tool_used: Optional[str] = None,  # 使用的工具
    metadata: Optional[Dict] = None
) -> bool:
    """
    保存一个交互情景作为 Few-shot 示例
    """
    content = f"Context: {context}\nAction: {action}\nOutcome: {outcome}"
    # ... 类似 save_user_memory 的逻辑 ...
```

**新增方法：`retrieve_similar_episodes()`**

```python
def retrieve_similar_episodes(self, query: str, k: int = 2) -> List[Dict]:
    """
    检索相似的历史情景用于 Few-shot
    优先返回 outcome=positive 的案例
    """
    # 1. 向量检索 Top-10
    # 2. 按 outcome 排序（positive > neutral > negative）
    # 3. 返回 Top-k
```

---

#### [MODIFY] [nodes.py](file:///Users/JiajunFei/Documents/开普勒/Neko_light/src/nodes.py)

**修改 `execution_node`**

在工具调用成功/失败后，自动保存 Episode：

```python
# 在 execution_node 中
if tool_success:
    memory_manager.save_episode(
        context=user_input,
        action=f"使用 {tool_name} 工具",
        outcome="positive",
        tool_used=tool_name
    )
else:
    memory_manager.save_episode(
        context=user_input,
        action=f"尝试使用 {tool_name} 失败",
        outcome="negative",
        tool_used=tool_name
    )
```

**修改 `plan_node` 或 Prompt 构建**

将 Few-shot 示例注入到规划 Prompt 中：

```python
# 获取相似案例
similar_episodes = memory_manager.retrieve_similar_episodes(user_input, k=2)

# 格式化为 Few-shot 示例
few_shot_examples = format_episodes_as_examples(similar_episodes)

# 注入 Prompt
prompt = f"""
参考以下成功案例:
{few_shot_examples}

当前对话:
{user_input}
"""
```

---

## Verification Plan

### Automated Tests

#### 1. Profile 合成测试

```bash
cd /Users/JiajunFei/Documents/开普勒/Neko_light
python -m pytest tests/test_profile_memory.py -v
```

> **注意**: 需要先查看现有测试内容，可能需要新增测试用例。

#### 2. Episode 保存/检索测试

新增测试文件 `tests/test_episode_memory.py`：

```bash
python -m pytest tests/test_episode_memory.py -v
```

测试内容：
- 保存 Episode 成功
- 检索相似 Episode
- outcome 排序正确

### Manual Verification

#### 1. Profile 合成验证

1. 启动系统，进行几轮包含偏好的对话（如"我喜欢拉面"、"我喜欢周杰伦"）
2. 调用 `synthesize_profile_from_collection()`
3. 检查 `user_profile.json` 中 `preference_summary` 是否正确填充

#### 2. Few-shot 效果验证

1. 进行一轮工具调用（如查天气）
2. 检查 `episodes` Collection 是否有新记录
3. 进行类似的新查询，确认 Few-shot 示例被注入 Prompt（通过日志验证）

---

## 实施顺序

1. ✅ 扩展 [UserProfile](file:///Users/JiajunFei/Documents/%E5%BC%80%E6%99%AE%E5%8B%92/Neko_light/src/state.py#6-43) 结构 ([state.py](file:///Users/JiajunFei/Documents/%E5%BC%80%E6%99%AE%E5%8B%92/Neko_light/src/state.py))
2. 添加 `episodes` Collection 初始化 ([memory_manager.py](file:///Users/JiajunFei/Documents/%E5%BC%80%E6%99%AE%E5%8B%92/Neko_light/src/memory_manager.py))
3. 实现 `save_episode()` 和 `retrieve_similar_episodes()` ([memory_manager.py](file:///Users/JiajunFei/Documents/%E5%BC%80%E6%99%AE%E5%8B%92/Neko_light/src/memory_manager.py))
4. 实现 `synthesize_profile_from_collection()` ([memory_manager.py](file:///Users/JiajunFei/Documents/%E5%BC%80%E6%99%AE%E5%8B%92/Neko_light/src/memory_manager.py))
5. 修改 `execution_node` 自动保存 Episode ([nodes.py](file:///Users/JiajunFei/Documents/%E5%BC%80%E6%99%AE%E5%8B%92/Neko_light/src/nodes.py))
6. 修改 Prompt 注入 Few-shot 示例 ([nodes.py](file:///Users/JiajunFei/Documents/%E5%BC%80%E6%99%AE%E5%8B%92/Neko_light/src/nodes.py) 或 [prompts.py](file:///Users/JiajunFei/Documents/%E5%BC%80%E6%99%AE%E5%8B%92/Neko_light/config/prompts.py))
7. 编写测试并验证

---

## 风险与规避方案

### 风险 1: Episode 存储量膨胀

> [!WARNING]
> Episodes 会随着使用累积，可能导致存储和检索性能下降。

**规避方案：滚动窗口 + 智能清理**

```python
# memory_manager.py 新增配置
EPISODE_CONFIG = {
    "max_count": 500,           # 最大存储数量
    "cleanup_threshold": 600,   # 触发清理的阈值
    "neutral_ttl_days": 30,     # neutral 记录的 TTL
    "similarity_threshold": 0.9 # 去重相似度阈值
}

def _cleanup_old_episodes(self):
    """
    清理策略（按优先级）：
    1. 删除 30 天前的 outcome=neutral 记录
    2. 删除重复度 >90% 的相似记录（保留最新）
    3. 如仍超限，删除最旧的 negative 记录
    4. 永不删除 positive 记录（但可降低检索权重）
    """
    now = time.time()
    ttl_cutoff = now - (EPISODE_CONFIG["neutral_ttl_days"] * 86400)
    
    # 1. 清理过期 neutral
    self.episodes_store.delete(
        where={"$and": [
            {"outcome": "neutral"},
            {"timestamp": {"$lt": ttl_cutoff}}
        ]}
    )
    
    # 2. 去重（保留最新）
    self._deduplicate_similar_episodes()
    
    # 3. 控制总量
    current_count = self._get_episode_count()
    if current_count > EPISODE_CONFIG["max_count"]:
        excess = current_count - EPISODE_CONFIG["max_count"]
        self._delete_oldest_by_outcome("negative", limit=excess)
```

---

### 风险 2: Profile 合成阻塞主流程

> [!IMPORTANT]
> 合成操作需要 LLM 调用，可能耗时 2-5 秒，不能阻塞用户交互。

**规避方案：异步执行 + 阈值触发**

```python
# memory_manager.py 新增配置
SYNTHESIS_CONFIG = {
    "min_interval_hours": 24,    # 最小合成间隔
    "memory_threshold": 10,      # 新增记忆数阈值
    "force_keywords": ["更新画像", "同步偏好"]  # 用户触发关键词
}

async def maybe_synthesize_profile_async(self, force: bool = False):
    """
    智能触发 Profile 合成（非阻塞）
    
    触发条件（满足任一）:
    1. force=True（用户手动触发）
    2. 距离上次合成 > 24 小时 AND 新增记忆 > 10 条
    """
    profile = self.load_profile()
    hours_since_last = (time.time() - profile.last_synthesized) / 3600
    
    if not force:
        # 检查是否满足自动触发条件
        if hours_since_last < SYNTHESIS_CONFIG["min_interval_hours"]:
            return False
        
        new_count = self._count_new_memories_since(profile.last_synthesized)
        if new_count < SYNTHESIS_CONFIG["memory_threshold"]:
            return False
    
    # 异步执行，不阻塞主流程
    asyncio.create_task(self._do_synthesize_profile())
    print("🔄 后台触发 Profile 合成...")
    return True

async def _do_synthesize_profile(self):
    """实际执行合成的后台任务"""
    try:
        # 1. 获取各类别的偏好记忆
        categories = ["food", "music", "activity", "habit", "work"]
        preference_summary = {}
        
        for cat in categories:
            memories = self.user_memory_store.get(
                where={"category": cat},
                limit=20
            )
            if memories["documents"]:
                # 2. LLM 归纳总结
                summary = await self._llm_summarize(cat, memories["documents"])
                preference_summary[cat] = summary
        
        # 3. 更新 Profile
        profile = self.load_profile()
        profile.preference_summary = preference_summary
        profile.last_synthesized = time.time()
        self.save_profile(profile)
        
        print("✅ Profile 合成完成")
    except Exception as e:
        print(f"[ERROR] Profile 合成失败: {e}")
```

---

### 实现检查清单

以下配置将作为代码中的常量，可根据实际使用情况调整：

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `EPISODE_MAX_COUNT` | 500 | Episode 最大存储数 |
| `EPISODE_NEUTRAL_TTL_DAYS` | 30 | neutral 记录保留天数 |
| `SYNTHESIS_MIN_INTERVAL_HOURS` | 24 | 自动合成最小间隔 |
| `SYNTHESIS_MEMORY_THRESHOLD` | 10 | 触发合成的新记忆数 |
