# tools.py - 外部工具定义
# 为 Neko-Light 提供联网和外部服务能力

import requests
import json
import time
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import os

# Web Search 使用百度智能云AI搜索API（国内服务，访问稳定）


# === 工具函数定义 ===

def get_weather(city: str = "北京", days: int = 0) -> str:
    """
    获取天气信息
    优先使用和风天气API，如果未配置则使用模拟数据
    支持 V2 规范：个性化 Host + Header 鉴权
    
    Args:
        city: 城市名称（中文）
        days: 预报天数，0=实时天气，1=明天，2=后天，以此类推
    """
    try:
        # 优先使用和风天气 API
        # 注册地址：https://dev.qweather.com/
        api_key = os.getenv("QWEATHER_API_KEY")
        # 支持 V2：自定义 API Host，默认为免费版域名
        api_host = os.getenv("QWEATHER_API_HOST", "devapi.qweather.com")
        
        if api_key:
            # 鉴权 Headers (V2 推荐)
            headers = {
                "X-QW-Api-Key": api_key
            }
            
            # 步骤1：通过GeoAPI获取LocationID
            # 尝试使用配置的 Host (新版 GeoAPI 路径为 /geo/v2/city/lookup)
            # 假设新版 API 下 Geo 接口为 /geo/v2/city/lookup
            geo_url = f"https://{api_host}/geo/v2/city/lookup"
            geo_params = {
                "location": city,
                "number": 1
            }
            
            # 兼容旧版：如果 host 是 devapi.qweather.com，GeoAPI 仍在 geoapi.qweather.com 且无 /geo 前缀
            # 但为了统一逻辑，我们先试配置的 Host。如果用户配置了 devapi，可能需要特殊处理。
            if "devapi.qweather.com" in api_host:
                geo_url = "https://geoapi.qweather.com/v2/city/lookup"
            
            # 发起 Geo 请求
            # 注意：requests.get 会自动处理 gzip 解压
            geo_response = requests.get(geo_url, params=geo_params, headers=headers, timeout=5)
            
            if geo_response.status_code != 200:
                print(f"[WARN] GeoAPI HTTP错误: {geo_response.status_code} - {geo_response.text}")
                # 尝试备用 Geo Host (如果首选失败且不是 404/403 等业务明确拒绝)
                if api_host != "geoapi.qweather.com" and "devapi" not in api_host:
                    print("   尝试回退到通用 GeoAPI Host...")
                    fallback_url = "https://geoapi.qweather.com/v2/city/lookup"
                    geo_response = requests.get(fallback_url, params=geo_params, headers=headers, timeout=5)

            if geo_response.status_code == 200:
                geo_data = geo_response.json()
                
                if geo_data.get("code") != "200":
                     print(f"[WARN] GeoAPI 业务错误: {geo_data.get('code')} - {geo_data}")
                
                if geo_data.get("code") == "200" and geo_data.get("location"):
                    location_id = geo_data["location"][0]["id"]
                    location_name = geo_data["location"][0]["name"]
                    
                    # 步骤2：根据days参数决定调用哪个API
                    # 确保 days 参数被正确转换为整数
                    try:
                        days = int(days)
                    except ValueError:
                        days = 0

                    if days == 0:
                        # 实时天气
                        weather_url = f"https://{api_host}/v7/weather/now"
                        weather_params = {
                            "location": location_id,
                            "lang": "zh"
                        }
                        
                        weather_response = requests.get(weather_url, params=weather_params, headers=headers, timeout=5)
                        
                        if weather_response.status_code != 200:
                            print(f"[WARN] WeatherAPI HTTP错误: {weather_response.status_code} - {weather_response.text}")

                        if weather_response.status_code == 200:
                            weather_data = weather_response.json()
                            
                            if weather_data.get("code") != "200":
                                print(f"[WARN] WeatherAPI 业务错误: {weather_data.get('code')} - {weather_data}")

                            if weather_data.get("code") == "200" and weather_data.get("now"):
                                now = weather_data["now"]
                                
                                temp = now.get("temp", "未知")
                                feels_like = now.get("feelsLike", temp)
                                condition = now.get("text", "未知")
                                humidity = now.get("humidity", "未知")
                                wind_dir = now.get("windDir", "未知")
                                wind_scale = now.get("windScale", "未知")
                                wind_speed = now.get("windSpeed", "未知")
                                
                                # 生成建议
                                advice = ""
                                try:
                                    temp_num = float(temp)
                                    if temp_num > 30:
                                        advice = "天气炎热，注意防暑降温"
                                    elif temp_num < 5:
                                        advice = "天气较冷，注意保暖"
                                    elif "雨" in condition:
                                        advice = "有降雨，记得带伞"
                                    elif "晴" in condition:
                                        advice = "天气不错，适合外出"
                                    else:
                                        advice = "天气适宜"
                                except:
                                    advice = "天气适宜"
                                
                                result = f"""{location_name}实时天气：
温度：{temp}°C（体感 {feels_like}°C）
天气：{condition}
湿度：{humidity}%
风向：{wind_dir} {wind_scale}级
风速：{wind_speed} km/h
建议：{advice}"""
                                
                                print(f"获取天气（和风天气-实时）: {location_name}")
                                return result
                    else:
                        # 未来天气预报（3天预报）
                        # 使用新版 Host
                        weather_url = f"https://{api_host}/v7/weather/3d"
                        weather_params = {
                            "location": location_id,
                            "lang": "zh"
                        }
                        
                        weather_response = requests.get(weather_url, params=weather_params, headers=headers, timeout=5)

                        if weather_response.status_code != 200:
                            print(f"[WARN] WeatherAPI HTTP错误: {weather_response.status_code} - {weather_response.text}")
                        
                        if weather_response.status_code == 200:
                            weather_data = weather_response.json()

                            if weather_data.get("code") != "200":
                                print(f"[WARN] WeatherAPI 业务错误: {weather_data.get('code')} - {weather_data}")
                            
                            if weather_data.get("code") == "200" and weather_data.get("daily"):
                                daily_list = weather_data["daily"]
                                
                                # 获取指定天数的预报（days=1表示明天，即列表中的第二个元素）
                                # daily[0]=今天, daily[1]=明天, daily[2]=后天
                                target_index = days 
                                
                                if target_index < len(daily_list):
                                    forecast = daily_list[target_index]  # 索引从0开始
                                    
                                    fx_date = forecast.get("fxDate", "")
                                    temp_max = forecast.get("tempMax", "未知")
                                    temp_min = forecast.get("tempMin", "未知")
                                    text_day = forecast.get("textDay", "未知")
                                    text_night = forecast.get("textNight", "未知")
                                    wind_dir_day = forecast.get("windDirDay", "未知")
                                    wind_scale_day = forecast.get("windScaleDay", "未知")
                                    humidity = forecast.get("humidity", "未知")
                                    precip = forecast.get("precip", "0.0")
                                    
                                    # 格式化日期
                                    date_str = "明天"
                                    if days == 2:
                                        date_str = "后天"
                                    elif days > 2:
                                        try:
                                            from datetime import datetime
                                            date_obj = datetime.strptime(fx_date, "%Y-%m-%d")
                                            date_str = date_obj.strftime("%m月%d日")
                                        except:
                                            date_str = fx_date
                                    else:
                                        # 如果是今天但传了days参数
                                        if days == 0:
                                            date_str = "今天"
                                    
                                    # 生成建议
                                    advice = ""
                                    try:
                                        temp_max_num = float(temp_max)
                                        if temp_max_num > 30:
                                            advice = "天气炎热，注意防暑降温"
                                        elif temp_max_num < 5:
                                            advice = "天气较冷，注意保暖"
                                        elif float(precip) > 0:
                                            advice = "有降雨，记得带伞"
                                        elif "晴" in text_day:
                                            advice = "天气不错，适合外出"
                                        else:
                                            advice = "天气适宜"
                                    except:
                                        advice = "天气适宜"
                                    
                                    result = f"""{location_name}{date_str}天气预报：
温度：{temp_min}°C ~ {temp_max}°C
白天：{text_day}
夜间：{text_night}
湿度：{humidity}%
风向：{wind_dir_day} {wind_scale_day}级
降水：{precip}mm
建议：{advice}"""
                                    
                                    print(f"获取天气（和风天气-{date_str}）: {location_name}")
                                    return result
                                else:
                                    return f"抱歉，无法获取{days}天后的天气预报（最多支持3天）"
            
            # 如果API调用失败，降级到模拟数据
            print(f"[WARN] 和风天气API调用失败，使用模拟数据")
        else:
            print("[WARN] 未配置 QWEATHER_API_KEY，使用模拟天气数据")
        
        # 降级方案：使用模拟数据
        mock_weather = {
            "北京": {
                "temperature": "25°C",
                "condition": "晴",
                "humidity": "45%",
                "wind": "3级",
                "advice": "天气不错，适合外出"
            },
            "上海": {
                "temperature": "28°C",
                "condition": "多云",
                "humidity": "65%",
                "wind": "2级",
                "advice": "湿度稍高，注意补水"
            },
            "深圳": {
                "temperature": "30°C",
                "condition": "炎热",
                "humidity": "75%",
                "wind": "1级",
                "advice": "天气炎热，注意防晒"
            }
        }

        # 获取城市天气
        weather_data = mock_weather.get(city, {
            "temperature": "未知",
            "condition": "未知",
            "humidity": "未知",
            "wind": "未知",
            "advice": f"{city}天气查询服务暂不可用（模拟数据）"
        })

        result = f"""{city}天气（模拟数据）：
温度：{weather_data['temperature']}
天气：{weather_data['condition']}
湿度：{weather_data['humidity']}
风力：{weather_data['wind']}
建议：{weather_data['advice']}"""

        print(f"获取天气（模拟）: {city}")
        return result

    except Exception as e:
        print(f"[ERROR] 天气查询失败: {e}")
        return f"抱歉，获取{city}天气信息失败了：{str(e)}"


