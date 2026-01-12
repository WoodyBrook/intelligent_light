#!/usr/bin/env python3
"""
测试多模型切换功能（三级模型）

验证 ModelManager 能否正确根据任务类型选择模型：
- Fast: 超快响应（问候、确认）
- Chat: 日常对话、情感陪伴
- Reasoning: 复杂推理、工具调用
"""

import os
import sys

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.model_manager import ModelManager, get_model_manager, reset_model_manager


def test_three_tier_model_selection():
    """测试三级模型选择逻辑"""
    print("=" * 60)
    print("🧪 测试三级模型切换功能")
    print("=" * 60)
    
    # 重置单例以确保干净的测试环境
    reset_model_manager()
    
    # 获取模型管理器
    model_manager = get_model_manager()
    info = model_manager.get_model_info()
    print(f"\n📋 模型配置:")
    print(f"   - ⚡ Fast 模型: {info['fast_model']}")
    print(f"   - 💬 Chat 模型: {info['chat_model']}")
    print(f"   - 🧠 Reasoning 模型: {info['reasoning_model']}")
    print(f"   - 默认策略: {info['default_strategy']}")
    
    # 测试用例：(输入, 期望层级, 说明)
    test_cases = [
        # === Fast 场景 ===
        ("你好", "fast", "简单问候"),
        ("hi", "fast", "英文问候"),
        ("嗯", "fast", "极短确认"),
        ("好的", "fast", "简单确认"),
        ("谢谢", "fast", "感谢"),
        ("再见", "fast", "道别"),
        ("ok", "fast", "英文确认"),
        ("知道了", "fast", "确认收到"),
        ("没问题", "fast", "简单确认"),
        
        # === Chat 场景（情感/闲聊）===
        ("好累啊", "chat", "情感表达"),
        ("今天心情不错", "chat", "心情分享"),
        ("我有点难过", "chat", "情感倾诉"),
        ("想你了", "chat", "情感表达"),
        
        # === Reasoning 场景 ===
        ("如果今天下雨怎么办", "reasoning", "条件逻辑"),
        ("帮我分析一下这个问题", "reasoning", "复杂任务"),
        ("先查天气，然后推荐一首歌", "reasoning", "多步骤任务"),
        ("为什么天空是蓝色的", "reasoning", "知识问答"),
        ("帮我查一下天气", "reasoning", "工具相关"),
        ("播放一首歌", "reasoning", "工具相关"),
        ("现在几点了", "reasoning", "工具相关"),
    ]
    
    print("\n" + "=" * 60)
    print("📊 测试用例执行结果")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    for i, (user_input, expected_tier, desc) in enumerate(test_cases, 1):
        # 选择模型
        llm, model_name = model_manager.select_model(
            task_type="auto",
            user_input=user_input,
            has_tools=False
        )
        
        # 获取实际层级
        actual_tier = model_manager.get_model_tier(model_name)
        
        # 验证结果
        tier_emoji = {"fast": "⚡", "chat": "💬", "reasoning": "🧠"}.get(actual_tier, "?")
        
        if actual_tier == expected_tier:
            print(f"   ✅ [{tier_emoji} {actual_tier:10}] '{user_input}' ({desc})")
            passed += 1
        else:
            print(f"   ❌ [{tier_emoji} {actual_tier:10}] '{user_input}' ({desc}) - 期望 {expected_tier}")
            failed += 1
    
    # 总结
    print("\n" + "=" * 60)
    print("📈 测试总结")
    print("=" * 60)
    print(f"   通过: {passed}/{len(test_cases)}")
    print(f"   失败: {failed}/{len(test_cases)}")
    
    if failed == 0:
        print("\n   ✅ 所有测试通过！")
    else:
        print(f"\n   ⚠️  有 {failed} 个测试失败")
    
    return failed == 0


def test_manual_selection():
    """测试手动选择模型"""
    print("\n" + "=" * 60)
    print("🔧 测试手动模型选择")
    print("=" * 60)
    
    model_manager = get_model_manager()
    
    # 强制使用 fast 模型
    llm1, name1 = model_manager.select_model(task_type="fast")
    print(f"   强制 Fast: {name1}")
    assert model_manager.get_model_tier(name1) == "fast", "应该选择 fast 模型"
    
    # 强制使用 chat 模型
    llm2, name2 = model_manager.select_model(task_type="chat")
    print(f"   强制 Chat: {name2}")
    assert model_manager.get_model_tier(name2) == "chat", "应该选择 chat 模型"
    
    # 强制使用 reasoning 模型
    llm3, name3 = model_manager.select_model(task_type="reasoning")
    print(f"   强制 Reasoning: {name3}")
    assert model_manager.get_model_tier(name3) == "reasoning", "应该选择 reasoning 模型"
    
    print("\n   ✅ 手动选择测试通过！")


