#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试去重修复：验证"用户喜欢蓝色"和"用户最喜欢的颜色是蓝色"能被识别为重复
"""

import os
import sys

# 设置 API Key（如果需要）
if not os.environ.get("VOLCENGINE_API_KEY"):
    print("⚠️  请设置 VOLCENGINE_API_KEY 环境变量")
    sys.exit(1)

from src.context_manager import ContextManager


def test_color_deduplication():
    """测试颜色相关的去重"""
    print("=" * 60)
    print("测试：颜色相关的语义去重")
    print("=" * 60)
    
    context_manager = ContextManager()
    
    # 测试用例 1：颜色重复
    print("\n测试用例 1: 颜色偏好重复")
    print("-" * 40)
    
    memories = [
        "用户喜欢蓝色",
        "用户最喜欢的颜色是蓝色",  # 应该被识别为重复
    ]
    
    print("原始记忆:")
    for i, mem in enumerate(memories, 1):
        print(f"  {i}. {mem}")
    
    deduplicated = context_manager.deduplicate_user_profile(memories)
    
    print(f"\n去重后记忆:")
    for i, mem in enumerate(deduplicated, 1):
        print(f"  {i}. {mem}")
    
    if len(deduplicated) == 1:
        print("\n✅ 测试通过：成功识别颜色重复，保留更详细的描述")
    else:
        print(f"\n❌ 测试失败：期望 1 条，实际 {len(deduplicated)} 条")
    
    # 测试用例 2：地点重复
    print("\n\n测试用例 2: 地点重复")
    print("-" * 40)
    
    memories = [
        "用户所在地是上海",
        "用户所在地是北京",  # 冲突，应该保留后者（更新）
        "用户住在北京市",  # 与上一条重复
    ]
    
    print("原始记忆:")
    for i, mem in enumerate(memories, 1):
        print(f"  {i}. {mem}")
    
    deduplicated = context_manager.deduplicate_user_profile(memories)
    
    print(f"\n去重后记忆:")
    for i, mem in enumerate(deduplicated, 1):
        print(f"  {i}. {mem}")
    
    # 应该只保留一条地点信息（最详细的那条）
    if len(deduplicated) <= 2:
        print("\n✅ 测试通过：成功识别地点重复")
    else:
        print(f"\n❌ 测试失败：期望 <= 2 条，实际 {len(deduplicated)} 条")
    
    # 测试用例 3：食物偏好重复
    print("\n\n测试用例 3: 食物偏好重复")
    print("-" * 40)
    
    memories = [
        "用户喜欢吃火锅",
        "用户喜欢在冷天吃火锅",  # 更详细，应该保留这条
        "用户爱吃火锅",  # 重复
    ]
    
    print("原始记忆:")
    for i, mem in enumerate(memories, 1):
        print(f"  {i}. {mem}")
    
    deduplicated = context_manager.deduplicate_user_profile(memories)
    
    print(f"\n去重后记忆:")
    for i, mem in enumerate(deduplicated, 1):
        print(f"  {i}. {mem}")
    
    if len(deduplicated) <= 2:
        print("\n✅ 测试通过：成功识别食物偏好重复")
    else:
        print(f"\n❌ 测试失败：期望 <= 2 条，实际 {len(deduplicated)} 条")
    
    # 测试用例 4：综合场景（来自终端输出）
    print("\n\n测试用例 4: 综合场景（实际问题）")
    print("-" * 40)
    
    memories = [
        "用户喜欢上海的美食",
        "用户喜欢吃日料",
        "用户喜欢吃火锅",
        "用户喜欢在忙碌一天后听轻音乐放松",
        "用户喜欢蓝色",
        "用户所在地是上海",
        "用户所在地是北京",
        "用户最喜欢的颜色是蓝色",  # 与第5条重复
    ]
    
    print("原始记忆:")
    for i, mem in enumerate(memories, 1):
        print(f"  {i}. {mem}")
    
    deduplicated = context_manager.deduplicate_user_profile(memories)
    
    print(f"\n去重后记忆:")
    for i, mem in enumerate(deduplicated, 1):
        print(f"  {i}. {mem}")
    
    # 期望：
    # - 颜色重复：2条 -> 1条
    # - 地点重复：2条 -> 1条
    # 总共应该从 8 条减少到 6 条左右
    expected_max = 6
    if len(deduplicated) <= expected_max:
        print(f"\n✅ 测试通过：成功去重，从 {len(memories)} 条减少到 {len(deduplicated)} 条")
    else:
        print(f"\n❌ 测试失败：期望 <= {expected_max} 条，实际 {len(deduplicated)} 条")


def test_keyword_extraction():
    """测试关键词提取逻辑"""
    print("\n\n" + "=" * 60)
    print("测试：关键词提取逻辑")
    print("=" * 60)
    
    context_manager = ContextManager()
    
    # 直接测试内部的 extract_keywords 函数
    # 由于是内部函数，我们通过实际去重来间接测试
    
    test_cases = [
        ("用户喜欢蓝色", "用户最喜欢的颜色是蓝色"),
        ("用户所在地是上海", "用户住在上海市"),
        ("用户喜欢吃火锅", "用户爱吃火锅"),
    ]
    
    for i, (mem1, mem2) in enumerate(test_cases, 1):
        print(f"\n测试对 {i}:")
        print(f"  A: {mem1}")
        print(f"  B: {mem2}")
        
        result = context_manager.deduplicate_user_profile([mem1, mem2])
        
        if len(result) == 1:
            print(f"  ✅ 成功识别为重复，保留: {result[0]}")
        else:
            print(f"  ❌ 未识别为重复，保留了 {len(result)} 条")


def main():
    """主测试函数"""
    print("\n🚀 开始测试去重修复\n")
    
    try:
        # 测试 1: 颜色去重
        test_color_deduplication()
        
        # 测试 2: 关键词提取
        test_keyword_extraction()
        
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