def get_air_quality(city: str = "北京", days: int = 0) -> str:
    """
    获取空气质量信息
    使用和风天气 API v1 版本（新版，使用经纬度查询）
    
    Args:
        city: 城市名称（中文）
        days: 预报天数，0=实时空气质量，1-3=未来预报
    """
    try:
        api_key = os.getenv("QWEATHER_API_KEY")
        api_host = os.getenv("QWEATHER_API_HOST", "devapi.qweather.com")
        
        if not api_key:
            return f"抱歉，空气质量查询需要配置 QWEATHER_API_KEY 环境变量。"
        
        headers = {"X-QW-Api-Key": api_key}
        
        # 步骤1：通过 GeoAPI 获取城市的经纬度
        if "devapi.qweather.com" in api_host:
            geo_url = "https://geoapi.qweather.com/v2/city/lookup"
        else:
            geo_url = f"https://{api_host}/geo/v2/city/lookup"
        
        geo_params = {"location": city, "number": 1}
        geo_response = requests.get(geo_url, params=geo_params, headers=headers, timeout=5)
        
        if geo_response.status_code != 200:
            print(f"[WARN] GeoAPI HTTP错误: {geo_response.status_code}")
            return f"抱歉，无法获取{city}的位置信息。"
        
        geo_data = geo_response.json()
        if geo_data.get("code") != "200" or not geo_data.get("location"):
            print(f"[WARN] GeoAPI 业务错误: {geo_data.get('code')}")
            return f"抱歉，无法找到城市：{city}"
        
        location_info = geo_data["location"][0]
        location_name = location_info["name"]
        location_id = location_info["id"]  # 城市 ID，用于旧版 API
        latitude = location_info["lat"]
        longitude = location_info["lon"]
        
        print(f"城市定位: {location_name} (ID:{location_id}, {latitude}, {longitude})")
        
        # 步骤2：使用新版 API v1 获取空气质量（使用经纬度）
        try:
            days = int(days)
        except ValueError:
            days = 0
        
        if days == 0:
            # 实时空气质量 - 新版 API 路径
            air_url = f"https://{api_host}/airquality/v1/current/{latitude}/{longitude}"
            
            air_response = requests.get(air_url, headers=headers, timeout=5)
            
            if air_response.status_code != 200:
                print(f"[WARN] AirAPI v1 HTTP错误: {air_response.status_code} - {air_response.text[:200]}")
                return f"抱歉，获取空气质量信息失败（HTTP {air_response.status_code}）。"
            
            air_data = air_response.json()
            
            # 新版 API 响应结构：indexes + pollutants
            if "error" in air_data:
                print(f"[WARN] AirAPI v1 业务错误: {air_data}")
                return f"抱歉，获取空气质量信息失败。"
            
            # 解析新版 API 响应 - 从 indexes 数组获取 AQI
            indexes = air_data.get("indexes", [])
            index_data = {}
            # 优先使用中国标准 (chn-mee)，否则用第一个
            for idx in indexes:
                if idx.get("code") == "chn-mee":
                    index_data = idx
                    break
            if not index_data and indexes:
                index_data = indexes[0]
            
            pollutants = air_data.get("pollutants", [])  # 注意是 pollutants
            
            aqi = index_data.get("aqi", "未知")
            category = index_data.get("category", "未知")  # 如 "Good", "Moderate"
            
            # 提取污染物数据
            pm25 = "未知"
            pm10 = "未知"
            no2 = "未知"
            so2 = "未知"
            co = "未知"
            o3 = "未知"
            primary = "无"
            
            for p in pollutants:
                code = p.get("code", "").lower()
                value = p.get("concentration", {}).get("value", "未知")
                if code == "pm2p5" or code == "pm25":
                    pm25 = value
                elif code == "pm10":
                    pm10 = value
                elif code == "no2":
                    no2 = value
                elif code == "so2":
                    so2 = value
                elif code == "co":
                    co = value
                elif code == "o3":
                    o3 = value
            
            # 查找主要污染物
            if index_data.get("primaryPollutant"):
                primary_code = index_data["primaryPollutant"].get("code", "")
                primary = primary_code.upper() if primary_code else "无"
            
            # 生成建议
            advice = ""
            try:
                aqi_num = int(aqi)
                if aqi_num <= 50:
                    advice = "空气质量优秀，适合户外活动"
                elif aqi_num <= 100:
                    advice = "空气质量良好，可以正常户外活动"
                elif aqi_num <= 150:
                    advice = "轻度污染，敏感人群减少户外活动"
                elif aqi_num <= 200:
                    advice = "中度污染，建议减少户外活动"
                elif aqi_num <= 300:
                    advice = "重度污染，避免户外活动"
                else:
                    advice = "严重污染，应留在室内"
            except:
                advice = "请关注空气质量变化"
            
            result = f"""{location_name}实时空气质量：
空气质量指数(AQI)：{aqi}
空气质量等级：{category}
主要污染物：{primary if primary and primary != "-" else "无"}
PM2.5：{pm25} μg/m³
PM10：{pm10} μg/m³
NO₂：{no2} μg/m³
SO₂：{so2} μg/m³
CO：{co} mg/m³
O₃：{o3} μg/m³
建议：{advice}"""
            
            print(f"🌫️ 获取空气质量（和风天气v1-实时）: {location_name}")
            return result
        
        else:
            # 未来空气质量预报 - 使用旧版 v7 API（免费版支持）
            # 注意：新版 v1 预报 API 免费版不可用，需要用旧版
            air_url = f"https://{api_host}/v7/air/5d"
            air_params = {"location": location_id, "lang": "zh"}
            
            air_response = requests.get(air_url, params=air_params, headers=headers, timeout=5)
            
            if air_response.status_code != 200:
                print(f"[WARN] AirAPI v7 Daily HTTP错误: {air_response.status_code}")
                return f"抱歉，暂时无法获取空气质量预报，可以先看看现在的空气质量哦~"
            
            air_data = air_response.json()
            
            if air_data.get("code") != "200" or not air_data.get("daily"):
                print(f"[WARN] AirAPI v7 Daily 业务错误: {air_data.get('code')}")
                return f"抱歉，暂时无法获取空气质量预报，可以先看看现在的空气质量哦~"
            
            daily_list = air_data["daily"]
            
            # 确保 days 不超过预报范围
            if days >= len(daily_list):
                days = len(daily_list) - 1
                print(f"[WARN] 预报天数超限，调整为 {days}")
            
            forecast = daily_list[days]
            
            fx_date = forecast.get("fxDate", "")
            aqi = forecast.get("aqi", "未知")
            category = forecast.get("category", "未知")
            primary = forecast.get("primary", "无")
            
            # 格式化日期
            date_str = "明天"
            if days == 0:
                date_str = "今天"
            elif days == 2:
                date_str = "后天"
            elif days > 2:
                try:
                    date_obj = datetime.strptime(fx_date, "%Y-%m-%d")
                    date_str = date_obj.strftime("%m月%d日")
                except:
                    date_str = fx_date
            
            # 生成建议
            advice = ""
            try:
                aqi_num = int(aqi)
                if aqi_num <= 50:
                    advice = "空气质量优秀，适合户外活动"
                elif aqi_num <= 100:
                    advice = "空气质量良好，可以正常户外活动"
                elif aqi_num <= 150:
                    advice = "轻度污染，敏感人群减少户外活动"
                elif aqi_num <= 200:
                    advice = "中度污染，建议减少户外活动"
                else:
                    advice = "空气质量较差，建议减少户外活动"
            except:
                advice = "请关注空气质量变化"
            
            result = f"""{location_name}{date_str}空气质量预报：
空气质量指数(AQI)：{aqi}
空气质量等级：{category}
主要污染物：{primary if primary and primary != "-" else "无"}
建议：{advice}"""
            
            print(f"🌫️ 获取空气质量（和风天气v7-{date_str}）: {location_name}")
            return result
    
    except Exception as e:
        print(f"[ERROR] 空气质量查询失败: {e}")
        import traceback
        traceback.print_exc()
        return f"抱歉，获取{city}空气质量信息失败了：{str(e)}"


