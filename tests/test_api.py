import os
import requests

api_key = os.environ.get("VOLCENGINE_API_KEY")
base_url = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"

if not api_key:
    print("❌ 错误：未找到环境变量 VOLCENGINE_API_KEY")
else:
    print(f"正在测试连接到: {base_url}...")
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    data = {
        "model": "deepseek-v3-1-terminus",
        "messages": [{"role": "user", "content": "你好，请回复'连接成功'"}],
        "temperature": 0.7
    }
    
    try:
        response = requests.post(base_url, headers=headers, json=data, timeout=10)
        if response.status_code == 200:
            result = response.json()
            print("✅ 连接成功！")
            print(f"回复内容: {result['choices'][0]['message']['content']}")
        else:
            print(f"❌ 连接失败，状态码: {response.status_code}")
            print(f"错误详情: {response.text}")
    except Exception as e:
        print(f"❌ 发生异常: {e}")