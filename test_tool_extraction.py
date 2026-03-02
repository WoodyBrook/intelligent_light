#!/usr/bin/env python3
"""
测试工具参数提取功能
"""

import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.nodes import ToolParameterExtractor, _get_tool_schema


def test_news_tool_extraction():
    """测试新闻工具参数提取"""
    print("=" * 60)
    print("测试新闻工具参数提取")
    print("=" * 60)
    
    # 创建参数提取器
    extractor = ToolParameterExtractor(
        ollama_url="http://localhost:11434",
        model="llama3.2:3b"
    )
    
    # 获取工具schema
    tool_schema = _get_tool_schema("news_tool")
    
    # 测试用例
    test_cases = [
        "我今天听到新闻说微信把元宝的链接屏蔽了，发生什么了？",
        "最近有什么科技新闻吗？",
        "特斯拉降价了，是真的吗？",
        "告诉我今天的财经新闻",
    ]
    
    for user_input in test_cases:
        print(f"\n用户输入: {user_input}")
        try:
            params = extractor.extract_parameters(user_input, "news_tool", tool_schema)
            print(f"提取的参数: {params}")
        except Exception as e:
            print(f"提取失败: {e}")
    
    print("\n" + "=" * 60)


def test_prompt_generation():
    """测试Prompt生成"""
    print("=" * 60)
    print("测试Prompt生成")
    print("=" * 60)
    
    extractor = ToolParameterExtractor()
    tool_schema = _get_tool_schema("news_tool")
    
    user_input = "我今天听到新闻说微信把元宝的链接屏蔽了，发生什么了？"
    
    prompt = extractor._build_extraction_prompt(user_input, "news_tool", tool_schema)
    
    print("生成的Prompt:")
    print("-" * 60)
    print(prompt)
    print("-" * 60)


if __name__ == "__main__":
    # 测试Prompt生成
    test_prompt_generation()
    
    print("\n\n")
    
    # 测试参数提取（需要Ollama运行）
    print("注意：参数提取测试需要Ollama在 http://localhost:11434 运行，并加载 llama3.2:3b 模型")
    print("如果Ollama未运行，测试会失败\n")
    
    try:
        test_news_tool_extraction()
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()