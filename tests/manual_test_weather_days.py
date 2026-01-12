import os
import sys
from dotenv import load_dotenv, find_dotenv

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.tools import get_weather

def test_weather_days():
    print("🌤️ 开始测试天气工具的多天预报功能...")
    
    # 加载环境变量
    load_dotenv(find_dotenv(), override=True)
    
    city = "上海"
    
    # 1. 测试实时天气 (days=0)
    print(f"\n[Test 1] 获取 {city} 实时天气 (days=0)")
    result_now = get_weather(city, days=0)
    print(result_now)
    if "实时天气" in result_now:
        print("✅ 实时天气测试通过")
    else:
        print("❌ 实时天气测试失败")

    # 2. 测试明天预报 (days=1)
    print(f"\n[Test 2] 获取 {city} 明天天气 (days=1)")
    result_tmr = get_weather(city, days=1)
    print(result_tmr)
    if "明天天气" in result_tmr:
        print("✅ 明天预报测试通过")
    else:
        print("❌ 明天预报测试失败")

    # 3. 测试后天预报 (days=2)
    print(f"\n[Test 3] 获取 {city} 后天天气 (days=2)")
    result_dat = get_weather(city, days=2)
    print(result_dat)
    if "后天天气" in result_dat:
        print("✅ 后天预报测试通过")
    else:
        print("❌ 后天预报测试失败")

if __name__ == "__main__":
    test_weather_days()
