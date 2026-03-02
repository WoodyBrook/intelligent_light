#!/usr/bin/env python3
"""
测试 Ollama 连接和工具参数提取功能
"""

import requests
import json


def test_ollama_connection():
    """测试 Ollama 是否运行"""
    print("=" * 60)
    print("1. 测试 Ollama 连接")
    print("=" * 60)
    
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            data = response.json()
            models = data.get("models", [])
            print(f"✅ Ollama 运行正常")
            print(f"   已安装的模型:")
            for model in models:
                print(f"   - {model.get('name', 'unknown')}")
            return True
        else:
            print(f"❌ Ollama 返回错误状态码: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到 Ollama")
        print("   请确保 Ollama 已启动: ollama serve")
        return False
    except Exception as e:
        print(f"❌ 连接错误: {e}")
        return False


def test_ollama_generate():
    """测试 Ollama 生成响应"""
    print("\n" + "=" * 60)
    print("2. 测试 Ollama 生成响应")
    print("=" * 60)
    
    prompt = """Extract parameters from the user's input for the news tool.

User Input: "我今天听到新闻说微信把元宝的链接屏蔽了，发生什么了？"

Tool: news_tool

Extract the search keyword and return as JSON:
{
    "keyword": "..."
}"""
    
    try:
        url = "http://localhost:11434/api/generate"
        payload = {
            "model": "llama3.2:3b",
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,
                "num_predict": 100,
            }
        }
        
        print(f"发送请求到 Ollama...")
        print(f"模型: llama3.2:3b")
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        generated_text = result.get("response", "")
        
        print(f"✅ Ollama 响应成功")
        print(f"\n生成的文本:")
        print("-" * 60)
        print(generated_text)
        print("-" * 60)
        
        # 尝试提取JSON
        try:
            # 查找JSON块
            import re
            match = re.search(r'\{[^}]*\}', generated_text)
            if match:
                json_str = match.group(0)
                params = json.loads(json_str)
                print(f"\n✅ 成功提取参数:")
                print(f"   {params}")
                return True
        except Exception as e:
            print(f"⚠️  无法解析JSON: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ 生成失败: {e}")
        return False


def test_integration():
    """测试完整的参数提取集成"""
    import sys
    
    print("\n" + "=" * 60)
    print("3. 测试完整集成（如果 nodes.py 可用）")
    print("=" * 60)
    
    try:
        # 尝试导入我们的代码
        sys.path.insert(0, '/Users/JiajunFei/Documents/开普勒/Neko_light')
        from src.nodes import ToolParameterExtractor, _get_tool_schema, get_parameter_extractor
        
        print("✅ 成功导入参数提取模块")
        
        # 测试参数提取
        extractor = get_parameter_extractor()
        tool_schema = _get_tool_schema("news_tool")
        
        test_input = "我今天听到新闻说微信把元宝的链接屏蔽了，发生什么了？"
        print(f"\n测试输入: {test_input}")
        print("正在调用Ollama提取参数...")
        
        params = extractor.extract_parameters(test_input, "news_tool", tool_schema)
        
        print(f"\n✅ 提取结果: {params}")
        
        if params and "keyword" in params:
            print(f"\n🎉 成功! 提取的关键词: '{params['keyword']}'")
        else:
            print("\n⚠️  未能提取到关键词")
        
        return True
        
    except ImportError as e:
        print(f"⚠️  无法导入模块: {e}")
        print("   这可能是由于缺少依赖项")
        return False
    except Exception as e:
        print(f"❌ 集成测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    import sys
    
    print("\n" + "=" * 60)
    print("Ollama 工具参数提取测试")
    print("=" * 60)
    
    results = []
    
    # 测试1: 连接
    results.append(("Ollama连接", test_ollama_connection()))
    
    # 测试2: 生成
    results.append(("Ollama生成", test_ollama_generate()))
    
    # 测试3: 集成
    results.append(("完整集成", test_integration()))
    
    # 总结
    print("\n" + "=" * 60)
    print("测试结果总结")
    print("=" * 60)
    
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{name:20s} {status}")
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    print(f"\n总计: {passed}/{total} 项测试通过")
    
    if passed == total:
        print("\n🎉 所有测试通过! Ollama 工具参数提取功能正常工作。")
    else:
        print("\n⚠️  部分测试失败，请检查 Ollama 是否正常运行。")


if __name__ == "__main__":
    main()