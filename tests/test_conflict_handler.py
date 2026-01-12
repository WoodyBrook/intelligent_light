"""
冲突处理器单元测试
测试冲突等级检测、惩罚应用、冷却期管理、道歉检测等功能
"""
import unittest
import time
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.conflict_handler import ConflictHandler
from src.state import LampState


class TestConflictHandler(unittest.TestCase):
    """冲突处理器测试类"""
    
    def setUp(self):
        """每个测试前的初始化"""
        self.handler = ConflictHandler()
        self.default_state = LampState(
            user_input=None,
            sensor_data={},
            energy_level=100,
            current_mood="gentle_firm",
            intent_route="reflex",
            should_proceed=True,
            action_plan={},
            voice_content=None,
            history=[],
            user_profile={},
            internal_drives={},
            memory_context=None,
            event_type=None,
            proactive_expression=None,
            user_preferences={},
            context_signals={},
            evaluation_reason=None,
            parsed_params=None,
            command_type=None,
            execution_status=None,
            current_hardware_state={},
            intimacy_level=30.0,
            intimacy_rank="stranger",
            intimacy_history=[],
            daily_presence_duration=0.0,
            focus_mode=False,
            focus_mode_start_time=None,
            focus_mode_duration=7200,
            focus_mode_auto=False,
            focus_mode_reason=None,
            conflict_state=None
        )
    
    def test_detect_conflict_level_l0(self):
        """测试检测L0（非冒犯）"""
        user_input = "今天天气真好"
        sensor_data = {}
        
        level = self.handler.detect_conflict_level(user_input, sensor_data)
        self.assertEqual(level, "L0")
    
    def test_detect_conflict_level_l1(self):
        """测试检测L1（轻度冒犯）"""
        # 测试各种L1关键词
        l1_inputs = ["真笨", "别吵", "烦死了", "闭嘴", "讨厌"]
        
        for user_input in l1_inputs:
            level = self.handler.detect_conflict_level(user_input, {})
            self.assertEqual(level, "L1", f"应该检测到L1: {user_input}")
    
    def test_detect_conflict_level_l2(self):
        """测试检测L2（中度冒犯）"""
        # 测试各种L2关键词
        l2_inputs = ["傻逼", "滚", "去死", "垃圾", "废物", "蠢货"]
        
        for user_input in l2_inputs:
            level = self.handler.detect_conflict_level(user_input, {})
            self.assertEqual(level, "L2", f"应该检测到L2: {user_input}")
    
    def test_detect_conflict_level_l3_physical(self):
        """测试检测L3（物理暴力）"""
        sensor_data = {"violent_shake": True}
        level = self.handler.detect_conflict_level("", sensor_data)
        self.assertEqual(level, "L3")
        
        sensor_data = {"violent_strike": True}
        level = self.handler.detect_conflict_level("", sensor_data)
        self.assertEqual(level, "L3")
    
    def test_detect_conflict_level_case_insensitive(self):
        """测试大小写不敏感"""
        level = self.handler.detect_conflict_level("真笨", {})
        self.assertEqual(level, "L1")
        
        level = self.handler.detect_conflict_level("真笨！", {})
        self.assertEqual(level, "L1")
    
    def test_apply_conflict_penalty_l0(self):
        """测试L0不触发惩罚"""
        result = self.handler.apply_conflict_penalty("L0", self.default_state)
        
        self.assertEqual(result["intimacy_delta"], 0)
        self.assertEqual(result["cooldown_seconds"], 0)
        self.assertIsNone(result["conflict_state"])
    
    def test_apply_conflict_penalty_l1(self):
        """测试L1惩罚"""
        result = self.handler.apply_conflict_penalty("L1", self.default_state)
        
        self.assertEqual(result["intimacy_delta"], -2)
        self.assertEqual(result["cooldown_seconds"], 30)
        self.assertIsNotNone(result["conflict_state"])
        self.assertEqual(result["conflict_state"]["offense_level"], "L1")
        self.assertFalse(result["conflict_state"]["protective_mode"])
    
    def test_apply_conflict_penalty_l2(self):
        """测试L2惩罚"""
        result = self.handler.apply_conflict_penalty("L2", self.default_state)
        
        self.assertEqual(result["intimacy_delta"], -5)
        self.assertEqual(result["cooldown_seconds"], 300)  # 5分钟
        self.assertIsNotNone(result["conflict_state"])
        self.assertEqual(result["conflict_state"]["offense_level"], "L2")
        self.assertFalse(result["conflict_state"]["protective_mode"])
    
    def test_apply_conflict_penalty_l3(self):
        """测试L3惩罚"""
        result = self.handler.apply_conflict_penalty("L3", self.default_state)
        
        self.assertEqual(result["intimacy_delta"], -10)
        self.assertEqual(result["cooldown_seconds"], 1200)  # 20分钟
        self.assertIsNotNone(result["conflict_state"])
        self.assertEqual(result["conflict_state"]["offense_level"], "L3")
        self.assertTrue(result["conflict_state"]["protective_mode"])
        self.assertEqual(result["conflict_state"]["repair_min_wait_seconds"], 120)
    
    def test_apply_conflict_penalty_cooldown_until(self):
        """测试冷却期时间戳计算"""
        result = self.handler.apply_conflict_penalty("L1", self.default_state)
        
        cooldown_until = result["conflict_state"]["cooldown_until"]
        current_time = time.time()
        
        # 冷却期应该在当前时间之后
        self.assertGreater(cooldown_until, current_time)
        # 应该在30秒左右（允许1秒误差）
        self.assertAlmostEqual(cooldown_until - current_time, 30, delta=1)
    
    def test_apply_conflict_penalty_allowed_commands(self):
        """测试冷却期允许的命令列表"""
        result = self.handler.apply_conflict_penalty("L1", self.default_state)
        
        allowed = result["conflict_state"]["allowed_commands_during_cooldown"]
        self.assertIn("safety_stop", allowed)
        self.assertIn("basic_light_control", allowed)
        self.assertIn("focus_mode_toggle", allowed)
        self.assertIn("status_query", allowed)
    
    def test_is_in_cooldown_false(self):
        """测试不在冷却期"""
        self.assertFalse(self.handler.is_in_cooldown(self.default_state))
    
    def test_is_in_cooldown_true(self):
        """测试在冷却期"""
        state = self.default_state.copy()
        state["conflict_state"] = {
            "offense_level": "L1",
            "cooldown_until": time.time() + 30,
            "protective_mode": False,
            "repair_min_wait_seconds": 0,
            "allowed_commands_during_cooldown": []
        }
        
        self.assertTrue(self.handler.is_in_cooldown(state))
    
    def test_is_in_cooldown_expired(self):
        """测试冷却期已过期"""
        state = self.default_state.copy()
        state["conflict_state"] = {
            "offense_level": "L1",
            "cooldown_until": time.time() - 10,  # 10秒前已过期
            "protective_mode": False,
            "repair_min_wait_seconds": 0,
            "allowed_commands_during_cooldown": []
        }
        
        self.assertFalse(self.handler.is_in_cooldown(state))
    
    def test_is_command_allowed_no_cooldown(self):
        """测试不在冷却期时允许所有命令"""
        self.assertTrue(self.handler.is_command_allowed("any_command", self.default_state))
    
    def test_is_command_allowed_in_cooldown_whitelist(self):
        """测试冷却期内的白名单命令"""
        state = self.default_state.copy()
        state["conflict_state"] = {
            "offense_level": "L1",
            "cooldown_until": time.time() + 30,
            "protective_mode": False,
            "repair_min_wait_seconds": 0,
            "allowed_commands_during_cooldown": ["safety_stop", "basic_light_control"]
        }
        
        self.assertTrue(self.handler.is_command_allowed("safety_stop", state))
        self.assertTrue(self.handler.is_command_allowed("basic_light_control", state))
        self.assertFalse(self.handler.is_command_allowed("random_command", state))
    
    def test_detect_forgiveness_true(self):
        """测试检测到道歉"""
        forgiveness_inputs = ["对不起", "抱歉", "我错了", "刚才太冲了", "sorry", "是我的错"]
        
        for user_input in forgiveness_inputs:
            result = self.handler.detect_forgiveness(user_input, self.default_state)
            self.assertTrue(result, f"应该检测到道歉: {user_input}")
    
    def test_detect_forgiveness_false(self):
        """测试未检测到道歉"""
        non_forgiveness_inputs = ["你好", "今天天气怎么样", "开灯"]
        
        for user_input in non_forgiveness_inputs:
            result = self.handler.detect_forgiveness(user_input, self.default_state)
            self.assertFalse(result, f"不应该检测到道歉: {user_input}")
    
    def test_detect_forgiveness_case_insensitive(self):
        """测试道歉检测大小写不敏感"""
        self.assertTrue(self.handler.detect_forgiveness("SORRY", self.default_state))
        self.assertTrue(self.handler.detect_forgiveness("Sorry", self.default_state))
    
    def test_can_repair_no_conflict(self):
        """测试无冲突状态时不能修复"""
        self.assertFalse(self.handler.can_repair(self.default_state))
    
    def test_can_repair_cooldown_expired(self):
        """测试冷却期结束后可以修复"""
        state = self.default_state.copy()
        state["conflict_state"] = {
            "offense_level": "L1",
            "cooldown_until": time.time() - 10,  # 已过期
            "protective_mode": False,
            "repair_min_wait_seconds": 0,
            "allowed_commands_during_cooldown": []
        }
        
        self.assertTrue(self.handler.can_repair(state))
    
    def test_can_repair_l3_min_wait(self):
        """测试L3需要等待最小时间"""
        state = self.default_state.copy()
        conflict_start = time.time() - 60  # 1分钟前开始
        state["conflict_state"] = {
            "offense_level": "L3",
            "cooldown_until": conflict_start + 1200,  # 20分钟冷却
            "cooldown_seconds": 1200,
            "protective_mode": True,
            "repair_min_wait_seconds": 120,  # 需要等待2分钟
            "allowed_commands_during_cooldown": []
        }
        
        # 只过了1分钟，还没到最小等待时间
        self.assertFalse(self.handler.can_repair(state))
        
        # 模拟过了3分钟
        state["conflict_state"]["cooldown_until"] = conflict_start + 180
        self.assertTrue(self.handler.can_repair(state))
    
    def test_get_cooldown_remaining(self):
        """测试获取冷却期剩余时间"""
        state = self.default_state.copy()
        remaining_seconds = 30
        state["conflict_state"] = {
            "offense_level": "L1",
            "cooldown_until": time.time() + remaining_seconds,
            "protective_mode": False,
            "repair_min_wait_seconds": 0,
            "allowed_commands_during_cooldown": []
        }
        
        remaining = self.handler.get_cooldown_remaining(state)
        self.assertAlmostEqual(remaining, remaining_seconds, delta=1)
    
    def test_get_cooldown_remaining_no_cooldown(self):
        """测试不在冷却期时返回0"""
        remaining = self.handler.get_cooldown_remaining(self.default_state)
        self.assertEqual(remaining, 0.0)
    
    def test_clear_conflict_state(self):
        """测试清除冲突状态"""
        result = self.handler.clear_conflict_state()
        self.assertIsNone(result["conflict_state"])


if __name__ == '__main__':
    unittest.main()

