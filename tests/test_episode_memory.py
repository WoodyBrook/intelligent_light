"""
测试 Episode 记忆功能
"""
import os
import sys
import tempfile
import shutil

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.memory_manager import MemoryManager


def test_episode_creation_and_retrieval():
    """测试 Episode 的保存和检索功能"""
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # 初始化内存管理器
        manager = MemoryManager(db_path=os.path.join(temp_dir, "test_db"))
        
        # 测试保存 Episode
        context = "用户想要查天气"
        action = "使用天气工具查询当前天气"
        outcome = "positive"
        tool_used = "weather_tool"
        
        success = manager.save_episode(
            context=context,
            action=action,
            outcome=outcome,
            tool_used=tool_used
        )
        
        assert success, "保存 Episode 失败"
        
        # 测试检索相似 Episode
        similar_episodes = manager.retrieve_similar_episodes("查天气", k=1)
        
        assert len(similar_episodes) > 0, "未找到相似的 Episode"
        print("✅ Episode 保存和检索测试通过")


def test_episode_outcome_sorting():
    """测试 Episode 按结果排序"""
    
    with tempfile.TemporaryDirectory() as temp_dir:
        manager = MemoryManager(db_path=os.path.join(temp_dir, "test_db"))
        
        # 保存不同结果的 Episode
        manager.save_episode(
            context="用户想要查天气",
            action="使用天气工具查询当前天气",
            outcome="negative",
            tool_used="weather_tool"
        )
        
        manager.save_episode(
            context="用户想要查天气",
            action="使用天气工具查询当前天气",
            outcome="positive",
            tool_used="weather_tool"
        )
        
        manager.save_episode(
            context="用户想要查天气",
            action="使用天气工具查询当前天气",
            outcome="neutral",
            tool_used="weather_tool"
        )
        
        # 检索相似 Episode
        similar_episodes = manager.retrieve_similar_episodes("查天气", k=3)
        
        assert len(similar_episodes) == 3, "未找到所有保存的 Episode"
        
        # 验证排序：positive 应该排在第一位
        assert similar_episodes[0]["metadata"]["outcome"] == "positive", "positive 结果没有排在第一位"
        
        print("✅ Episode 结果排序测试通过")


if __name__ == "__main__":
    print("开始测试 Episode 记忆功能...")
    
    try:
        test_episode_creation_and_retrieval()
        test_episode_outcome_sorting()
        print("\n🎉 所有测试通过！")
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        print(traceback.format_exc())
