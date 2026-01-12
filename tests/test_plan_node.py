# test_plan_node.py
"""
Plan Node 单元测试
"""

import pytest
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.nodes import (
    plan_node,
    plan_decision,
    reasoning_decision,
    _is_simple_task,
    _analyze_task_complexity,
    _detect_required_tools,
    _convert_step_to_tool_call,
    _generate_simple_plan,
    _validate_plan
)


class TestSimpleTaskDetection:
    """测试简单任务检测"""
    
    def test_greeting_is_simple(self):
        """问候语应该被识别为简单任务"""
        assert _is_simple_task("你好") == True
        assert _is_simple_task("嗨") == True
        assert _is_simple_task("早上好") == True
    
    def test_simple_control_is_simple(self):
        """简单控制命令应该被识别为简单任务"""
        assert _is_simple_task("开灯") == True
        assert _is_simple_task("关灯") == True
        assert _is_simple_task("停止") == True
    
    def test_condition_is_not_simple(self):
        """包含条件逻辑的任务不是简单任务"""
        assert _is_simple_task("如果下雨就提醒我带伞") == False
        assert _is_simple_task("当温度超过30度时告诉我") == False
    
    def test_multi_step_is_not_simple(self):
        """包含多步骤的任务不是简单任务"""
        assert _is_simple_task("查一下天气然后推荐一首歌") == False
        assert _is_simple_task("先帮我查新闻再告诉我时间") == False
    
    def test_short_query_is_simple(self):
        """短查询应该被识别为简单任务"""
        assert _is_simple_task("北京天气") == True
        assert _is_simple_task("现在几点") == True


class TestTaskComplexityAnalysis:
    """测试任务复杂度分析"""
    
    def test_simple_complexity(self):
        """简单任务应该返回 simple"""
        assert _analyze_task_complexity("你好") == "simple"
        assert _analyze_task_complexity("北京天气") == "simple"
    
    def test_moderate_complexity(self):
        """中等复杂度任务"""
        assert _analyze_task_complexity("查一下天气然后告诉我") == "moderate"
    
    def test_complex_complexity(self):
        """复杂任务应该返回 complex"""
        assert _analyze_task_complexity("如果今天下雨就提醒我带伞") == "complex"
        assert _analyze_task_complexity("查天气然后推荐音乐接着播放") == "complex"


class TestToolDetection:
    """测试工具检测"""
    
    def test_weather_tool(self):
        """天气关键词应该检测到 weather_tool"""
        tools = _detect_required_tools("今天北京天气怎么样")
        assert "weather_tool" in tools
    
    def test_time_tool(self):
        """时间关键词应该检测到 time_tool"""
        tools = _detect_required_tools("现在几点了")
        assert "time_tool" in tools
    
    def test_news_tool(self):
        """新闻关键词应该检测到 news_tool"""
        tools = _detect_required_tools("最新新闻是什么")
        assert "news_tool" in tools
    
    def test_calculator_tool(self):
        """计算关键词应该检测到 calculator_tool"""
        tools = _detect_required_tools("帮我计算 2+3 等于多少")
        assert "calculator_tool" in tools
    
    def test_multiple_tools(self):
        """应该能检测到多个工具"""
        tools = _detect_required_tools("查一下北京天气，顺便告诉我现在几点")
        assert "weather_tool" in tools
        assert "time_tool" in tools
    
    def test_no_tools(self):
        """普通对话不需要工具"""
        tools = _detect_required_tools("你好，最近怎么样")
        assert len(tools) == 0


class TestStepConversion:
    """测试步骤转换"""
    
    def test_tool_call_step(self):
        """工具调用步骤应该正确转换"""
        step = {
            "step_id": 1,
            "action_type": "tool_call",
            "tool_name": "weather_tool",
            "tool_args": {"city": "北京"}
        }
        result = _convert_step_to_tool_call(step)
        assert result is not None
        assert result["name"] == "weather_tool"
        assert result["args"]["city"] == "北京"
        assert "id" in result
    
    def test_llm_reasoning_step(self):
        """LLM 推理步骤不应该转换"""
        step = {
            "step_id": 1,
            "action_type": "llm_reasoning",
            "tool_name": None
        }
        result = _convert_step_to_tool_call(step)
        assert result is None


class TestSimplePlanGeneration:
    """测试简单计划生成"""
    
    def test_single_tool_plan(self):
        """单工具计划生成"""
        plan = _generate_simple_plan("北京天气", ["weather_tool"])
        assert plan is not None
        assert "steps" in plan
        assert len(plan["steps"]) >= 1
        assert plan["required_tools"] == ["weather_tool"]
    
    def test_no_tool_plan(self):
        """无工具计划生成"""
        plan = _generate_simple_plan("你好", [])
        assert plan is not None
        assert "steps" in plan
        assert len(plan["steps"]) == 1
        assert plan["steps"][0]["action_type"] == "llm_reasoning"
    
    def test_plan_has_required_fields(self):
        """计划应该包含所有必要字段"""
        plan = _generate_simple_plan("北京天气", ["weather_tool"])
        assert "plan_id" in plan
        assert "created_at" in plan
        assert "complexity" in plan
        assert "steps" in plan
        assert "total_steps" in plan
        assert "required_tools" in plan
        assert "estimated_time" in plan


