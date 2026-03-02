# intimacy_manager.py - 亲密度管理器
# 管理用户与Animus之间的亲密度系统

import time
from typing import Dict, Any, List
from datetime import datetime, date


class IntimacyManager:
    """亲密度管理器"""
    
    def __init__(self):
        self.intimacy_level: float = 30.0  # 初始值
        self.intimacy_rank: str = "stranger"
        self.daily_touch_count: int = 0  # 每日抚摸次数（上限10次）
        self.daily_praise_count: int = 0  # 每日夸奖次数（上限10次）
        self.last_reset_date: str = ""  # 上次重置日期（格式：YYYY-MM-DD）
        self.intimacy_history: List[Dict[str, Any]] = []  # 历史记录
    
    def update_intimacy(self, delta: float, reason: str) -> Dict[str, Any]:
        """
        更新亲密度
        
        Args:
            delta: 变化量（可为正负）
            reason: 原因（"touch", "praise", "conflict_L1", "conflict_L2", "conflict_L3", etc.）
        
        Returns:
            {
                "intimacy_level": float,
                "intimacy_rank": str,
                "delta": float,
                "reason": str,
                "rank_changed": bool
            }
        """
        # 检查是否需要重置每日计数器
        self._check_and_reset_daily_counters()
        
        # 1. 检查每日上限（仅对正向操作）
        if delta > 0:
            if reason == "touch":
                if self.daily_touch_count >= 10:
                    delta = 0.0  # 达到上限，不再增加
                    print(f"[WARN]  今日抚摸次数已达上限（10次）")
                else:
                    self.daily_touch_count += 1
            
            elif reason == "praise":
                if self.daily_praise_count >= 10:
                    delta = 0.0  # 达到上限，不再增加
                    print(f"[WARN]  今日夸奖次数已达上限（10次）")
                else:
                    self.daily_praise_count += 1
        
        # 2. 更新亲密度
        old_level = self.intimacy_level
        self.intimacy_level = max(0.0, min(100.0, round(self.intimacy_level + delta, 2)))
        
        # 3. 更新等级
        old_rank = self.intimacy_rank
        self.intimacy_rank = self.get_intimacy_rank(self.intimacy_level)
        rank_changed = (old_rank != self.intimacy_rank)
        
        # 4. 记录历史（可选）
        if abs(delta) > 0:
            self.intimacy_history.append({
                "timestamp": time.time(),
                "old_level": old_level,
                "new_level": self.intimacy_level,
                "delta": delta,
                "reason": reason,
                "rank_changed": rank_changed
            })
            
            # 限制历史记录长度（最多保留最近100条）
            if len(self.intimacy_history) > 100:
                self.intimacy_history = self.intimacy_history[-100:]
        
        # 5. 如果等级变化，输出提示
        if rank_changed:
            print(f"   🎉 亲密度等级变化: {old_rank} → {self.intimacy_rank}")
        
        return {
            "intimacy_level": self.intimacy_level,
            "intimacy_rank": self.intimacy_rank,
            "delta": delta,
            "reason": reason,
            "rank_changed": rank_changed
        }
    
    def get_intimacy_rank(self, level: float) -> str:
        """
        根据亲密度数值返回等级
        
        Args:
            level: 亲密度数值（0-100）
        
        Returns:
            "stranger" (0-30)
            "acquaintance" (31-50)
            "friend" (51-75)
            "soulmate" (76-100)
        """
        if level <= 30.0:
            return "stranger"
        elif level <= 50.0:
            return "acquaintance"
        elif level <= 75.0:
            return "friend"
        else:
            return "soulmate"
    
    def reset_daily_counters(self):
        """每日重置计数器"""
        self.daily_touch_count = 0
        self.daily_praise_count = 0
        self.last_reset_date = date.today().isoformat()
        print(f"   每日计数器已重置（日期: {self.last_reset_date}）")
    
    def _check_and_reset_daily_counters(self):
        """检查并重置每日计数器（如果日期变化）"""
        today = date.today().isoformat()
        if self.last_reset_date != today:
            self.reset_daily_counters()
    
    def calculate_daily_bonus(self, presence_duration_seconds: float) -> float:
        """
        计算每日陪伴奖励（>1小时 +2）
        
        Args:
            presence_duration_seconds: 今日陪伴时长（秒）
        
        Returns:
            奖励的亲密度增量（0或2）
        """
        if presence_duration_seconds >= 3600:  # 1小时 = 3600秒
            return 2.0
        return 0.0
    
    def get_current_state(self) -> Dict[str, Any]:
        """
        获取当前状态（用于状态同步）
        
        Returns:
            包含当前所有状态的字典
        """
        return {
            "intimacy_level": self.intimacy_level,
            "intimacy_rank": self.intimacy_rank,
            "daily_touch_count": self.daily_touch_count,
            "daily_praise_count": self.daily_praise_count,
            "last_reset_date": self.last_reset_date,
            "intimacy_history": self.intimacy_history[-10:]  # 只返回最近10条
        }
    
    def load_state(self, state: Dict[str, Any]):
        """
        从状态字典加载数据（用于状态恢复）
        
        Args:
            state: 状态字典
        """
        if "intimacy_level" in state:
            self.intimacy_level = state["intimacy_level"]
        if "intimacy_rank" in state:
            self.intimacy_rank = state["intimacy_rank"]
        if "daily_touch_count" in state:
            self.daily_touch_count = state["daily_touch_count"]
        if "daily_praise_count" in state:
            self.daily_praise_count = state["daily_praise_count"]
        if "last_reset_date" in state:
            self.last_reset_date = state["last_reset_date"]
        if "intimacy_history" in state:
            self.intimacy_history = state["intimacy_history"]

