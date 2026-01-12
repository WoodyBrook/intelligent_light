"""
亲密度管理器单元测试
测试亲密度计算、等级判断、每日重置等功能
"""
import unittest
from datetime import date, timedelta
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.intimacy_manager import IntimacyManager


class TestIntimacyManager(unittest.TestCase):
    """亲密度管理器测试类"""
    
    def setUp(self):
        """每个测试前的初始化"""
        self.manager = IntimacyManager()
        self.manager.intimacy_level = 30.0  # 重置为初始值
        self.manager.intimacy_rank = "stranger"
        self.manager.daily_touch_count = 0
        self.manager.daily_praise_count = 0
        self.manager.last_reset_date = date.today().isoformat()
    
    def test_initial_state(self):
        """测试初始状态"""
        manager = IntimacyManager()
        self.assertEqual(manager.intimacy_level, 30.0)
        self.assertEqual(manager.intimacy_rank, "stranger")
        self.assertEqual(manager.daily_touch_count, 0)
        self.assertEqual(manager.daily_praise_count, 0)
    
    def test_update_intimacy_touch(self):
        """测试抚摸增加亲密度"""
        result = self.manager.update_intimacy(0.5, "touch")
        self.assertEqual(result["intimacy_level"], 30.5)  # 现在支持浮点数，不再被截断
        self.assertEqual(result["delta"], 0.5)
        self.assertEqual(result["reason"], "touch")
        self.assertEqual(self.manager.daily_touch_count, 1)
    
    def test_update_intimacy_praise(self):
        """测试夸奖增加亲密度"""
        result = self.manager.update_intimacy(1.0, "praise")
        self.assertEqual(result["intimacy_level"], 31.0)
        self.assertEqual(result["delta"], 1.0)
        self.assertEqual(result["reason"], "praise")
        self.assertEqual(self.manager.daily_praise_count, 1)
    
    def test_update_intimacy_conflict_l1(self):
        """测试L1冲突减少亲密度"""
        self.manager.intimacy_level = 50.0
        result = self.manager.update_intimacy(-2, "conflict_L1")
        self.assertEqual(result["intimacy_level"], 48.0)
        self.assertEqual(result["delta"], -2)
        self.assertEqual(result["reason"], "conflict_L1")
    
    def test_update_intimacy_conflict_l2(self):
        """测试L2冲突减少亲密度"""
        self.manager.intimacy_level = 50.0
        result = self.manager.update_intimacy(-5, "conflict_L2")
        self.assertEqual(result["intimacy_level"], 45.0)
        self.assertEqual(result["delta"], -5)
    
    def test_update_intimacy_conflict_l3(self):
        """测试L3冲突减少亲密度"""
        self.manager.intimacy_level = 50.0
        result = self.manager.update_intimacy(-10, "conflict_L3")
        self.assertEqual(result["intimacy_level"], 40.0)
        self.assertEqual(result["delta"], -10)
    
    def test_intimacy_bounds(self):
        """测试亲密度边界（0-100）"""
        # 测试最小值
        self.manager.intimacy_level = 5.0
        result = self.manager.update_intimacy(-10, "test")
        self.assertEqual(result["intimacy_level"], 0.0)
        
        # 测试最大值
        self.manager.intimacy_level = 95.0
        result = self.manager.update_intimacy(10, "test")
        self.assertEqual(result["intimacy_level"], 100.0)
    
    def test_get_intimacy_rank_stranger(self):
        """测试亲密度等级：陌生（0-30）"""
        self.assertEqual(self.manager.get_intimacy_rank(0.0), "stranger")
        self.assertEqual(self.manager.get_intimacy_rank(15.5), "stranger")
        self.assertEqual(self.manager.get_intimacy_rank(30.0), "stranger")
    
    def test_get_intimacy_rank_acquaintance(self):
        """测试亲密度等级：熟人（31-50）"""
        self.assertEqual(self.manager.get_intimacy_rank(30.1), "acquaintance")
        self.assertEqual(self.manager.get_intimacy_rank(40.0), "acquaintance")
        self.assertEqual(self.manager.get_intimacy_rank(50.0), "acquaintance")
    
    def test_get_intimacy_rank_friend(self):
        """测试亲密度等级：好友（51-75）"""
        self.assertEqual(self.manager.get_intimacy_rank(50.1), "friend")
        self.assertEqual(self.manager.get_intimacy_rank(60.0), "friend")
        self.assertEqual(self.manager.get_intimacy_rank(75.0), "friend")
    
    def test_get_intimacy_rank_soulmate(self):
        """测试亲密度等级：灵魂伴侣（76-100）"""
        self.assertEqual(self.manager.get_intimacy_rank(75.1), "soulmate")
        self.assertEqual(self.manager.get_intimacy_rank(85.0), "soulmate")
        self.assertEqual(self.manager.get_intimacy_rank(100.0), "soulmate")
    
    def test_rank_change_detection(self):
        """测试等级变化检测"""
        self.manager.intimacy_level = 30.0
        self.manager.intimacy_rank = "stranger"
        
        # 从陌生升级到熟人
        result = self.manager.update_intimacy(0.1, "praise")
        self.assertTrue(result["rank_changed"])
        self.assertEqual(result["intimacy_rank"], "acquaintance")
        
        # 从熟人升级到好友
        self.manager.intimacy_level = 50.0
        self.manager.intimacy_rank = "acquaintance"
        result = self.manager.update_intimacy(0.1, "praise")
        self.assertTrue(result["rank_changed"])
        self.assertEqual(result["intimacy_rank"], "friend")
    
    def test_daily_touch_limit(self):
        """测试每日抚摸次数上限（10次）"""
        # 抚摸10次
        for i in range(10):
            result = self.manager.update_intimacy(0.5, "touch")
            self.assertEqual(self.manager.daily_touch_count, i + 1)
        
        # 第11次应该不再增加
        initial_level = self.manager.intimacy_level
        result = self.manager.update_intimacy(0.5, "touch")
        self.assertEqual(result["intimacy_level"], initial_level)
        self.assertEqual(result["delta"], 0.0)
        self.assertEqual(self.manager.daily_touch_count, 10)
    
    def test_daily_praise_limit(self):
        """测试每日夸奖次数上限（10次）"""
        # 夸奖10次
        for i in range(10):
            result = self.manager.update_intimacy(1.0, "praise")
            self.assertEqual(self.manager.daily_praise_count, i + 1)
        
        # 第11次应该不再增加
        initial_level = self.manager.intimacy_level
        result = self.manager.update_intimacy(1.0, "praise")
        self.assertEqual(result["intimacy_level"], initial_level)
        self.assertEqual(result["delta"], 0.0)
        self.assertEqual(self.manager.daily_praise_count, 10)
    
    def test_daily_bonus_calculation(self):
        """测试每日陪伴奖励计算"""
        # 小于1小时，无奖励
        result = self.manager.calculate_daily_bonus(1800)  # 30分钟
        self.assertEqual(result, 0.0)
        
        # 等于1小时，有奖励
        result = self.manager.calculate_daily_bonus(3600)  # 1小时
        self.assertEqual(result, 2.0)
        
        # 大于1小时，有奖励
        result = self.manager.calculate_daily_bonus(7200)  # 2小时
        self.assertEqual(result, 2.0)
    
    def test_reset_daily_counters(self):
        """测试每日计数器重置"""
        self.manager.daily_touch_count = 5
        self.manager.daily_praise_count = 3
        self.manager.reset_daily_counters()
        
        self.assertEqual(self.manager.daily_touch_count, 0)
        self.assertEqual(self.manager.daily_praise_count, 0)
        self.assertEqual(self.manager.last_reset_date, date.today().isoformat())
    
    def test_check_and_reset_daily_counters(self):
        """测试自动检查并重置每日计数器"""
        # 设置昨天的日期
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        self.manager.last_reset_date = yesterday
        self.manager.daily_touch_count = 5
        self.manager.daily_praise_count = 3
        
        # 调用更新（会自动检查并重置）
        self.manager.update_intimacy(0.5, "touch")
        
        # 应该已重置
        self.assertEqual(self.manager.daily_touch_count, 1)  # 重置后+1
        self.assertEqual(self.manager.daily_praise_count, 0)
        self.assertEqual(self.manager.last_reset_date, date.today().isoformat())
    
    def test_intimacy_history_recording(self):
        """测试亲密度历史记录"""
        initial_history_len = len(self.manager.intimacy_history)
        
        # 更新亲密度
        result = self.manager.update_intimacy(1.0, "praise")
        
        # 应该记录到历史
        self.assertEqual(len(self.manager.intimacy_history), initial_history_len + 1)
        history_entry = self.manager.intimacy_history[-1]
        self.assertEqual(history_entry["delta"], 1.0)
        self.assertEqual(history_entry["reason"], "praise")
        self.assertTrue("timestamp" in history_entry)
    
    def test_get_current_state(self):
        """测试获取当前状态"""
        self.manager.intimacy_level = 50.5
        self.manager.intimacy_rank = "acquaintance"
        self.manager.daily_touch_count = 3
        self.manager.daily_praise_count = 2
        
        state = self.manager.get_current_state()
        
        self.assertEqual(state["intimacy_level"], 50.5)
        self.assertEqual(state["intimacy_rank"], "acquaintance")
        self.assertEqual(state["daily_touch_count"], 3)
        self.assertEqual(state["daily_praise_count"], 2)
        # self.assertEqual(len(state["intimacy_history"]), 0)  # 只返回最近10条
    
    def test_load_state(self):
        """测试加载状态"""
        state = {
            "intimacy_level": 60.5,
            "intimacy_rank": "friend",
            "daily_touch_count": 5,
            "daily_praise_count": 3,
            "last_reset_date": "2024-01-01",
            "intimacy_history": []
        }
        
        self.manager.load_state(state)
        
        self.assertEqual(self.manager.intimacy_level, 60.5)
        self.assertEqual(self.manager.intimacy_rank, "friend")
        self.assertEqual(self.manager.daily_touch_count, 5)
        self.assertEqual(self.manager.daily_praise_count, 3)
        self.assertEqual(self.manager.last_reset_date, "2024-01-01")


if __name__ == '__main__':
    unittest.main()

