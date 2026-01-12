# content_providers.py - 内容服务提供商支持
# 支持音乐推荐和新闻推送（场景 4.1 & 4.2）

import json
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import requests

# 可选导入 feedparser（RSS 解析）
try:
    import feedparser
    FEEDPARSER_AVAILABLE = True
except ImportError:
    feedparser = None
    FEEDPARSER_AVAILABLE = False
    logging.warning("⚠️ feedparser 库未安装，新闻聚合功能将不可用。安装命令: pip install feedparser")

logger = logging.getLogger("ContentProviders")

# ==========================================
# 数据模型
# ==========================================

@dataclass
class MusicRecommendation:
    """音乐推荐"""
    title: str
    artist: str
    album: Optional[str] = None
    genre: Optional[str] = None
    mood: Optional[str] = None  # happy, sad, relaxed, energetic
    url: Optional[str] = None
    reason: Optional[str] = None  # 推荐理由

@dataclass
class NewsItem:
    """新闻条目"""
    title: str
    summary: str
    source: str
    published_date: str
    url: str
    category: Optional[str] = None
    relevance_score: float = 0.0  # 相关性评分

# ==========================================
# 音乐推荐服务（场景 4.1）
# ==========================================

class MusicRecommender:
    """
    音乐推荐服务 - 基于情绪推荐音乐
    场景 4.1: 音乐与内容推荐
    """
    
    def __init__(self):
        # 情绪 -> 音乐类型映射
        self.mood_genre_map = {
            "happy": ["pop", "dance", "electronic"],
            "sad": ["ballad", "acoustic", "indie"],
            "relaxed": ["ambient", "classical", "jazz"],
            "energetic": ["rock", "hip-hop", "edm"],
            "tired": ["lo-fi", "ambient", "classical"],
            "focused": ["instrumental", "lo-fi", "classical"],
            "anxious": ["ambient", "meditation", "nature sounds"]
        }
        
        # 本地音乐库（示例数据）
        self.local_music_library = [
            {"title": "晴天", "artist": "周杰伦", "genre": "pop", "mood": "happy"},
            {"title": "说好不哭", "artist": "周杰伦", "genre": "ballad", "mood": "sad"},
            {"title": "River Flows in You", "artist": "Yiruma", "genre": "classical", "mood": "relaxed"},
            {"title": "Faded", "artist": "Alan Walker", "genre": "edm", "mood": "energetic"},
            {"title": "Lo-fi Hip Hop Mix", "artist": "Various", "genre": "lo-fi", "mood": "focused"},
        ]
    
    def recommend_by_mood(self, mood: str, user_preferences: Optional[List[str]] = None) -> List[MusicRecommendation]:
        """
        根据情绪推荐音乐
        
        Args:
            mood: 用户当前情绪 (happy, sad, relaxed, energetic, tired, focused, anxious)
            user_preferences: 用户偏好的艺术家或类型
        
        Returns:
            推荐的音乐列表
        """
        logger.info(f"根据情绪推荐音乐: {mood}")
        
        # 获取适合该情绪的音乐类型
        suitable_genres = self.mood_genre_map.get(mood.lower(), ["pop"])
        
        # 从本地库筛选
        recommendations = []
        for music in self.local_music_library:
            if music["mood"] == mood.lower() or music["genre"] in suitable_genres:
                reason = f"适合{mood}的心情"
                if user_preferences and music["artist"] in user_preferences:
                    reason += f"，你喜欢的艺术家"
                
                recommendations.append(MusicRecommendation(
                    title=music["title"],
                    artist=music["artist"],
                    genre=music["genre"],
                    mood=music["mood"],
                    reason=reason
                ))
        
        return recommendations[:3]  # 返回前3个推荐
    
    def get_mood_from_conversation(self, conversation_history: List[Dict[str, str]]) -> str:
        """
        从对话历史中推断用户情绪（简化版）
        实际应用中可以使用情感分析模型
        """
        if not conversation_history:
            return "neutral"
        
        # 简单关键词匹配
        recent_text = " ".join([msg.get("content", "") for msg in conversation_history[-3:]])
        
        keywords = {
            "happy": ["开心", "高兴", "快乐", "哈哈", "😊", "😄"],
            "sad": ["难过", "伤心", "郁闷", "😢", "😭"],
            "tired": ["累", "疲惫", "困", "😴"],
            "energetic": ["兴奋", "激动", "精神", "💪"],
            "anxious": ["焦虑", "紧张", "担心", "😰"],
            "focused": ["工作", "学习", "专注", "忙"],
        }
        
        for mood, words in keywords.items():
            if any(word in recent_text for word in words):
                return mood
        
        return "neutral"