def get_news(keyword: str = "", category: str = "", limit: int = 5, use_doubao_summary: bool = True) -> str:
    """
    获取新闻信息 - 直接使用百度搜索 API
    无需维护 RSS 源，稳定可靠
    
    Args:
        keyword: 搜索关键词（如"人工智能"、"特斯拉"）
        category: 新闻分类（tech/sports/entertainment/finance/general）
        limit: 返回条数（默认5条）
        use_doubao_summary: 是否使用豆包生成摘要（默认True）
    """
    try:
        # 构建搜索查询
        category_map = {
            "tech": "科技",
            "sports": "体育",
            "entertainment": "娱乐",
            "finance": "财经",
            "general": "时事",
        }
        
        # 组合搜索词
        search_parts = []
        if category and category in category_map:
            search_parts.append(category_map[category])
        if keyword:
            # 如果 keyword 和 category 重复，只保留 keyword
            if keyword not in category_map.get(category, ""):
                search_parts.append(keyword)
        
        # 如果没有任何条件，默认搜索热点新闻
        if not search_parts:
            search_parts = ["今日热点新闻"]
        
        search_query = " ".join(search_parts) + " 最新新闻"
        
        print(f"获取新闻: category='{category}', keyword='{keyword}' -> 搜索: '{search_query}'")
        
        # 调用 web_search 获取新闻
        result = web_search(search_query, max_results=limit)
        
        # 如果搜索成功且启用了豆包摘要，使用豆包生成摘要
        if result and "搜索结果" in result and use_doubao_summary:
            try:
                print(f"   [豆包摘要] 使用豆包生成新闻摘要...")
                
                # 导入豆包模型
                from .model_manager import get_model_manager
                
                model_manager = get_model_manager()
                chat_llm = model_manager.chat_llm  # 使用豆包 1.5 Pro
                
                # 构建摘要 prompt
                summary_prompt = f"""你是一个新闻助手。请根据以下搜索到的新闻内容，为用户生成一个简洁明了的中文摘要（100-200字），回答用户关于"{keyword}"的问题。

新闻内容:
{result}

请生成摘要："""

                # 调用豆包生成摘要
                response = chat_llm.invoke(summary_prompt)
                summary = response.content.strip()
                
                print(f"   [豆包摘要] 生成成功，摘要长度: {len(summary)} 字")
                
                # 返回豆包生成的摘要
                return f"📰 **{keyword}** 相关新闻摘要：\n\n{summary}\n\n---\n*信息来源：网络搜索*"
                
            except Exception as e:
                print(f"   [豆包摘要] 生成失败: {e}，回退到原始搜索结果")
                # 如果豆包摘要失败，回退到原始搜索结果
                pass
        
        # 如果搜索成功，美化输出格式
        if result and "搜索结果" in result:
            # 替换标题前缀
            header = f"最新新闻"
            if category and category in category_map:
                header += f"【{category_map[category]}】"
            if keyword and keyword not in category_map.get(category, ""):
                header += f"（{keyword}）"
            header += "：\n"
            
            # 将 web_search 结果的标题替换
            result = result.replace(f"搜索结果（{search_query}）：", header)
        
        return result

    except Exception as e:
        print(f"[ERROR] 新闻查询失败: {e}")
        return f"抱歉，获取新闻信息失败了：{str(e)}"


