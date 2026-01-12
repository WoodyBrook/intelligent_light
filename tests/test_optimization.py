#!/usr/bin/env python3
"""
测试优化后的两阶段过滤逻辑
独立测试文件，不依赖完整的项目导入
"""

from typing import List

# === 复制优化后的函数进行独立测试 ===

# 简单任务关键词（无需规划，直接跳过）
SIMPLE_TASK_KEYWORDS = {
    "greeting": ["你好", "嗨", "早上好", "晚上好", "下午好", "hello", "hi"],
    "single_query": ["现在几点", "什么时间", "今天几号"],
    "simple_control": ["开灯", "关灯", "停止", "暂停"],
}

# 多步骤任务关键词（需要规划）
MULTI_STEP_KEYWORDS = ["然后", "之后", "接着", "再", "并且", "同时", "先", "最后"]

# 条件逻辑关键词
CONDITION_KEYWORDS = ["如果", "当", "若", "要是", "假如", "如若", "万一", "倘若"]


def _is_clearly_simple(user_input: str, history: List = None) -> bool:
    """
    阶段1：快速规则判断 - 明确的简单任务（不调用LLM）
    """
    if not user_input:
        return True
    
    input_lower = user_input.lower().strip()
    user_input_stripped = user_input.strip()
    
    # === 排除词检查：包含这些词的绝对不是简单任务 ===
    reference_keywords = ["那", "这个", "那个", "它", "呢", "怎么样", "如何", "怎样"]
    query_keywords = ["天气", "空气", "温度", "pm", "aqi", "新闻", "几点", "时间", "查", "搜"]
    condition_keywords = ["如果", "当", "若", "要是", "假如"]
    
    has_reference = any(kw in user_input for kw in reference_keywords)
    has_query = any(kw in input_lower for kw in query_keywords)
    has_condition = any(kw in user_input for kw in condition_keywords)
    
    if has_reference or has_query or has_condition:
        return False
    
    # === 简单任务检查 ===
    greetings = ["你好", "嗨", "早上好", "晚上好", "下午好", "hello", "hi", "早安", "晚安", "嘿"]
    for greeting in greetings:
        if input_lower == greeting or (input_lower.startswith(greeting) and len(user_input_stripped) < 15):
            return True
    
    control_commands = ["开灯", "关灯", "停止", "暂停", "停", "继续", "开始"]
    for cmd in control_commands:
        if cmd in input_lower:
            return True
    
    simple_responses = ["好的", "好", "嗯", "ok", "谢谢", "谢了", "感谢", "明白", "知道了", 
                        "收到", "了解", "可以", "行", "没问题", "没事", "算了", "不用了"]
    for resp in simple_responses:
        if input_lower == resp or user_input_stripped == resp:
            return True
    
    if len(user_input_stripped) < 6 and (not history or len(history) == 0):
        return True
    
    return False


def _is_clearly_complex(user_input: str, history: List = None) -> bool:
    """
    阶段2：快速规则判断 - 明确的复杂任务（不调用LLM）
    """
    if not user_input:
        return False
    
    input_lower = user_input.lower()
    
    if any(kw in user_input for kw in CONDITION_KEYWORDS):
        return True
    
    if any(kw in user_input for kw in MULTI_STEP_KEYWORDS):
        return True
    
    explicit_query_keywords = {
        "weather_tool": ["天气", "气温", "温度", "几度", "下雨", "晴天", "阴天", "多云"],
        "web_search_tool": ["空气", "空气质量", "pm2.5", "pm10", "aqi", "污染", "雾霾"],
        "news_tool": ["新闻", "资讯", "热点", "头条"],
        "time_tool": ["几点", "什么时间", "现在时间", "日期"],
        "calculator_tool": ["计算", "等于多少", "加", "减", "乘", "除"],
        "wikipedia_tool": ["是什么", "什么是", "百科", "介绍一下"]
    }
    
    detected_tools = []
    for tool_name, keywords in explicit_query_keywords.items():
        if any(kw in input_lower for kw in keywords):
            detected_tools.append(tool_name)
    
    if detected_tools:
        return True
    
    reference_keywords = ["那", "这个", "那个", "它", "呢", "怎么样", "如何", "怎样"]
    has_reference = any(kw in user_input for kw in reference_keywords)
    
    if has_reference and history:
        tool_related_keywords = ["天气", "空气", "pm2.5", "温度", "新闻", "时间", "查", "搜索"]
        for conv in history[-3:]:
            if isinstance(conv, dict):
                prev_user = conv.get("user", "")
                prev_assistant = conv.get("assistant", "")
                if any(kw in prev_user or kw in prev_assistant for kw in tool_related_keywords):
                    return True
    
    return False


