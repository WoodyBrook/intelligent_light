#!/usr/bin/env python3
"""
测试豆包生成新闻摘要功能
"""

import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.tools import get_news


def test_doubao_news_summary():
    """测试豆包新闻摘要功能"""
    
    print("=" * 60)
    print("测试豆包新闻摘要功能")
    print("=" * 60)
    
    # 测试用例
    test_cases = [
        {
            "keyword": "巴拿马对李嘉诚港口",
            "description": "巴拿马港口事件"
        },
        {
            "keyword": "微信屏蔽元宝",
            "description": "微信元宝事件"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'─' * 60}")
        print(f"测试 {i}: {test_case['description']}")
        print(f"关键词: {test_case['keyword']}")
        print(f"{'─' * 60}")
        
        try:
            # 调用 get_news，启用豆包摘要
            print("\n调用 get_news (use_doubao_summary=True)...")
            result = get_news(
                keyword=test_case['keyword'],
                use_doubao_summary=True
            )
            
            print(f"\n✅ 成功获取结果！")
            print(f"\n结果预览 (前300字):")
            print("-" * 60)
            print(result[:300] if len(result) > 300 else result)
            if len(result) > 300:
                print("...")
            print("-" * 60)
            
            # 检查结果是否包含豆包生成的标记
            if "📰" in result or "相关新闻" in result or "摘要" in result:
                print("\n✅ 看起来是豆包生成的摘要格式！")
            else:
                print("\n⚠️  可能是原始搜索结果（豆包摘要可能失败了）")
            
        except Exception as e:
            print(f"\n❌ 测试失败: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


def test_compare_with_without_doubao():
    """对比使用和不使用豆包摘要的效果"""
    
    print("\n" + "=" * 60)
    print("对比测试：使用 vs 不使用豆包摘要")
    print("=" * 60)
    
    keyword = "巴拿马对李嘉诚港口"
    
    # 不使用豆包摘要
    print("\n1. 不使用豆包摘要 (use_doubao_summary=False):")
    print("-" * 60)
    try:
        result_without = get_news(keyword=keyword, use_doubao_summary=False)
        print(result_without[:500])
        print("..." if len(result_without) > 500 else "")
    except Exception as e:
        print(f"错误: {e}")
    
    # 使用豆包摘要
    print("\n2. 使用豆包摘要 (use_doubao_summary=True):")
    print("-" * 60)
    try:
        result_with = get_news(keyword=keyword, use_doubao_summary=True)
        print(result_with[:500])
        print("..." if len(result_with) > 500 else "")
    except Exception as e:
        print(f"错误: {e}")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    # 运行测试
    test_doubao_news_summary()
    
    # 运行对比测试
    # test_compare_with_without_doubao()