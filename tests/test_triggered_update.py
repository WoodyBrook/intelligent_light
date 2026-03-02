"""
测试触发式记忆更新功能
"""

import pytest
import os
import sys
import json
import tempfile
import shutil

# 添加 src 到 path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.state import UserProfile


class TestTriggeredMemoryUpdate:
    """测试触发式记忆更新"""
    
    @pytest.fixture
    def temp_db_path(self):
        """创建临时数据库目录"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture
    def memory_manager(self, temp_db_path, monkeypatch):
        """创建测试用的 MemoryManager"""
        # 设置环境变量
        monkeypatch.setenv("VOLCENGINE_API_KEY", "test_key")
        
        # 创建一个简化版的 MemoryManager 用于测试正则提取
        from unittest.mock import MagicMock, patch
        
        # Mock OllamaEmbeddings 和 Chroma
        with patch('src.memory_manager.OllamaEmbeddings') as mock_embeddings, \
             patch('src.memory_manager.Chroma') as mock_chroma, \
             patch('src.memory_manager.ChatOpenAI') as mock_llm:
            
            mock_embeddings.return_value = MagicMock()
            mock_chroma.return_value = MagicMock()
            mock_llm.return_value = MagicMock()
            
            from src.memory_manager import MemoryManager
            mm = MemoryManager(db_path=temp_db_path)
            
            # Mock profile 加载
            test_profile = UserProfile()
            mm.load_profile = MagicMock(return_value=test_profile)
            mm.save_profile = MagicMock(return_value=True)
            
            yield mm, test_profile
    
    def test_trigger_keyword_detection(self, memory_manager):
        """测试触发词检测"""
        mm, profile = memory_manager
        
        # 应该触发
        result = mm.triggered_memory_update("记住，我叫张三", "好的")
        assert result["triggered"] == True
        
        result = mm.triggered_memory_update("以后给我推荐咖啡", "好的")
        assert result["triggered"] == True
        
        # 不应该触发
        result = mm.triggered_memory_update("今天天气怎么样", "今天天气不错")
        assert result["triggered"] == False
    
    def test_direct_name_update(self, memory_manager):
        """测试直接姓名更新"""
        mm, profile = memory_manager
        
        result = mm.triggered_memory_update("记住，我叫张三", "好的")
        
        assert result["triggered"] == True
        assert "name" in result["updated_fields"]
        assert profile.name == "张三"
    
    def test_direct_birthday_update(self, memory_manager):
        """测试直接生日更新"""
        mm, profile = memory_manager
        
        result = mm.triggered_memory_update("我的生日是3月15日", "好的")
        
        assert result["triggered"] == True
        assert "birthday" in result["updated_fields"]
        assert profile.birthday == "03-15"
    
    def test_direct_city_update(self, memory_manager):
        """测试直接城市更新"""
        mm, profile = memory_manager
        
        result = mm.triggered_memory_update("我住在上海", "好的")
        
        assert result["triggered"] == True
        assert "home_city" in result["updated_fields"]
        assert profile.home_city == "上海"
    
    def test_unknown_city_not_updated(self, memory_manager):
        """测试未知城市不更新"""
        mm, profile = memory_manager
        
        result = mm.triggered_memory_update("我住在某个小镇", "好的")
        
        # 触发了，但没有更新城市（因为不在已知城市列表）
        assert result["triggered"] == True
        assert "home_city" not in result["updated_fields"]


class TestPreferenceConflictDetection:
    """测试偏好冲突检测"""
    
    def test_detect_like_dislike_conflict(self):
        """测试喜欢/不喜欢冲突检测"""
        from src.memory_manager import MemoryManager
        from unittest.mock import MagicMock, patch
        
        with patch('src.memory_manager.OllamaEmbeddings'), \
             patch('src.memory_manager.Chroma'), \
             patch('src.memory_manager.ChatOpenAI'), \
             patch.dict(os.environ, {"VOLCENGINE_API_KEY": "test"}):
            
            mm = MemoryManager.__new__(MemoryManager)
            mm.TRIGGERED_UPDATE_CONFIG = {"trigger_keywords": [], "known_cities": []}
            
            # 设置 profile
            profile = UserProfile()
            profile.preference_summary["food"] = ["用户喜欢吃辣"]
            
            # 检测冲突
            conflicts = mm._detect_preference_conflicts("用户不喜欢吃辣", "food", profile)
            
            assert len(conflicts) == 1
            assert "用户喜欢吃辣" in conflicts
    
    def test_no_conflict_different_topic(self):
        """测试不同主题无冲突"""
        from src.memory_manager import MemoryManager
        from unittest.mock import patch
        
        with patch('src.memory_manager.OllamaEmbeddings'), \
             patch('src.memory_manager.Chroma'), \
             patch('src.memory_manager.ChatOpenAI'), \
             patch.dict(os.environ, {"VOLCENGINE_API_KEY": "test"}):
            
            mm = MemoryManager.__new__(MemoryManager)
            mm.TRIGGERED_UPDATE_CONFIG = {"trigger_keywords": [], "known_cities": []}
            
            profile = UserProfile()
            profile.preference_summary["food"] = ["用户喜欢吃辣"]
            
            # 不同主题，不应该冲突
            conflicts = mm._detect_preference_conflicts("用户不喜欢喝咖啡", "food", profile)
            
            assert len(conflicts) == 0


class TestReflectionHelpers:
    """测试 Reflection 辅助方法"""
    
    def test_get_recent_memories_empty(self):
        """测试空记忆库"""
        from src.memory_manager import MemoryManager
        from unittest.mock import MagicMock, patch
        
        with patch('src.memory_manager.OllamaEmbeddings'), \
             patch('src.memory_manager.Chroma') as mock_chroma, \
             patch('src.memory_manager.ChatOpenAI'), \
             patch.dict(os.environ, {"VOLCENGINE_API_KEY": "test"}):
            
            mock_store = MagicMock()
            mock_store.get.return_value = {"documents": [], "metadatas": []}
            mock_chroma.return_value = mock_store
            
            mm = MemoryManager()
            mm.user_memory_store = mock_store
            
            memories = mm.get_recent_memories(limit=10)
            assert memories == []
    
    def test_get_recent_memories_sorted(self):
        """测试记忆按时间排序"""
        from src.memory_manager import MemoryManager
        from unittest.mock import MagicMock, patch
        import time
        
        with patch('src.memory_manager.OllamaEmbeddings'), \
             patch('src.memory_manager.Chroma') as mock_chroma, \
             patch('src.memory_manager.ChatOpenAI'), \
             patch.dict(os.environ, {"VOLCENGINE_API_KEY": "test"}):
            
            now = time.time()
            mock_store = MagicMock()
            mock_store.get.return_value = {
                "documents": ["旧记忆", "新记忆"],
                "metadatas": [
                    {"timestamp": now - 1000, "date": "2024-01-01", "category": "test"},
                    {"timestamp": now, "date": "2024-01-02", "category": "test"},
                ]
            }
            mock_chroma.return_value = mock_store
            
            mm = MemoryManager()
            mm.user_memory_store = mock_store
            
            memories = mm.get_recent_memories(limit=10)
            
            # 最新的应该在前
            assert len(memories) == 2
            assert memories[0]["content"] == "新记忆"
            assert memories[1]["content"] == "旧记忆"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
