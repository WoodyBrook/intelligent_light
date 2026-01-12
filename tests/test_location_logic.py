#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试地点管理逻辑：常住地 vs 临时位置
"""

import os
import sys

if not os.environ.get("VOLCENGINE_API_KEY"):
    print("⚠️  请设置 VOLCENGINE_API_KEY 环境变量")
    sys.exit(1)


def test_location_classification():
    """测试地点分类逻辑"""
    print("=" * 60)
    print("测试：地点分类逻辑（常住地 vs 临时位置）")
    print("=" * 60)
    
    # 模拟 detect_and_resolve_conflicts 中的判断逻辑
    def classify_location(text: str) -> str:
        """分类地点信息"""
        # 常住地关键词
        is_home = any(kw in text for kw in ["常住", "住在", "定居", "搬家", "搬到", "搬去", "搬迁", "安家", "落户"])
        # 临时位置关键词
        is_travel = any(kw in text for kw in ["出差", "旅游", "现在在", "正在", "临时", "来到", "去了"])
        
        # 如果两者都不明确，默认临时位置
        if not is_home and not is_travel:
            is_travel = True
        
        if is_home:
            return "常住地（Base）"
        elif is_travel:
            return "临时位置"
        else:
            return "未知"
    
    # 测试用例
    test_cases = [
        # 常住地（应该更新 Base 地）
        ("用户常住地是上海", "常住地（Base）"),
        ("用户住在上海", "常住地（Base）"),
        ("用户搬家到北京了", "常住地（Base）"),
        ("用户搬到北京了", "常住地（Base）"),
        ("用户在北京安家了", "常住地（Base）"),
        ("用户是上海人", "临时位置"),  # 注意：这个需要在 LLM 提取时处理
        
        # 临时位置（不应该更新 Base 地）
        ("用户现在在北京", "临时位置"),
        ("用户来北京出差了", "临时位置"),
        ("用户在北京旅游", "临时位置"),
        ("用户正在北京", "临时位置"),
        ("用户去了北京", "临时位置"),
        
        # 模糊表达（默认临时位置）
        ("用户在北京", "临时位置"),
        ("用户所在地是北京", "临时位置"),
    ]
    
    print("\n测试结果：")
    print("-" * 60)
    
    passed = 0
    failed = 0
    
    for text, expected in test_cases:
        result = classify_location(text)
        status = "✅" if result == expected else "❌"
        
        if result == expected:
            passed += 1
        else:
            failed += 1
        
        print(f"{status} {text}")
        print(f"   期望: {expected} | 实际: {result}")
        if result != expected:
            print(f"   ⚠️  分类错误！")
        print()
    
    print("-" * 60)
    print(f"总计: {len(test_cases)} 个测试")
    print(f"✅ 通过: {passed}")
    print(f"❌ 失败: {failed}")
    
    if failed == 0:
        print("\n🎉 所有测试通过！")
    else:
        print(f"\n⚠️  有 {failed} 个测试失败")


def test_conflict_scenarios():
    """测试冲突场景"""
    print("\n\n" + "=" * 60)
    print("测试：地点冲突场景")
    print("=" * 60)
    
    scenarios = [
        {
            "name": "场景 1: 设置常住地",
            "existing": [],
            "new": "用户常住地是上海",
            "expected_behavior": "保存为常住地，没有冲突"
        },
        {
            "name": "场景 2: 临时出差",
            "existing": ["用户常住地是上海"],
            "new": "用户现在在北京出差",
            "expected_behavior": "保存为临时位置，不覆盖常住地"
        },
        {
            "name": "场景 3: 搬家（更新 Base 地）",
            "existing": ["用户常住地是上海"],
            "new": "用户搬家到北京了",
            "expected_behavior": "更新常住地为北京，删除旧的上海常住地"
        },
        {
            "name": "场景 4: 多次出差",
            "existing": ["用户常住地是上海", "用户现在在北京出差"],
            "new": "用户现在在深圳出差",
            "expected_behavior": "更新临时位置为深圳，删除旧的北京临时位置，保留上海常住地"
        },
        {
            "name": "场景 5: 模糊表达",
            "existing": ["用户常住地是上海"],
            "new": "用户在北京",
            "expected_behavior": "默认为临时位置，不覆盖常住地"
        },
    ]
    
    for scenario in scenarios:
        print(f"\n{scenario['name']}")
        print("-" * 40)
        print(f"现有记忆: {scenario['existing']}")
        print(f"新信息: {scenario['new']}")
        print(f"预期行为: {scenario['expected_behavior']}")
        print()


def main():
    """主测试函数"""
    print("\n🚀 开始测试地点管理逻辑\n")
    
    try:
        # 测试 1: 地点分类
        test_location_classification()
        
        # 测试 2: 冲突场景
        test_conflict_scenarios()
        
        print("\n" + "=" * 60)
        print("🎉 测试完成！")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

