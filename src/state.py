# state.py
import operator
from typing import Annotated, TypedDict, List, Dict, Any, Optional, Literal
from pydantic import BaseModel

class UserProfile(BaseModel):
    """
    用户画像结构化数据模型 (RAM)
    v2.0: 扩展核心画像字段，支持主动行为和个性化
    """
    version: str = "2.0"  # Schema 版本号
    
    # === 基础信息 ===
    name: Optional[str] = None
    gender: Optional[str] = None  # "male" | "female" | "other"
    age: Optional[int] = None
    occupation: Optional[str] = None
    birthday: Optional[str] = None  # "MM-DD" 格式
    
    # === 地理位置 ===
    home_city: Optional[str] = None  # 常住地（长期稳定）
    timezone: Optional[str] = None  # "Asia/Shanghai"
    # 注意：current_location 已移至 LampState.context_signals（临时状态，不持久化）
    
    # === 时间规律（用于主动行为）===
    typical_wake_time: Optional[str] = None  # "07:30"
    typical_sleep_time: Optional[str] = None  # "23:00"
    active_hours: List[str] = []  # ["09:00-12:00", "14:00-18:00"]
    
    # === 核心偏好 ===
    core_preferences: List[str] = []  # Top 5 核心偏好，如 ["喜欢咖啡", "不喜欢吵闹"]
    
    # === 结构化偏好对象 ===
    music_preferences: Optional[Dict[str, Any]] = None  # {liked_artists: [...], liked_genres: [...]}
    news_preferences: Optional[Dict[str, Any]] = None  # {categories: [...], keywords: [...]}
    light_preferences: Optional[Dict[str, Any]] = None  # {preferred_color_temp: 4000, ...}
    
    # === 新增：分类偏好摘要 ===
    preference_summary: Dict[str, List[str]] = {
        "food": [],      # ["喜欢拉面", "不喜欢辣的"]
        "music": [],     # ["喜欢周杰伦"]
        "activity": [],  # ["喜欢散步"]
        "habit": [],     # ["习惯晚睡"]
        "work": [],      # ["工作压力大"]
    }
    
    # === 重要日期 ===
    important_dates: List[Dict[str, Any]] = []  # [{"date": "MM-DD", "name": "...", "type": "..."}]
    
    # === 元数据 ===
    last_updated: float = 0.0  # 最后更新时间戳
    last_synthesized: float = 0.0  # 上次从 Collection 合成的时间


# ==========================================
# 工具调用和结果的数据类型定义
# ==========================================

class ToolResult(TypedDict, total=False):
    """工具执行结果的数据结构"""
    tool_call_id: str  # 工具调用ID，对应 tool_call["id"]
    output: Optional[str]  # 成功时的输出内容
    error: Optional[str]  # 失败时的错误信息
    error_type: Optional[Literal["network", "parameter", "service", "timeout", "unknown"]]  # 错误类型
    tool_name: str  # 工具名称
    execution_time: Optional[float]  # 执行耗时（秒）
    timestamp: float  # 执行时间戳


class ToolCall(TypedDict, total=False):
    """工具调用的数据结构"""
    id: str  # 调用唯一标识
    name: str  # 工具名称，必须是 AVAILABLE_TOOLS 中的有效名称
    args: Dict[str, Any]  # 工具参数字典
    expected_output_type: Optional[str]  # 预期输出类型（用于验证）
    retry_on_error: bool  # 是否在错误时重试（默认 False）


class ExecutionStep(TypedDict, total=False):
    """执行计划步骤的数据结构"""
    step_id: int  # 步骤序号（从1开始）
    description: str  # 步骤描述
    action_type: Literal["tool_call", "llm_reasoning", "conditional"]  # 动作类型
    tool_name: Optional[str]  # 工具名称（如果是 tool_call）
    tool_args: Optional[Dict[str, Any]]  # 工具参数
    expected_output: str  # 预期输出描述
    depends_on: List[int]  # 依赖的步骤ID列表
    timeout_seconds: Optional[float]  # 超时时间（秒）
    retry_count: int  # 重试次数（默认0）
    result: Optional[ToolResult]  # 执行结果（执行后填充）


class ExecutionPlan(TypedDict, total=False):
    """执行计划的完整数据结构"""
    plan_id: str  # 计划唯一标识（UUID前8位）
    created_at: float  # 创建时间戳
    complexity: Literal["simple", "moderate", "complex"]  # 复杂度
    steps: List[ExecutionStep]  # 步骤列表
    total_steps: int  # 总步骤数
    required_tools: List[str]  # 需要的工具列表
    estimated_time: float  # 预估执行时间（秒）
    current_step_index: int  # 当前执行步骤索引（从0开始）
    status: Literal["created", "executing", "completed", "failed", "cancelled"]  # 计划状态


