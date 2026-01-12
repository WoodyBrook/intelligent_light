# reflex_router.py
import re
import time
from typing import Dict, Any, Optional, List

class ReflexResult:
    """反射结果数据结构"""
    def __init__(self, 
                 triggered: bool = False, 
                 action_plan: Optional[Dict] = None, 
                 voice_content: Optional[str] = None,
                 block_llm: bool = False, 
                 new_state_delta: Optional[Dict] = None,
                 command_type: Optional[str] = None):
        self.triggered = triggered          # 是否触发了反射
        self.action_plan = action_plan      # 硬件执行计划
        self.voice_content = voice_content  # 硬编码语音回复
        self.block_llm = block_llm          # 是否阻止后续推理层调用
        self.new_state_delta = new_state_delta or {} # 需要更新的状态增量
        self.command_type = command_type    # 指令类型

class ReflexRouter:
    """
    反射路由器 (System 1)
    负责极速响应、物理本能、安全防御和简单指令
    """
    def __init__(self):
        # 关键词库 (使用更简短的关键词以提高匹配率)
        self.stop_keywords = ["停", "闭嘴", "别说了", "安静", "stop", "quiet", "shut up"]
        self.focus_enter_keywords = ["进入专注", "开启专注", "我要工作", "我要学习", "开启专注模式"]
        self.focus_exit_keywords = ["退出专注", "关闭专注", "结束工作", "休息一下", "关闭专注模式"]
        self.time_keywords = ["几点", "时间", "时刻"]
        self.light_keywords = ["灯", "亮", "暗", "色温"]
        self.weather_keywords = ["天气", "温度", "气温"]
        self.air_quality_keywords = ["空气", "AQI", "PM2.5", "PM10", "雾霾", "污染"]
        
    def _match_keywords(self, text: str, keywords: List[str]) -> bool:
        """通用的关键词匹配逻辑"""
        if not text:
            return False
        text_lower = text.lower()
        return any(kw.lower() in text_lower for kw in keywords)

    def route(self, event: Any, current_state: Dict[str, Any]) -> ReflexResult:
        """
        核心路由函数 (漏斗模型)
        """
        event_type = event.type
        data = event.data
        
        # 获取当前关键状态
        is_focus = current_state.get("focus_mode", False)
        conflict_state = current_state.get("conflict_state")
        
        # 获取对话历史（用于上下文推理）
        conversation_history = current_state.get("history", [])
        
        # --- P0: 物理安全防御 (L3 冲突) ---
        # 假设 event_type "sensor" 中包含加速度信息
        if event_type == "sensor" and data.get("sensor_type") == "imu":
            if data.get("intensity", 0) > 8.0:
                print("   🚨 [Reflex P0] 检测到剧烈撞击！启动紧急防御。")
                return ReflexResult(
                    triggered=True,
                    action_plan={
                        "motor": {"vibration": "stutter", "speed": 0},
                        "light": {"color": "red", "blink": "fast", "brightness": 100},
                        "sound": "emergency_scream.mp3"
                    },
                    voice_content="别打了！好痛...",
                    block_llm=True,
                    command_type="safety_trigger",
                    new_state_delta={
                        "conflict_state": {"offense_level": "L3", "cooldown_until": time.time() + 1200},
                        "intimacy_delta": -5.0,
                        "intimacy_reason": "conflict_L3"
                    }
                )

        # --- P1: 语音打断 (Stop Command) ---
        if event_type == "user_input":
            text = data.get("text", "")
            if self._match_keywords(text, self.stop_keywords):
                print("   🛑 [Reflex P1] 收到停止指令。")
                return ReflexResult(
                    triggered=True,
                    action_plan={
                        "motor": {"speed": 0, "vibration": "none"},
                        "light": {"blink": "none"},
                        "sound": None,
                        "control": "stop_all"
                    },
                    voice_content="好的。",
                    block_llm=True,
                    command_type="stop"
                )

        # --- P2: 延迟遮蔽 (Latency Masking) ---
        # 当语音输入结束，LLM 尚未开始前，立即触发
        if event_type == "vad_voice_end":
            # 仅在非专注模式下显示思考动画
            if not is_focus:
                print("   ⏳ [Reflex P2] 语音结束，启动延迟遮蔽动画。")
                return ReflexResult(
                    triggered=True,
                    action_plan={
                        "light": {"color": "blue", "blink": "slow", "brightness": 40},
                        "motor": {"vibration": "gentle_breathe"}
                    },
                    block_llm=False  # 并行：不阻断推理层
                )

        # --- P3: 物理本能 (Touch Feedback) ---
        if event_type == "sensor" and data.get("sensor_type") == "touch":
            print(f"   🐱 [Reflex P3] 触摸响应 (专注模式: {is_focus})")
            
            # 如果处于冲突状态（生气），反射变为躲避
            if conflict_state:
                return ReflexResult(
                    triggered=True,
                    action_plan={
                        "motor": {"vibration": "shiver"},
                        "light": {"color": "dim_white"},
                        "sound": "whimper.mp3"
                    },
                    voice_content="...别碰我。",
                    block_llm=True,
                    new_state_delta={"intimacy_delta": -0.1}
                )
            
            # 专注模式下：仅轻微震动反馈
            if is_focus:
                return ReflexResult(
                    triggered=True,
                    action_plan={"motor": {"vibration": "short_bump"}},
                    block_llm=True
                )
            else:
                # 正常模式：享受反馈
                return ReflexResult(
                    triggered=True,
                    action_plan={
                        "motor": {"vibration": "purr"},
                        "light": {"color": "orange", "blink": "breathe", "brightness": 60},
                        "sound": "meow_happy.mp3"
                    },
                    voice_content="喵~",
                    block_llm=True,
                    new_state_delta={"intimacy_delta": 0.5, "intimacy_reason": "touch"}
                )

        # --- P5: 状态/简单指令 (Hardcoded Commands) ---
        if event_type == "user_input":
            text = data.get("text", "")
            
            # 时间查询
            if self._match_keywords(text, self.time_keywords):
                from datetime import datetime
                now_str = datetime.now().strftime("%H:%M")
                print(f"   🕒 [Reflex P5] 时间查询: {now_str}")
                return ReflexResult(
                    triggered=True,
                    voice_content=f"现在是北京时间 {now_str}。",
                    action_plan={"light": {"blink": "once"}},
                    block_llm=True
                )
                
            # 专注模式开关
            if self._match_keywords(text, self.focus_enter_keywords):
                print("   🔇 [Reflex P5] 开启专注模式。")
                return ReflexResult(
                    triggered=True,
                    voice_content="好的，我会保持安静，不打扰你工作。",
                    action_plan={"light": {"color": "cool_white", "brightness": 40}},
                    block_llm=True,
                    new_state_delta={"focus_mode": True, "focus_mode_reason": "user_input"}
                )
                
            if self._match_keywords(text, self.focus_exit_keywords):
                print("   🔊 [Reflex P5] 关闭专注模式。")
                return ReflexResult(
                    triggered=True,
                    voice_content="辛苦啦，休息一下吧！",
                    action_plan={"light": {"color": "warm_yellow", "brightness": 70}},
                    block_llm=True,
                    new_state_delta={"focus_mode": False}
                )

            # 天气查询 (P5) - 支持上下文推理
            # 1. 直接询问天气
            if self._match_keywords(text, self.weather_keywords):
                print("   🌤️ [Reflex P5] 天气查询指令识别。")
                
                # 检查日期关键词
                days = 0
                if "明天" in text:
                    days = 1
                elif "后天" in text:
                    days = 2
                
                # 简单解析城市
                city = None
                for c in ["上海", "深圳", "广州", "杭州", "北京", "成都", "武汉", "南京", "苏州"]:
                    if c in text:
                        city = c
                        break
                
                # 如果用户输入中没提到城市，尝试从用户画像中获取
                if not city:
                    # 1. 先从 user_profile.city 中读取
                    profile_city = current_state.get("user_profile", {}).get("city", "")
                    if profile_city and profile_city != "未知":
                        city = profile_city
                        print(f"   📍 从用户画像读取城市: {city}")
                    # 2. 如果画像中也没有，尝试从记忆上下文中提取
                    elif current_state.get("memory_context"):
                        memory_profile = current_state.get("memory_context", {}).get("user_profile", "")
                        if memory_profile:
                            # 从记忆中查找城市信息
                            for c in ["上海", "深圳", "广州", "杭州", "北京", "成都", "武汉", "南京", "苏州"]:
                                if f"所在地是{c}" in memory_profile or f"住在{c}" in memory_profile or f"在{c}" in memory_profile:
                                    city = c
                                    print(f"   📍 从长期记忆提取城市: {city}")
                                    break
                    # 3. 如果都没有，使用默认值
                    if not city:
                        city = "北京"
                        print(f"   📍 使用默认城市: {city}")
                
                from .tools import get_weather, get_air_quality
                weather_info = get_weather(city, days=days)
                air_info = get_air_quality(city, days=days)
                
                # 合并天气和空气质量信息
                combined_info = f"{weather_info}\n\n{air_info}"
                
                return ReflexResult(
                    triggered=True,
                    voice_content=f"没问题！{combined_info}",
                    action_plan={"light": {"color": "skyblue", "blink": "once"}},
                    block_llm=True,
                    command_type="weather_query"
                )
            
            # 2. 上下文推理：如果上一轮问了天气，这一轮只说地点
            if conversation_history and len(conversation_history) > 0:
                last_user_input = conversation_history[-1].get("user", "") if isinstance(conversation_history[-1], dict) else ""
                # 检查上一轮是否提到天气
                if any(kw in last_user_input for kw in self.weather_keywords):
                    # 检查本轮是否只是地点信息
                    for city in ["上海", "北京", "深圳", "广州", "杭州"]:
                        if city in text and not self._match_keywords(text, self.weather_keywords):
                            print(f"   🌤️ [Reflex P5 续接] 检测到地点补充（{city}），续接上轮天气查询。")
                            
                            # 续接也支持日期
                            days = 0
                            if "明天" in text:
                                days = 1
                            elif "后天" in text:
                                days = 2
                                
                            from .tools import get_weather, get_air_quality
                            weather_info = get_weather(city, days=days)
                            air_info = get_air_quality(city, days=days)
                            
                            # 合并天气和空气质量信息
                            combined_info = f"{weather_info}\n\n{air_info}"
                            
                            return ReflexResult(
                                triggered=True,
                                voice_content=f"好的！{combined_info}",
                                action_plan={"light": {"color": "skyblue", "blink": "slow"}},
                                block_llm=True,
                                command_type="weather_query_followup"
                            )

            # --- P5b: 空气质量查询 (独立查询，不包含天气) ---
            # 仅当用户明确问空气质量且未触发天气查询时
            if self._match_keywords(text, self.air_quality_keywords) and not self._match_keywords(text, self.weather_keywords):
                print("   🌫️ [Reflex P5b] 空气质量查询指令识别。")
                
                # 检查日期关键词
                days = 0
                if "明天" in text:
                    days = 1
                elif "后天" in text:
                    days = 2
                
                # 简单解析城市（复用天气查询的逻辑）
                city = None
                for c in ["上海", "深圳", "广州", "杭州", "北京", "成都", "武汉", "南京", "苏州"]:
                    if c in text:
                        city = c
                        break
                
                # 如果用户输入中没提到城市，尝试从用户画像中获取
                if not city:
                    profile_city = current_state.get("user_profile", {}).get("city", "")
                    if profile_city and profile_city != "未知":
                        city = profile_city
                        print(f"   📍 从用户画像读取城市: {city}")
                    elif current_state.get("memory_context"):
                        memory_profile = current_state.get("memory_context", {}).get("user_profile", "")
                        if memory_profile:
                            for c in ["上海", "深圳", "广州", "杭州", "北京", "成都", "武汉", "南京", "苏州"]:
                                if f"所在地是{c}" in memory_profile or f"住在{c}" in memory_profile or f"在{c}" in memory_profile:
                                    city = c
                                    print(f"   📍 从长期记忆提取城市: {city}")
                                    break
                    if not city:
                        city = "北京"
                        print(f"   📍 使用默认城市: {city}")
                
                from .tools import get_air_quality
                air_info = get_air_quality(city, days=days)
                
                return ReflexResult(
                    triggered=True,
                    voice_content=f"好的！{air_info}",
                    action_plan={"light": {"color": "soft_green", "blink": "once"}},
                    block_llm=True,
                    command_type="air_quality_query"
                )

            # --- P5c: 天气/空气查询的上下文续接 ---
            # 处理 "今天呢？"、"明天呢？"、"上海呢？" 等续接查询
            if conversation_history and len(conversation_history) > 0:
                last_user_input = conversation_history[-1].get("user", "") if isinstance(conversation_history[-1], dict) else ""
                last_assistant_output = conversation_history[-1].get("assistant", "") if isinstance(conversation_history[-1], dict) else ""
                
                # 检查上一轮是否涉及天气或空气质量
                weather_or_air_keywords = self.weather_keywords + self.air_quality_keywords
                last_was_weather_or_air = any(kw in last_user_input for kw in weather_or_air_keywords) or \
                                          "空气质量" in last_assistant_output or "天气" in last_assistant_output
                
                if last_was_weather_or_air:
                    # 检查本轮是否只是日期或地点的补充
                    date_keywords = ["今天", "明天", "后天"]
                    city_list = ["上海", "北京", "深圳", "广州", "杭州", "成都", "武汉", "南京", "苏州"]
                    
                    is_date_followup = any(d in text for d in date_keywords) and len(text) <= 10
                    is_city_followup = any(c in text for c in city_list) and len(text) <= 10
                    
                    # 排除已经有明确关键词的情况（那些会被前面的逻辑处理）
                    already_handled = self._match_keywords(text, weather_or_air_keywords)
                    
                    if (is_date_followup or is_city_followup) and not already_handled:
                        print(f"   🔄 [Reflex P5c] 检测到续接查询，续接上轮天气/空气查询")
                        
                        # 解析日期
                        days = 0
                        if "明天" in text:
                            days = 1
                        elif "后天" in text:
                            days = 2
                        
                        # 解析城市（优先从本轮输入，其次从上一轮，最后从用户画像）
                        city = None
                        for c in city_list:
                            if c in text:
                                city = c
                                break
                        
                        if not city:
                            # 尝试从上一轮提取城市
                            for c in city_list:
                                if c in last_user_input or c in last_assistant_output:
                                    city = c
                                    print(f"   📍 从上一轮对话提取城市: {city}")
                                    break
                        
                        if not city:
                            # 从用户画像获取
                            profile_city = current_state.get("user_profile", {}).get("city", "")
                            if profile_city and profile_city != "未知":
                                city = profile_city
                                print(f"   📍 从用户画像读取城市: {city}")
                            else:
                                city = "北京"
                                print(f"   📍 使用默认城市: {city}")
                        
                        # 判断上一轮主要问的是天气还是空气
                        # 如果上一轮同时包含天气和空气，返回两者；否则只返回对应的
                        from .tools import get_weather, get_air_quality
                        
                        last_was_weather = any(kw in last_user_input for kw in self.weather_keywords) or "天气" in last_assistant_output
                        last_was_air = any(kw in last_user_input for kw in self.air_quality_keywords) or "空气质量" in last_assistant_output
                        
                        if last_was_weather and last_was_air:
                            # 上一轮问的是天气（包含空气），返回两者
                            weather_info = get_weather(city, days=days)
                            air_info = get_air_quality(city, days=days)
                            combined_info = f"{weather_info}\n\n{air_info}"
                            return ReflexResult(
                                triggered=True,
                                voice_content=f"好的！{combined_info}",
                                action_plan={"light": {"color": "skyblue", "blink": "once"}},
                                block_llm=True,
                                command_type="weather_air_followup"
                            )
                        elif last_was_air:
                            # 上一轮只问空气
                            air_info = get_air_quality(city, days=days)
                            return ReflexResult(
                                triggered=True,
                                voice_content=f"好的！{air_info}",
                                action_plan={"light": {"color": "soft_green", "blink": "once"}},
                                block_llm=True,
                                command_type="air_quality_followup"
                            )
                        else:
                            # 上一轮只问天气（理论上不会到这里，因为天气已经包含空气了）
                            weather_info = get_weather(city, days=days)
                            air_info = get_air_quality(city, days=days)
                            combined_info = f"{weather_info}\n\n{air_info}"
                            return ReflexResult(
                                triggered=True,
                                voice_content=f"好的！{combined_info}",
                                action_plan={"light": {"color": "skyblue", "blink": "once"}},
                                block_llm=True,
                                command_type="weather_followup"
                            )

            # --- P4: 基础灯光控制 (Simple Hardware Control) ---
            if self._match_keywords(text, self.light_keywords):
                print("   💡 [Reflex P4] 基础灯光指令识别。")
                
                # 获取当前亮度
                hw_state = current_state.get("current_hardware_state", {})
                current_brightness = hw_state.get("light", {}).get("brightness", 50)
                
                new_brightness = current_brightness
                voice = "好的，已经帮你调整了灯光。"
                
                if "开" in text:
                    new_brightness = 100
                    voice = "灯已开启。"
                elif "关" in text:
                    new_brightness = 0
                    voice = "灯已关闭。"
                elif "亮" in text:
                    new_brightness = min(100, current_brightness + 20)
                    voice = "调亮一点啦，现在亮度是{}%。".format(new_brightness)
                elif "暗" in text:
                    new_brightness = max(0, current_brightness - 20)
                    voice = "调暗一点啦，现在亮度是{}%。".format(new_brightness)
                
                return ReflexResult(
                    triggered=True,
                    voice_content=voice,
                    action_plan={
                        "light": {"brightness": new_brightness},
                        "motor": {"vibration": "gentle"}
                    },
                    block_llm=True,
                    command_type="light_control"
                )

        # --- Default: 无反射触发，交给 LLM ---
        return ReflexResult(triggered=False)