class TestPlanValidation:
    """测试计划验证"""
    
    def test_valid_plan(self):
        """有效计划应该通过验证"""
        plan = {
            "steps": [
                {
                    "step_id": 1,
                    "action_type": "tool_call",
                    "tool_name": "weather_tool",
                    "depends_on": []
                }
            ]
        }
        is_valid, error = _validate_plan(plan)
        assert is_valid == True
        assert error is None
    
    def test_empty_plan_invalid(self):
        """空计划应该验证失败"""
        is_valid, error = _validate_plan(None)
        assert is_valid == False
    
    def test_no_steps_invalid(self):
        """没有步骤的计划应该验证失败"""
        plan = {"steps": []}
        is_valid, error = _validate_plan(plan)
        assert is_valid == False
    
    def test_too_many_steps_invalid(self):
        """步骤过多的计划应该验证失败"""
        plan = {
            "steps": [{"step_id": i, "action_type": "llm_reasoning", "depends_on": []} for i in range(15)]
        }
        is_valid, error = _validate_plan(plan)
        assert is_valid == False
    
    def test_unknown_tool_invalid(self):
        """未知工具应该验证失败"""
        plan = {
            "steps": [
                {
                    "step_id": 1,
                    "action_type": "tool_call",
                    "tool_name": "unknown_tool",
                    "depends_on": []
                }
            ]
        }
        is_valid, error = _validate_plan(plan)
        assert is_valid == False


class TestPlanDecision:
    """测试规划决策函数"""
    
    def test_skipped_plan(self):
        """跳过的计划应该返回 skipped"""
        state = {"plan_status": "skipped"}
        assert plan_decision(state) == "skipped"
    
    def test_failed_plan(self):
        """失败的计划应该返回 skipped"""
        state = {"plan_status": "failed"}
        assert plan_decision(state) == "skipped"
    
    def test_plan_with_tools(self):
        """有工具调用的计划应该返回 need_tool"""
        state = {
            "plan_status": "created",
            "tool_calls": [{"name": "weather_tool"}]
        }
        assert plan_decision(state) == "need_tool"
    
    def test_plan_without_tools(self):
        """没有工具调用的计划应该返回 no_tool"""
        state = {
            "plan_status": "created",
            "tool_calls": [],
            "execution_plan": {"required_tools": []}
        }
        assert plan_decision(state) == "no_tool"


class TestReasoningDecision:
    """测试推理决策函数"""
    
    def test_with_tool_calls(self):
        """有工具调用应该返回 tool_call"""
        state = {"tool_calls": [{"name": "weather_tool"}]}
        assert reasoning_decision(state) == "tool_call"
    
    def test_without_tool_calls(self):
        """没有工具调用应该返回 complete"""
        state = {"tool_calls": []}
        assert reasoning_decision(state) == "complete"
    
    def test_empty_state(self):
        """空状态应该返回 complete"""
        state = {}
        assert reasoning_decision(state) == "complete"


class TestPlanNodeIntegration:
    """Plan Node 集成测试"""
    
    def test_simple_task_skips_planning(self):
        """简单任务应该跳过规划"""
        state = {
            "user_input": "你好",
            "history": [],
            "memory_context": {}
        }
        result = plan_node(state)
        assert result["plan_status"] == "skipped"
        assert result["plan_skip_reason"] == "simple_task"
    
    def test_no_input_skips_planning(self):
        """无输入应该跳过规划"""
        state = {
            "user_input": "",
            "history": [],
            "memory_context": {}
        }
        result = plan_node(state)
        assert result["plan_status"] == "skipped"
        assert result["plan_skip_reason"] == "no_user_input"
    
    def test_tool_loop_return(self):
        """工具调用循环返回应该正确处理"""
        existing_plan = {
            "plan_id": "test",
            "created_at": 0,
            "complexity": "moderate",
            "steps": [
                {"step_id": 1, "action_type": "tool_call", "tool_name": "weather_tool"},
                {"step_id": 2, "action_type": "llm_reasoning", "tool_name": None}
            ],
            "total_steps": 2,
            "required_tools": ["weather_tool"]
        }
        state = {
            "user_input": "北京天气",
            "execution_plan": existing_plan,
            "tool_results": [{"output": "晴天 25度"}],
            "current_step_index": 0
        }
        result = plan_node(state)
        
        # 应该移动到下一步
        assert result["current_step_index"] == 1
        assert result["plan_status"] == "executing"
    
    def test_plan_completion(self):
        """计划完成应该正确标记"""
        existing_plan = {
            "plan_id": "test",
            "created_at": 0,
            "complexity": "simple",
            "steps": [
                {"step_id": 1, "action_type": "tool_call", "tool_name": "weather_tool"}
            ],
            "total_steps": 1,
            "required_tools": ["weather_tool"]
        }
        state = {
            "user_input": "北京天气",
            "execution_plan": existing_plan,
            "tool_results": [{"output": "晴天 25度"}],
            "current_step_index": 0
        }
        result = plan_node(state)
        
        # 应该标记为完成
        assert result["plan_status"] == "completed"
        assert result["tool_calls"] == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