def get_time_info(timezone: str = "北京") -> str:
    """
    获取时间信息
    """
    try:
        now = datetime.now()

        if timezone == "北京":
            time_str = now.strftime("%Y年%m月%d日 %H:%M:%S")
            weekday = ["一", "二", "三", "四", "五", "六", "日"][now.weekday()]
            result = f"🕐 北京时间：{time_str}（星期{weekday}）"
        elif timezone == "纽约":
            # 简单时区转换（实际应该使用pytz库）
            ny_time = now - timedelta(hours=14)  # 简化为固定时差
            time_str = ny_time.strftime("%Y-%m-%d %H:%M:%S")
            result = f"🕐 纽约时间：{time_str}"
        elif timezone == "伦敦":
            london_time = now - timedelta(hours=8)
            time_str = london_time.strftime("%Y-%m-%d %H:%M:%S")
            result = f"🕐 伦敦时间：{time_str}"
        else:
            result = f"🕐 当前时间：{now.strftime('%Y-%m-%d %H:%M:%S')}（{timezone}时区暂不支持）"

        print(f"🕐 获取时间: {timezone}")
        return result

    except Exception as e:
        print(f"[ERROR] 时间查询失败: {e}")
        # P0 Backup: 使用系统时间作为硬备份
        try:
            now = datetime.now()
            time_str = now.strftime("%Y年%m月%d日 %H:%M:%S")
            weekday = ["一", "二", "三", "四", "五", "六", "日"][now.weekday()]
            print(f"   使用系统时间硬备份: {time_str}")
            return f"🕐 当前时间：{time_str}（星期{weekday}）"
        except Exception as backup_error:
            # 最后的硬备份：即使datetime.now()也失败（几乎不可能）
            print(f"[WARN] 系统时间硬备份也失败: {backup_error}")
            return "🕐 抱歉，无法获取准确时间"


