import pytest
from src.memory_manager import MemoryManager
from unittest.mock import MagicMock, patch

@pytest.fixture
def memory_manager():
    # 使用测试数据库路径
    return MemoryManager(db_path="./test_chroma_db")

def test_extract_music_preference_positive():
    """测试提取正面音乐偏好"""
    mm = MemoryManager()
    
    # 用户表示喜欢推荐的音乐
    user_input = "这首歌真好听，我喜欢周杰伦的歌"
    llm_response = "太好了！我会记住你喜欢周杰伦的音乐"
    recommended_music = "晴天 - 周杰伦"
    
    preference = mm.extract_music_preference(user_input, llm_response, recommended_music)
    
    assert preference is not None
    assert preference["category"] == "music"
    assert preference["sentiment"] == "positive"
    assert "周杰伦" in preference["content"]
    assert preference["confidence"] > 0.6

def test_extract_music_preference_negative():
    """测试提取负面音乐偏好"""
    mm = MemoryManager()
    
    # 用户表示不喜欢
    user_input = "我不喜欢这种类型的音乐，太吵了"
    llm_response = "好的，我会记住你不喜欢摇滚音乐"
    
    preference = mm.extract_music_preference(user_input, llm_response)
    
    assert preference is not None
    assert preference["sentiment"] == "negative"

def test_extract_news_preference_positive():
    """测试提取正面新闻偏好"""
    mm = MemoryManager()
    
    # 用户表示对AI新闻感兴趣
    user_input = "我对AI和科技类的新闻很感兴趣"
    llm_response = "好的，我会多推送AI和科技相关的新闻给你"
    news_topics = ["AI", "科技"]
    
    preference = mm.extract_news_preference(user_input, llm_response, news_topics)
    
    assert preference is not None
    assert preference["category"] == "news"
    assert preference["sentiment"] == "positive"
    assert "AI" in preference.get("topics", []) or "科技" in preference.get("topics", [])

def test_extract_news_preference_negative():
    """测试提取负面新闻偏好"""
    mm = MemoryManager()
    
    # 用户表示不感兴趣
    user_input = "我不喜欢看娱乐新闻，别推给我"
    llm_response = "好的，我不会再推送娱乐新闻"
    
    preference = mm.extract_news_preference(user_input, llm_response)
    
    assert preference is not None
    assert preference["sentiment"] == "negative"

def test_get_music_preferences():
    """测试从记忆中检索音乐偏好"""
    mm = MemoryManager()
    
    # Mock 向量数据库
    mock_doc1 = MagicMock()
    mock_doc1.page_content = "用户喜欢周杰伦的音乐"
    mock_doc1.metadata = {"category": "music", "sentiment": "positive", "artist": "周杰伦"}
    
    mock_doc2 = MagicMock()
    mock_doc2.page_content = "用户不喜欢摇滚类型的音乐"
    mock_doc2.metadata = {"category": "music", "sentiment": "negative", "genre": "摇滚"}
    
    with patch.object(mm, 'user_memory_store') as mock_store:
        mock_store.similarity_search.return_value = [mock_doc1, mock_doc2]
        
        prefs = mm.get_music_preferences()
        
        assert "周杰伦" in prefs["liked_artists"]
        assert "摇滚" in prefs["disliked_genres"]

def test_get_news_interests():
    """测试从记忆中检索新闻兴趣"""
    mm = MemoryManager()
    
    # Mock 向量数据库
    mock_doc = MagicMock()
    mock_doc.page_content = "用户对AI和科技相关的新闻感兴趣"
    mock_doc.metadata = {"category": "news", "sentiment": "positive", "topics": ["AI", "科技"]}
    
    with patch.object(mm, 'user_memory_store') as mock_store:
        mock_store.similarity_search.return_value = [mock_doc]
        
        interests = mm.get_news_interests()
        
        assert "AI" in interests or "科技" in interests

