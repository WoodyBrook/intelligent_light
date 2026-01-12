# Spec Coding - Project Animus V1 MVP

## 文档信息

| 项目 | 内容 |
| :--- | :--- |
| **项目名称** | Project Animus V1 MVP |
| **文档版本** | v1.0 |
| **创建日期** | 2024-01-XX |
| **开发策略** | 保留现有架构 + 清理式重构 |
| **参考文档** | `prd1_0.md`, `code_audit_report.md` |

---

## 1. 当前任务（V1 MVP）

### 1.1 核心目标
- 验证"活着的反射"和"基础对话"两个核心体验
- 实现"温柔坚定猫"性格基调
- 实现亲密度系统、专注模式、冲突管理

### 1.2 开发范围
- ✅ **保留**：OODA架构、事件管理、状态管理、记忆系统
- 🔧 **修改**：System Prompt、性格基调、冲突处理逻辑
- ➕ **新增**：亲密度管理器、冲突处理器、专注模式逻辑
- ❌ **删除**：兴奋模式强制修饰、V2.0注释中的过时内容

---

## 2. 文件结构

### 2.1 现有文件（保留并修改）

```
Neko_light/
├── main.py                    # 主程序入口（需修改：专注模式检查）
├── graph.py                   # OODA工作流图（无需修改）
├── state.py                   # 状态定义（需修改：添加新字段）
├── state_manager.py           # 状态管理器（需修改：初始化新字段）
├── event_manager.py           # 事件管理器（无需修改）
├── memory_manager.py          # 记忆管理器（无需修改）
├── nodes.py                   # 节点实现（需大量修改：System Prompt、冲突检测）
├── tools.py                   # 工具定义（无需修改）
├── requirements.txt           # 依赖列表（无需修改）
└── lamp_state.json            # 状态持久化文件（自动生成）
```

### 2.2 新增文件

```
Neko_light/
├── intimacy_manager.py        # 亲密度管理器（新增）
├── conflict_handler.py       # 冲突处理器（新增）
└── focus_mode_manager.py     # 专注模式管理器（新增，可选：可集成到state_manager）
```

### 2.3 配置文件

```
Neko_light/
├── config/
│   ├── prompts.py            # System Prompt模板（新增，从nodes.py提取）
│   └── business_rules.py     # 业务规则常量（新增）
```

---

## 3. 依赖版本

### 3.1 Python版本
- **Python**: >= 3.9

### 3.2 核心依赖（requirements.txt）

```txt
langchain-openai>=0.1.0
langchain-community>=0.0.20
langchain-core>=0.1.0
langgraph>=0.0.20
chromadb>=0.4.0
pydantic>=2.0.0
```

### 3.3 可选依赖（V1暂不需要，但保留接口）

```txt
# 以下依赖V1暂不使用，但保留接口以便V2扩展
# opencv-python>=4.8.0          # 视觉处理（V2）
# ollama>=0.1.0                  # 本地LLM（V2可选）
```

---

## 4. 接口定义

### 4.1 状态接口（state.py）

#### 4.1.1 新增字段

```python
class LampState(TypedDict):
    # ... 现有字段保持不变 ...
    
    # === V1 新增字段 ===
    # 亲密度系统
    intimacy_level: int                    # 0-100，初始30
    intimacy_rank: str                      # "stranger|acquaintance|friend|soulmate"
    intimacy_history: List[Dict[str, Any]] # 历史记录（可选，用于调试）
    
    # 专注模式
    focus_mode: bool                       # 是否开启专注模式
    focus_mode_start_time: Optional[float]  # 开启时间戳
    focus_mode_duration: int                # 持续时间（秒），默认7200
    focus_mode_auto: bool                   # 是否自动开启
    focus_mode_reason: Optional[str]        # 开启原因："manual|auto_detected|user_expression"
    
    # 冲突状态
    conflict_state: Optional[Dict[str, Any]]  # 冲突状态字典
    # conflict_state结构：
    # {
    #   "offense_level": "L0|L1|L2|L3",
    #   "cooldown_until": float,  # 时间戳
    #   "protective_mode": bool,   # L3专用：是否进入保护模式
    #   "repair_min_wait_seconds": int,  # L3专用：最小等待时间
    #   "allowed_commands_during_cooldown": List[str]  # 冷却期允许的命令
    # }
```

