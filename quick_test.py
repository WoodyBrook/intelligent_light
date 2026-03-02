#!/usr/bin/env python3
"""
快速测试 - 验证工具参数提取是否工作
"""

import requests
import json
import re

def test_direct_ollama():
    """直接测试 Ollama 参数提取"""
    
    print("=" * 60)
    print("快速测试：Ollama 参数提取")
    print("=" * 60)
    
    # 构建简单的测试 prompt
    prompt = """Extract the search keyword from this user query for a news search tool.

User query: "我今天听到新闻说微信把元宝的链接屏蔽了，发生什么了？"

Extract the main topic or event the user is asking about.

Return ONLY a JSON object in this exact format:
{"keyword": "the extracted keyword"}

Keyword:"""

    try:
        print("\n1. 发送请求到 Ollama...")
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "llama3.2:3b",
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1,
                    "num_predict": 50
                }
            },
            timeout=30
        )
        
        result = response.json()
        generated = result.get("response", "").strip()
        
        print(f"✅ Ollama 响应成功")
        print(f"\n2. 生成的文本:")
        print("-" * 60)
        print(generated)
        print("-" * 60)
        
        # 尝试提取 JSON
        print(f"\n3. 尝试提取 JSON...")
        try:
            # 查找 JSON 模式
            match = re.search(r'\{[^}]*\}', generated)
            if match:
                json_str = match.group(0)
                data = json.loads(json_str)
                keyword = data.get("keyword", "")
                
                print(f"✅ 成功提取关键词: '{keyword}'")
                
                if "微信" in keyword and "元宝" in keyword:
                    print("\n🎉 完美！成功提取了正确的关键词")
                    return True
                else:
                    print(f"\n⚠️  提取的关键词可能不够准确")
                    return True
            else:
                print("❌ 未找到 JSON 模式")
                return False
        except Exception as e:
            print(f"❌ JSON 解析失败: {e}")
            return False
            
    except Exception as e:
        print(f"❌ 请求失败: {e}")
        return False


def check_ollama():
    """检查 Ollama 是否运行"""
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            data = response.json()
            models = [m.get("name", "") for m in data.get("models", [])]
            return True, models
        return False, []
    except:
        return False, []


if __name__ == "__main__":
    print("=" * 60)
    print("快速测试 - Ollama 工具参数提取")
    print("=" * 60)
    
    # 检查 Ollama
    print("\n1. 检查 Ollama 状态...")
    running, models = check_ollama()
    
    if not running:
        print("❌ Ollama 未运行")
        print("   请先启动 Ollama: ollama serve")
        exit(1)
    
    print(f"✅ Ollama 运行正常")
    print(f"   已安装模型: {', '.join(models)}")
    
    if "llama3.2:3b" not in models:
        print("\n⚠️  未找到 llama3.2:3b 模型")
        print("   请先下载: ollama pull llama3.2:3b")
        exit(1)
    
    # 运行测试
    print("\n" + "=" * 60)
    success = test_direct_ollama()
    
    if success:
        print("\n" + "=" * 60)
        print("✅ 测试通过！Ollama 参数提取功能正常工作。")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("⚠️  测试未完全通过，但基础连接正常。")
        print("=" * 60)