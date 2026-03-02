# pattern_scanner.py
"""
模式检测模块
扫描 ROM (ChromaDB) 中的事件，识别时间规律（如"每月10号发工资"）
"""

import re
from typing import List, Dict, Any, Optional
from collections import defaultdict


class PatternScanner:
    """
    模式扫描器：从长期记忆中识别时间规律
    
    使用场景：
    - 识别"每月X号"的重复事件（如发薪日）
    - 识别"每周X"的习惯
    - 识别"每年X月X日"的纪念日
    """
    
    def __init__(self, memory_manager):
        """
        初始化模式扫描器
        
        Args:
            memory_manager: MemoryManager 实例
        """
        self.memory_manager = memory_manager
        self.min_occurrences = 2  # 最少出现次数才算规律
    
    def scan_all_patterns(self) -> List[Dict[str, Any]]:
        """
        扫描所有时间相关的模式
        
        Returns:
            检测到的模式列表
        """
        patterns = []
        
        # 1. 扫描每月同一天的事件
        monthly_patterns = self.scan_monthly_patterns()
        patterns.extend(monthly_patterns)
        
        # 2. 扫描每周同一天的事件
        weekly_patterns = self.scan_weekly_patterns()
        patterns.extend(weekly_patterns)
        
        return patterns
    
    def _extract_day_from_content(self, content: str) -> Optional[int]:
        """
        从内容中提取明确的日期描述（如"每月10号"）
        
        Args:
            content: 记忆内容
            
        Returns:
            提取到的日期（1-31），如果没有则返回 None
        """
        # 匹配 "每月X号"、"X号"、"X日" 等模式
        patterns = [
            r'每月(\d{1,2})[号日]',       # "每月10号"
            r'每个月(\d{1,2})[号日]',     # "每个月10号"
            r'(\d{1,2})[号日]',           # "10号"（需要上下文判断）
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content)
            if match:
                day = int(match.group(1))
                if 1 <= day <= 31:
                    return day
        return None
    
    def scan_monthly_patterns(self) -> List[Dict[str, Any]]:
        """
        扫描每月同一天发生的事件模式
        例如：用户每月10号说"发工资了"
        
        Returns:
            检测到的月度规律列表
        """
        if not self.memory_manager.user_memory_store:
            return []
        
        try:
            # 获取所有记忆
            results = self.memory_manager.user_memory_store.get()
            documents = results.get("documents", [])
            metadatas = results.get("metadatas", [])
            
            if not documents or not metadatas:
                return []
            
            # 按 day_of_month 分组
            # 优先使用内容中提取的日期（如"每月10号"），而非元数据中的记忆写入日期
            day_groups = defaultdict(list)
            for doc, meta in zip(documents, metadatas):
                # 优先从内容中提取日期
                content_day = self._extract_day_from_content(doc)
                # 回退到元数据中的日期
                day = content_day if content_day else meta.get("day_of_month")
                if day:
                    day_groups[day].append({
                        "content": doc,
                        "metadata": meta
                    })
            
            patterns = []
            
            # 检测规律：同一天出现 >= min_occurrences 次
            for day, events in day_groups.items():
                if len(events) >= self.min_occurrences:
                    # 聚类相似内容
                    content_clusters = self._cluster_by_content(events)
                    
                    for cluster_content, cluster_events in content_clusters.items():
                        if len(cluster_events) >= self.min_occurrences:
                            pattern = {
                                "type": "monthly",
                                "day_of_month": day,
                                "frequency": f"每月{day}号",
                                "sample_content": cluster_content,
                                "occurrences": len(cluster_events),
                                "confidence": min(1.0, len(cluster_events) / 5.0)
                            }
                            patterns.append(pattern)
                            print(f"检测到月度规律: {pattern['frequency']} - {cluster_content[:30]}...")
            
            return patterns
            
        except Exception as e:
            print(f"[ERROR] 扫描月度规律失败: {e}")
            return []
    
    def scan_weekly_patterns(self) -> List[Dict[str, Any]]:
        """
        扫描每周同一天发生的事件模式
        例如：用户每周五说"终于周末了"
        
        Returns:
            检测到的周度规律列表
        """
        if not self.memory_manager.user_memory_store:
            return []
        
        try:
            results = self.memory_manager.user_memory_store.get()
            documents = results.get("documents", [])
            metadatas = results.get("metadatas", [])
            
            if not documents or not metadatas:
                return []
            
            # 按 weekday 分组
            weekday_groups = defaultdict(list)
            weekday_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
            
            for doc, meta in zip(documents, metadatas):
                weekday = meta.get("weekday")
                if weekday is not None:
                    # 【修复】如果内容明确包含月度日期描述（如"每月10号"），则不应识别为周规律
                    if self._extract_day_from_content(doc) is not None:
                        continue  # 跳过月度模式的记忆
                    
                    weekday_groups[weekday].append({
                        "content": doc,
                        "metadata": meta
                    })
            
            patterns = []
            
            for weekday, events in weekday_groups.items():
                if len(events) >= self.min_occurrences:
                    content_clusters = self._cluster_by_content(events)
                    
                    for cluster_content, cluster_events in content_clusters.items():
                        if len(cluster_events) >= self.min_occurrences:
                            pattern = {
                                "type": "weekly",
                                "weekday": weekday,
                                "frequency": f"每{weekday_names[weekday]}",
                                "sample_content": cluster_content,
                                "occurrences": len(cluster_events),
                                "confidence": min(1.0, len(cluster_events) / 5.0)
                            }
                            patterns.append(pattern)
                            print(f"检测到周度规律: {pattern['frequency']} - {cluster_content[:30]}...")
            
            return patterns
            
        except Exception as e:
            print(f"[ERROR] 扫描周度规律失败: {e}")
            return []
    
    def _cluster_by_content(self, events: List[Dict]) -> Dict[str, List[Dict]]:
        """
        按内容相似度聚类事件
        简单实现：基于关键词匹配
        
        Args:
            events: 事件列表
            
        Returns:
            聚类结果 {代表内容: [事件列表]}
        """
        clusters = defaultdict(list)
        
        # 【新增】删除意图关键词 - 包含这些词的记忆不应被识别为规律
        deletion_keywords = ["不需要", "不用", "取消", "删除", "不再", "不要", "别"]
        
        # 关键词提取和匹配
        keywords_map = {
            "工资": ["发工资", "工资", "薪水", "发薪"],
            "周末": ["周末", "休息", "放假"],
            "开心": ["开心", "高兴", "真好", "太棒"],
            "累": ["累", "疲惫", "辛苦"],
        }
        
        for event in events:
            content = event["content"]
            
            # 【新增】跳过删除意图的记忆
            if any(kw in content for kw in deletion_keywords):
                continue
            matched_keyword = None
            
            # 匹配关键词
            for key, synonyms in keywords_map.items():
                if any(s in content for s in synonyms):
                    matched_keyword = key
                    break
            
            if matched_keyword:
                clusters[matched_keyword].append(event)
            else:
                # 无法聚类的单独处理
                clusters[content[:20]].append(event)
        
        return dict(clusters)
    
    def consolidate_to_profile(self, patterns: List[Dict[str, Any]]) -> int:
        """
        将检测到的规律写入 Profile.important_dates
        
        Args:
            patterns: 模式列表
            
        Returns:
            成功添加/更新的数量
        """
        if not patterns:
            return 0
        
        profile = self.memory_manager.load_profile()
        processed_count = 0
        modified = False
        
        for pattern in patterns:
            if pattern.get("confidence", 0) >= 0.4:  # 置信度阈值
                date_entry = {
                    "date": self._pattern_to_date_str(pattern),
                    "name": pattern.get("sample_content", "未知事件"),
                    "type": pattern.get("type", "routine"),
                    "frequency": pattern.get("frequency", "")
                }
                
                # 检查是否存在同名事件 (覆盖逻辑)
                existing_index = -1
                for i, existing in enumerate(profile.important_dates):
                    if existing.get("name") == date_entry["name"]:
                        existing_index = i
                        break
                
                if existing_index >= 0:
                    # 更新已有事件
                    old_entry = profile.important_dates[existing_index]
                    if old_entry != date_entry:
                        profile.important_dates[existing_index] = date_entry
                        modified = True
                        processed_count += 1
                        print(f"更新规律 Profile: {date_entry['frequency']} - {date_entry['name']}")
                else:
                    # 添加新事件
                    profile.important_dates.append(date_entry)
                    modified = True
                    processed_count += 1
                    print(f"新增规律到 Profile: {date_entry['frequency']} - {date_entry['name']}")
        
        if modified:
            self.memory_manager.save_profile(profile)
        
        return processed_count
    
    def _pattern_to_date_str(self, pattern: Dict) -> str:
        """
        将模式转换为日期字符串
        """
        if pattern["type"] == "monthly":
            return f"*-{pattern['day_of_month']:02d}"  # 例如 "*-10" 表示每月10号
        elif pattern["type"] == "weekly":
            return f"W{pattern['weekday']}"  # 例如 "W4" 表示每周五
        return ""


# 全局实例
_pattern_scanner = None


def get_pattern_scanner():
    """获取模式扫描器单例"""
    global _pattern_scanner
    if _pattern_scanner is None:
        from .memory_manager import get_memory_manager
        _pattern_scanner = PatternScanner(get_memory_manager())
    return _pattern_scanner


def scan_and_consolidate_patterns() -> Dict[str, Any]:
    """
    扫描模式并写入 Profile 的便捷函数
    手动调用入口
    
    Returns:
        扫描结果
    """
    scanner = get_pattern_scanner()
    patterns = scanner.scan_all_patterns()
    added_count = scanner.consolidate_to_profile(patterns)
    
    return {
        "patterns_found": len(patterns),
        "patterns_added_to_profile": added_count,
        "patterns": patterns
    }