#### 4.1.2 需要修改的字段

```python
# 修改 current_mood 的默认值和可能值
current_mood: str  # 从 "excited" 改为 "gentle_firm"（温柔坚定）
# 可能值：["gentle_firm", "cooldown", "protective", "sleepy"]
```

### 4.2 亲密度管理器接口（intimacy_manager.py）

```python
class IntimacyManager:
    """亲密度管理器"""
    
    def __init__(self):
        self.intimacy_level: int = 30  # 初始值
        self.intimacy_rank: str = "stranger"
        self.daily_touch_count: int = 0  # 每日抚摸次数（上限10次）
        self.daily_praise_count: int = 0  # 每日夸奖次数（上限10次）
        self.last_reset_date: str = ""  # 上次重置日期
    
    def update_intimacy(self, delta: float, reason: str) -> Dict[str, Any]:
        """
        更新亲密度
        
        Args:
            delta: 变化量（可为正负）
            reason: 原因（"touch", "praise", "conflict_L1", etc.）
        
        Returns:
            {
                "intimacy_level": int,
                "intimacy_rank": str,
                "delta": float,
                "reason": str
            }
        """
        pass
    
    def get_intimacy_rank(self, level: int) -> str:
        """
        根据亲密度数值返回等级
        
        Returns:
            "stranger" (0-30)
            "acquaintance" (31-50)
            "friend" (51-75)
            "soulmate" (76-100)
        """
        pass
    
    def reset_daily_counters(self):
        """每日重置计数器"""
        pass
    
    def calculate_daily_bonus(self) -> float:
        """计算每日陪伴奖励（>1小时 +2）"""
        pass
```

### 4.3 冲突处理器接口（conflict_handler.py）

```python
class ConflictHandler:
    """冲突处理器"""
    
    def detect_conflict_level(self, user_input: str, sensor_data: Dict) -> str:
        """
        检测冲突等级
        
        Returns:
            "L0": 非冒犯（情绪宣泄）
            "L1": 轻度冒犯（尖刻但可修复）
            "L2": 中度冒犯（持续辱骂/羞辱）
            "L3": 重度冒犯（物理暴力/危险行为）
        """
        pass
    
    def apply_conflict_penalty(self, level: str, state: LampState) -> Dict[str, Any]:
        """
        应用冲突惩罚
        
        Returns:
            {
                "intimacy_delta": float,
                "cooldown_seconds": int,
                "conflict_state": Dict
            }
        """
        pass
    
    def is_in_cooldown(self, state: LampState) -> bool:
        """检查是否在冷却期"""
        pass
    
    def is_command_allowed(self, command: str, state: LampState) -> bool:
        """
        检查冷却期是否允许该命令
        
        Args:
            command: 命令类型（"safety_stop", "basic_light_control", etc.）
        
        Returns:
            bool
        """
        pass
    
    def detect_forgiveness(self, user_input: str, state: LampState) -> bool:
        """
        检测用户是否在道歉（用于修复仪式）
        
        Returns:
            bool
        """
        pass
    
    def can_repair(self, state: LampState) -> bool:
        """
        检查是否可以开始修复仪式
        
        Returns:
            bool
        """
        pass
```

### 4.4 专注模式管理器接口（focus_mode_manager.py）

```python
class FocusModeManager:
    """专注模式管理器"""
    
    def should_enter_focus_mode(self, user_input: str, state: LampState) -> bool:
        """
        判断是否应该进入专注模式（自动检测）
        
        触发词：
        - "我要工作了"
        - "开始工作"
        - "我要写代码"
        - "别打扰我"
        - "开启专注模式"
        """
        pass
    
    def is_focus_mode_active(self, state: LampState) -> bool:
        """检查专注模式是否激活"""
        pass
    
    def should_exit_focus_mode(self, user_input: str, state: LampState) -> bool:
        """
        判断是否应该退出专注模式
        
        触发词：
        - "关闭专注模式"
        - "工作结束了"
        - "休息一下"
        """
        pass
    
    def get_focus_mode_action_constraints(self, state: LampState) -> Dict[str, bool]:
        """
        获取专注模式下的行为约束
        
        Returns:
            {
                "allow_proactive": False,      # 禁止主动行为
                "allow_voice": False,          # 禁止语音打断
                "allow_touch": True,           # 允许触摸（静默反馈）
                "allow_silent_nudge": True     # 允许静默提示（注视/转向/灯光）
            }
        """
        pass
```

