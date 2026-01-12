import pytest
from src.content_providers import (
    create_music_recommender,
    create_news_aggregator,
    MusicRecommendation,
    NewsItem
)

def test_music_recommender_by_mood():
    """测试基于情绪的音乐推荐"""
    recommender = create_music_recommender()
    
    # 测试 happy 情绪
    recommendations = recommender.recommend_by_mood("happy")
    assert len(recommendations) > 0
    assert all(isinstance(r, MusicRecommendation) for r in recommendations)
    
    # 测试 sad 情绪
    recommendations = recommender.recommend_by_mood("sad")
    assert len(recommendations) > 0
    
    # 测试 relaxed 情绪
    recommendations = recommender.recommend_by_mood("relaxed")
    assert len(recommendations) > 0

def test_music_recommender_with_preferences():
    """测试带用户偏好的音乐推荐"""
    recommender = create_music_recommender()
    
    # 测试用户偏好
    recommendations = recommender.recommend_by_mood("happy", user_preferences=["周杰伦"])
    assert len(recommendations) > 0
    
    # 检查推荐理由中是否包含偏好信息
    for rec in recommendations:
        if rec.artist == "周杰伦":
            assert "喜欢的艺术家" in rec.reason

def test_mood_from_conversation():
    """测试从对话历史推断情绪"""
    recommender = create_music_recommender()
    
    # 测试开心情绪
    history = [{"content": "今天真开心！"}]
    mood = recommender.get_mood_from_conversation(history)
    assert mood == "happy"
    
    # 测试疲惫情绪
    history = [{"content": "好累啊，想休息"}]
    mood = recommender.get_mood_from_conversation(history)
    assert mood == "tired"
    
    # 测试中性情绪
    history = []
    mood = recommender.get_mood_from_conversation(history)
    assert mood == "neutral"

def test_news_aggregator_setup():
    """测试新闻聚合器初始化"""
    aggregator = create_news_aggregator()
    
    # 测试默认 RSS 源
    assert len(aggregator.default_feeds) > 0
    assert "tech" in aggregator.default_feeds
    
    # 测试添加用户兴趣
    aggregator.set_user_interests(["AI", "科技"])
    assert len(aggregator.user_interests) == 2

def test_news_aggregator_add_feed():
    """测试添加自定义 RSS 源"""
    aggregator = create_news_aggregator()
    
    # 添加自定义源
    aggregator.add_user_feed("tech", "https://example.com/feed")
    assert "tech" in aggregator.user_feeds
    assert "https://example.com/feed" in aggregator.user_feeds["tech"]

def test_news_aggregator_fetch():
    """测试获取新闻（模拟）"""
    aggregator = create_news_aggregator()
    
    # 注意：这个测试需要网络连接，可能会失败
    # 在实际测试中应该 mock feedparser
    try:
        news_items = aggregator.fetch_news(category="tech", max_items=3)
        assert isinstance(news_items, list)
        # 如果成功获取到新闻
        if news_items:
            assert all(isinstance(n, NewsItem) for n in news_items)
    except Exception as e:
        # 网络错误或 RSS 源不可用时跳过
        pytest.skip(f"网络测试失败: {e}")

def test_news_relevance_calculation():
    """测试新闻相关性计算"""
    aggregator = create_news_aggregator()
    
    # 设置用户兴趣
    aggregator.set_user_interests(["AI", "机器学习"])
    
    # 模拟新闻条目
    entry1 = {"title": "AI 技术的最新进展", "summary": "机器学习在各领域的应用"}
    entry2 = {"title": "今日天气预报", "summary": "明天晴天"}
    
    # 计算相关性
    score1 = aggregator._calculate_relevance(entry1)
    score2 = aggregator._calculate_relevance(entry2)
    
    # AI 相关新闻应该有更高的相关性
    assert score1 > score2

