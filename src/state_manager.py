# state_manager.py - 状态管理器
# 管理内部状态更新、初始化和持久化

from .state import LampState
from typing import Optional, Dict, Any
import time
import json
import os
from datetime import datetime


class StateManager:
    """
    状态管理器 - 处理内部状态更新和状态生命周期
    """

    def __init__(self, state_file: str = "./data/lamp_state.json"):
        self.state_file = state_file
        print("🔄 StateManager 初始化完成")

    def initialize_state(self) -> LampState:
        """
        初始化台灯状态
        """
        # 尝试从文件加载之前的状态
        saved_state = self.load_state()

        current_time = time.time()

        # 默认状态
        default_state = LampState(
            # 基础输入数据
            user_input=None,
            sensor_data={},

            # 基础内部状态
            energy_level=100,
            current_mood="gentle_firm",

            # 决策结果
            intent_route="reflex",
            action_plan={},
            voice_content=None,

            # 历史记录
            history=[],

            # 扩展字段
            user_profile={
                "name": "用户",
                "city": "未知",
                "preferences": {}
            },

            internal_drives={
                "boredom": 0,           # 无聊度 (0-100)
                "energy": 100,          # 能量值 (0-100)
                "last_interaction_time": current_time,  # 上次交互时间
                "absence_duration": 0   # 用户离开时长(秒)
            },

            memory_context=None,

            event_type=None,

            proactive_expression=None,

            user_preferences={
                "enabled": True,
                "level": 3,  # 主动行为级别 (0-3) - 提高到最高级别
                "frequency": "high",  # "high", "medium", "low", "off" - 提高频率
                "allowed_types": ["greeting", "reminder", "care"],
                "quiet_hours": [22, 23, 0, 1, 2, 3, 4, 5, 6],  # 勿扰时间
                "min_interval_minutes": 10  # 主动行为最小间隔 - 从30分钟降低到10分钟
            },

            context_signals={
                "current_time": current_time,
                "current_hour": datetime.now().hour,
                "current_day": datetime.now().weekday(),
                "activity_level": "unknown",  # 用户活动状态
                "focus_mode": False  # 是否处于专注模式
            },
            
            # 状态感知 - 初始化硬件状态
            current_hardware_state={
                "light": {
                    "brightness": 0,
                    "color_temp": "warm",
                    "status": "off"
                },
                "motor": {
                    "vibration": "none",
                    "status": "off"
                }
            },
            
            # === V1 新增字段 ===
            # 亲密度系统
            intimacy_level=30.0,                     # 初始30.0
            intimacy_rank="stranger",                # 初始等级：陌生
            intimacy_history=[],                     # 历史记录
            intimacy_delta=0.0,                      # 增量初始化
            intimacy_reason=None,                    # 原因初始化
            
            # 每日陪伴时长
            daily_presence_duration=0.0,             # 初始0.0
            
            # 专注模式
            focus_mode=False,                        # 初始关闭
            focus_mode_start_time=None,              # 开启时间戳
            focus_mode_duration=7200,               # 默认2小时
            focus_mode_auto=False,                   # 是否自动开启
            focus_mode_reason=None,                  # 开启原因
            
            # 冲突状态
            conflict_state=None                      # 初始无冲突
        )

        # 如果有保存的状态，合并部分字段
        if saved_state:
            # 保留用户画像
            if "user_profile" in saved_state:
                default_state["user_profile"] = saved_state["user_profile"]

            # 保留用户偏好设置
            if "user_preferences" in saved_state:
                default_state["user_preferences"] = saved_state["user_preferences"]
            
            # 恢复上次的硬件状态（避免重启后状态不一致）
            if "current_hardware_state" in saved_state:
                default_state["current_hardware_state"] = saved_state["current_hardware_state"]
                print("💡 恢复了上次的硬件状态")
            
            # 恢复V1新增字段
            if "intimacy_level" in saved_state:
                default_state["intimacy_level"] = saved_state["intimacy_level"]
            if "intimacy_rank" in saved_state:
                default_state["intimacy_rank"] = saved_state["intimacy_rank"]
            if "intimacy_history" in saved_state:
                default_state["intimacy_history"] = saved_state["intimacy_history"]
            
            if "daily_presence_duration" in saved_state:
                default_state["daily_presence_duration"] = saved_state["daily_presence_duration"]
            
            if "focus_mode" in saved_state:
                default_state["focus_mode"] = saved_state["focus_mode"]
            if "focus_mode_start_time" in saved_state:
                default_state["focus_mode_start_time"] = saved_state["focus_mode_start_time"]
            if "focus_mode_duration" in saved_state:
                default_state["focus_mode_duration"] = saved_state["focus_mode_duration"]
            if "focus_mode_auto" in saved_state:
                default_state["focus_mode_auto"] = saved_state["focus_mode_auto"]
            if "focus_mode_reason" in saved_state:
                default_state["focus_mode_reason"] = saved_state["focus_mode_reason"]
            
            if "conflict_state" in saved_state:
                default_state["conflict_state"] = saved_state["conflict_state"]

            # 不再加载历史记录，每次启动都是新会话
            # 这样可以避免跨会话的对话历史污染

            print("从文件加载了之前的状态（用户偏好、亲密度、专注模式、冲突状态）")

        # [新增] 启动时从长期记忆同步用户画像
        try:
            from .memory_manager import MemoryManager
            memory_manager = MemoryManager()
            user_profile_text = memory_manager.retrieve_user_profile()
            
            if user_profile_text and user_profile_text != "暂无详细画像":
                # 提取城市信息
                cities = ["上海", "北京", "深圳", "广州", "杭州", "成都", "武汉", "南京", "苏州", "重庆", "西安", "天津", "厦门", "青岛", "大连"]
                for city in cities:
                    if f"所在地是{city}" in user_profile_text or f"住在{city}" in user_profile_text or f"在{city}工作" in user_profile_text:
                        default_state["user_profile"]["city"] = city
                        print(f"   📍 从长期记忆同步用户所在地: {city}")
                        break
                
                # 提取用户名
                import re
                name_match = re.search(r"用户名[字叫]+([\u4e00-\u9fa5a-zA-Z]+)", user_profile_text)
                if name_match:
                    name = name_match.group(1)
                    if name and name != "用户":
                        default_state["user_profile"]["name"] = name
                        print(f"   👤 从长期记忆同步用户名: {name}")
        except Exception as e:
            print(f"   ⚠️  长期记忆同步失败（跳过）: {e}")

        print("状态初始化完成")
        print(f"   - 当前时间: {datetime.now().strftime('%H:%M:%S')}")
        print(f"   - 能量值: {default_state['internal_drives']['energy']}")
        print(f"   - 无聊度: {default_state['internal_drives']['boredom']}")

        return default_state

    def update_internal_state(self, state: LampState) -> LampState:
        """
        更新内部状态 - 在每个 OODA 循环中调用
        """
        current_time = time.time()
        internal = state.get("internal_drives", {})
        context_signals = state.get("context_signals", {})

        # 获取上次交互时间
        last_interaction = internal.get("last_interaction_time", current_time)

        # 计算用户离开时长
        absence_duration = current_time - last_interaction
        internal["absence_duration"] = absence_duration

        # 更新无聊度（每30秒 +1，最高 100）
        boredom_increase = int(absence_duration / 30)  # 每30秒 +1 - 加快累积
        current_boredom = internal.get("boredom", 0)
        new_boredom = min(current_boredom + boredom_increase, 100)
        internal["boredom"] = new_boredom

        # 更新能量值（随时间缓慢下降，最低 20）
        energy_decay = int(absence_duration / 300)  # 每5分钟 -1
        current_energy = internal.get("energy", 100)
        new_energy = max(current_energy - energy_decay, 20)
        internal["energy"] = new_energy

        # 更新上下文信号
        context_signals["current_time"] = current_time
        context_signals["current_hour"] = datetime.now().hour
        context_signals["current_day"] = datetime.now().weekday()

        # 推断用户活动状态（简单规则）
        if absence_duration < 60:  # 1分钟内有交互
            context_signals["activity_level"] = "active"
        elif absence_duration < 3600:  # 1小时内有交互
            context_signals["activity_level"] = "recent"
        else:  # 超过1小时
            context_signals["activity_level"] = "away"

        # 更新状态
        updated_state = {**state}
        updated_state["internal_drives"] = internal
        updated_state["context_signals"] = context_signals

        # 调试输出（仅在状态发生显著变化时）
        if abs(new_boredom - current_boredom) > 5 or abs(new_energy - current_energy) > 5:
            print("🔄 内部状态更新:")
            print(f"   - 无聊度: {current_boredom} → {new_boredom}")
            print(f"   - 能量值: {current_energy} → {new_energy}")
            print(".1f")
        return updated_state

    def reset_interaction_time(self, state: LampState) -> LampState:
        """
        重置交互时间 - 当用户有新交互时调用
        """
        current_time = time.time()
        internal = state.get("internal_drives", {})

        # 重置交互时间
        internal["last_interaction_time"] = current_time
        internal["absence_duration"] = 0

        # 稍微降低无聊度（表示用户回来）
        current_boredom = internal.get("boredom", 0)
        internal["boredom"] = max(current_boredom - 20, 0)  # 降低20，最低0

        # 稍微提升能量值
        current_energy = internal.get("energy", 100)
        internal["energy"] = min(current_energy + 10, 100)  # 提升10，最高100

        updated_state = {**state}
        updated_state["internal_drives"] = internal

        print("🤝 用户交互 - 状态重置:")
        print(f"   - 无聊度降低至: {internal['boredom']}")
        print(f"   - 能量值提升至: {internal['energy']}")

        return updated_state

    def save_state(self, state: LampState) -> bool:
        """
        保存状态到文件（可选功能）
        """
        try:
            # 只保存需要持久化的字段（不保存对话历史）
            persistent_data = {
                "user_profile": state.get("user_profile", {}),
                "user_preferences": state.get("user_preferences", {}),
                "current_hardware_state": state.get("current_hardware_state", {}),  # 保存硬件状态
                # V1新增字段：持久化亲密度、专注模式、冲突状态
                "intimacy_level": state.get("intimacy_level", 30),
                "intimacy_rank": state.get("intimacy_rank", "stranger"),
                "intimacy_history": state.get("intimacy_history", []),
                "daily_presence_duration": state.get("daily_presence_duration", 0.0),
                "focus_mode": state.get("focus_mode", False),
                "focus_mode_start_time": state.get("focus_mode_start_time"),
                "focus_mode_duration": state.get("focus_mode_duration", 7200),
                "focus_mode_auto": state.get("focus_mode_auto", False),
                "focus_mode_reason": state.get("focus_mode_reason"),
                "conflict_state": state.get("conflict_state"),
                # 不再保存对话历史，每次启动都是新会话
                "saved_at": time.time()
            }

            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(persistent_data, f, ensure_ascii=False, indent=2)

            print(f"💾 状态已保存到 {self.state_file}")
            return True

        except Exception as e:
            print(f"❌ 状态保存失败: {e}")
            return False

    def load_state(self) -> Optional[LampState]:
        """
        从文件加载状态
        """
        if not os.path.exists(self.state_file):
            return None

        try:
            with open(self.state_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            print(f"📂 从 {self.state_file} 加载了持久化状态")
            return data

        except Exception as e:
            print(f"❌ 状态加载失败: {e}")
            return None

    def get_state_summary(self, state: LampState) -> Dict[str, Any]:
        """
        获取状态摘要
        """
        internal = state.get("internal_drives", {})
        context = state.get("context_signals", {})

        return {
            "energy_level": state.get("energy_level", 0),
            "current_mood": state.get("current_mood", "unknown"),
            "boredom": internal.get("boredom", 0),
            "energy": internal.get("energy", 100),
            "absence_duration_minutes": round(internal.get("absence_duration", 0) / 60, 1),
            "activity_level": context.get("activity_level", "unknown"),
            "current_hour": context.get("current_hour", 0),
            "user_name": state.get("user_profile", {}).get("name", "unknown")
        }
