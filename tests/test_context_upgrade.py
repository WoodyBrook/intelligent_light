#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 Context Engineering 升级功能（2.3 和 2.4）
测试内容：
1. Context 去重与清洗
2. XML 结构化提示词
"""

import os
import sys

# 设置 API Key（如果需要）
if not os.environ.get("VOLCENGINE_API_KEY"):
    print("⚠️  请设置 VOLCENGINE_API_KEY 环境变量")
    sys.exit(1)

from src.context_manager import ContextManager


def test_deduplication():
    """测试去重功能"""
    print("=" * 60)
    print("测试 1: Context 去重与清洗")
    print("=" * 60)
    
    context_manager = ContextManager()
    
    # 测试用户画像去重
    print("\n1.1 测试用户画像去重")
    print("-" * 40)
    
    # 模拟有重复的用户画像
    duplicate_memories = [
        "用户喜欢吃火锅",
        "用户喜欢吃火锅",  # 完全重复
        "用户喜欢在冷天吃火锅",  # 语义重复，但更详细
        "用户常住地是北京",
        "用户住在北京市",  # 语义重复
        "用户喜欢听音乐",
        "用户经常听音乐放松",  # 语义重复，但更详细
    ]
    
    print(f"原始记忆数量: {len(duplicate_memories)}")
    for i, mem in enumerate(duplicate_memories, 1):
        print(f"  {i}. {mem}")
    
    deduplicated = context_manager.deduplicate_user_profile(duplicate_memories)
    
    print(f"\n去重后记忆数量: {len(deduplicated)}")
    for i, mem in enumerate(deduplicated, 1):
        print(f"  {i}. {mem}")
    
    # 测试记忆上下文清洗
    print("\n1.2 测试记忆上下文清洗")
    print("-" * 40)
    
    # 模拟记忆上下文
    memory_context = {
        "user_memories": duplicate_memories,
        "action_patterns": [
            "[场景] 深度工作：需要冷白光",
            "[场景] 看电影：需要暗光",
            "[场景] 睡前放松：需要暖光",
            "[场景] 起床唤醒：模拟日出",
            "[场景] 触摸反馈：温暖色调",
            "[场景] 闲置求关注：轻微摆动",
            "[场景] 用户疲惫：温暖昏暗",
        ],
        "search_query": "test query"
    }
    
    print(f"清洗前:")
    print(f"  - 用户记忆: {len(memory_context['user_memories'])} 条")
    print(f"  - 动作模式: {len(memory_context['action_patterns'])} 条")
    
    cleaned = context_manager.clean_memory_context(memory_context)
    
    print(f"\n清洗后:")
    print(f"  - 用户记忆: {len(cleaned['user_memories'])} 条")
    print(f"  - 动作模式: {len(cleaned['action_patterns'])} 条")
    
    print("\n✅ 去重与清洗测试完成")


def test_xml_formatting():
    """测试 XML 格式化功能"""
    print("\n" + "=" * 60)
    print("测试 2: XML 结构化提示词")
    print("=" * 60)
    
    context_manager = ContextManager()
    
    # 准备测试数据
    user_profile = """- 用户常住地是北京
- 用户喜欢在冷天吃火锅
- 用户经常听音乐放松

【实时环境】
- 当前时间：2025-12-24 14:30:00 (星期二)"""
    
    recent_memories = [
        "用户上次询问了天气信息",
        "用户表扬了助手的回答",
        "用户提到明天要出差"
    ]
    
    action_patterns = [
        "[场景] 深度工作：需要冷白光，保持安静",
        "[场景] 看电影：极暗背景光，冷色调"
    ]
    
    conversation_history = """【历史摘要】
- 用户询问了北京的天气，当时是晴天 5°C
- 用户要求调整灯光亮度到 80%
- 用户表扬了助手的回答，亲密度提升

【最近对话】
1. 用户: 今天天气怎么样
   助手: 北京今天晴天，温度 5°C，挺冷的呢
