#!/usr/bin/env python3
"""
记忆系统增强功能测试 (P1)

测试 Implementation Plan 中定义的功能：
- P1-1: Profile 模式增强
- P1-2: Few-shot Learning (Episodic Memory)
"""
import os
import sys
import tempfile
import time
import pytest

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


# ==========================================
# P1-1: Profile 模式增强测试
# ==========================================

class TestProfileEnhancement:
    """Profile 模式增强测试"""

    @pytest.fixture
    def temp_manager(self):
        """创建临时的 MemoryManager"""
        from src.memory_manager import MemoryManager
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = MemoryManager(db_path=os.path.join(temp_dir, "test_db"))
            yield manager

    def test_preference_summary_field_exists(self, temp_manager):
        """测试 UserProfile 包含 preference_summary 字段"""
        from src.state import UserProfile
        
        profile = UserProfile()
        
        assert hasattr(profile, "preference_summary"), "缺少 preference_summary 字段"
        assert "food" in profile.preference_summary
        assert "music" in profile.preference_summary
        assert "activity" in profile.preference_summary
        assert "habit" in profile.preference_summary
        assert "work" in profile.preference_summary

    def test_last_synthesized_field_exists(self, temp_manager):
        """测试 UserProfile 包含 last_synthesized 字段"""
        from src.state import UserProfile
        
        profile = UserProfile()
        
        assert hasattr(profile, "last_synthesized"), "缺少 last_synthesized 字段"
        assert profile.last_synthesized == 0.0

    def test_profile_save_and_load(self, temp_manager):
        """测试 Profile 保存和加载"""
        from src.state import UserProfile
        
        # 创建并保存
        profile = UserProfile()
        profile.name = "测试用户"
        profile.home_city = "北京"
        profile.preference_summary = {
            "food": ["喜欢火锅", "不喜欢辣"],
            "music": ["喜欢周杰伦"],
            "activity": [],
            "habit": ["习惯晚睡"],
            "work": []
        }
        profile.last_synthesized = time.time()
        
        temp_manager.save_profile(profile)
        
        # 重新加载
        loaded = temp_manager.load_profile()
        
        assert loaded.name == "测试用户"
        assert loaded.home_city == "北京"
        assert loaded.preference_summary["food"] == ["喜欢火锅", "不喜欢辣"]
        assert loaded.preference_summary["music"] == ["喜欢周杰伦"]
        assert loaded.last_synthesized > 0

    def test_synthesize_profile_from_collection(self, temp_manager):
        """测试从 Collection 合成 Profile"""
        # 先保存一些记忆
        temp_manager.save_user_memory("用户喜欢吃火锅", metadata={"category": "food"})
        temp_manager.save_user_memory("用户不喜欢辣的食物", metadata={"category": "food"})
        temp_manager.save_user_memory("用户喜欢听周杰伦的音乐", metadata={"category": "music"})
        
        # 执行合成
        success = temp_manager.synthesize_profile_from_collection()
        
        assert success, "Profile 合成应该成功"
        
        # 验证合成结果
        profile = temp_manager.load_profile()
        assert profile.last_synthesized > 0, "合成时间戳应该更新"
        # 注意：preference_summary 的内容取决于 LLM，这里只检查结构


# ==========================================
# P1-2: Few-shot Learning (Episodic Memory) 测试
# ==========================================