class LampState(TypedDict):
    """
    台灯智能体的核心状态定义 - OODA架构
    """
    # --- 输入数据 ---
    user_input: Optional[str]     # 用户语音/文本
    sensor_data: Dict[str, Any]   # 传感器数据 (touch, vision, etc.)

    # --- 内部状态 ---
    energy_level: int             # 0-100
    current_mood: str             # "gentle_firm", "cooldown", "protective", "sleepy", etc.

    # --- 决策结果 ---
    intent_route: str             # "reflex", "reasoning", "ignore"
    should_proceed: bool          # 是否继续处理工作流
    monologue: Optional[str]      # 内部独白，用于展示思考过程

    # LLM 生成的结构化指令
    action_plan: Dict
    voice_content: Optional[str]

    # --- 记忆/上下文 ---
    # 使用替换策略而非累加策略，避免历史重复
    # 当节点返回新的 history 时，用新值替换旧值
    history: Annotated[List[Any], lambda old, new: new if new is not None else old]

    # --- 扩展字段 ---
    user_profile: Dict[str, Any]                    # 静态用户画像 (name, city, etc.)
    internal_drives: Dict[str, Any]                 # 内部驱动力 (boredom, energy, etc.)
    memory_context: Optional[Dict]                  # RAG检索的用户历史偏好 (修改为Dict类型)
    event_type: Optional[str]                       # 事件类型 (user_input, timer, sensor, internal_drive)
    proactive_expression: Optional[str]             # 主动行为的表达内容
    user_preferences: Dict[str, Any]                # 用户偏好设置
    context_signals: Dict[str, Any]                 # 当前上下文信号 (time, activity, etc.)
    current_emotion: Optional[Dict[str, Any]]       # 当前情感状态 (type, intensity, confidence, etc.)
    evaluation_reason: Optional[str]                # 评估原因
    parsed_params: Optional[Dict]                   # 解析的参数
    command_type: Optional[str]                     # 命令类型
    execution_status: Optional[str]                 # 执行状态
    
    # --- 状态感知 (State Awareness) ---
    current_hardware_state: Dict[str, Any]          # 当前硬件状态快照 (brightness, color_temp, etc.)
    
    # === V1 新增字段 ===
    # 亲密度系统
    intimacy_level: float                           # 0-100，初始30.0
    intimacy_rank: str                              # "stranger|acquaintance|friend|soulmate"
    intimacy_history: List[Dict[str, Any]]          # 历史记录（可选，用于调试）
    intimacy_delta: Optional[float]                 # 本次变化的增量
    intimacy_reason: Optional[str]                  # 变化原因
    
    # 每日陪伴时长（秒）
    daily_presence_duration: float                  # 累计在场时长
    
    # 专注模式
    focus_mode: bool                                # 是否开启专注模式
    focus_mode_start_time: Optional[float]          # 开启时间戳
    focus_mode_duration: int                       # 持续时间（秒），默认7200
    focus_mode_auto: bool                           # 是否自动开启
    focus_mode_reason: Optional[str]                # 开启原因："manual|auto_detected|user_expression"
    
    # 冲突状态
    conflict_state: Optional[Dict[str, Any]]        # 冲突状态字典
    # conflict_state结构：
    # {
    #   "offense_level": "L0|L1|L2|L3",
    #   "cooldown_until": float,  # 时间戳
    #   "protective_mode": bool,   # L3专用：是否进入保护模式
    #   "repair_min_wait_seconds": int,  # L3专用：最小等待时间
    #   "allowed_commands_during_cooldown": List[str]  # 冷却期允许的命令
    # }
    
    # === V2 Plan Node 新增字段 ===
    execution_plan: Optional[Dict[str, Any]]        # 执行计划
    plan_status: Optional[str]                       # 计划状态: "created" | "skipped" | "failed" | "executing" | "completed"
    plan_skip_reason: Optional[str]                  # 跳过规划的原因
    current_step_index: int                          # 当前执行步骤索引（从0开始）
    tool_calls: Optional[List[ToolCall]]              # 当前需要执行的工具调用
    tool_results: Optional[List[ToolResult]]         # 工具执行结果
    # execution_plan 结构：
    # {
    #   "plan_id": str,                    # 计划唯一标识
    #   "created_at": float,               # 创建时间戳
    #   "complexity": str,                 # "simple" | "moderate" | "complex"
    #   "steps": List[Dict],               # 执行步骤列表
    #   "total_steps": int,                # 总步骤数
    #   "required_tools": List[str],       # 需要的工具列表
    #   "estimated_time": float,           # 预估执行时间（秒）
    # }