# conflict_handler.py - 冲突处理器
# 处理用户与Animus之间的冲突，实现"温柔坚定"的边界保护

import time
from typing import Dict, Any, Optional
from .state import LampState


class ConflictHandler:
    """冲突处理器"""
    
    def __init__(self):
        # L2级别关键词（中度冒犯）
        self.l2_keywords = ["傻逼", "滚", "去死", "垃圾", "废物", "蠢货"]
        # L1级别关键词（轻度冒犯）
        self.l1_keywords = ["真笨", "别吵", "烦死了", "闭嘴", "讨厌"]
        # 道歉关键词
        self.forgiveness_keywords = ["对不起", "抱歉", "我错了", "刚才太冲了", "sorry", "是我的错"]
    
    def detect_conflict_level(self, user_input: str, sensor_data: Dict) -> str:
        """
        检测冲突等级
        
        Args:
            user_input: 用户输入文本
            sensor_data: 传感器数据（可能包含物理暴力信号）
        
        Returns:
            "L0": 非冒犯（情绪宣泄）
            "L1": 轻度冒犯（尖刻但可修复）
            "L2": 中度冒犯（持续辱骂/羞辱）
            "L3": 重度冒犯（物理暴力/危险行为）
        """
        # 1. 检查物理暴力（L3）- 最高优先级
        if sensor_data.get("violent_shake") or sensor_data.get("violent_strike"):
            print("   ⚠️  检测到物理暴力（L3）")
            return "L3"
        
        # 2. 检查用户输入（V1简化：使用关键词匹配）
        # V2可升级：使用LLM情感分析
        if not user_input:
            return "L0"
        
        user_input_lower = user_input.lower()
        
        # 检查L2级别关键词（中度冒犯）
        if any(kw in user_input_lower for kw in self.l2_keywords):
            print(f"   ⚠️  检测到中度冒犯（L2）: {user_input}")
            return "L2"
        
        # 检查L1级别关键词（轻度冒犯）
        elif any(kw in user_input_lower for kw in self.l1_keywords):
            print(f"   ⚠️  检测到轻度冒犯（L1）: {user_input}")
            return "L1"
        
        # 默认L0（情绪宣泄，非冒犯）
        return "L0"
    
    def apply_conflict_penalty(self, level: str, state: LampState) -> Dict[str, Any]:
        """
        应用冲突惩罚
        
        Args:
            level: 冲突等级（"L0"|"L1"|"L2"|"L3"）
            state: 当前状态
        
        Returns:
            {
                "intimacy_delta": float,
                "cooldown_seconds": int,
                "conflict_state": Dict
            }
        """
        # L0不触发惩罚
        if level == "L0":
            return {
                "intimacy_delta": 0,
                "cooldown_seconds": 0,
                "conflict_state": None
            }
        
        # 定义惩罚规则
        penalties = {
            "L1": {"intimacy_delta": -2, "cooldown_seconds": 30},      # 30秒冷却
            "L2": {"intimacy_delta": -5, "cooldown_seconds": 300},     # 5分钟冷却
            "L3": {"intimacy_delta": -10, "cooldown_seconds": 1200}    # 20分钟冷却
        }
        
        penalty = penalties[level]
        current_time = time.time()
        cooldown_until = current_time + penalty["cooldown_seconds"]
        
        # 构建冲突状态字典
        conflict_state = {
            "offense_level": level,
            "cooldown_until": cooldown_until,
            "protective_mode": (level == "L3"),
            "repair_min_wait_seconds": 120 if level == "L3" else 0,  # L3需要等待2分钟才能修复
            "allowed_commands_during_cooldown": [
                "safety_stop",
                "basic_light_control",
                "focus_mode_toggle",
                "status_query"
            ]
        }
        
        print(f"   🛡️  应用冲突惩罚: 等级={level}, 亲密度-{abs(penalty['intimacy_delta'])}, 冷却{penalty['cooldown_seconds']}秒")
        
        return {
            "intimacy_delta": penalty["intimacy_delta"],
            "cooldown_seconds": penalty["cooldown_seconds"],
            "conflict_state": conflict_state
        }
    
    def is_in_cooldown(self, state: LampState) -> bool:
        """
        检查是否在冷却期
        
        Args:
            state: 当前状态
        
        Returns:
            bool: 是否在冷却期
        """
        conflict_state = state.get("conflict_state")
        if not conflict_state:
            return False
        
        cooldown_until = conflict_state.get("cooldown_until", 0)
        current_time = time.time()
        
        return current_time < cooldown_until
    
    def is_command_allowed(self, command: str, state: LampState) -> bool:
        """
        检查冷却期是否允许该命令
        
        Args:
            command: 命令类型（"safety_stop", "basic_light_control", "focus_mode_toggle", "status_query"等）
            state: 当前状态
        
        Returns:
            bool: 是否允许执行
        """
        # 如果不在冷却期，允许所有命令
        if not self.is_in_cooldown(state):
            return True
        
        conflict_state = state.get("conflict_state")
        if not conflict_state:
            return True
        
        # 检查命令是否在白名单中
        allowed_commands = conflict_state.get("allowed_commands_during_cooldown", [])
        return command in allowed_commands
    
    def detect_forgiveness(self, user_input: str, state: LampState) -> bool:
        """
        检测用户是否在道歉（用于修复仪式）
        
        Args:
            user_input: 用户输入文本
            state: 当前状态
        
        Returns:
            bool: 是否检测到道歉
        """
        if not user_input:
            return False
        
        user_input_lower = user_input.lower()
        
        # 检查道歉关键词
        has_forgiveness_keyword = any(kw in user_input_lower for kw in self.forgiveness_keywords)
        
        if has_forgiveness_keyword:
            print(f"   💚 检测到道歉: {user_input}")
        
        return has_forgiveness_keyword
    
    def can_repair(self, state: LampState) -> bool:
        """
        检查是否可以开始修复仪式
        
        Args:
            state: 当前状态
        
        Returns:
            bool: 是否可以修复
        """
        conflict_state = state.get("conflict_state")
        if not conflict_state:
            return False
        
        # 如果不在冷却期，可以修复
        if not self.is_in_cooldown(state):
            return True
        
        # L3需要等待最小时间
        offense_level = conflict_state.get("offense_level", "")
        repair_min_wait = conflict_state.get("repair_min_wait_seconds", 0)
        
        if offense_level == "L3" and repair_min_wait > 0:
            conflict_start_time = conflict_state.get("cooldown_until", 0) - conflict_state.get("cooldown_seconds", 0)
            current_time = time.time()
            elapsed = current_time - conflict_start_time
            
            if elapsed < repair_min_wait:
                remaining = repair_min_wait - elapsed
                print(f"   ⏳ L3冲突需要等待 {int(remaining)} 秒后才能修复")
                return False
        
        return True
    
    def get_cooldown_remaining(self, state: LampState) -> float:
        """
        获取冷却期剩余时间（秒）
        
        Args:
            state: 当前状态
        
        Returns:
            float: 剩余秒数，如果不在冷却期返回0
        """
        if not self.is_in_cooldown(state):
            return 0.0
        
        conflict_state = state.get("conflict_state")
        if not conflict_state:
            return 0.0
        
        cooldown_until = conflict_state.get("cooldown_until", 0)
        current_time = time.time()
        remaining = max(0, cooldown_until - current_time)
        
        return remaining
    
    def clear_conflict_state(self) -> Dict[str, Any]:
        """
        清除冲突状态（用于修复后）
        
        Returns:
            清除后的冲突状态（None）
        """
        print("   ✨ 冲突状态已清除")
        return {"conflict_state": None}

