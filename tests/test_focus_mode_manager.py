"""
专注模式管理器单元测试
测试专注模式检测、进入/退出、行为约束等功能
"""
import unittest
import time
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.focus_mode_manager import FocusModeManager
from src.state import LampState


class TestFocusModeManager(unittest.TestCase):
    """专注模式管理器测试类"""
    
    def setUp(self):
        """每个测试前的初始化"""
        self.manager = FocusModeManager()
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
    
    def test_should_enter_focus_mode_true(self):
        """测试检测到进入专注模式的触发词"""
        enter_keywords = [
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
        
        for keyword in enter_keywords:
            result = self.manager.should_enter_focus_mode(keyword, self.default_state)
            self.assertTrue(result, f"应该检测到进入专注模式: {keyword}")
    
    def test_should_enter_focus_mode_false(self):
        """测试未检测到进入专注模式的触发词"""
        non_enter_inputs = [
            "你好",
            "今天天气怎么样",
            "开灯",
            "工作完成了"
        ]
        
        for user_input in non_enter_inputs:
            result = self.manager.should_enter_focus_mode(user_input, self.default_state)
            self.assertFalse(result, f"不应该检测到进入专注模式: {user_input}")
    
    def test_should_enter_focus_mode_case_insensitive(self):
        """测试大小写不敏感"""
        self.assertTrue(self.manager.should_enter_focus_mode("我要工作了", self.default_state))
        self.assertTrue(self.manager.should_enter_focus_mode("我要工作了！", self.default_state))
    
    def test_should_exit_focus_mode_true(self):
        """测试检测到退出专注模式的触发词"""
        exit_keywords = [
            "关闭专注模式",
            "工作结束了",
            "休息一下",
            "退出专注模式",
            "结束专注模式",
            "工作完成",
            "可以说话了"
        ]
        
        for keyword in exit_keywords:
            result = self.manager.should_exit_focus_mode(keyword, self.default_state)
            self.assertTrue(result, f"应该检测到退出专注模式: {keyword}")
    
    def test_should_exit_focus_mode_false(self):
        """测试未检测到退出专注模式的触发词"""
        non_exit_inputs = [
            "你好",
            "开始工作",
            "开启专注模式"
        ]
        
        for user_input in non_exit_inputs:
            result = self.manager.should_exit_focus_mode(user_input, self.default_state)
            self.assertFalse(result, f"不应该检测到退出专注模式: {user_input}")
    
    def test_is_focus_mode_active_false(self):
        """测试专注模式未激活"""
        self.assertFalse(self.manager.is_focus_mode_active(self.default_state))
    
    def test_is_focus_mode_active_true(self):
        """测试专注模式已激活"""
        state = self.default_state.copy()
        state["focus_mode"] = True
        state["focus_mode_start_time"] = time.time()
        state["focus_mode_duration"] = 7200
        
        self.assertTrue(self.manager.is_focus_mode_active(state))
    
    def test_is_focus_mode_active_expired(self):
        """测试专注模式已过期"""
        state = self.default_state.copy()
        state["focus_mode"] = True
        state["focus_mode_start_time"] = time.time() - 7201  # 超过2小时
        state["focus_mode_duration"] = 7200
        
        self.assertFalse(self.manager.is_focus_mode_active(state))
    
    def test_enter_focus_mode(self):
        """测试进入专注模式"""
        result = self.manager.enter_focus_mode(
            self.default_state,
            reason="user_expression",
            auto=False
        )
        
        self.assertTrue(result["focus_mode"])
        self.assertIsNotNone(result["focus_mode_start_time"])
        self.assertEqual(result["focus_mode_duration"], 7200)
        self.assertFalse(result["focus_mode_auto"])
        self.assertEqual(result["focus_mode_reason"], "user_expression")
    
    def test_enter_focus_mode_auto(self):
        """测试自动进入专注模式"""
        result = self.manager.enter_focus_mode(
            self.default_state,
            reason="auto_detected",
            auto=True
        )
        
        self.assertTrue(result["focus_mode"])
        self.assertTrue(result["focus_mode_auto"])
        self.assertEqual(result["focus_mode_reason"], "auto_detected")
    
    def test_enter_focus_mode_custom_duration(self):
        """测试自定义持续时间"""
        state = self.default_state.copy()
        state["focus_mode_duration"] = 3600  # 1小时
        
        result = self.manager.enter_focus_mode(state, reason="manual", auto=False)
        
        self.assertEqual(result["focus_mode_duration"], 3600)
    
    def test_exit_focus_mode(self):
        """测试退出专注模式"""
        state = self.default_state.copy()
        state["focus_mode"] = True
        state["focus_mode_start_time"] = time.time()
        state["focus_mode_reason"] = "user_expression"
        
        result = self.manager.exit_focus_mode(state)
        
        self.assertFalse(result["focus_mode"])
        self.assertIsNone(result["focus_mode_start_time"])
        self.assertIsNone(result["focus_mode_reason"])
    
    def test_get_focus_mode_action_constraints_inactive(self):
        """测试非专注模式下的行为约束（允许所有）"""
        constraints = self.manager.get_focus_mode_action_constraints(self.default_state)
        
        self.assertTrue(constraints["allow_proactive"])
        self.assertTrue(constraints["allow_voice"])
        self.assertTrue(constraints["allow_touch"])
        self.assertTrue(constraints["allow_silent_nudge"])
    
    def test_get_focus_mode_action_constraints_active(self):
        """测试专注模式下的行为约束"""
        state = self.default_state.copy()
        state["focus_mode"] = True
        state["focus_mode_start_time"] = time.time()
        state["focus_mode_duration"] = 7200
        
        constraints = self.manager.get_focus_mode_action_constraints(state)
        
        self.assertFalse(constraints["allow_proactive"])  # 禁止主动行为
        self.assertFalse(constraints["allow_voice"])      # 禁止语音打断
        self.assertTrue(constraints["allow_touch"])        # 允许触摸
        self.assertTrue(constraints["allow_silent_nudge"])  # 允许静默提示
    
    def test_get_focus_mode_remaining_time_active(self):
        """测试获取专注模式剩余时间（激活状态）"""
        state = self.default_state.copy()
        state["focus_mode"] = True
        duration = 7200  # 2小时
        elapsed = 1800  # 已过30分钟
        state["focus_mode_start_time"] = time.time() - elapsed
        state["focus_mode_duration"] = duration
        
        remaining = self.manager.get_focus_mode_remaining_time(state)
        
        expected_remaining = duration - elapsed
        self.assertAlmostEqual(remaining, expected_remaining, delta=5)  # 允许5秒误差
    
    def test_get_focus_mode_remaining_time_inactive(self):
        """测试获取专注模式剩余时间（未激活）"""
        remaining = self.manager.get_focus_mode_remaining_time(self.default_state)
        self.assertEqual(remaining, 0.0)
    
    def test_get_focus_mode_remaining_time_expired(self):
        """测试获取专注模式剩余时间（已过期）"""
        state = self.default_state.copy()
        state["focus_mode"] = True
        state["focus_mode_start_time"] = time.time() - 7201  # 超过2小时
        state["focus_mode_duration"] = 7200
        
        remaining = self.manager.get_focus_mode_remaining_time(state)
        self.assertEqual(remaining, 0.0)
    
    def test_focus_mode_lifecycle(self):
        """测试专注模式完整生命周期"""
        # 1. 初始状态：未激活
        self.assertFalse(self.manager.is_focus_mode_active(self.default_state))
        
        # 2. 进入专注模式
        state = self.default_state.copy()
        enter_result = self.manager.enter_focus_mode(state, reason="user_expression", auto=False)
        state.update(enter_result)
        
        self.assertTrue(self.manager.is_focus_mode_active(state))
        constraints = self.manager.get_focus_mode_action_constraints(state)
        self.assertFalse(constraints["allow_proactive"])
        self.assertFalse(constraints["allow_voice"])
        
        # 3. 退出专注模式
        exit_result = self.manager.exit_focus_mode(state)
        state.update(exit_result)
        
        self.assertFalse(self.manager.is_focus_mode_active(state))
        constraints = self.manager.get_focus_mode_action_constraints(state)
        self.assertTrue(constraints["allow_proactive"])
        self.assertTrue(constraints["allow_voice"])
    
    def test_focus_mode_auto_expiry(self):
        """测试专注模式自动过期"""
        state = self.default_state.copy()
        state["focus_mode"] = True
        state["focus_mode_start_time"] = time.time() - 7201  # 超过2小时
        state["focus_mode_duration"] = 7200
        
        # 应该检测为未激活（已过期）
        self.assertFalse(self.manager.is_focus_mode_active(state))
        
        # 剩余时间应该为0
        remaining = self.manager.get_focus_mode_remaining_time(state)
        self.assertEqual(remaining, 0.0)


if __name__ == '__main__':
    unittest.main()