def calculate_math(expression: str) -> str:
    """
    数学计算工具
    """
    try:
        # 移除危险字符，只允许基本数学运算
        safe_chars = "0123456789+-*/(). "
        if not all(c in safe_chars for c in expression):
            return "抱歉，只支持基本的数学运算。"

        # 使用eval执行计算（在受控环境中）
        result = eval(expression, {"__builtins__": {}})

        print(f"🧮 数学计算: {expression} = {result}")
        return f"🧮 计算结果：{expression} = {result}"

    except Exception as e:
        print(f"[ERROR] 数学计算失败: {e}")
        return f"抱歉，无法计算 '{expression}'。请检查表达式是否正确。"


def search_wikipedia(query: str) -> str:
    """
    维基百科搜索（模拟）
    """
    try:
        # 模拟维基百科搜索结果
        mock_results = {
            "人工智能": "人工智能（Artificial Intelligence，AI）是指由人类制造的机器所展现出来的智能。通常，人工智能是指通过普通计算机程序来呈现人类智能的技术。",
            "机器学习": "机器学习（Machine Learning）是人工智能的一个分支，它使用算法和统计模型让计算机在数据中学习，而无需显式编程。",
            "深度学习": "深度学习（Deep Learning）是机器学习的一个子领域，使用多层神经网络来模拟人脑的学习过程。",
        }

        result = mock_results.get(query, f"关于'{query}'的维基百科信息暂不可用。")
        print(f"📖 维基搜索: {query}")
        return f"📖 维基百科：{query}\n{result}"

    except Exception as e:
        print(f"[ERROR] 维基搜索失败: {e}")
        return "抱歉，维基百科搜索失败了。"


def web_search(query: str, max_results: int = 5) -> str:
    """
    网络搜索工具 - 使用百度智能云AI搜索API
    获取互联网上的实时信息（国内服务，访问稳定）
    
    每日免费额度：100次
    API文档：https://cloud.baidu.com/doc/apiguide/index.html
    """
    try:
        # 获取 API Key（从环境变量）
        api_key = os.getenv("BAIDU_SEARCH_API_KEY")
        if not api_key:
            return "抱歉，网络搜索功能需要配置 BAIDU_SEARCH_API_KEY 环境变量。\n" \
                   "请访问 https://cloud.baidu.com/ 获取 API Key（每日免费100次）。\n" \
                   "获取方式：登录百度智能云 -> 千帆平台 -> 创建应用 -> 获取 API Key"
        
        # 百度智能云AI搜索API端点
        search_url = "https://qianfan.baidubce.com/v2/ai_search/web_search"
        
        # 构建请求头
        headers = {
            "X-Appbuilder-Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        # 构建请求体（根据API文档）
        # 限制max_results在合理范围内（网页top_k最大50）
        top_k = min(max_results, 50)
        
        payload = {
            "messages": [
                {
                    "content": query,
                    "role": "user"
                }
            ],
            "search_source": "baidu_search_v2",
            "resource_type_filter": [
                {
                    "type": "web",
                    "top_k": top_k
                }
            ]
        }
        
        print(f"网络搜索: {query}")
        
        # 发送请求
        response = requests.post(
            search_url,
            headers=headers,
            json=payload,
            timeout=30
        )
        
        # 检查响应状态
        if response.status_code != 200:
            error_info = response.text
            try:
                error_json = response.json()
                error_msg = error_json.get("message", error_info)
                error_code = error_json.get("code", response.status_code)
            except:
                error_msg = error_info
                error_code = response.status_code
            
            print(f"[ERROR] 网络搜索API错误: HTTP {response.status_code}, Code: {error_code}, Message: {error_msg}")
            
            if response.status_code == 401 or "Authentication" in error_msg:
                return "抱歉，网络搜索 API Key 无效或已过期。请检查 BAIDU_SEARCH_API_KEY 环境变量。"
            elif "quota" in error_msg.lower() or "limit" in error_msg.lower():
                return "抱歉，网络搜索已达到使用限额（每日免费100次）。请稍后再试或升级 API 套餐。"
            else:
                return f"抱歉，网络搜索请求失败（HTTP {response.status_code}）：{error_msg}"
        
        # 解析响应
        result = response.json()
        
        # 检查是否有错误码
        if "code" in result and result["code"] != "200":
            error_msg = result.get("message", "未知错误")
            return f"抱歉，网络搜索API返回错误：{error_msg}"
        
        # 提取搜索结果
        references = result.get("references", [])
        
        if not references:
            return f"抱歉，没有找到关于'{query}'的相关信息。"
        
        # 格式化结果（限制返回数量）
        formatted_results = []
        for ref in references[:max_results]:
            title = ref.get("title", "无标题")
            url = ref.get("url", "")
            content = ref.get("content", "")
            date = ref.get("date", "")
            
            # 构建格式化结果
            result_item = f"Title: {title}\nURL: {url}"
            if content:
                result_item += f"\nContent: {content}"
            if date:
                result_item += f"\nDate: {date}"
            
            formatted_results.append(result_item)
        
        results_text = "\n\n".join(formatted_results)
        return f"搜索结果（{query}）：\n\n{results_text}"
        
    except requests.exceptions.Timeout:
        print(f"[ERROR] 网络搜索超时")
        return "抱歉，网络搜索请求超时，请稍后再试。"
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] 网络搜索网络错误: {e}")
        return f"抱歉，网络搜索网络请求失败：{str(e)}"
    except json.JSONDecodeError as e:
        print(f"[ERROR] 网络搜索响应解析失败: {e}")
        return "抱歉，网络搜索响应格式错误，请稍后再试。"
    except Exception as e:
        print(f"[ERROR] 网络搜索失败: {e}")
        return f"抱歉，网络搜索失败了：{str(e)}"


