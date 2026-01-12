#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试关键词提取
"""

import os
import sys

if not os.environ.get("VOLCENGINE_API_KEY"):
    print("⚠️  请设置 VOLCENGINE_API_KEY 环境变量")
    sys.exit(1)

from src.context_manager import ContextManager

def debug_keywords():
    """调试关键词提取"""
    
    # 模拟 extract_keywords 函数
    def extract_keywords(text: str) -> set:
        """提取关键词：针对中文优化"""
        keywords = set()
        
        # 提取颜色词
        colors = ["红色", "蓝色", "绿色", "黄色", "白色", "黑色", "紫色", "粉色", "橙色", "灰色", "棕色"]
        for color in colors:
            if color in text:
                keywords.add(color)
                keywords.add("颜色")
        
        # 提取城市名
        cities = ["上海", "北京", "深圳", "广州", "杭州", "成都", "武汉", "南京", "苏州", 
                  "重庆", "西安", "天津", "厦门", "青岛", "大连", "长沙", "郑州", "济南"]
        for city in cities:
            if city in text or f"{city}市" in text:
                keywords.add(city)
                if any(kw in text for kw in ["所在地", "常住", "住在", "居住"]):
                    keywords.add("地点信息")
        
        # 提取食物类型
        foods = ["火锅", "日料", "川菜", "粤菜", "西餐", "烧烤", "海鲜", "面食", "米饭", "咖啡", "茶"]
        for food in foods:
            if food in text:
                keywords.add(food)
                if any(kw in text for kw in ["喜欢", "爱吃", "偏好", "爱", "吃"]):
                    keywords.add("食物喜好")
        
        # 提取动作/状态词
        if any(word in text for word in ["喜欢", "爱", "偏好", "最爱"]):
            keywords.add("喜好表达")
        
        if any(word in text for word in ["所在地", "住在", "居住", "常住"]):
            keywords.add("居住表达")
        
        # 移除常见停用词后提取其他关键词
        stopwords = {"用户", "的", "是", "在", "有", "和", "与", "或", "但", "而", 
                     "最", "喜欢", "爱", "经常", "总是", "习惯", "偏好", "吃"}
        
        current_word = ""
        for char in text:
            if char not in stopwords and char not in ["，", "。", "、", "：", "；", " "]:
                current_word += char
            else:
                if len(current_word) >= 2 and current_word not in stopwords:
                    keywords.add(current_word)
                current_word = ""
        if len(current_word) >= 2 and current_word not in stopwords:
            keywords.add(current_word)
        
        return keywords
    
    test_cases = [
        "用户所在地是上海",
        "用户住在上海市",
        "用户喜欢蓝色",
        "用户最喜欢的颜色是蓝色",
    ]
    
    for text in test_cases:
        keywords = extract_keywords(text)
        print(f"\n文本: {text}")
        print(f"关键词: {keywords}")
    
    # 计算相似度
    print("\n\n相似度计算:")
    pairs = [
        ("用户所在地是上海", "用户住在上海市"),
        ("用户喜欢蓝色", "用户最喜欢的颜色是蓝色"),
    ]
    
    for text1, text2 in pairs:
        words1 = extract_keywords(text1)
        words2 = extract_keywords(text2)
        
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        similarity = intersection / union if union > 0 else 0
        
        print(f"\n对比:")
        print(f"  A: {text1}")
        print(f"  B: {text2}")
        print(f"  关键词A: {words1}")
        print(f"  关键词B: {words2}")
        print(f"  交集: {words1 & words2}")
        print(f"  并集: {words1 | words2}")
        print(f"  相似度: {similarity:.2f} (阈值 0.6)")
        print(f"  是否重复: {'是' if similarity > 0.6 else '否'}")

if __name__ == "__main__":
    debug_keywords()

