import os
import sys
import requests
from dotenv import load_dotenv, find_dotenv

def diagnose():
    print("🔍 开始诊断天气 API 配置 (V2 - 个性化域名支持)...")
    print(f"📂 当前工作目录: {os.getcwd()}")
    
    # 1. 检查 .env 文件
    env_path = find_dotenv()
    if not env_path:
        print("❌ 未找到 .env 文件！")
        return
    print(f"✅ 找到 .env 文件: {env_path}")
    
    # 2. 加载环境变量
    load_dotenv(env_path, override=True)
    
    api_key = os.getenv("QWEATHER_API_KEY")
    api_host = os.getenv("QWEATHER_API_HOST", "devapi.qweather.com")
    
    if not api_key:
        print("❌ 环境变量 QWEATHER_API_KEY 未找到！请在 .env 中配置。")
        return
    
    # 掩码显示 Key
    masked_key = f"{api_key[:3]}******{api_key[-3:]}" if len(api_key) > 6 else "******"
    print(f"✅ API Key: {masked_key}")
    print(f"✅ API Host: {api_host}")
    
    # 设置请求头 (使用 Header 鉴权)
    headers = {
        "X-QW-Api-Key": api_key
    }
    
    # 3. 测试 GeoAPI
    # 注意：新版 GeoAPI 在 API Host 下的路径为 /geo/v2/city/lookup
    # 参考文档: https://dev.qweather.com/docs/api/geoapi/city-lookup/
    
    print("\n🌍 [Step 1] 测试 GeoAPI (城市查询)...")
    city = "北京"
    
    # 尝试两个 URL：一个是配置的 Host (带 /geo)，一个是旧的 geoapi Host (不带 /geo)
    urls_to_test = [
        (f"https://{api_host}/geo/v2/city/lookup", "配置的 API Host (新版 /geo/v2)"),
        (f"https://{api_host}/v2/city/lookup", "配置的 API Host (旧版 /v2 - 备用)"),
        ("https://geoapi.qweather.com/v2/city/lookup", "通用 GeoAPI Host (旧版)")
    ]
    
    location_id = None
    location_name = None
    
    for url, desc in urls_to_test:
        print(f"   👉 尝试 {desc}: {url}")
        params = {"location": city}
        
        try:
            # 打印请求信息 (不含 key)
            print(f"      Headers: {{'X-QW-Api-Key': '{masked_key}'}}")
            
            response = requests.get(url, params=params, headers=headers, timeout=10)
            print(f"      HTTP 状态码: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"      响应数据: {data}")
                
                if data.get("code") == "200" and data.get("location"):
                    location_id = data["location"][0]["id"]
                    location_name = data["location"][0]["name"]
                    print(f"      ✅ 成功获取 Location ID: {location_id}")
                    break # 成功则停止尝试其他 URL
                else:
                    print(f"      ❌ 业务错误: {data.get('code')}")
            else:
                print(f"      ❌ 请求失败: {response.text[:100]}...")
                
        except Exception as e:
            print(f"      ❌ 发生异常: {e}")
            
    if not location_id:
        print("\n❌ GeoAPI 测试全部失败，无法进行后续测试。")
        return

    # 4. 测试 WeatherAPI
    print(f"\n🌤️ [Step 2] 测试 WeatherAPI (实时天气)...")
    weather_url = f"https://{api_host}/v7/weather/now"
    weather_params = {"location": location_id, "lang": "zh"}
    
    try:
        print(f"   请求 URL: {weather_url}")
        response = requests.get(weather_url, params=weather_params, headers=headers, timeout=10)
        print(f"   HTTP 状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   响应数据: {data}")
            
            if data.get("code") == "200":
                now = data.get("now", {})
                print(f"✅ WeatherAPI 成功! {location_name} 天气: {now.get('text')}, 温度: {now.get('temp')}°C")
            else:
                print(f"❌ WeatherAPI 业务错误: {data.get('code')}")
        else:
            print(f"❌ WeatherAPI 请求失败: {response.text}")
            
    except Exception as e:
        print(f"❌ 发生异常: {e}")

if __name__ == "__main__":
    diagnose()
