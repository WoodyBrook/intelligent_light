#!/usr/bin/env python3
"""
测试记忆系统增强功能
"""
import os
import sys
import tempfile
import time

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.memory_manager import MemoryManager
from src.state import UserProfile


def test_profile_enhancement():
    """测试 Profile 增强功能"""
    with tempfile.TemporaryDirectory() as temp_dir:
        print("=== 测试 Profile 增强功能 ===")
        
        # 初始化内存管理器
        manager = MemoryManager(db_path=os.path.join(temp_dir, "test_db"))
        
        # 创建一个用户画像
        profile = UserProfile()
        profile.name = "张三"
        profile.home_city = "北京"
        profile.core_preferences = ["喜欢咖啡", "喜欢读书"]
        
        # 保存用户画像
        manager.save_profile(profile)
        
        # 验证加载
        loaded_profile = manager.load_profile()
        assert loaded_profile.name == "张三", "用户姓名不匹配"
        assert loaded_profile.home_city == "北京", "用户所在城市不匹配"
        assert loaded_profile.core_preferences == ["喜欢咖啡", "喜欢读书"], "核心偏好不匹配"
        
        print("✅ 用户画像保存和加载成功")
        
        # 测试偏好摘要字段
        assert "food" in loaded_profile.preference_summary, "食物偏好字段不存在"
        assert "music" in loaded_profile.preference_summary, "音乐偏好字段不存在"
        assert "activity" in loaded_profile.preference_summary, "活动偏好字段不存在"
        assert "habit" in loaded_profile.preference_summary, "习惯偏好字段不存在"
        assert "work" in loaded_profile.preference_summary, "工作偏好字段不存在"
        
        print("✅ 偏好摘要字段验证成功")
        
        # 测试合成时间戳
        assert hasattr(loaded_profile, "last_synthesized"), "合成时间戳字段不存在"
        print(f"✅ 合成时间戳: {loaded_profile.last_synthesized}")
        
        print("\n== Profile 增强功能测试通过 ==\n")


def test_episode_management():
    """测试 Episode 管理功能"""
    with tempfile.TemporaryDirectory() as temp_dir:
        print("=== 测试 Episode 管理功能 ===")
        
        manager = MemoryManager(db_path=os.path.join(temp_dir, "test_db"))
        
        # 测试保存成功的 Episode
        success = manager.save_episode(
            context="用户想要查天气",
            action="使用天气工具查询当前天气",
            outcome="positive",
            tool_used="weather_tool"
        )
        
        assert success, "保存成功 Episode 失败"
        print("✅ 成功 Episode 保存成功")
        
        # 测试保存失败的 Episode
        success = manager.save_episode(
            context="用户想要查天气",
            action="使用天气工具查询当前天气",
            outcome="negative",
            tool_used="weather_tool"
        )
        
        assert success, "保存失败 Episode 失败"
        print("✅ 失败 Episode 保存成功")
        
        # 测试检索相似 Episode
        similar_episodes = manager.retrieve_similar_episodes("查天气")
        assert len(similar_episodes) >= 2, "未找到足够的相似 Episode"
        print(f"✅ 找到 {len(similar_episodes)} 个相似 Episode")
        
        print("\n== Episode 管理功能测试通过 ==\n")


def test_profile_synthesis():
    """测试 Profile 合成功能"""
    with tempfile.TemporaryDirectory() as temp_dir:
        print("=== 测试 Profile 合成功能 ===")
        
        manager = MemoryManager(db_path=os.path.join(temp_dir, "test_db"))
        
        # 保存一些用户记忆
        manager.save_user_memory("用户喜欢吃火锅", metadata={"category": "food"})
        manager.save_user_memory("用户不喜欢辣的食物", metadata={"category": "food"})
        manager.save_user_memory("用户喜欢听周杰伦的音乐", metadata={"category": "music"})
        manager.save_user_memory("用户习惯晚睡", metadata={"category": "habit"})
        
        print("✅ 用户记忆保存成功")
        
        # 测试合成功能
        success = manager.synthesize_profile_from_collection()
        assert success, "Profile 合成失败"
        
        # 验证合成结果
        profile = manager.load_profile()
        assert len(profile.preference_summary["food"]) > 0, "食物偏好合成失败"
        assert len(profile.preference_summary["music"]) > 0, "音乐偏好合成失败"
        assert len(profile.preference_summary["habit"]) > 0, "习惯偏好合成失败"
        
        print("✅ Profile 合成功能测试通过")
        print(f"食物偏好: {profile.preference_summary['food']}")
        print(f"音乐偏好: {profile.preference_summary['music']}")
        print(f"习惯偏好: {profile.preference_summary['habit']}")
        
        print("\n== Profile 合成功能测试通过 ==\n")


def test_memory_context_retrieval():
    """测试记忆上下文检索功能"""
    with tempfile.TemporaryDirectory() as temp_dir:
        print("=== 测试记忆上下文检索功能 ===")
        
        manager = MemoryManager(db_path=os.path.join(temp_dir, "test_db"))
        
        # 保存用户记忆
        manager.save_user_memory("用户喜欢吃火锅", metadata={"category": "food"})
        manager.save_user_memory("用户喜欢听周杰伦的音乐", metadata={"category": "music"})
        
        # 保存一些 Episode
        manager.save_episode(
            context="用户想要查天气",
            action="使用天气工具查询当前天气",
            outcome="positive",
            tool_used="weather_tool"
        )
        
        # 检索记忆上下文
        context = manager.retrieve_memory_context("我饿了，想吃点东西")
        
        # 验证返回结果
        assert "profile_summary" in context, "缺少 Profile 摘要"
        assert "detailed_memories" in context, "缺少详细记忆"
        assert "few_shot_examples" in context, "缺少 Few-shot 示例"
        
        print("✅ 记忆上下文结构验证成功")
        print(f"Profile 摘要: {context['profile_summary']}")
        print(f"详细记忆: {context['detailed_memories']}")
        print(f"Few-shot 示例: {context['few_shot_examples']}")
        
        print("\n== 记忆上下文检索功能测试通过 ==\n")


if __name__ == "__main__":
    print("开始测试记忆系统增强功能...")
    print("=" * 50)
    
    try:
        # 检查环境变量
        if "VOLCENGINE_API_KEY" not in os.environ:
            print("⚠️  警告: 未设置 VOLCENGINE_API_KEY 环境变量")
            print("某些功能（如 LLM 相关）可能无法正常工作")
            print("")
        
        # 运行测试
        test_profile_enhancement()
        test_episode_management()
        test_profile_synthesis()
        test_memory_context_retrieval()
        
        print("=" * 50)
        print("🎉 所有记忆系统增强功能测试通过！")
        print("\n已实现的功能：")
        print("- ✅ Profile 模式增强：扩展了用户画像结构")
        print("- ✅ Few-shot Learning (Episodic Memory)：添加了情景记忆")
        print("- ✅ Profile 自动合成：从用户记忆中自动生成摘要")
        print("- ✅ 检索优化：优先返回 Profile 摘要")
        print("- ✅ Episode 管理：保存和检索相似交互情景")
        print("- ✅ Few-shot 示例注入：在规划时使用相似案例")
        
    except Exception as e:
        print("\n❌ 测试失败:")
        print(f"错误: {e}")
        import traceback
        print("\n详细信息:")
        print(traceback.format_exc())
        sys.exit(1)