# ==========================================
# 新闻推送服务（场景 4.2）
# ==========================================

class NewsAggregator:
    """
    新闻聚合服务 - 基于用户兴趣推送新闻
    场景 4.2: 新闻与资讯推送
    """
    
    def __init__(self):
        # 默认 RSS 源（中文新闻）
        self.default_feeds = {
            "tech": [
                "https://www.oschina.net/news/rss",  # 开源中国
                "https://www.cnbeta.com.tw/backend.php",  # cnBeta
                "https://rsshub.app/zaobao/realtime/china",  # RSSHub 联合早报
            ],
            "general": [
                "https://www.thepaper.cn/rss.jsp",  # 澎湃新闻（全品类高质量源）
                "http://www.people.com.cn/rss/politics.xml",  # 人民网
            ],
            "science": [
                "https://www.guokr.com/rss/",  # 果壳网
            ]
        }
        
        self.user_feeds = {}  # 用户自定义 RSS 源
        self.user_interests = []  # 用户兴趣关键词
    
    def add_user_feed(self, category: str, feed_url: str):
        """添加用户自定义 RSS 源"""
        if category not in self.user_feeds:
            self.user_feeds[category] = []
        self.user_feeds[category].append(feed_url)
        logger.info(f"已添加 RSS 源: {category} - {feed_url}")
    
    def set_user_interests(self, interests: List[str]):
        """设置用户兴趣关键词"""
        self.user_interests = interests
        logger.info(f"已设置用户兴趣: {interests}")
    
    def fetch_news(self, category: Optional[str] = None, keyword: Optional[str] = None, max_items: int = 5) -> List[NewsItem]:
        """
        获取新闻
        
        Args:
            category: 新闻分类 (tech, general, science)
            keyword: 搜索关键词（如果提供，且本地没有匹配分类，则使用百度搜索 via RSSHub）
            max_items: 最多返回条数
        
        Returns:
            新闻列表
        """
        logger.info(f"获取新闻: category={category}, keyword={keyword}, max_items={max_items}")
        
        # 如果提供了关键词，且本地没有匹配的分类，使用百度搜索 RSS
        if keyword and not category:
            # 检查关键词是否匹配已知分类
            keyword_lower = keyword.lower()
            matched_category = None
            if any(kw in keyword_lower for kw in ["科技", "技术", "ai", "人工智能", "互联网", "数码"]):
                matched_category = "tech"
            elif any(kw in keyword_lower for kw in ["科学", "研究", "医学", "健康"]):
                matched_category = "science"
            elif any(kw in keyword_lower for kw in ["时事", "政治", "社会", "经济", "财经"]):
                matched_category = "general"
            
            if matched_category:
                # 找到了匹配的分类，使用本地源
                category = matched_category
                logger.info(f"关键词 '{keyword}' 匹配到分类: {category}")
            else:
                # 没有匹配的分类，直接使用澎湃新闻通用源 + 本地关键词过滤
                # 澎湃新闻的 RSS 包含全品类新闻（娱乐、体育、财经等），我们在本地过滤即可
                logger.info(f"关键词 '{keyword}' 没有匹配的本地分类，使用澎湃新闻通用源 + 关键词过滤")
                general_feeds = self.default_feeds.get("general", [])
                if general_feeds:
                    # 使用澎湃新闻（第一个通用源）
                    feed_url = general_feeds[0]
                    all_items = self._fetch_from_single_feed(feed_url, max_items * 3, source_name="澎湃新闻")
                    
                    if all_items:
                        # 在本地进行关键词过滤
                        filtered_items = []
                        keyword_lower = keyword.lower()
                        for item in all_items:
                            # 检查标题和摘要中是否包含关键词
                            title_lower = item.title.lower()
                            summary_lower = (item.summary or "").lower()
                            if keyword_lower in title_lower or keyword_lower in summary_lower:
                                filtered_items.append(item)
                                if len(filtered_items) >= max_items:
                                    break
                        
                        if filtered_items:
                            logger.info(f"从澎湃新闻中筛选出 {len(filtered_items)} 条与'{keyword}'相关的新闻")
                            return filtered_items
                        else:
                            logger.warning(f"澎湃新闻中没有找到与'{keyword}'相关的新闻")
                    else:
                        logger.warning(f"从澎湃新闻获取新闻失败")
                
                # 如果澎湃新闻也失败，返回空列表，让上层处理（会回退到 web_search）
                return []
        
        # 选择 RSS 源
        feeds = []
        if category:
            feeds = self.default_feeds.get(category, []) + self.user_feeds.get(category, [])
        else:
            # 获取所有分类的源
            for cat_feeds in self.default_feeds.values():
                feeds.extend(cat_feeds)
            for cat_feeds in self.user_feeds.values():
                feeds.extend(cat_feeds)
        
        if not FEEDPARSER_AVAILABLE:
            logger.warning("feedparser 未安装，无法获取新闻。请运行: pip install feedparser")
            return []
        
        news_items = []
        if not feeds:
            logger.warning(f"没有找到 {category} 分类的 RSS 源")
            return []
        
        logger.info(f"尝试从 {len(feeds[:3])} 个 RSS 源获取新闻: {feeds[:3]}")
        
        # 通用请求头，模拟真实浏览器
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/rss+xml, application/xml, text/xml, */*"
        }
        
        for feed_url in feeds[:3]:  # 限制最多3个源
            try:
                logger.info(f"正在抓取 RSS 源: {feed_url}")
                # 先使用 requests 获取内容，这样可以设置 User-Agent 和处理 SSL
                # verify=False 可以在证书有问题时强制继续（虽然不推荐，但对于 RSS 通常可接受）
                response = requests.get(feed_url, headers=headers, timeout=15, verify=True)
                response.raise_for_status()
                
                # 将内容传递给 feedparser
                feed = feedparser.parse(response.text)
                
                # 检查 feed 是否有效
                if not hasattr(feed, 'entries') or not feed.entries:
                    logger.warning(f"RSS 源 {feed_url} 解析后没有返回任何条目")
                    # 如果 requests 成功但 feedparser 没解析出来，可能是编码问题
                    # 尝试直接解析 URL 作为降级方案
                    if not feed.entries:
                        logger.info(f"尝试直接解析 URL 作为降级方案: {feed_url}")
                        feed = feedparser.parse(feed_url)
                
                if not hasattr(feed, 'entries') or not feed.entries:
                    logger.warning(f"RSS 源 {feed_url} 最终失败，无条目")
                    continue
                
                logger.info(f"从 {feed_url} 获取到 {len(feed.entries)} 条新闻条目")
                
                for entry in feed.entries[:max_items]:
                    # 计算相关性评分
                    relevance = self._calculate_relevance(entry)
                    
                    news_items.append(NewsItem(
                        title=entry.get("title", "无标题"),
                        summary=entry.get("summary", entry.get("description", ""))[:200],
                        source=feed.feed.get("title", "未知来源"),
                        published_date=entry.get("published", "未知时间"),
                        url=entry.get("link", ""),
                        category=category,
                        relevance_score=relevance
                    ))
                    
                logger.info(f"从 {feed_url} 成功提取 {len([e for e in feed.entries[:max_items]])} 条新闻")
            except requests.exceptions.HTTPError as e:
                # HTTP 错误（如 403 Forbidden）只打印简短警告，不打印堆栈
                status_code = e.response.status_code if hasattr(e, 'response') and e.response else "未知"
                logger.warning(f"RSS 源 {feed_url} 访问失败 (HTTP {status_code}): {str(e)}")
            except Exception as e:
                # 其他未知异常才打印详细堆栈
                logger.error(f"解析 RSS 源失败 {feed_url}: {e}", exc_info=True)
        
        # 按相关性排序
        news_items.sort(key=lambda x: x.relevance_score, reverse=True)
        return news_items[:max_items]
    
    def _fetch_from_single_feed(self, feed_url: str, max_items: int, source_name: str = "未知来源") -> List[NewsItem]:
        """
        从单个 RSS 源获取新闻（用于动态搜索源）
        
        Args:
            feed_url: RSS 源地址
            max_items: 最多返回条数
            source_name: 来源名称
        
        Returns:
            新闻列表
        """
        if not FEEDPARSER_AVAILABLE:
            logger.warning("feedparser 未安装，无法获取新闻。请运行: pip install feedparser")
            return []
        
        news_items = []
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/rss+xml, application/xml, text/xml, */*"
        }
        
        try:
            logger.info(f"正在抓取动态 RSS 源: {feed_url}")
            response = requests.get(feed_url, headers=headers, timeout=15, verify=True)
            response.raise_for_status()
            
            feed = feedparser.parse(response.text)
            
            if not hasattr(feed, 'entries') or not feed.entries:
                logger.warning(f"动态 RSS 源 {feed_url} 解析后没有返回任何条目")
                return []
            
            logger.info(f"从 {feed_url} 获取到 {len(feed.entries)} 条新闻条目")
            
            for entry in feed.entries[:max_items]:
                # 对于百度搜索结果，优化标题提取（可能包含来源信息）
                title = entry.get("title", "无标题")
                # 移除标题中可能存在的来源后缀（如 " - 来源"）
                if " - " in title:
                    title = title.split(" - ")[0]
                
                relevance = self._calculate_relevance(entry)
                
                news_items.append(NewsItem(
                    title=title,
                    summary=entry.get("summary", entry.get("description", ""))[:200],
                    source=source_name if source_name != "未知来源" else feed.feed.get("title", "未知来源"),
                    published_date=entry.get("published", "未知时间"),
                    url=entry.get("link", ""),
                    category=None,  # 动态搜索没有固定分类
                    relevance_score=relevance
                ))
            
            logger.info(f"从动态 RSS 源成功提取 {len(news_items)} 条新闻")
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code if hasattr(e, 'response') and e.response else "未知"
            logger.warning(f"动态 RSS 源 {feed_url} 访问失败 (HTTP {status_code}): {str(e)}")
        except Exception as e:
            logger.error(f"解析动态 RSS 源失败 {feed_url}: {e}", exc_info=True)
        
        return news_items[:max_items]
    
    def _calculate_relevance(self, entry: Dict[str, Any]) -> float:
        """计算新闻相关性评分"""
        if not self.user_interests:
            return 0.5  # 默认评分
        
        title = entry.get("title", "").lower()
        summary = entry.get("summary", entry.get("description", "")).lower()
        content = title + " " + summary
        
        # 简单关键词匹配
        score = 0.0
        for interest in self.user_interests:
            if interest.lower() in content:
                score += 0.3
        
        return min(score, 1.0)
    
    def get_daily_digest(self, max_items: int = 3) -> List[NewsItem]:
        """
        获取每日新闻摘要（最相关的新闻）
        """
        all_news = self.fetch_news(max_items=10)
        return all_news[:max_items]

# ==========================================
# 工厂方法
# ==========================================

def create_music_recommender() -> MusicRecommender:
    """创建音乐推荐器实例"""
    return MusicRecommender()

def create_news_aggregator() -> NewsAggregator:
    """创建新闻聚合器实例"""
    return NewsAggregator()