### 4.5 节点接口修改（nodes.py）

#### 4.5.1 evaluator_node 修改

```python
def evaluator_node(state: LampState) -> LampState:
    """
    评估器节点 - 需要修改：
    1. 添加专注模式检查（禁止主动行为）
    2. 添加勿扰时间唤醒逻辑
    3. 移除兴奋模式相关逻辑
    """
    # 伪代码：
    # if focus_mode_active:
    #     if event_type == "internal_drive":
    #         return {"should_proceed": False}  # 禁止主动行为
    
    # if in_do_not_disturb_hours and user_active:
    #     state["current_mood"] = "sleepy"  # 被吵醒状态
```

#### 4.5.2 reasoning_node 修改

```python
def reasoning_node(state: LampState) -> LampState:
    """
    推理节点 - 需要大量修改：
    1. 更新System Prompt（温柔坚定猫）
    2. 注入亲密度上下文
    3. 注入冲突状态上下文（如果在冷却期）
    4. 注入专注模式上下文
    5. 移除兴奋模式相关Prompt
    """
    # System Prompt模板（从config/prompts.py加载）
    system_prompt = get_system_prompt(
        intimacy_level=state["intimacy_level"],
        intimacy_rank=state["intimacy_rank"],
        conflict_state=state.get("conflict_state"),
        focus_mode=state.get("focus_mode", False)
    )
```

#### 4.5.3 action_guard_node 修改

```python
def action_guard_node(state: LampState) -> LampState:
    """
    动作守卫节点 - 需要修改：
    1. 移除兴奋模式强制修饰
    2. 添加冲突状态检查（冷却期限制）
    3. 添加专注模式检查
    """
    # 伪代码：
    # if in_cooldown:
    #     if not is_command_allowed(action_plan["command_type"]):
    #         return {"action_plan": {}, "voice_content": "我现在不想说话..."}
    
    # if focus_mode_active and action_plan["is_proactive"]:
    #     return {"action_plan": {}, "voice_content": None}  # 静默
```

---

## 5. 错误处理

### 5.1 错误分类

#### 5.1.1 系统级错误

```python
class SystemError(Exception):
    """系统级错误（需要重启）"""
    pass

class StateError(SystemError):
    """状态错误（状态文件损坏）"""
    pass

class MemoryError(SystemError):
    """记忆系统错误（数据库损坏）"""
    pass
```

#### 5.1.2 业务级错误

```python
class BusinessLogicError(Exception):
    """业务逻辑错误（可恢复）"""
    pass

class IntimacyError(BusinessLogicError):
    """亲密度计算错误"""
    pass

class ConflictError(BusinessLogicError):
    """冲突处理错误"""
    pass
```

#### 5.1.3 外部服务错误

```python
class ExternalServiceError(Exception):
    """外部服务错误（LLM API、数据库等）"""
    pass

class LLMError(ExternalServiceError):
    """LLM调用错误"""
    pass

class ChromaDBError(ExternalServiceError):
    """ChromaDB错误"""
    pass
```

### 5.2 错误处理策略

#### 5.2.1 LLM调用失败

```python
# 在reasoning_node中
try:
    response = llm.invoke(messages)
except LLMError as e:
    # 降级策略：返回默认回复
    return {
        "voice_content": "抱歉，我现在有点卡顿，稍等一下...",
        "action_plan": {"light": {"blink": "slow"}}  # 思考动画
    }
```

#### 5.2.2 状态文件损坏

