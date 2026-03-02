#!/usr/bin/env python3
"""
OpenAI Agent SDK Demo - 天气工具

这是一个独立的 demo 脚本，用于测试 OpenAI Agent SDK + LiteLLM + 火山引擎 DeepSeek 的组合。
不影响现有代码，可以先体验效果再决定是否迁移。

使用方式：
1. 安装依赖：pip install "openai-agents[litellm]"
2. 确保环境变量已设置：VOLCENGINE_API_KEY, QWEATHER_API_KEY
3. 运行：python scripts/demo_openai_agent_sdk.py
"""

import os
import sys
import requests
from datetime import datetime

# 添加项目根目录到 Python 路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# 加载 .env 文件（关键！否则无法读取 QWEATHER_API_KEY 等配置）
from dotenv import load_dotenv
load_dotenv(os.path.join(project_root, ".env"))

# ============================================
# 1. 环境检查
# ============================================

print("=" * 60)
print("🔍 OpenAI Agent SDK Demo - 环境检查")
print("=" * 60)

# 检查必要的环境变量
volcengine_key = os.environ.get("VOLCENGINE_API_KEY")
qweather_key = os.environ.get("QWEATHER_API_KEY")

if not volcengine_key:
    print("❌ 请设置 VOLCENGINE_API_KEY 环境变量")
    sys.exit(1)
else:
    print(f"✅ VOLCENGINE_API_KEY 已设置 (前6位: {volcengine_key[:6]}...)")

if not qweather_key:
    print("⚠️ QWEATHER_API_KEY 未设置，天气功能将使用模拟数据")
else:
    print(f"✅ QWEATHER_API_KEY 已设置 (前6位: {qweather_key[:6]}...)")

# 尝试导入 OpenAI Agents SDK
try:
    from agents import Agent, Runner, function_tool
    print("✅ OpenAI Agents SDK 已安装")
except ImportError:
    print("❌ 请先安装 OpenAI Agents SDK:")
    print("   pip install \"openai-agents[litellm]\"")
    sys.exit(1)

# 尝试导入 LiteLLM
try:
    import litellm
    print("✅ LiteLLM 已安装")
except ImportError:
    print("❌ 请先安装 LiteLLM:")
    print("   pip install litellm")
    sys.exit(1)

print()

# ============================================
# 2. 配置 LiteLLM 使用火山引擎
# ============================================

print("=" * 60)
print("⚙️ 配置 LiteLLM + 火山引擎")
print("=" * 60)

# 配置 LiteLLM 环境
os.environ["LITELLM_LOG"] = "DEBUG"  # 可选：开启调试日志

# 火山引擎配置
VOLCENGINE_BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"
VOLCENGINE_MODEL = "deepseek-v3-1-terminus"

print(f"   Base URL: {VOLCENGINE_BASE_URL}")
print(f"   Model: {VOLCENGINE_MODEL}")
print()


# ============================================
# 3. 定义工具函数（使用 OpenAI SDK 的装饰器）
# ============================================

print("=" * 60)
print("🔧 定义工具函数")
print("=" * 60)


