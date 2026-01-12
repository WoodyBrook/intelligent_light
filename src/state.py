# state.py
import operator
from typing import Annotated, TypedDict, List, Dict, Any, Optional
from pydantic import BaseModel

class UserProfile(BaseModel):
    """用户画像结构化数据模型 (RAM)"""
    version: str = "1.0"  # Schema 版本号
    name: Optional[str] = None
    home_city: Optional[str] = None  # 常住地
    current_location: Optional[str] = None  # 临时位置
    core_preferences: List[str] = []  # 核心偏好 (Top N)
    last_updated: float = 0.0  # 最后更新时间戳

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
    history: Annotated[List[Any], operator.add]

    # --- 扩展字段 ---
    user_profile: Dict[str, Any]                    # 静态用户画像 (name, city, etc.)
    internal_drives: Dict[str, Any]                 # 内部驱动力 (boredom, energy, etc.)
    memory_context: Optional[Dict]                  # RAG检索的用户历史偏好 (修改为Dict类型)
    event_type: Optional[str]                       # 事件类型 (user_input, timer, sensor, internal_drive)
    proactive_expression: Optional[str]             # 主动行为的表达内容
    user_preferences: Dict[str, Any]                # 用户偏好设置
    context_signals: Dict[str, Any]                 # 当前上下文信号 (time, activity, etc.)
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
    tool_calls: Optional[List[Dict[str, Any]]]       # 当前需要执行的工具调用
    tool_results: Optional[List[Dict[str, Any]]]     # 工具执行结果
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