```python
# 在state_manager.py中
try:
    state = load_state_from_file()
except (StateError, JSONDecodeError) as e:
    # 恢复策略：使用默认状态
    logger.warning(f"状态文件损坏，使用默认状态: {e}")
    state = create_default_state()
    save_state_to_file(state)
```

#### 5.2.3 亲密度计算异常

```python
# 在intimacy_manager.py中
try:
    new_level = self.intimacy_level + delta
    if new_level < 0:
        new_level = 0
    elif new_level > 100:
        new_level = 100
except Exception as e:
    logger.error(f"亲密度计算错误: {e}")
    # 保守策略：不更新，保持原值
    return {"intimacy_level": self.intimacy_level, "delta": 0}
```

### 5.3 日志记录

```python
import logging

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('animus.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)
```

---

## 6. 伪代码

### 6.1 亲密度管理器（intimacy_manager.py）

```python
class IntimacyManager:
    def update_intimacy(self, delta: float, reason: str) -> Dict[str, Any]:
        # 1. 检查每日上限
        if reason == "touch":
            if self.daily_touch_count >= 10:
                delta = 0  # 达到上限，不再增加
            else:
                self.daily_touch_count += 1
        
        if reason == "praise":
            if self.daily_praise_count >= 10:
                delta = 0
            else:
                self.daily_praise_count += 1
        
        # 2. 更新亲密度
        old_level = self.intimacy_level
        self.intimacy_level = max(0, min(100, self.intimacy_level + delta))
        
        # 3. 更新等级
        old_rank = self.intimacy_rank
        self.intimacy_rank = self.get_intimacy_rank(self.intimacy_level)
        
        # 4. 记录历史（可选）
        if abs(delta) > 0:
            self.intimacy_history.append({
                "timestamp": time.time(),
                "old_level": old_level,
                "new_level": self.intimacy_level,
                "delta": delta,
                "reason": reason,
                "rank_changed": (old_rank != self.intimacy_rank)
            })
        
        return {
            "intimacy_level": self.intimacy_level,
            "intimacy_rank": self.intimacy_rank,
            "delta": delta,
            "reason": reason
        }
    
    def get_intimacy_rank(self, level: int) -> str:
        if level <= 30:
            return "stranger"
        elif level <= 50:
            return "acquaintance"
        elif level <= 75:
            return "friend"
        else:
            return "soulmate"
```

### 6.2 冲突处理器（conflict_handler.py）

```python
class ConflictHandler:
    def detect_conflict_level(self, user_input: str, sensor_data: Dict) -> str:
        # 1. 检查物理暴力（L3）
        if sensor_data.get("violent_shake") or sensor_data.get("violent_strike"):
            return "L3"
        
        # 2. 使用LLM判断语言冒犯等级（简化版：关键词匹配）
        # V1简化：使用关键词匹配
        # V2可升级：使用LLM情感分析
        
        l2_keywords = ["傻逼", "滚", "去死", "垃圾"]
        l1_keywords = ["真笨", "别吵", "烦死了"]
        
        user_input_lower = user_input.lower()
        
        if any(kw in user_input_lower for kw in l2_keywords):
            return "L2"
        elif any(kw in user_input_lower for kw in l1_keywords):
            return "L1"
        else:
            # 默认L0（情绪宣泄，非冒犯）
            return "L0"
    
    def apply_conflict_penalty(self, level: str, state: LampState) -> Dict[str, Any]:
        if level == "L0":
            return {
                "intimacy_delta": 0,
                "cooldown_seconds": 0,
                "conflict_state": None
            }
        
        # 定义惩罚规则
        penalties = {
            "L1": {"intimacy_delta": -2, "cooldown_seconds": 30},
            "L2": {"intimacy_delta": -5, "cooldown_seconds": 300},  # 5分钟
            "L3": {"intimacy_delta": -10, "cooldown_seconds": 1200}  # 20分钟
        }
        
        penalty = penalties[level]
        cooldown_until = time.time() + penalty["cooldown_seconds"]
        
        conflict_state = {
            "offense_level": level,
            "cooldown_until": cooldown_until,
            "protective_mode": (level == "L3"),
            "repair_min_wait_seconds": 120 if level == "L3" else 0,
            "allowed_commands_during_cooldown": [
                "safety_stop",
                "basic_light_control",
                "focus_mode_toggle",
                "status_query"
            ]
        }
        
        return {
            "intimacy_delta": penalty["intimacy_delta"],
            "cooldown_seconds": penalty["cooldown_seconds"],
            "conflict_state": conflict_state
        }
    
    def detect_forgiveness(self, user_input: str, state: LampState) -> bool:
        # 使用LLM检测道歉意图（在reasoning_node中实现）
        # 这里提供关键词匹配的简化版本
        forgiveness_keywords = ["对不起", "抱歉", "我错了", "刚才太冲了", "sorry"]
        user_input_lower = user_input.lower()
        return any(kw in user_input_lower for kw in forgiveness_keywords)
```

