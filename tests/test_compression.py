#!/usr/bin/env python3
# test_compression.py
"""
测试对话历史压缩功能
"""

import os
import sys

# 确保可以导入项目模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.context_manager import get_context_manager


def test_compression():
    """测试对话历史压缩"""
    print("=" * 60)
    print("测试对话历史压缩功能")
    print("=" * 60)
    
    # 创建模拟对话历史
    mock_history = [
        {
            "type": "conversation",
            "user": "今天天气怎么样？",
            "assistant": "今天上海天气晴朗，温度 22°C，适合出门活动。"
        },
        {
            "type": "conversation",
            "user": "帮我把灯调亮一点",
            "assistant": "好的，已经把亮度调到 80%。"
        },
        {
            "type": "conversation",
            "user": "现在几点了？",
            "assistant": "现在是下午 3:45。"
        },
        {
            "type": "conversation",
            "user": "播放一首轻音乐",
            "assistant": "好的，正在为您播放轻音乐《River Flows in You》。"
        },
        {
            "type": "conversation",
            "user": "你真棒！",
            "assistant": "谢谢夸奖！能帮到你我很开心～"
        },
        {
            "type": "conversation",
            "user": "明天我要去北京出差",
            "assistant": "好的，我记住了。祝您出差顺利！需要我提醒您准备什么吗？"
        },
        {
            "type": "conversation",
            "user": "不用了，谢谢",
            "assistant": "好的，有需要随时叫我～"
        },
    ]
    
    # 获取上下文管理器
    context_manager = get_context_manager()
    
    # 测试 1: 小于阈值，不压缩
    print("\n测试 1: 小于阈值（不压缩）")
    print("-" * 60)
    small_history = mock_history[:2]
    result = context_manager.compress_conversation_history(small_history)
    print(f"原始大小: {result['original_size']} 字符")
    print(f"是否压缩: {result['compressed']}")
    print(f"最近对话数: {len(result['recent_history'])}")
    
    # 测试 2: 超过阈值，自动压缩
    print("\n测试 2: 超过阈值（自动压缩）")
    print("-" * 60)
    result = context_manager.compress_conversation_history(mock_history, force=True)
    print(f"原始大小: {result['original_size']} 字符")
    print(f"压缩后大小: {result['compressed_size']} 字符")
    print(f"压缩比例: {result['compression_ratio']}")
    print(f"是否压缩: {result['compressed']}")
    print(f"最近对话数: {len(result['recent_history'])}")
    print(f"需要归档数: {len(result['should_archive'])}")
    
    # 测试 3: 格式化输出
    print("\n测试 3: 格式化压缩结果")
    print("-" * 60)
    formatted = context_manager.format_compressed_history(result)
    print(formatted)
    
    # 测试 4: 大量对话（触发归档）
    print("\n测试 4: 大量对话（触发归档）")
    print("-" * 60)
    large_history = mock_history * 5  # 35 轮对话
    result = context_manager.compress_conversation_history(large_history, force=True)
    print(f"总对话数: {len(large_history)}")
    print(f"最近对话数: {len(result['recent_history'])}")
    print(f"需要归档数: {len(result['should_archive'])}")
    print(f"压缩比例: {result['compression_ratio']}")
    
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)


if __name__ == "__main__":
    try:
        test_compression()
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