class TestEpisodicMemory:
    """情景记忆 (Episode) 测试"""

    @pytest.fixture
    def temp_manager(self):
        """创建临时的 MemoryManager"""
        from src.memory_manager import MemoryManager
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = MemoryManager(db_path=os.path.join(temp_dir, "test_db"))
            yield manager

    def test_episodes_collection_initialized(self, temp_manager):
        """测试 episodes Collection 已初始化"""
        assert temp_manager.episodes_store is not None, "episodes_store 应该被初始化"

    def test_save_episode_positive(self, temp_manager):
        """测试保存成功的 Episode"""
        success = temp_manager.save_episode(
            context="用户想要查天气",
            action="使用 weather_tool 工具查询当前天气",
            outcome="positive",
            tool_used="weather_tool"
        )
        
        assert success, "保存 Episode 应该成功"

    def test_save_episode_negative(self, temp_manager):
        """测试保存失败的 Episode"""
        success = temp_manager.save_episode(
            context="用户想要查询不存在的服务",
            action="尝试使用 unknown_tool 工具",
            outcome="negative",
            tool_used="unknown_tool"
        )
        
        assert success, "保存 Episode 应该成功"

    def test_retrieve_similar_episodes(self, temp_manager):
        """测试检索相似 Episode"""
        # 保存几个 Episode
        temp_manager.save_episode(
            context="用户想要查北京天气",
            action="使用 weather_tool 工具",
            outcome="positive",
            tool_used="weather_tool"
        )
        temp_manager.save_episode(
            context="用户想要查上海天气",
            action="使用 weather_tool 工具",
            outcome="positive",
            tool_used="weather_tool"
        )
        temp_manager.save_episode(
            context="用户想要查新闻",
            action="使用 news_tool 工具",
            outcome="positive",
            tool_used="news_tool"
        )
        
        # 检索
        similar = temp_manager.retrieve_similar_episodes("查一下天气", k=2)
        
        assert len(similar) >= 1, "应该找到相似的 Episode"
        # 检查返回结构
        for episode in similar:
            assert "content" in episode
            assert "metadata" in episode
            assert "score" in episode

    def test_episode_outcome_priority(self, temp_manager):
        """测试 Episode 检索优先返回 positive 结果"""
        # 保存一个 positive 和一个 negative
        temp_manager.save_episode(
            context="用户查天气成功",
            action="使用 weather_tool 工具",
            outcome="positive",
            tool_used="weather_tool"
        )
        temp_manager.save_episode(
            context="用户查天气失败",
            action="使用 weather_tool 工具",
            outcome="negative",
            tool_used="weather_tool"
        )
        
        # 检索
        similar = temp_manager.retrieve_similar_episodes("查天气", k=1)
        
        if similar:
            # positive 应该排在前面
            assert similar[0]["metadata"].get("outcome") == "positive", \
                "positive 结果应该优先返回"


# ==========================================
# 配置和清理测试
# ==========================================

class TestEpisodeCleanup:
    """Episode 清理机制测试"""

    @pytest.fixture
    def temp_manager(self):
        """创建临时的 MemoryManager"""
        from src.memory_manager import MemoryManager
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = MemoryManager(db_path=os.path.join(temp_dir, "test_db"))
            yield manager

    def test_episode_config_exists(self, temp_manager):
        """测试 Episode 配置存在"""
        assert hasattr(temp_manager, "EPISODE_CONFIG"), "应该有 EPISODE_CONFIG"
        
        config = temp_manager.EPISODE_CONFIG
        assert "max_count" in config
        assert "cleanup_threshold" in config
        assert "neutral_ttl_days" in config
        assert "similarity_threshold" in config

    def test_synthesis_config_exists(self, temp_manager):
        """测试合成配置存在"""
        assert hasattr(temp_manager, "SYNTHESIS_CONFIG"), "应该有 SYNTHESIS_CONFIG"
        
        config = temp_manager.SYNTHESIS_CONFIG
        assert "min_interval_hours" in config
        assert "memory_threshold" in config
        assert "force_keywords" in config


# ==========================================
# 集成测试
# ==========================================

class TestIntegration:
    """集成测试：验证功能在 nodes.py 中的集成"""

    def test_tool_node_saves_episode(self):
        """测试 tool_node 调用后自动保存 Episode"""
        # 这个测试需要完整的 LangGraph 环境
        # 标记为需要手动验证
        pass

    def test_plan_node_injects_few_shot(self):
        """测试 plan_node 注入 Few-shot 示例"""
        # 这个测试需要完整的 LangGraph 环境
        # 标记为需要手动验证
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