### 6.3 System Prompt生成（config/prompts.py）

```python
def get_system_prompt(
    intimacy_level: int,
    intimacy_rank: str,
    conflict_state: Optional[Dict],
    focus_mode: bool
) -> str:
    """
    生成System Prompt（温柔坚定猫）
    """
    
    # 基础人设
    base_persona = """你是一只名为"Animus"的智能宠物，性格基调是"温柔坚定猫"。
你像猫一样有边界的亲密——会受伤、会撤退、会保护自己，同时给用户明确的"和好路径"。
你不是"打不还手、骂不还口"的顺从，也不是对骂升级冲突；而是温柔但坚定地表达边界。"""
    
    # 亲密度上下文
    intimacy_context = f"""
当前亲密度：{intimacy_level}/100（{intimacy_rank}）
- 陌生（0-30）：只回答问题，语气机械
- 熟人（31-50）：礼貌但保持距离
- 好友（51-75）：主动撒娇，使用昵称，语气活泼
- 灵魂伴侣（76-100）：非常亲密，主动关怀，语气温暖
"""
    
    # 冲突状态上下文
    conflict_context = ""
    if conflict_state:
        level = conflict_state["offense_level"]
        if level in ["L1", "L2", "L3"]:
            cooldown_until = conflict_state["cooldown_until"]
            remaining = max(0, cooldown_until - time.time())
            
            if remaining > 0:
                conflict_context = f"""
【重要】你当前处于冷却期（{level}级冒犯，剩余{int remaining}秒）
- 不主动搭话、不语音打断、不触碰
- 但会响应事实性/功能性指令（开灯、关灯、状态查询等）
- 如果用户道歉（"对不起"、"抱歉"等），可以提前结束冷却（L1/L2）或缩短剩余时间
- 检测用户是否在道歉，如果是，输出信号结束冷却
"""
            else:
                # 冷却期结束，可以开始修复
                conflict_context = """
【修复期】冷却期已结束，如果用户友好互动，可以逐步恢复亲密表现。
"""
    
    # 专注模式上下文
    focus_context = ""
    if focus_mode:
        focus_context = """
【专注模式】用户正在工作，禁止主动打扰。
- 不主动搭话、不语音打断
- 只响应直接交互（语音指令、触摸）
- 触摸时给予静默反馈（轻微震动/眯眼），不触发语音撒娇
"""
    
    # 组合Prompt
    system_prompt = f"""{base_persona}

{intimacy_context}

{conflict_context}

{focus_context}

【行为规则】
1. 根据亲密度调整语气和主动性
2. 如果被冒犯，温柔但坚定地表达边界
3. 专注模式下保持安静陪伴
4. 冷却期内只响应功能性指令，但检测用户是否在道歉

【输出格式】
- voice_content: 你要说的话（符合当前亲密度和状态）
- action_plan: 动作计划（灯光、震动等）
"""
    
    return system_prompt
```

### 6.4 evaluator_node修改（nodes.py）