# === LangChain 工具注册 ===

from langchain_core.tools import tool

@tool
def weather_tool(city: str, days: int = 0) -> str:
    """
    获取指定城市的天气信息
    
    Args:
        city: 城市名称（中文，如"北京"、"上海"）
        days: 预报天数，0=实时天气，1=明天，2=后天，3=3天后（最多3天）
    """
    return get_weather(city, days)

@tool
def air_quality_tool(city: str, days: int = 0) -> str:
    """
    获取指定城市的空气质量信息（AQI、PM2.5、PM10等）
    
    Args:
        city: 城市名称（中文，如"北京"、"上海"）
        days: 预报天数，0=实时空气质量，1=明天，2=后天（最多5天）
    """
    return get_air_quality(city, days)

@tool
def news_tool(keyword: str = "", category: str = "", limit: int = 5, use_doubao_summary: bool = True) -> str:
    """
    获取最新新闻信息
    
    Args:
        keyword: 搜索关键词（如"人工智能"、"特斯拉"、"NBA"）
        category: 新闻分类，可选值：tech(科技), sports(体育), entertainment(娱乐), finance(财经), general(时事)
        limit: 返回条数，默认5条
        use_doubao_summary: 是否使用豆包生成摘要（默认True），使用后可跳过后续的reasoning节点
    """
    return get_news(keyword, category, limit, use_doubao_summary)

@tool
def time_tool(timezone: str = "北京") -> str:
    """获取指定时区的时间信息"""
    return get_time_info(timezone)

@tool
def calculator_tool(expression: str) -> str:
    """执行数学计算"""
    return calculate_math(expression)

@tool
def wikipedia_tool(query: str) -> str:
    """在维基百科中搜索信息"""
    return search_wikipedia(query)

@tool
def web_search_tool(query: str, max_results: int = 5) -> str:
    """在互联网上搜索实时信息，获取最新的网络内容"""
    return web_search(query, max_results)

@tool
def update_profile_tool(updates: str) -> str:
    """
    更新用户画像的结构化信息（RAM）。
    
    Args:
        updates: JSON 格式的更新内容字符串。
                 例如: '{"home_city": "上海", "current_location": "北京"}'
                 支持字段: name, home_city, current_location, core_preferences
    """
    try:
        data = json.loads(updates)
    except json.JSONDecodeError:
        return "错误：updates 参数必须是有效的 JSON 字符串"

    if not isinstance(data, dict):
        return "错误：updates 解析后必须是字典"

    from .nodes import get_memory_manager
    manager = get_memory_manager()
    
    # 直接传递字典给 manager.update_profile，manager 会负责校验字段
    manager.update_profile(data)
    return f"已更新用户画像: {data}"

@tool
def query_user_memory_tool(query: str, max_results: int = 3) -> str:
    """
    检索用户的长期记忆（非结构化的过往经历、琐碎偏好等）。
    适用于回答"我以前说过什么"、"我上次去了哪里"等问题。
    """
    from nodes import get_memory_manager
    manager = get_memory_manager()
    # 注意：history 将由 tool_node 自动注入到 manager，此处仅传递 query
    docs = manager.retrieve_user_memory(query, k=max_results)
    if not docs:
        return "未找到相关记忆"
    
    # 增加时间戳显示 [YYYY-MM-DD]
    results = []
    for doc in docs:
        date_str = doc.metadata.get("date", "未知日期")[:10]  # 只取 YYYY-MM-DD
        results.append(f"- [{date_str}] {doc.page_content}")
        
    return "\n".join(results)

@tool
def save_user_memory_tool(content: str, category: str = "general") -> str:
    """
    保存新的非结构化用户记忆（如"用户喜欢吃辣"、"用户昨天去了公园"）。
    """
    from nodes import get_memory_manager
    manager = get_memory_manager()
    success = manager.save_user_memory(content, metadata={"category": category})
    return "记忆已保存" if success else "记忆保存失败"

