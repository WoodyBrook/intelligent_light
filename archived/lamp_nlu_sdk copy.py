#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
纯米台灯 NLU SDK - 封装版

主要功能：
  - 自然语言解析
  - 意图识别
  - 槽位提取
  - 支持灯光、机械臂、灯头控制


"""
__version__ = "1.0.3"

import re
from typing import Dict, Optional, Any
from rapidfuzz import process, fuzz


class LampNLUSDK:
    """
    自然语言理解SDK
    
    使用示例：
        >>> nlu = LampNLUSDK()
        >>> result = nlu.parse("打开灯")
        >>> print(result)
        {'intent': 'LightOn', 'slots': {}, 'confidence': 0.95}
    """
    
    def __init__(self):
        """初始化NLU引擎"""
        # 硬件档位配置
        self.GEARS_BRIGHTNESS = [10, 30, 50, 70, 90, 100]
        self.GEARS_TEMP = [2700, 3500, 4000, 5000, 6500]
        
        # 意图词库
        self._init_commands()
        
        # 展平词库用于模糊匹配
        self._build_keyword_index()
    
    def _init_commands(self):
        """初始化意图词库"""
        self.commands = {
            # === 灯光控制 ===
            "LightOn": [
                "打开灯", "开灯", "亮起来", "开启",
                "点灯", "把灯开开", "把灯打开"
            ],
            "LightOff": [
                "关灯", "关闭", "灭灯", "关掉", "关了", "关上",
                "关灯光", "关掉灯光", "关闭灯光",
                "关灯头", "关掉灯头", "关闭灯头",
                "熄灯", "熄掉", "熄灭"
            ],
            
            # === 亮度调节 ===
            "BrightnessUp": [
                "调亮", "调亮点", "调亮一点", "亮一点", "亮点", 
                "再亮点", "再亮一点", "更亮", "亮些",
                "亮一丢丢", "亮一点点", "亮一小点",
                "给点光", "给点亮", "稍微亮一点", "稍微亮一丢丢", "稍微给点光"
            ],
            "BrightnessDown": [
                "调暗", "调暗点", "调暗一点", "暗一点", "暗点",
                "再暗点", "再暗一点", "更暗", "暗些"
            ],
            
            # === 色温调节 ===
            "TempWarmer": [
                "调暖", "调暖点", "暖一点", "暖点", "黄一点", "偏黄",
                "柔和", "柔和一点", "柔和点", "柔和些", "温和", "温和一点"
            ],
            "TempCooler": [
                "调冷", "调冷点", "冷一点", "冷点", "白一点", "偏白",
                "清爽", "清爽一点", "清爽点", "清爽些",
                "明亮", "亮白", "清晰"
            ],
            
            # === 模式切换 ===
            "SetLightMode_Read": [
                "阅读模式", "看书", "读写", "学习",
                "阅读", "我要阅读", "打开阅读灯", "阅读灯", "开启阅读模式"
            ],
            "SetLightMode_Screen": [
                "读屏模式", "看电脑", "屏幕", "网课",
                "读屏", "我要看电脑", "打开读屏模式", "读屏灯", "开启读屏模式"
            ],
            "SetLightMode_Sleep": [
                "睡前模式", "助眠", "准备睡觉",
                "睡觉", "睡觉了", "我要睡觉", "我要睡觉了", "该睡了", "我想睡觉",
                "打开睡前模式", "开启睡前模式"
            ],
            "SetLightMode_Night": [
                "夜灯模式", "起夜",
                "夜灯", "我要起夜", "打开夜灯", "开启夜灯模式"
            ],
            "SetLightMode_Handmade": [
                "手作模式", "手工", "做手工",
                "手作", "我要做手工", "打开手作模式", "开启手作模式"
            ],
            "SetLightMode_Video": [
                "摄像辅助", "直播", "补光", "录像", "视频会议", "拍照", "拍摄", "拍视频", "拍东西", "开会",
                "我要拍照", "我要直播", "打开摄像模式", "开启摄像模式", "摄像模式"
            ],
            "SetLightMode_Companion": [
                "陪伴模式", "氛围",
                "陪伴", "我要氛围", "打开陪伴模式", "开启陪伴模式"
            ],
            
            # === 任务 ===
            "StartRest": [
                "休息吧", "休息", "我要休息", "想休息",
                "番茄钟", "累了", "好累", "歇会", "歇歇",
                "休息会", "休息会儿", "要休息了"
            ],
            "ContinueWork": [
                "继续工作", "开始工作", "回到工作", "恢复工作",
                "干活", "工作", "我要工作", "开始干活", "上班了",
                "工作了", "要工作了", "开工", "开始学习", "开始看书"
            ],
            "DrinkWaterReminder": [
                "喝水", "提醒我喝水", "喝一点水", "喝点水", "喝口水",
                "喝些水", "补充水分", "要喝水", "想喝水", "该喝水了"
            ],
            
            # === 机械臂控制 (槽位对接版 + 口语化扩展) ===
            "ControlArmMove": [
                # 基础指令（带主语）
                "机械臂往前", "机械臂往后", "机械臂往左", "机械臂往右", 
                "机械臂往上", "机械臂往下",
                "支架往前", "支架往后", "支架往左", "支架往右",
                "支架往上", "支架往下",
                "机械臂前移", "机械臂后移", "机械臂左移", "机械臂右移",
                "机械臂上移", "机械臂下移",
                
                # 方向移动
                "往前移", "往后移", "往左移", "往右移", "往上移", "往下移",
                "往前", "往后", "往左", "往右", "往上", "往下",
                
                # 微调/调整（合并到Move，通过move_amount区分幅度）
                "微调", "调整", "调一下", "调整一下", "调整位置", 
                "微调一下", "稍微调整", "调调", "调整调整",
                
                # 连续动作表达
                "再往前", "再往后", "再往左", "再往右", "再往上", "再往下",
                "往前点", "往后点", "往左点", "往右点", "往上点", "往下点",
                "再往前点", "再往后点", "再往左点", "再往右点",
                "继续往前", "继续往后", "继续往左", "继续往右",
                "再前进", "再后退", "再左移", "再右移",
                "往前一点", "往后一点", "往左一点", "往右一点",
                "向左一点", "向右一点", "向左边一点", "向右边一点",
                "靠左一点", "靠右一点", "靠左边一点", "靠右边一点",
                "向左边", "向右边", "靠左边", "靠右边",
                
                # 极限位置表达
                "移动到最前", "移动到最后", "移动到最左", "移动到最右",
                "移动到最上", "移动到最下",
                "到最前", "到最后", "到最左", "到最右", "到最上", "到最下",
                "移到最前面", "移到最后面", "移到最左边", "移到最右边",
                "最前", "最后", "最左", "最右", "最上", "最下",
                
                # 口语化动词（v4.4扩展 - 重点新增）
                # 上下动作（绝对方向，保留）
                "放下", "放低", "放到最低", "放低一点", "降下", "降低", "降低一点",
                "抬起", "抬高", "抬高一点", "提高", "升高", "升起",
                "下来", "下去", "下来一点", "下去一点", "趴下", "趴下来", "趴下去",
                "上来", "上去", "上来一点", "上去一点", "抬上来", "抬上去",
                
                # 前后动作（绝对方向动词）
                "推前", "推后", "推出去",  # 推=向前/向外
                "收回", "缩回",            # 收/缩=向后/向内
                "伸出", "伸出去",          # 伸=向前/向外
                
                # 距离动作
                "远离", "远离一点", "离远点", "离远一点",
                
                # 相对用户位置（以用户为参考系）
                "过来", "过来点", "过来一点",
                "回来", "回来点", "回来一点",
                "靠近", "靠近点", "靠近一点",
                "凑过来", "凑过来点", "凑过来一点", "凑近", "凑近点",
                "过去", "过去点", "过去一点",
                "回去", "回去点", "回去一点",
                
                # 组合方向（v4.4扩展 - 支持对角线移动）
                # 水平+垂直
                "左上", "右上", "左下", "右下",
                "往左上", "往右上", "往左下", "往右下",
                "左上方", "右上方", "左下方", "右下方",
                "往左上方", "往右上方", "往左下方", "往右下方",
                # 水平+纵深
                "左前", "右前", "左后", "右后",
                "往左前", "往右前", "往左后", "往右后",
                "左前方", "右前方", "左后方", "右后方",
                # 纵深+垂直
                "前上", "前下", "后上", "后下",
                "往前上", "往前下", "往后上", "往后下",
            ],
            
            "ControlArmRotate": [
                "旋转", "转一下", "顺时针", "逆时针", "转动"
            ],
            
            # === 灯头控制 (v5.0扩展：增加幅度控制表达) ===
            "ControlHeadAngle": [
                # 基础方向
                "灯头往上", "灯头往下", "灯头往左", "灯头往右",
                "灯头向上", "灯头向下", "灯头向左", "灯头向右",
                "灯往上照", "灯往下照", "灯往左照", "灯往右照",
                "抬头", "低头", "转头",
                
                # 连续动作（v4.4）
                "灯头再往上", "灯头再往下", "灯头再往左", "灯头再往右",
                "再抬头", "再低头", "继续往上照", "继续往下照",
                
                # 幅度控制表达（v5.0新增）
                "灯头稍微往上", "灯头稍微往下", "灯头稍微往左", "灯头稍微往右",
                "灯头大幅往上", "灯头大幅往下", "灯头大幅往左", "灯头大幅往右",
                "灯头往上一点", "灯头往下一点", "灯头往左一点", "灯头往右一点",
                "灯头到最上", "灯头到最下", "灯头到最左", "灯头到最右",
                "抬头一点", "低头一点", "大幅抬头", "大幅低头",
            ],
            
            # === 状态查询 ===
            "QueryState": ["当前状态", "现在在哪", "亮度是多少", "什么模式", "状态报告"]
        }
    
    def _build_keyword_index(self):
        """构建关键词索引"""
        self.flat_keywords = []
        self.keyword_to_intent = {}
        for intent, kws in self.commands.items():
            for kw in kws:
                self.flat_keywords.append(kw)
                self.keyword_to_intent[kw] = intent
    
    def _get_nearest_gear(self, target: int, gears: list) -> int:
        """获取最近的硬件档位"""
        return min(gears, key=lambda x: abs(x - target))
    
    def _extract_number(self, text: str) -> Optional[int]:
        """
        提取文本中的数字
        支持阿拉伯数字和常见中文数字
        """
        # 阿拉伯数字
        match = re.search(r'\d+', text)
        if match:
            return int(match.group())
        
        # 中文数字映射（支持口语组合）
        chinese_map = {
            # 千位（含常用组合，如"三千五"）
            "一千": 1000, "二千": 2000, "三千": 3000, "四千": 4000, "五千": 5000,
            "六千": 6000, "七千": 7000, "八千": 8000, "九千": 9000,
            # 常用千位组合（口语表达）
            "两千五": 2500, "三千五": 3500, "四千五": 4500, "五千五": 5500, "六千五": 6500,
            "三千八": 3800, "四千二": 4200, "四千八": 4800,
            # 百位
            "一百": 100, "二百": 200, "三百": 300, "四百": 400, "五百": 500,
            "六百": 600, "七百": 700, "八百": 800, "九百": 900,
            # 十位
            "十": 10, "二十": 20, "三十": 30, "四十": 40, "五十": 50,
            "六十": 60, "七十": 70, "八十": 80, "九十": 90,
        }
        
        # 按长度降序匹配
        for chinese, num in sorted(chinese_map.items(), key=lambda x: len(x[0]), reverse=True):
            if chinese in text:
                return num
        
        return None
    
    def _extract_direction(self, text: str) -> Optional[str]:
        """
        提取方向信息
        返回值: "forward", "backward", "left", "right", "up", "down" 
               或组合方向: "left-up", "right-forward" 等
        
        v5.1扩展：支持单字识别（远、近、高、低）+ 排除干扰词
        v5.2扩展：支持ASR同音字纠错（网→往、软→暖等）
        """
        # ===== 预处理1：ASR同音字纠错 =====
        # 修复常见ASR识别错误，避免影响方向提取
        text = text.replace("网", "往")  # "网前" → "往前"（ASR误识别）
        text = text.replace("软", "暖")  # "调软" → "调暖"（ASR误识别，虽然这里不直接影响方向，但保持一致性）
        
        # ===== 预处理2：移除量词干扰 =====
        # 避免"调整一下"、"往前点一下"中的"下"被误判为方向词
        text_clean = text
        for q in ["一下", "点一下", "一点", "下子", "会儿", "一会儿"]:
            text_clean = text_clean.replace(q, "")
        
        # ===== 优先级0：灯头专用表达（单独词汇） =====
        if "抬头" in text_clean or "仰头" in text_clean:
            return "up"
        if "低头" in text_clean or "俯头" in text_clean:
            return "down"
        if "转头" in text:
            return "left"  # 默认向左转
        
        # ===== 优先级1：组合方向（对角线移动）- 12种组合 =====
        # 水平+垂直（4个）
        if "左上" in text_clean or (("左" in text_clean) and ("上" in text_clean)):
            return "left-up"
        if "右上" in text_clean or (("右" in text_clean) and ("上" in text_clean)):
            return "right-up"
        if "左下" in text_clean or (("左" in text_clean) and ("下" in text_clean)):
            return "left-down"
        if "右下" in text_clean or (("右" in text_clean) and ("下" in text_clean)):
            return "right-down"
        
        # 水平+纵深（4个）
        if "左前" in text_clean or (("左" in text_clean) and ("前" in text_clean)):
            return "left-forward"
        if "右前" in text_clean or (("右" in text_clean) and ("前" in text_clean)):
            return "right-forward"
        if "左后" in text_clean or (("左" in text_clean) and ("后" in text_clean)):
            return "left-backward"
        if "右后" in text_clean or (("右" in text_clean) and ("后" in text_clean)):
            return "right-backward"
        
        # 纵深+垂直（4个）
        if "前上" in text_clean or (("前" in text_clean) and ("上" in text_clean)):
            return "forward-up"
        if "前下" in text_clean or (("前" in text_clean) and ("下" in text_clean)):
            return "forward-down"
        if "后上" in text_clean or (("后" in text_clean) and ("上" in text_clean)):
            return "backward-up"
        if "后下" in text_clean or (("后" in text_clean) and ("下" in text_clean)):
            return "backward-down"
        
        # ===== 优先级2：动词明确的方向动作 =====
        # 收缩类动词
        if any(w in text for w in ["收回", "缩回"]):
            return "backward"  # 收/缩 = 向内/向后
        if any(w in text for w in ["推出"]):
            return "forward"  # 推出 = 向外
        
        # 距离动词
        if any(w in text for w in ["远离", "离远"]):
            return "backward"  # 远离/离远 = 灯远离用户 = 往后退
        
        # 退下/退后类
        if any(w in text for w in ["退下", "退后", "退回", "退回去", "退一步", "后退"]):
            return "backward"
        
        # 🔥 单独的"远"字（如"远一点"、"远点"）- 关键修复！
        if "远" in text and not any(w in text for w in ["远程", "遥远", "永远", "远方"]):
            return "backward"  # 远 = 灯远离用户 = 往后退
        
        # 🔥 单独的"近"字（如"近一点"、"近点"、"离我近点"）- 关键修复！
        if "近" in text and not any(w in text for w in ["附近", "最近", "近期"]):
            return "forward"  # 近 = 灯靠近用户 = 往前移
        
        # 边界方位词
        if "左边" in text_clean:
            return "left"
        if "右边" in text_clean:
            return "right"
        
        # 🔥 单独的"高"字（如"高一点"、"高点"）
        if "太高" in text or "高了" in text:
            if not any(w in text for w in ["色温", "亮度"]):
                return "down"  # 抱怨太高→往下
        if "高" in text and not any(w in text for w in ["最高", "色温", "亮度"]):
            return "up"  # 高 = 向上
        
        # 🔥 单独的"低"字（如"低一点"、"低点"）
        if "低" in text and not any(w in text for w in ["最低", "色温", "亮度"]):
            return "down"  # 低 = 向下
        
        # 伸展类动词
        if "伸出" in text:
            if "上" in text_clean:
                return "up"
            else:
                return "forward"  # 伸出 = 向外/向前
        
        # ===== 优先级3：上下动作的"来/去"（绝对方向）=====
        # 上下是重力参考系，不存在相对位置歧义
        if any(w in text for w in ["上来", "上去", "抬上"]):
            return "up"
        if any(w in text for w in ["下来", "下去", "趴下", "放下"]):
            return "down"
        
        # ===== 优先级4：相对用户位置（以台灯为参考系）=====
        # forward（灯向用户移动 = 灯往前走）
        if any(w in text for w in ["过来", "回来", "靠近", "凑过来", "凑近"]):
            return "forward"
        # backward（灯远离用户 = 灯往后退）
        if any(w in text for w in ["过去", "回去"]):
            return "backward"
        
        # ===== 优先级5：正则匹配单一方向（使用清洗后的文本） =====
        # 支持两种词序：1) 动词+方向（往左）2) 方向+动词（左移）
        patterns = {
            "forward": r'((往|向|移|动|最|再|到|推)\s*(前|远)|前\s*(移|动))',
            "backward": r'((往|向|移|动|最|再|到|拉|缩|收)\s*后|后\s*(移|动))',
            "left": r'((往|向|移|动|最|再|到|靠)\s*左|左\s*(移|动|靠))',
            "right": r'((往|向|移|动|最|再|到|靠)\s*右|右\s*(移|动|靠))',
            "up": r'((往|向|移|动|抬|最|再|到|提|升)\s*(上|高|起)|上\s*(移|动))',
            "down": r'((往|向|移|动|低|最|再|到|放|降|趴)\s*(下|低)|下\s*(移|动))',
        }
        
        for direction, pattern in patterns.items():
            if re.search(pattern, text_clean):
                return direction
        
        return None
    
    def _extract_move_amount(self, text: str) -> str:
        """
        提取移动幅度
        返回值: 数字 | "maximum" | "large" | "small" | "medium" | "default"
        """
        # 优先提取数字
        num = self._extract_number(text)
        if num:
            return num
        
        # 语义量词
        if "最" in text:
            return "maximum"
        elif any(w in text for w in ["大", "多", "大幅", "长"]):
            return "large"
        elif any(w in text for w in ["小", "少", "一点", "稍微", "微", "点", "一下"]):
            return "small"
        elif any(w in text for w in ["中等", "适中"]):
            return "medium"
        
        return "default"
    
    def _extract_rotate_direction(self, text: str) -> Optional[str]:
        """提取旋转方向"""
        if any(w in text for w in ["顺时针", "右转"]):
            return "clockwise"
        elif any(w in text for w in ["逆时针", "左转"]):
            return "counterclockwise"
        return None
    
    def parse(self, text: str) -> Dict[str, Any]:
        """
        解析用户输入的自然语言
        
        参数:
            text (str): 用户输入的文本
        
        返回:
            dict: 解析结果，包含以下字段：
                - intent (str): 识别的意图
                - slots (dict): 提取的槽位信息
                - confidence (float): 置信度 (0-1)
                - raw_text (str): 原始输入文本
        
        示例:
            >>> nlu.parse("机械臂往前移50")
            {
                'intent': 'ControlArmMove',
                'slots': {'move_direction': 'forward', 'move_amount': 50},
                'confidence': 0.95,
                'raw_text': '机械臂往前移50'
            }
        """
        if not text:
            return {
                "intent": "Unknown",
                "slots": {},
                "confidence": 0.0,
                "raw_text": text
            }
        
        # ===== 预处理：ASR同音字纠错 =====
        # 修复常见ASR识别错误，提升识别准确率
        # 注意：这里只处理影响意图和槽位提取的关键同音字
        text = text.replace("网", "往")  # "网前" → "往前"（影响方向提取）
        text = text.replace("软", "暖")  # "调软" → "调暖"（影响色温意图识别）
        text = text.replace("等", "灯")  # "开等" → "开灯"（影响开关灯意图识别）
        
        # ===== 预处理：词汇标准化 =====
        # 注意：不要把"灯光"替换成"灯头"，会导致"把灯光调亮"被误判为灯头控制
        
        # ===== 模式优先判断（在特殊值判断之前）=====
        # 避免模式意图被开关灯等意图截走
        mode_keywords_map = {
            "Read": ["阅读", "看书", "读写", "学习"],
            "Screen": ["读屏", "看电脑", "屏幕", "网课"],
            "Sleep": ["睡觉", "睡前", "助眠"],
            "Night": ["夜灯", "起夜"],
            "Handmade": ["手作", "手工"],
            "Video": ["拍照", "拍摄", "直播", "摄像", "录像", "视频会议", "开会", "补光"],
            "Companion": ["陪伴", "氛围"]
        }
        
        for mode, keywords in mode_keywords_map.items():
            if any(kw in text for kw in keywords):
                # 如果包含"打开"+"模式关键词"+"灯/模式"，优先识别为模式
                if ("打开" in text or "开启" in text) and ("灯" in text or "模式" in text):
                    return {
                        "intent": "SetLightMode",
                        "slots": {"mode": mode},
                        "confidence": 0.9,
                        "raw_text": text
                    }
                # 如果包含"我要"+"模式关键词"，识别为模式（优先于短文本判断）
                elif "我要" in text:
                    return {
                        "intent": "SetLightMode",
                        "slots": {"mode": mode},
                        "confidence": 0.88,
                        "raw_text": text
                    }
                # 如果只是模式关键词（短文本或包含"模式"），也识别为模式
                elif len(text) <= 6 or "模式" in text:
                    return {
                        "intent": "SetLightMode",
                        "slots": {"mode": mode},
                        "confidence": 0.85,
                        "raw_text": text
                    }
        
        # 优先处理特殊值
        if any(w in text for w in ["最亮", "全亮", "最大", "最高", "最高亮度"]):
            # 排除色温相关，避免"色温调到最高"等被误判为亮度调节
            if "色温" not in text:
                # 排除机械臂相关动词，避免"抬到最高"等被误判为亮度调节
                arm_verbs = ["放", "降", "移", "抬", "升", "推", "收", "缩", "伸"]
                if not any(verb in text for verb in arm_verbs):
                    return {
                        "intent": "AdjustBrightness",
                        "slots": {"val": 100, "type": "max"},
                        "confidence": 1.0,
                        "raw_text": text
                    }
        
        if any(w in text for w in ["最暗", "微光", "最小", "最低", "最低亮度"]):
            # 排除色温相关，避免"色温调到最低"等被误判为亮度调节
            if "色温" not in text:
                # 排除机械臂相关动词，避免"放到最低"等被误判为亮度调节
                arm_verbs = ["放", "降", "移", "抬", "升", "推", "收", "缩", "伸"]
                if not any(verb in text for verb in arm_verbs):
                    return {
                        "intent": "AdjustBrightness",
                        "slots": {"val": 10, "type": "min"},
                        "confidence": 1.0,
                        "raw_text": text
                    }
        
        # 属性调节
        if "亮度" in text:
            if any(w in text for w in ["高", "调高", "增加", "大"]):
                return {
                    "intent": "BrightnessUp",
                    "slots": {},
                    "confidence": 0.95,
                    "raw_text": text
                }
            elif any(w in text for w in ["低", "调低", "减少", "小"]):
                return {
                    "intent": "BrightnessDown",
                    "slots": {},
                    "confidence": 0.95,
                    "raw_text": text
                }
        
        if "色温" in text:
            # 处理"色温调到最高/最低"的特殊情况
            if any(w in text for w in ["最高"]):
                return {
                    "intent": "AdjustColorTemperature",
                    "slots": {"val": 6500, "type": "max"},
                    "confidence": 1.0,
                    "raw_text": text
                }
            elif any(w in text for w in ["最低"]):
                return {
                    "intent": "AdjustColorTemperature",
                    "slots": {"val": 2700, "type": "min"},
                    "confidence": 1.0,
                    "raw_text": text
                }
            elif any(w in text for w in ["高", "调高", "增加", "大"]):
                return {
                    "intent": "TempCooler",
                    "slots": {},
                    "confidence": 0.95,
                    "raw_text": text
                }
            elif any(w in text for w in ["低", "调低", "减少", "小"]):
                return {
                    "intent": "TempWarmer",
                    "slots": {},
                    "confidence": 0.95,
                    "raw_text": text
                }
        
        # 色温特殊值
        if any(w in text for w in ["暖光", "黄光", "最暖"]):
            return {
                "intent": "AdjustColorTemperature",
                "slots": {"val": 2700, "type": "warm"},
                "confidence": 1.0,
                "raw_text": text
            }
        
        if any(w in text for w in ["白光", "冷光", "最冷"]):
            return {
                "intent": "AdjustColorTemperature",
                "slots": {"val": 6500, "type": "cold"},
                "confidence": 1.0,
                "raw_text": text
            }
        
        # 亮度主观抱怨：太亮/刺眼 → 降亮
        if any(w in text for w in ["刺眼", "晃眼", "太亮了", "太刺眼"]):
            return {
                "intent": "BrightnessDown",
                "slots": {},
                "confidence": 0.9,
                "raw_text": text
            }
        
        # 亮度主观抱怨：太暗 → 提亮
        if any(w in text for w in ["太暗了", "太暗", "暗得看不见", "看不见", "太黑了"]):
            return {
                "intent": "BrightnessUp",
                "slots": {},
                "confidence": 0.9,
                "raw_text": text
            }
        
        # 关灯优先：含“关/关闭/关掉”且有灯相关词，无方向词时，直接关灯，避免被灯头截走
        close_words = ["关", "关闭", "关掉", "灭"]
        lamp_words = ["灯", "灯光", "灯头"]
        has_close = any(w in text for w in close_words)
        has_lamp = any(w in text for w in lamp_words)
        if has_close and has_lamp:
            dir_for_head_tmp = self._extract_direction(text)
            if dir_for_head_tmp is None:
                return {
                    "intent": "LightOff",
                    "slots": {},
                    "confidence": 0.95,
                    "raw_text": text
                }
        
        # 灯头/灯光优先：含“灯头/灯光”，或“灯/头”+方向词，或“光”+方向（打光、往左打光等）时走灯头控制
        dir_for_head = self._extract_direction(text)
        has_light_words_hint = any(w in text for w in ["亮", "暗", "色温", "暖光", "白光", "冷光", "黄光"])
        # 🔥 亮度调节动词优先判断
        brightness_adjust_verbs = ["调亮", "调暗", "调亮点", "调暗点", "调亮一点", "调暗一点", 
                                   "亮一点", "暗一点", "亮点", "暗点", "亮些", "暗些", "更亮", "更暗"]
        has_brightness_verb = any(verb in text for verb in brightness_adjust_verbs)
        
        lamp_head_hint = (
            ("灯头" in text and not has_brightness_verb)
            or ("灯光" in text and not has_brightness_verb)
            or (("灯" in text or "头" in text) and dir_for_head is not None)
            or ("光" in text and dir_for_head is not None and not has_light_words_hint)
        )
        if lamp_head_hint:
            amount = self._extract_move_amount(text)
            slots = {}
            if dir_for_head:
                slots["adjust_direction"] = dir_for_head
            if amount and amount != "default":
                slots["adjust_amount"] = amount
            return {
                "intent": "ControlHeadAngle",
                "slots": slots,
                "confidence": 0.9,
                "raw_text": text
            }
        
        # 数值提取（避免与机械臂冲突）
        num = self._extract_number(text)
        if num is not None:
            movement_keywords = [
                "机械臂", "支架", "移动", "移到",
                "往前", "往后", "往左", "往右", "往上", "往下",
                "前移", "后移", "左移", "右移", "上移", "下移",
                "调整", "微调", "旋转"
            ]
            has_movement = any(kw in text for kw in movement_keywords)
            
            if not has_movement:
                if num > 100 or "色温" in text:
                    val = self._get_nearest_gear(num, self.GEARS_TEMP)
                    return {
                        "intent": "AdjustColorTemperature",
                        "slots": {"val": val},
                        "confidence": 0.9,
                        "raw_text": text
                    }
                else:
                    val = self._get_nearest_gear(num, self.GEARS_BRIGHTNESS)
                    return {
                        "intent": "AdjustBrightness",
                        "slots": {"val": val},
                        "confidence": 0.9,
                        "raw_text": text
                    }
        
        # 方向优先：含明显方向词且不含亮度/色温/灯头词时优先归为机械臂移动
        direction = dir_for_head if 'dir_for_head' in locals() else self._extract_direction(text)
        has_light_words = any(w in text for w in ["亮", "暗", "色温", "暖光", "白光", "冷光", "黄光"])
        if direction and not has_light_words and "灯头" not in text and "灯光" not in text and "头" not in text and not ("灯" in text and direction):
            amount = self._extract_move_amount(text)
            # 调整类表达默认视为小幅微调
            if (not amount or amount == "default") and any(w in text for w in ["调整", "微调", "稍微", "调一下", "调整一下"]):
                amount = "small"
            slots = {"move_direction": direction}
            if amount and amount != "default":
                slots["move_amount"] = amount
            return {
                "intent": "ControlArmMove",
                "slots": slots,
                "confidence": 0.9,
                "raw_text": text
            }
        
        # 模糊匹配
        match = process.extractOne(
            text, 
            self.flat_keywords, 
            scorer=fuzz.partial_ratio, 
            score_cutoff=75
        )
        
        if match:
            matched_keyword, confidence = match[0], match[1] / 100.0
            raw_intent = self.keyword_to_intent[matched_keyword]
            
            # 灯头优先判断
            if "灯头" in text and raw_intent == "ControlArmMove":
                raw_intent = "ControlHeadAngle"
            
            # 处理模式切换
            if raw_intent.startswith("SetLightMode_"):
                mode_type = raw_intent.replace("SetLightMode_", "")
                return {
                    "intent": "SetLightMode",
                    "slots": {"mode": mode_type},
                    "confidence": confidence,
                    "raw_text": text
                }
            
            # 处理机械臂移动
            if raw_intent == "ControlArmMove":
                slots = {}
                direction = self._extract_direction(text)
                amount = self._extract_move_amount(text)
                
                # 微调关键词自动设置小幅度
                if any(w in text for w in ["微调", "调整", "稍微", "调一下"]):
                    if amount == "default":
                        amount = "small"
                
                if direction:
                    slots["move_direction"] = direction
                if amount and amount != "default":
                    slots["move_amount"] = amount
                
                return {
                    "intent": "ControlArmMove",
                    "slots": slots,
                    "confidence": confidence,
                    "raw_text": text
                }
            
            # 处理机械臂旋转
            if raw_intent == "ControlArmRotate":
                rotate_dir = self._extract_rotate_direction(text)
                slots = {"rotate_direction": rotate_dir} if rotate_dir else {}
                return {
                    "intent": raw_intent,
                    "slots": slots,
                    "confidence": confidence,
                    "raw_text": text
                }
            
            # 处理灯头控制
            if raw_intent == "ControlHeadAngle":
                slots = {}
                direction = self._extract_direction(text)
                amount = self._extract_move_amount(text)
                
                if direction:
                    slots["adjust_direction"] = direction
                if amount and amount != "default":
                    slots["adjust_amount"] = amount
                
                return {
                    "intent": raw_intent,
                    "slots": slots,
                    "confidence": confidence,
                    "raw_text": text
                }
            
            # 其他意图
            return {
                "intent": raw_intent,
                "slots": {},
                "confidence": confidence,
                "raw_text": text
            }
        
        # 未识别
        return {
            "intent": "Unknown",
            "slots": {},
            "confidence": 0.0,
            "raw_text": text
        }
    
    def get_supported_intents(self) -> list:
        """
        获取所有支持的意图列表
        
        返回:
            list: 意图名称列表
        """
        return list(set(self.keyword_to_intent.values()))
    
    def get_intent_examples(self, intent: str) -> list:
        """
        获取指定意图的示例语句
        
        参数:
            intent (str): 意图名称
        
        返回:
            list: 示例语句列表
        """
        return self.commands.get(intent, [])



# 便捷函数

def create_nlu() -> LampNLUSDK:
    """
    创建NLU实例的便捷函数
    
    返回:
        LampNLUSDK: NLU实例
    """
    return LampNLUSDK()


def quick_parse(text: str) -> Dict[str, Any]:
    """
    快速解析接口（无需创建实例）
    
    参数:
        text (str): 输入文本
    
    返回:
        dict: 解析结果
    """
    nlu = LampNLUSDK()
    return nlu.parse(text)


if __name__ == "__main__":
    # 简单测试
    nlu = create_nlu()
    
    test_cases = [
        "打开灯",
        "机械臂往前移50",
        "灯头往下一点",
        "亮度调到80",
        "阅读模式",
    ]
    
    print("=" * 60)
    print("NLU SDK 测试")
    print("=" * 60)
    
    for text in test_cases:
        result = nlu.parse(text)
        print(f"\n输入: {text}")
        print(f"意图: {result['intent']}")
        print(f"槽位: {result['slots']}")
        print(f"置信度: {result['confidence']:.2f}")