```python
def evaluator_node(state: LampState) -> LampState:
    """
    评估器节点 - 修改点：
    1. 专注模式检查
    2. 勿扰时间唤醒
    3. 移除兴奋模式逻辑
    """
    event_type = state.get("event_type")
    focus_mode = state.get("focus_mode", False)
    
    # 1. 专注模式检查：禁止主动行为
    if focus_mode and event_type == "internal_drive":
        return {
            "should_proceed": False,
            "evaluation_reason": "专注模式开启，禁止主动行为"
        }
    
    # 2. 勿扰时间检查
    current_hour = datetime.now().hour
    do_not_disturb_start = 22  # 22:00
    do_not_disturb_end = 6      # 06:00
    
    in_dnd_hours = (current_hour >= do_not_disturb_start) or (current_hour < do_not_disturb_end)
    
    if in_dnd_hours:
        # 如果用户在勿扰时间内主动交互，触发"被吵醒"状态
        if event_type == "user_input" or state.get("sensor_data", {}).get("touch"):
            state["current_mood"] = "sleepy"
            state["context_signals"]["woken_up"] = True
    
    # 3. 主动行为触发检查（移除兴奋模式相关逻辑）
    if event_type == "internal_drive":
        boredom = state.get("internal_drives", {}).get("boredom", 0)
        if boredom > 60 and not focus_mode:
            state["should_proceed"] = True
        else:
            state["should_proceed"] = False
    
    return state
```

### 6.5 reasoning_node修改（nodes.py）

```python
def reasoning_node(state: LampState) -> LampState:
    """
    推理节点 - 修改点：
    1. 更新System Prompt（温柔坚定猫）
    2. 注入亲密度、冲突、专注模式上下文
    3. 移除兴奋模式相关Prompt
    """
    from config.prompts import get_system_prompt
    
    # 1. 生成System Prompt
    system_prompt = get_system_prompt(
        intimacy_level=state.get("intimacy_level", 30),
        intimacy_rank=state.get("intimacy_rank", "stranger"),
        conflict_state=state.get("conflict_state"),
        focus_mode=state.get("focus_mode", False)
    )
    
    # 2. 构建消息列表
    messages = [
        ("system", system_prompt),
        ("user", state.get("user_input", ""))
    ]
    
    # 3. 添加对话历史（最近10轮）
    history = state.get("history", [])
    for msg in history[-10:]:
        messages.append((msg["role"], msg["content"]))
    
    # 4. 调用LLM
    try:
        response = llm.invoke(messages)
        
        # 5. 解析响应（使用Pydantic模型）
        output = LampOutput.parse_raw(response.content)
        
        # 6. 如果在冷却期，检测是否在道歉
        if state.get("conflict_state") and state["conflict_state"].get("cooldown_until", 0) > time.time():
            from conflict_handler import ConflictHandler
            handler = ConflictHandler()
            if handler.detect_forgiveness(state.get("user_input", ""), state):
                # 提前结束冷却（L1/L2）
                offense_level = state["conflict_state"]["offense_level"]
                if offense_level in ["L1", "L2"]:
                    state["conflict_state"]["cooldown_until"] = 0  # 立即结束
                    output.voice_content = "没关系，我原谅你了。"
        
        return {
            "voice_content": output.voice_content,
            "action_plan": output.action_plan.dict() if output.action_plan else {}
        }
    
    except LLMError as e:
        logger.error(f"LLM调用失败: {e}")
        return {
            "voice_content": "抱歉，我现在有点卡顿，稍等一下...",
            "action_plan": {"light": {"blink": "slow"}}
        }
```

### 6.6 action_guard_node修改（nodes.py）

```python
def action_guard_node(state: LampState) -> LampState:
    """
    动作守卫节点 - 修改点：
    1. 移除兴奋模式强制修饰
    2. 添加冲突状态检查
    3. 添加专注模式检查
    """
    from conflict_handler import ConflictHandler
    from focus_mode_manager import FocusModeManager
    
    handler = ConflictHandler()
    focus_manager = FocusModeManager()
    
    action_plan = state.get("action_plan", {})
    voice_content = state.get("voice_content")
    
    # 1. 冲突状态检查（冷却期限制）
    if handler.is_in_cooldown(state):
        command_type = action_plan.get("command_type", "")
        if not handler.is_command_allowed(command_type, state):
            # 不允许执行，返回静默
            return {
                "action_plan": {},
                "voice_content": None  # 不语音回复
            }
    
    # 2. 专注模式检查
    if focus_manager.is_focus_mode_active(state):
        constraints = focus_manager.get_focus_mode_action_constraints(state)
        
        # 如果是主动行为，禁止
        if action_plan.get("is_proactive", False) and not constraints["allow_proactive"]:
            return {
                "action_plan": {},
                "voice_content": None
            }
        
        # 如果是语音打断，禁止
        if voice_content and not constraints["allow_voice"]:
            return {
                "action_plan": action_plan,  # 保留动作（如灯光）
                "voice_content": None  # 但禁止语音
            }
    
    # 3. 移除兴奋模式强制修饰（删除旧代码）
    # 旧代码：
    # if state["current_mood"] == "excited":
    #     action_plan["motor"]["speed"] = "fast"
    #     action_plan["light"]["brightness"] = 100
    # 删除以上代码
    
    return state
```