@tool
def create_schedule_tool(
    title: str,
    datetime_ts: float,
    schedule_type: str = "reminder",
    reminder_minutes: int = None,
    description: str = "",
    recurrence_type: str = None,
    recurrence_value: int = None
) -> str:
    """
    创建日程、提醒、待办事项或注意事项。支持循环事件。
    
    Args:
        title: 标题
        datetime_ts: 时间戳（Unix timestamp），循环事件为首次发生时间
        schedule_type: 类型 "schedule" | "reminder" | "todo" | "note"
        reminder_minutes: 提前提醒分钟数（仅 schedule 有效，默认15）
        description: 描述（可选）
        recurrence_type: 循环类型 "daily" | "weekly" | "monthly" | "yearly" | None
        recurrence_value: 循环值：weekly时为周几(0=周一,6=周日)，monthly时为每月几号(1-31)，yearly时不需要此参数
    """
    from .schedule_manager import get_schedule_manager
    manager = get_schedule_manager()
    
    # 根据类型设置默认 reminder_minutes
    if schedule_type == "schedule":
        reminder_minutes = reminder_minutes if reminder_minutes is not None else 15
    else:
        reminder_minutes = 0
    
    # 构建 recurrence 字典
    recurrence = None
    if recurrence_type:
        recurrence = {
            "type": recurrence_type,
            "interval": 1
        }
        if recurrence_type == "weekly" and recurrence_value is not None:
            recurrence["days_of_week"] = [recurrence_value]
        elif recurrence_type == "monthly" and recurrence_value is not None:
            recurrence["day_of_month"] = recurrence_value
    
    item = manager.add_schedule(title, datetime_ts, schedule_type, reminder_minutes, description, recurrence)
    
    time_str = datetime.fromtimestamp(datetime_ts).strftime("%Y-%m-%d %H:%M") if datetime_ts else "无"
    recurrence_str = ""
    if recurrence:
        if recurrence_type == "daily":
            recurrence_str = " (每天循环)"
        elif recurrence_type == "weekly":
            weekday_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
            day_name = weekday_names[recurrence_value] if recurrence_value is not None else ""
            recurrence_str = f" (每{day_name}循环)"
        elif recurrence_type == "monthly":
            recurrence_str = f" (每月{recurrence_value}号循环)"
        elif recurrence_type == "yearly":
            # yearly 类型使用 datetime_ts 的月份和日期
            date_obj = datetime.fromtimestamp(datetime_ts)
            recurrence_str = f" (每年{date_obj.month}月{date_obj.day}号循环)"
    return f"已创建{schedule_type}: {title}, 时间: {time_str}{recurrence_str}, ID: {item['id']}"

@tool
def query_schedule_tool(
    start_ts: float = None,
    end_ts: float = None,
    schedule_type: str = None,
    include_completed: bool = False
) -> str:
    """
    查询日程信息。
    
    Args:
        start_ts: 开始时间戳（默认当前时间）
        end_ts: 结束时间戳（默认7天后）
        schedule_type: 类型过滤 "schedule" | "reminder" | "todo" | "note" | None
        include_completed: 是否包含已完成的待办
    """
    from .schedule_manager import get_schedule_manager
    manager = get_schedule_manager()
    
    if start_ts is None:
        start_ts = time.time()
    if end_ts is None:
        end_ts = start_ts + 7 * 24 * 3600
        
    schedules = manager.get_schedules(start_ts, end_ts, schedule_type, include_completed)
    
    if not schedules:
        return "未找到相关日程"
        
    res = ["日程列表:"]
    for s in schedules:
        time_str = datetime.fromtimestamp(s['datetime']).strftime("%Y-%m-%d %H:%M") if s['datetime'] else "无"
        status = " [已完成]" if s.get('completed') else ""
        recurrence_label = " (循环)" if s.get('recurrence') else ""
        res.append(f"- [{s['type']}] {s['title']} ({time_str}){recurrence_label}{status} ID: {s['id']}")
        
    return "\n".join(res)

@tool
def delete_schedule_tool(schedule_id: str) -> str:
    """删除指定日程"""
    from .schedule_manager import get_schedule_manager
    manager = get_schedule_manager()
    if manager.delete_schedule(schedule_id):
        return f"已删除日程: {schedule_id}"
    return f"未找到日程: {schedule_id}"

@tool
def complete_todo_tool(schedule_id: str) -> str:
    """标记待办事项为完成"""
    from .schedule_manager import get_schedule_manager
    manager = get_schedule_manager()
    if manager.complete_todo(schedule_id):
        return f"已完成待办事项: {schedule_id}"
    return f"未找到待办事项: {schedule_id}"


# === 倒计时提醒工具 ===

# 全局定时器管理
_active_timers = {}

@tool
def countdown_timer_tool(
    title: str,
    delay_seconds: int,
    message: str = ""
) -> str:
    """
    创建倒计时提醒（精确到秒，后台线程执行）。
    适用于短期提醒（< 30分钟），到时间后弹出系统通知。
    
    Args:
        title: 提醒标题（如"喝水"、"休息"）
        delay_seconds: 倒计时秒数
        message: 提醒消息（可选，默认使用标题）
    
    Returns:
        创建结果
    """
    import uuid
    import threading
    import subprocess
    from datetime import datetime, timedelta
    
    timer_id = str(uuid.uuid4())[:8]
    trigger_time = datetime.now() + timedelta(seconds=delay_seconds)
    final_message = message or f"该{title}了！"
    
    def _trigger_reminder():
        """后台线程触发提醒"""
        print(f"\n⏰ ========== 倒计时提醒触发 ==========")
        print(f"   标题: {title}")
        print(f"   消息: {final_message}")
        print(f"   =====================================\n")
        
        # 尝试发送系统通知
        try:
            # 方法1: 使用 plyer（跨平台）
            from plyer import notification
            notification.notify(
                title=f"⏰ {title}",
                message=final_message,
                timeout=10
            )
            print(f"   系统通知已发送 (plyer)")
        except ImportError:
            # 方法2: macOS 原生通知
            try:
                subprocess.run([
                    "osascript", "-e",
                    f'display notification "{final_message}" with title "⏰ Animus 提醒: {title}" sound name "Glass"'
                ], check=True)
                print(f"   系统通知已发送 (osascript)")
            except Exception as e:
                print(f"[WARN] 系统通知失败: {e}")
        
        # 清理定时器记录
        _active_timers.pop(timer_id, None)
    
    # 创建后台定时器
    timer = threading.Timer(delay_seconds, _trigger_reminder)
    timer.daemon = True  # 主进程退出时自动终止
    timer.start()
    
    # 记录活跃定时器
    _active_timers[timer_id] = {
        "title": title,
        "trigger_time": trigger_time.isoformat(),
        "delay_seconds": delay_seconds,
        "timer": timer
    }
    
    # 格式化时间显示
    if delay_seconds < 60:
        time_display = f"{delay_seconds}秒后"
    elif delay_seconds < 3600:
        minutes = delay_seconds // 60
        seconds = delay_seconds % 60
        time_display = f"{minutes}分钟{f'{seconds}秒' if seconds else ''}后"
    else:
        hours = delay_seconds // 3600
        minutes = (delay_seconds % 3600) // 60
        time_display = f"{hours}小时{f'{minutes}分钟' if minutes else ''}后"
    
    time_str = trigger_time.strftime("%H:%M:%S")
    print(f"   倒计时已启动: {title}, {time_display} ({time_str}) 提醒")
    
    return f"已设置倒计时提醒: {title}, 将在{time_display}（{time_str}）提醒你, ID: {timer_id}"