@function_tool
def get_weather(city: str, days: int = 0) -> str:
    """
    获取指定城市的天气信息。

    Args:
        city: 城市名称（中文，如"北京"、"上海"）
        days: 预报天数，0=实时天气，1=明天，2=后天

    Returns:
        天气信息的文本描述
    """
    print(f"   🌤️ [工具调用] get_weather(city={city}, days={days})")
    
    api_key = os.getenv("QWEATHER_API_KEY")
    api_host = os.getenv("QWEATHER_API_HOST", "devapi.qweather.com")
    
    if api_key:
        try:
            headers = {"X-QW-Api-Key": api_key}
            
            # GeoAPI URL 逻辑：
            # - 付费版 (如 pd4up4jrvp.re.qweatherapi.com): 使用 /geo/v2/city/lookup
            # - 免费版 (devapi.qweather.com): 使用 geoapi.qweather.com
            if "devapi.qweather.com" in api_host:
                geo_url = "https://geoapi.qweather.com/v2/city/lookup"
            else:
                # 付费版 API
                geo_url = f"https://{api_host}/geo/v2/city/lookup"
            
            print(f"   📍 GeoAPI URL: {geo_url}")
            geo_params = {"location": city, "number": 1}
            geo_response = requests.get(geo_url, params=geo_params, headers=headers, timeout=5)
            
            print(f"   📍 GeoAPI Response: {geo_response.status_code}")
            
            if geo_response.status_code == 200:
                geo_data = geo_response.json()
                print(f"   📍 GeoAPI Data: {geo_data.get('code')}")
                
                if geo_data.get("code") == "200" and geo_data.get("location"):
                    location_id = geo_data["location"][0]["id"]
                    location_name = geo_data["location"][0]["name"]
                    print(f"   📍 Location: {location_name} (ID: {location_id})")
                    
                    # 获取天气
                    if days == 0:
                        weather_url = f"https://{api_host}/v7/weather/now"
                        weather_params = {"location": location_id, "lang": "zh"}
                        weather_response = requests.get(weather_url, params=weather_params, headers=headers, timeout=5)
                        
                        print(f"   🌤️ WeatherAPI Response: {weather_response.status_code}")
                        
                        if weather_response.status_code == 200:
                            weather_data = weather_response.json()
                            if weather_data.get("code") == "200" and weather_data.get("now"):
                                now = weather_data["now"]
                                return f"""{location_name}实时天气：
温度：{now.get("temp", "未知")}°C（体感 {now.get("feelsLike", "未知")}°C）
天气：{now.get("text", "未知")}
湿度：{now.get("humidity", "未知")}%
风向：{now.get("windDir", "未知")} {now.get("windScale", "未知")}级"""
                    else:
                        weather_url = f"https://{api_host}/v7/weather/3d"
                        weather_params = {"location": location_id, "lang": "zh"}
                        weather_response = requests.get(weather_url, params=weather_params, headers=headers, timeout=5)
                        
                        if weather_response.status_code == 200:
                            weather_data = weather_response.json()
                            if weather_data.get("code") == "200" and weather_data.get("daily"):
                                if days < len(weather_data["daily"]):
                                    forecast = weather_data["daily"][days]
                                    date_str = ["今天", "明天", "后天"][min(days, 2)]
                                    return f"""{location_name}{date_str}天气预报：
温度：{forecast.get("tempMin", "未知")}°C ~ {forecast.get("tempMax", "未知")}°C
白天：{forecast.get("textDay", "未知")}
夜间：{forecast.get("textNight", "未知")}
湿度：{forecast.get("humidity", "未知")}%"""
        except Exception as e:
            print(f"   ⚠️ 和风天气 API 调用失败: {e}")
            import traceback
            traceback.print_exc()
    
    # 降级到模拟数据
    mock_weather = {
        "北京": {"temp": "25°C", "condition": "晴", "humidity": "45%"},
        "上海": {"temp": "28°C", "condition": "多云", "humidity": "65%"},
        "深圳": {"temp": "30°C", "condition": "炎热", "humidity": "75%"},
    }
    
    data = mock_weather.get(city, {"temp": "未知", "condition": "未知", "humidity": "未知"})
    return f"{city}天气（模拟数据）：温度 {data['temp']}，{data['condition']}，湿度 {data['humidity']}"


@function_tool
def get_current_time() -> str:
    """
    获取当前时间。

    Returns:
        当前时间的文本描述
    """
    print("   🕐 [工具调用] get_current_time()")
    now = datetime.now()
    weekday = ["一", "二", "三", "四", "五", "六", "日"][now.weekday()]
    return f"当前时间：{now.strftime('%Y年%m月%d日 %H:%M:%S')}（星期{weekday}）"