def test_statistics():
    """测试调用统计功能"""
    print("\n" + "=" * 60)
    print("📊 测试调用统计功能（三级模型）")
    print("=" * 60)
    
    # 重置单例
    reset_model_manager()
    model_manager = get_model_manager()
    
    # 重置统计
    model_manager.reset_stats()
    
    # 模拟一些调用
    model_manager.record_call("fast", 0.3, 100)
    model_manager.record_call("fast", 0.4, 150)
    model_manager.record_call("chat", 1.5, 500)
    model_manager.record_call("chat", 1.2, 300)
    model_manager.record_call("reasoning", 3.5, 1000)
    
    # 获取统计
    stats = model_manager.get_stats()
    
    print(f"\n   ⚡ Fast 调用次数: {stats['fast']['calls']}")
    print(f"   💬 Chat 调用次数: {stats['chat']['calls']}")
    print(f"   🧠 Reasoning 调用次数: {stats['reasoning']['calls']}")
    print(f"   总调用次数: {stats['total']['calls']}")
    print(f"   Fast 平均耗时: {stats['fast']['avg_time']:.3f}s")
    print(f"   Chat 平均耗时: {stats['chat']['avg_time']:.3f}s")
    print(f"   Reasoning 平均耗时: {stats['reasoning']['avg_time']:.3f}s")
    print(f"   总估算成本: ¥{stats['total']['estimated_cost']:.6f}")
    
    # 验证
    assert stats['fast']['calls'] == 2, "Fast 调用次数应该是 2"
    assert stats['chat']['calls'] == 2, "Chat 调用次数应该是 2"
    assert stats['reasoning']['calls'] == 1, "Reasoning 调用次数应该是 1"
    assert stats['total']['calls'] == 5, "总调用次数应该是 5"
    
    print("\n   ✅ 调用统计测试通过！")
    
    # 打印完整统计报告
    print("\n" + "-" * 40)
    model_manager.print_stats()


def test_tools_trigger_reasoning():
    """测试工具调用触发 reasoning 模型"""
    print("\n" + "=" * 60)
    print("🔧 测试工具调用触发 Reasoning")
    print("=" * 60)
    
    model_manager = get_model_manager()
    
    # 即使是简单输入，有工具时也应该用 reasoning
    llm, name = model_manager.select_model(
        task_type="auto",
        user_input="你好",  # 本来应该是 fast
        has_tools=True      # 但有工具调用
    )
    
    tier = model_manager.get_model_tier(name)
    print(f"   输入: '你好' + has_tools=True")
    print(f"   选择: {name} ({tier})")
    
    assert tier == "reasoning", "有工具调用时应该选择 reasoning"
    print("\n   ✅ 工具触发测试通过！")


def test_edge_cases():
    """测试边界情况"""
    print("\n" + "=" * 60)
    print("🔍 测试边界情况")
    print("=" * 60)
    
    # 使用激进策略
    reset_model_manager()
    model_manager = get_model_manager(default_strategy="aggressive")
    
    edge_cases = [
        # (输入, 期望层级, 说明)
        ("你好！", "fast", "问候带感叹号"),
        ("嗯~", "fast", "确认带波浪号"),
        ("当然可以", "chat", "'当然'不应被'当'误判"),
        ("再见啦", "chat", "'再见啦'有情感色彩，用chat"),
        ("你觉得呢", "chat", "不明确的闲聊"),
        ("", "chat", "空输入"),
    ]
    
    passed = 0
    failed = 0
    
    for user_input, expected, desc in edge_cases:
        _, name = model_manager.select_model(task_type="auto", user_input=user_input)
        actual = model_manager.get_model_tier(name)
        
        if actual == expected:
            print(f"   ✅ '{user_input or '(空)'}' → {actual} ({desc})")
            passed += 1
        else:
            print(f"   ❌ '{user_input or '(空)'}' → {actual}，期望 {expected} ({desc})")
            failed += 1
    
    print(f"\n   边界测试: {passed}/{len(edge_cases)} 通过")
    return failed == 0


if __name__ == "__main__":
    try:
        # 检查 API Key
        api_key = os.environ.get("VOLCENGINE_API_KEY") or os.environ.get("ARK_API_KEY")
        if not api_key:
            print("❌ 请设置 VOLCENGINE_API_KEY 或 ARK_API_KEY 环境变量")
            sys.exit(1)
        
        # 运行测试
        test1_passed = test_three_tier_model_selection()
        test_manual_selection()
        test_statistics()
        test_tools_trigger_reasoning()
        test2_passed = test_edge_cases()
        
        all_passed = test1_passed and test2_passed
        
        if all_passed:
            print("\n" + "=" * 60)
            print("🎉 所有测试通过！")
            print("=" * 60)
            sys.exit(0)
        else:
            print("\n" + "=" * 60)
            print("⚠️  部分测试失败，请检查逻辑")
            print("=" * 60)
            sys.exit(1)
            
    except Exception as e:
        print(f"\n❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