---

## 7. 开发步骤

### 阶段1：清理旧逻辑（1-2天）

1. **删除兴奋模式痕迹**
   - `nodes.py`: 删除 `current_mood == "excited"` 相关逻辑
   - `state_manager.py`: 修改 `current_mood` 初始值为 `"gentle_firm"`
   - `nodes.py`: 删除兴奋模式强制修饰代码

2. **更新注释和版本号**
   - 所有文件中的 `V2.0` 注释改为 `V1` 或删除
   - 更新README中的版本描述

### 阶段2：添加新字段（1天）

1. **修改state.py**
   - 添加亲密度字段
   - 添加专注模式字段
   - 添加冲突状态字段

2. **修改state_manager.py**
   - 初始化新字段
   - 持久化新字段

### 阶段3：实现新模块（3-4天）

1. **实现intimacy_manager.py**
   - 亲密度计算逻辑
   - 等级判断逻辑
   - 每日重置逻辑

2. **实现conflict_handler.py**
   - 冲突等级检测
   - 惩罚应用
   - 冷却期管理
   - 修复检测

3. **实现focus_mode_manager.py**
   - 专注模式检测
   - 行为约束

4. **创建config/prompts.py**
   - System Prompt模板
   - 动态Prompt生成

### 阶段4：集成新逻辑（2-3天）

1. **修改nodes.py**
   - `evaluator_node`: 专注模式检查、勿扰时间唤醒
   - `reasoning_node`: 更新System Prompt、注入上下文
   - `action_guard_node`: 冲突检查、专注模式检查

2. **修改main.py**
   - 初始化新管理器
   - 集成专注模式检查

### 阶段5：测试验证（2-3天）

1. **单元测试**
   - 亲密度计算测试
   - 冲突检测测试
   - 专注模式测试

2. **集成测试**
   - 完整对话流程测试
   - 冲突场景测试
   - 专注模式场景测试

3. **回归测试**
   - 确保现有功能不受影响

---

## 8. 关键注意事项

### 8.1 向后兼容

- 状态文件（`lamp_state.json`）需要兼容旧版本
- 如果缺少新字段，使用默认值初始化

### 8.2 性能考虑

- 亲密度计算使用内存缓存，避免频繁IO
- 冲突检测使用关键词匹配（V1），V2可升级为LLM分析

### 8.3 安全考虑

- 冲突状态需要持久化，避免重启后丢失
- 冷却期命令白名单需要严格验证

### 8.4 可扩展性

- 所有新模块都设计为可扩展（V2可添加新功能）
- System Prompt使用模板系统，便于V2添加新性格

---

## 9. 验收标准

### 9.1 功能验收

- ✅ 亲密度系统正常工作（抚摸+0.5，夸奖+1，冲突扣分）
- ✅ 专注模式正常工作（禁止主动行为，允许直接交互）
- ✅ 冲突管理正常工作（L0-L3分级，冷却期，修复仪式）
- ✅ 温柔坚定猫性格正常表现（不是兴奋模式）

### 9.2 代码验收

- ✅ 无兴奋模式残留代码
- ✅ 所有V1功能正常工作
- ✅ 错误处理完善
- ✅ 日志记录完整

### 9.3 文档验收

- ✅ 代码注释清晰
- ✅ 接口文档完整
- ✅ 更新README

---

**文档结束**