@tool
def cancel_countdown_tool(timer_id: str) -> str:
    """
    取消倒计时提醒。
    
    Args:
        timer_id: 倒计时ID
    
    Returns:
        取消结果
    """
    if timer_id in _active_timers:
        timer_info = _active_timers[timer_id]
        timer_info["timer"].cancel()
        del _active_timers[timer_id]
        return f"已取消倒计时: {timer_info['title']}"
    return f"未找到倒计时: {timer_id}"


@tool
def list_countdowns_tool() -> str:
    """
    列出所有活跃的倒计时提醒。
    
    Returns:
        活跃倒计时列表
    """
    if not _active_timers:
        return "当前没有活跃的倒计时提醒"
    
    lines = ["当前活跃的倒计时提醒："]
    for timer_id, info in _active_timers.items():
        lines.append(f"- [{timer_id}] {info['title']} @ {info['trigger_time']}")
    return "\n".join(lines)


# === 工具列表 ===

AVAILABLE_TOOLS = [
    weather_tool,
    air_quality_tool,
    news_tool,
    time_tool,
    calculator_tool,
    wikipedia_tool,
    web_search_tool,
    update_profile_tool,
    query_user_memory_tool,
    save_user_memory_tool,
    create_schedule_tool,
    query_schedule_tool,
    delete_schedule_tool,
    complete_todo_tool,
    countdown_timer_tool,
    cancel_countdown_tool,
    list_countdowns_tool,
]

# 工具描述（用于提示LLM）
TOOL_DESCRIPTIONS = {
    "weather_tool": "获取天气信息，参数：city（城市名，如'北京'），days（可选，预报天数：0=实时，1=明天，2=后天，默认0）",
    "air_quality_tool": "获取空气质量信息（AQI、PM2.5、PM10等），参数：city（城市名），days（可选，预报天数：0=实时，1=明天，默认0）",
    "news_tool": "获取新闻，参数：keyword（关键词，如'人工智能'）, category（分类：tech/sports/entertainment/finance/general）, limit（数量，默认5）",
    "time_tool": "获取时间，参数：timezone（时区，如'北京'、'纽约'、'伦敦'）",
    "calculator_tool": "数学计算，参数：expression（数学表达式，如'2+3*4'）",
    "wikipedia_tool": "维基百科搜索，参数：query（搜索关键词）",
    "web_search_tool": "网络搜索，在互联网上搜索实时信息，参数：query（搜索关键词，必需）, max_results（最大结果数，可选，默认5）",
    "update_profile_tool": "更新用户核心画像，参数：updates (JSON string: {'field': 'value'})",
    "query_user_memory_tool": "检索用户过往记忆，参数：query, max_results",
    "save_user_memory_tool": "保存用户新记忆，参数：content, category",
    "create_schedule_tool": "创建日程、待办、注意事项或重要日期（生日/纪念日）。参数：title, datetime_ts(时间戳), schedule_type, reminder_minutes, description, recurrence_type(daily/weekly/monthly/yearly), recurrence_value(周几0-6或日期1-31)。【重要日期示例】生日用 yearly 循环，recurrence_type='yearly'。",
    "query_schedule_tool": "查询日程。参数：start_ts, end_ts, schedule_type, include_completed(bool)",
    "delete_schedule_tool": "删除指定日程。参数：schedule_id",
    "complete_todo_tool": "标记待办事项为完成。参数：schedule_id",
    "countdown_timer_tool": "创建倒计时提醒（短期，<30分钟），精确到秒，后台线程执行，到时间弹系统通知。参数：title（提醒标题）, delay_seconds（延迟秒数）, message（可选，提醒消息）",
    "cancel_countdown_tool": "取消倒计时提醒。参数：timer_id",
    "list_countdowns_tool": "列出所有活跃的倒计时提醒。无参数",
}


def get_tool_descriptions() -> str:
    """获取所有工具的描述"""
    descriptions = ["可用工具："]
    for name, desc in TOOL_DESCRIPTIONS.items():
        descriptions.append(f"- {name}: {desc}")
    return "\n".join(descriptions)


if __name__ == "__main__":
    # 测试工具
    print("工具测试：")
    print(get_weather("北京"))
    print()
    print(get_time_info("北京"))
    print()
    print(calculate_math("2 + 3 * 4"))
    print()
    print(search_wikipedia("人工智能"))
    print()
    # 测试新闻和网络搜索（需要配置 BAIDU_SEARCH_API_KEY）
    if os.getenv("BAIDU_SEARCH_API_KEY"):
        print("--- 测试新闻工具 ---")
        print(get_news(keyword="人工智能", category="tech", limit=3))
        print()
        print("--- 测试网络搜索 ---")
        print(web_search("Python教程", 3))
    else:
        print("[WARN] 跳过新闻和网络搜索测试（未配置 BAIDU_SEARCH_API_KEY）")