def _rule_based_tool_detection(user_input: str) -> List[str]:
    """
    轻量级规则检测工具需求（不调用LLM）
    """
    if not user_input:
        return []
    
    input_lower = user_input.lower()
    detected_tools = []
    
    tool_keywords = {
        "weather_tool": ["天气", "气温", "温度", "几度", "下雨", "晴天"],
        "web_search_tool": ["空气", "空气质量", "pm2.5", "pm10", "aqi", "污染"],
        "news_tool": ["新闻", "资讯", "热点", "头条"],
        "time_tool": ["几点", "什么时间", "现在时间"],
        "calculator_tool": ["计算", "等于多少"],
    }
    
    for tool_name, keywords in tool_keywords.items():
        if any(kw in input_lower for kw in keywords):
            detected_tools.append(tool_name)
    
    return detected_tools


def _is_simple_task(user_input: str, history: List = None) -> bool:
    """
    两阶段过滤：先规则判断，再LLM判断（优化性能）
    """
    if not user_input:
        return True
    
    # 阶段1: 规则快速判断
    if _is_clearly_simple(user_input, history):
        return True
    
    if _is_clearly_complex(user_input, history):
        return False
    
    # 阶段2: 不确定场景，这里模拟返回 False（实际会调用 LLM）
    return False  # 模拟 LLM 判断为复杂任务


# === 测试 ===

def test_clearly_simple():
    """测试明确的简单任务"""
    print("=== 测试 _is_clearly_simple ===")
    tests = [
        ("你好", True, "问候语"),
        ("嗨", True, "问候语"),
        ("早上好", True, "问候语"),
        ("开灯", True, "控制命令"),
        ("关灯", True, "控制命令"),
        ("停止", True, "控制命令"),
        ("好的", True, "简单回复"),
        ("谢谢", True, "简单回复"),
        ("嗯", True, "简单回复"),
        ("天气怎么样", False, "包含查询词"),
        ("那呢", False, "包含指代词"),
        ("如果下雨", False, "包含条件词"),
        ("帮我查一下", False, "包含查询词"),
    ]
    
    passed = 0
    failed = 0
    for inp, expected, reason in tests:
        result = _is_clearly_simple(inp, [])
        status = "✓" if result == expected else "✗"
        if result == expected:
            passed += 1
        else:
            failed += 1
        print(f'  {status} "{inp}" -> {result} (expected: {expected}) [{reason}]')
    
    print(f"  结果: {passed}/{passed+failed} 通过\n")
    return failed == 0


def test_clearly_complex():
    """测试明确的复杂任务"""
    print("=== 测试 _is_clearly_complex ===")
    tests = [
        ("如果下雨就提醒我", True, "条件逻辑"),
        ("当温度超过30度时", True, "条件逻辑"),
        ("查天气然后推荐音乐", True, "多步骤"),
        ("先查新闻再告诉我", True, "多步骤"),
        ("今天北京天气", True, "明确查询词-天气"),
        ("空气质量怎么样", True, "明确查询词-空气"),
        ("最新新闻是什么", True, "明确查询词-新闻"),
        ("现在几点了", True, "明确查询词-时间"),
        ("你好", False, "简单问候"),
        ("好的", False, "简单回复"),
        ("我很开心", False, "情感表达"),
    ]
    
    passed = 0
    failed = 0
    for inp, expected, reason in tests:
        result = _is_clearly_complex(inp, [])
        status = "✓" if result == expected else "✗"
        if result == expected:
            passed += 1
        else:
            failed += 1
        print(f'  {status} "{inp}" -> {result} (expected: {expected}) [{reason}]')
    
    print(f"  结果: {passed}/{passed+failed} 通过\n")
    return failed == 0