2. 用户: 谢谢你，真贴心
   助手: 嘿嘿，能帮到你我也很开心呀~"""
    
    current_state = {
        "intimacy_level": 65,
        "focus_mode": False,
        "conflict_state": None
    }
    
    # 生成 XML 格式化的上下文
    print("\n2.1 生成 XML 格式化上下文")
    print("-" * 40)
    
    xml_context = context_manager.format_context_with_xml(
        user_profile=user_profile,
        recent_memories=recent_memories,
        action_patterns=action_patterns,
        conversation_history=conversation_history,
        current_state=current_state
    )
    
    print("\n生成的 XML 上下文：")
    print("-" * 40)
    print(xml_context)
    print("-" * 40)
    
    # 验证 XML 结构
    print("\n2.2 验证 XML 结构")
    print("-" * 40)
    
    expected_tags = [
        "<context>",
        "</context>",
        "<user_profile>",
        "</user_profile>",
        "<recent_memories>",
        "</recent_memories>",
        "<action_patterns>",
        "</action_patterns>",
        "<current_state>",
        "</current_state>",
        "<conversation_history>",
        "</conversation_history>"
    ]
    
    all_present = True
    for tag in expected_tags:
        if tag in xml_context:
            print(f"  ✅ {tag} 存在")
        else:
            print(f"  ❌ {tag} 缺失")
            all_present = False
    
    if all_present:
        print("\n✅ XML 结构验证通过")
    else:
        print("\n❌ XML 结构验证失败")
    
    # 测试空值处理
    print("\n2.3 测试空值处理")
    print("-" * 40)
    
    xml_context_empty = context_manager.format_context_with_xml(
        user_profile="",
        recent_memories=[],
        action_patterns=[],
        conversation_history="",
        current_state=None
    )
    
    print("空值情况下的 XML 上下文：")
    print(xml_context_empty)
    
    if "<context>" in xml_context_empty and "</context>" in xml_context_empty:
        print("\n✅ 空值处理正常")
    else:
        print("\n❌ 空值处理异常")


def test_integration():
    """测试集成场景"""
    print("\n" + "=" * 60)
    print("测试 3: 集成场景测试")
    print("=" * 60)
    
    context_manager = ContextManager()
    
    # 模拟完整的上下文处理流程
    print("\n3.1 模拟完整流程")
    print("-" * 40)
    
    # 1. 准备对话历史
    conversation_history = [
        {"type": "conversation", "user": "今天天气怎么样", "assistant": "北京今天晴天，5°C"},
        {"type": "conversation", "user": "有点冷啊", "assistant": "是呀，要不要调暖一点灯光"},
        {"type": "conversation", "user": "好的", "assistant": "已经调整为暖光了"},
        {"type": "conversation", "user": "谢谢", "assistant": "不客气~"},
    ]
    
    # 2. 压缩对话历史
    print("步骤 1: 压缩对话历史")
    compression_result = context_manager.compress_conversation_history(conversation_history)
    print(f"  - 压缩状态: {'已压缩' if compression_result['compressed'] else '未压缩'}")
    print(f"  - 原始大小: {compression_result['original_size']} 字符")
    print(f"  - 压缩后大小: {compression_result['compressed_size']} 字符")
    
    # 3. 准备记忆上下文（带重复）
    memory_context = {
        "user_memories": [
            "用户常住地是北京",
            "用户住在北京",  # 重复
            "用户喜欢吃火锅",
            "用户喜欢吃火锅",  # 完全重复
        ],
        "action_patterns": [
            "[场景] 深度工作：冷白光",
            "[场景] 看电影：暗光",
        ]
    }
    
    # 4. 清洗记忆上下文
    print("\n步骤 2: 清洗记忆上下文")
    cleaned_context = context_manager.clean_memory_context(memory_context)
    print(f"  - 用户记忆: {len(memory_context['user_memories'])} -> {len(cleaned_context['user_memories'])} 条")
    
    # 5. 格式化为 XML
    print("\n步骤 3: 生成 XML 上下文")
    formatted_history = context_manager.format_compressed_history(compression_result)
    
    xml_context = context_manager.format_context_with_xml(
        user_profile="用户常住地是北京\n用户喜欢吃火锅",
        recent_memories=cleaned_context["user_memories"],
        action_patterns=cleaned_context["action_patterns"],
        conversation_history=formatted_history,
        current_state={"intimacy_level": 50, "focus_mode": False}
    )
    
    print(f"  - XML 上下文长度: {len(xml_context)} 字符")
    print(f"  - 包含标签数: {xml_context.count('<')}")
    
    print("\n最终 XML 上下文预览（前 500 字符）：")
    print("-" * 40)
    print(xml_context[:500])
    print("...")
    print("-" * 40)
    
    print("\n✅ 集成场景测试完成")


def main():
    """主测试函数"""
    print("\n🚀 开始测试 Context Engineering 升级功能\n")
    
    try:
        # 测试 1: 去重与清洗
        test_deduplication()
        
        # 测试 2: XML 格式化
        test_xml_formatting()
        
        # 测试 3: 集成场景
        test_integration()
        
        print("\n" + "=" * 60)
        print("🎉 所有测试完成！")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