@function_tool
def get_air_quality(city: str) -> str:
    """
    获取指定城市的空气质量信息（AQI、PM2.5等）。

    Args:
        city: 城市名称（中文，如"北京"、"上海"）

    Returns:
        空气质量信息的文本描述
    """
    print(f"   🌫️ [工具调用] get_air_quality(city={city})")
    
    api_key = os.getenv("QWEATHER_API_KEY")
    api_host = os.getenv("QWEATHER_API_HOST", "devapi.qweather.com")
    
    if not api_key:
        return f"抱歉，空气质量查询需要配置 QWEATHER_API_KEY。"
    
    try:
        headers = {"X-QW-Api-Key": api_key}
        
        # GeoAPI
        if "devapi.qweather.com" in api_host:
            geo_url = "https://geoapi.qweather.com/v2/city/lookup"
        else:
            geo_url = f"https://{api_host}/geo/v2/city/lookup"
        
        geo_params = {"location": city, "number": 1}
        geo_response = requests.get(geo_url, params=geo_params, headers=headers, timeout=5)
        
        if geo_response.status_code == 200:
            geo_data = geo_response.json()
            if geo_data.get("code") == "200" and geo_data.get("location"):
                location_info = geo_data["location"][0]
                location_name = location_info["name"]
                latitude = location_info["lat"]
                longitude = location_info["lon"]
                
                print(f"   📍 Location: {location_name} ({latitude}, {longitude})")
                
                # 空气质量 API (v1)
                air_url = f"https://{api_host}/airquality/v1/current/{latitude}/{longitude}"
                air_response = requests.get(air_url, headers=headers, timeout=5)
                
                print(f"   🌫️ AirAPI Response: {air_response.status_code}")
                
                if air_response.status_code == 200:
                    air_data = air_response.json()
                    
                    # 解析
                    indexes = air_data.get("indexes", [])
                    index_data = {}
                    for idx in indexes:
                        if idx.get("code") == "chn-mee":
                            index_data = idx
                            break
                    if not index_data and indexes:
                        index_data = indexes[0]
                    
                    aqi = index_data.get("aqi", "未知")
                    category = index_data.get("category", "未知")
                    
                    # 提取 PM2.5
                    pm25 = "未知"
                    for p in air_data.get("pollutants", []):
                        if p.get("code", "").lower() in ["pm2p5", "pm25"]:
                            pm25 = p.get("concentration", {}).get("value", "未知")
                            break
                    
                    # 建议
                    advice = "请关注空气质量"
                    try:
                        aqi_num = int(aqi)
                        if aqi_num <= 50:
                            advice = "空气质量优秀，适合户外活动"
                        elif aqi_num <= 100:
                            advice = "空气质量良好"
                        elif aqi_num <= 150:
                            advice = "轻度污染，敏感人群注意"
                        elif aqi_num <= 200:
                            advice = "中度污染，减少户外活动"
                        else:
                            advice = "重度污染，避免户外活动"
                    except:
                        pass
                    
                    return f"""{location_name}空气质量：
AQI指数：{aqi}
等级：{category}
PM2.5：{pm25} μg/m³
建议：{advice}"""
    except Exception as e:
        print(f"   ⚠️ 空气质量 API 调用失败: {e}")
    
    return f"抱歉，无法获取{city}的空气质量信息。"


print("   ✅ get_weather - 获取天气信息")
print("   ✅ get_current_time - 获取当前时间")
print("   ✅ get_air_quality - 获取空气质量")
print()


# ============================================
# 4. 创建 Agent
# ============================================

print("=" * 60)
print("🤖 创建 Agent")
print("=" * 60)

# 创建模型配置
# 使用 LiteLLM 的 custom_llm_provider 支持火山引擎
from agents.extensions.models.litellm_model import LitellmModel

# 创建 LiteLLM 模型适配器
model = LitellmModel(
    model=f"openai/{VOLCENGINE_MODEL}",  # 使用 openai 兼容格式
    api_key=volcengine_key,
    base_url=VOLCENGINE_BASE_URL,
)

# 创建 Agent
agent = Agent(
    name="Neko-Demo",
    instructions="""你是一只温柔的台灯精灵，名字叫 Neko。
你的性格是温柔但坚定的，会用可爱的语气和用户交流。
当用户问天气时，使用 get_weather 工具获取天气信息，同时使用 get_air_quality 工具获取空气质量信息，两者一起告诉用户。
当用户问时间时，使用 get_current_time 工具获取信息。
回答要简洁、亲切，带有一点可爱的语气。""",
    model=model,
    tools=[get_weather, get_current_time, get_air_quality],
)

print(f"   Agent 名称: {agent.name}")
print(f"   可用工具: {[t.name for t in agent.tools]}")
print()


# ============================================
# 5. 运行测试
# ============================================

print("=" * 60)
print("🧪 运行测试")
print("=" * 60)

test_queries = [
    "北京今天天气怎么样？",  # 应该同时调用天气和空气质量
    "现在几点了？",
]

for i, query in enumerate(test_queries, 1):
    print(f"\n--- 测试 {i}: {query} ---")
    print()
    
    try:
        # 使用 OpenAI Agent SDK 运行
        result = Runner.run_sync(agent, query)
        
        # 输出结果
        print(f"📣 Neko 回复:")
        print("-" * 40)
        
        # 获取最终输出
        if hasattr(result, 'final_output'):
            print(result.final_output)
        elif hasattr(result, 'messages'):
            for msg in result.messages:
                if hasattr(msg, 'content') and msg.content:
                    print(msg.content)
        else:
            print(result)
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
    
    print()

print("=" * 60)
print("✅ Demo 完成！")
print("=" * 60)
print()
print("📊 对比总结：")
print("   - OpenAI SDK 自动处理了工具调用的调度")
print("   - 无需手写 tool_node 的循环和匹配逻辑")
print("   - 工具定义更简洁（@function_tool 装饰器）")
print()
print("💡 如果效果满意，可以考虑逐步迁移其他工具")