def test_rule_based_tool_detection():
    """测试规则检测工具需求"""
    print("=== 测试 _rule_based_tool_detection ===")
    tests = [
        ("北京天气", ["weather_tool"]),
        ("今天天气怎么样", ["weather_tool"]),
        ("空气质量如何", ["web_search_tool"]),
        ("pm2.5多少", ["web_search_tool"]),
        ("最新新闻", ["news_tool"]),
        ("现在几点", ["time_tool"]),
        ("帮我计算2+3", ["calculator_tool"]),
        ("你好", []),
        ("我很开心", []),
    ]
    
    passed = 0
    failed = 0
    for inp, expected in tests:
        result = _rule_based_tool_detection(inp)
        status = "✓" if result == expected else "✗"
        if result == expected:
            passed += 1
        else:
            failed += 1
        print(f'  {status} "{inp}" -> {result} (expected: {expected})')
    
    print(f"  结果: {passed}/{passed+failed} 通过\n")
    return failed == 0


def test_two_stage_filtering():
    """测试两阶段过滤"""
    print("=== 测试两阶段过滤 _is_simple_task ===")
    tests = [
        ("你好", True, "阶段1-简单"),
        ("开灯", True, "阶段1-简单"),
        ("好的", True, "阶段1-简单"),
        ("天气怎么样", False, "阶段1-复杂（查询词）"),
        ("如果下雨提醒我", False, "阶段1-复杂（条件）"),
        ("查天气然后推荐音乐", False, "阶段1-复杂（多步骤）"),
        ("空气质量", False, "阶段1-复杂（查询词）"),
    ]
    
    passed = 0
    failed = 0
    for inp, expected, reason in tests:
        result = _is_simple_task(inp, [])
        status = "✓" if result == expected else "✗"
        if result == expected:
            passed += 1
        else:
            failed += 1
        print(f'  {status} "{inp}" -> {result} (expected: {expected}) [{reason}]')
    
    print(f"  结果: {passed}/{passed+failed} 通过\n")
    return failed == 0


def test_reference_resolution():
    """测试指代消解"""
    print("=== 测试指代消解 ===")
    
    # 模拟对话历史
    history_with_weather = [
        {"user": "今天北京天气怎么样", "assistant": "北京今天晴天，25度"}
    ]
    
    tests = [
        ("那呢", [], False, "无历史-指代词-不确定"),
        ("那呢", history_with_weather, True, "有历史-指代词+天气话题-复杂"),
    ]
    
    passed = 0
    failed = 0
    for inp, history, expected_complex, reason in tests:
        result = _is_clearly_complex(inp, history)
        status = "✓" if result == expected_complex else "✗"
        if result == expected_complex:
            passed += 1
        else:
            failed += 1
        print(f'  {status} "{inp}" (history: {len(history)}) -> complex={result} (expected: {expected_complex}) [{reason}]')
    
    print(f"  结果: {passed}/{passed+failed} 通过\n")
    return failed == 0


if __name__ == "__main__":
    print("=" * 60)
    print("优化后的两阶段过滤逻辑测试")
    print("=" * 60)
    print()
    
    all_passed = True
    all_passed &= test_clearly_simple()
    all_passed &= test_clearly_complex()
    all_passed &= test_rule_based_tool_detection()
    all_passed &= test_two_stage_filtering()
    all_passed &= test_reference_resolution()
    
    print("=" * 60)
    if all_passed:
        print("✅ 所有测试通过！")
    else:
        print("❌ 部分测试失败，请检查")
    print("=" * 60)
