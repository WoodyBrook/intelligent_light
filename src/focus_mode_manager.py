# focus_mode_manager.py - 专注模式管理器
# 管理用户的专注模式，实现智能陪伴（不打扰工作）

import time
from typing import Dict, Any
from .state import LampState


class FocusModeManager:
    """专注模式管理器"""
    
    def __init__(self):
        # 进入专注模式的触发词
        self.enter_keywords = [
            "我要工作了",
            "开始工作",
            "我要写代码",
            "别打扰我",
            "开启专注模式",
            "进入专注模式",
            "专注模式",
            "工作模式",
            "勿扰模式"
        ]
        
        # 退出专注模式的触发词
        self.exit_keywords = [
            "关闭专注模式",
            "工作结束了",
            "休息一下",
            "退出专注模式",
            "结束专注模式",
            "工作完成",
            "可以说话了"
        ]
    
    def should_enter_focus_mode(self, user_input: str, state: LampState) -> bool:
        """
        判断是否应该进入专注模式（自动检测）
        
        Args:
            user_input: 用户输入文本
            state: 当前状态
        
        Returns:
            bool: 是否应该进入专注模式
        """
        if not user_input:
            return False
        
        user_input_lower = user_input.lower()
        
        # 检查是否包含触发词
        for keyword in self.enter_keywords:
            if keyword in user_input_lower:
                print(f"   🎯 检测到专注模式触发词: {keyword}")
                return True
        
        return False
    
    def is_focus_mode_active(self, state: LampState) -> bool:
        """
        检查专注模式是否激活
        
        Args:
            state: 当前状态
        
        Returns:
            bool: 是否处于专注模式
        """
        focus_mode = state.get("focus_mode", False)
        
        if not focus_mode:
            return False
        
        # 检查是否超过持续时间
        focus_mode_start_time = state.get("focus_mode_start_time")
        focus_mode_duration = state.get("focus_mode_duration", 7200)  # 默认2小时
        
        if focus_mode_start_time:
            elapsed = time.time() - focus_mode_start_time
            if elapsed >= focus_mode_duration:
                print(f"   ⏰ 专注模式已自动过期（持续时间: {focus_mode_duration}秒）")
                return False
        
        return True
    
    def should_exit_focus_mode(self, user_input: str, state: LampState) -> bool:
        """
        判断是否应该退出专注模式
        
        Args:
            user_input: 用户输入文本
            state: 当前状态
        
        Returns:
            bool: 是否应该退出专注模式
        """
        if not user_input:
            return False
        
        user_input_lower = user_input.lower()
        
        # 检查是否包含退出触发词
        for keyword in self.exit_keywords:
            if keyword in user_input_lower:
                print(f"   🎯 检测到退出专注模式触发词: {keyword}")
                return True
        
        return False
    
    def enter_focus_mode(self, state: LampState, reason: str = "user_expression", auto: bool = False) -> Dict[str, Any]:
        """
        进入专注模式
        
        Args:
            state: 当前状态
            reason: 开启原因（"manual"|"auto_detected"|"user_expression"）
            auto: 是否自动开启
        
        Returns:
            更新后的状态字典
        """
        current_time = time.time()
        focus_mode_duration = state.get("focus_mode_duration", 7200)
        
        print(f"   🔇 进入专注模式（原因: {reason}, 持续时间: {focus_mode_duration}秒）")
        
        return {
            "focus_mode": True,
            "focus_mode_start_time": current_time,
            "focus_mode_duration": focus_mode_duration,
            "focus_mode_auto": auto,
            "focus_mode_reason": reason
        }
    
    def exit_focus_mode(self, state: LampState) -> Dict[str, Any]:
        """
        退出专注模式
        
        Args:
            state: 当前状态
        
        Returns:
            更新后的状态字典
        """
        print("   🔊 退出专注模式")
        
        return {
            "focus_mode": False,
            "focus_mode_start_time": None,
            "focus_mode_reason": None
        }
    
    def get_focus_mode_action_constraints(self, state: LampState) -> Dict[str, bool]:
        """
        获取专注模式下的行为约束
        
        Args:
            state: 当前状态
        
        Returns:
            {
                "allow_proactive": False,      # 禁止主动行为
                "allow_voice": False,          # 禁止语音打断
                "allow_touch": True,           # 允许触摸（静默反馈）
                "allow_silent_nudge": True     # 允许静默提示（注视/转向/灯光）
            }
        """
        if not self.is_focus_mode_active(state):
            # 非专注模式：允许所有行为
            return {
                "allow_proactive": True,
                "allow_voice": True,
                "allow_touch": True,
                "allow_silent_nudge": True
            }
        
        # 专注模式：限制行为
        return {
            "allow_proactive": False,      # 禁止主动行为
            "allow_voice": False,          # 禁止语音打断
            "allow_touch": True,           # 允许触摸（静默反馈）
            "allow_silent_nudge": True     # 允许静默提示（注视/转向/灯光）
        }
    
    def get_focus_mode_remaining_time(self, state: LampState) -> float:
        """
        获取专注模式剩余时间（秒）
        
        Args:
            state: 当前状态
        
        Returns:
            float: 剩余秒数，如果不在专注模式返回0
        """
        if not self.is_focus_mode_active(state):
            return 0.0
        
        focus_mode_start_time = state.get("focus_mode_start_time")
        focus_mode_duration = state.get("focus_mode_duration", 7200)
        
        if not focus_mode_start_time:
            return 0.0
        
        elapsed = time.time() - focus_mode_start_time
        remaining = max(0, focus_mode_duration - elapsed)
        
        return remaining

