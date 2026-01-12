import unittest
import os
import shutil
import json
from unittest.mock import MagicMock, patch
# Setup paths
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.state import UserProfile
from src.memory_manager import MemoryManager
from src.tools import update_profile_tool, query_user_memory_tool, AVAILABLE_TOOLS

class TestProfileMemory(unittest.TestCase):
    def setUp(self):
        # 使用临时目录进行测试
        self.test_db_path = "./data/test_db"
        if os.path.exists(self.test_db_path):
            shutil.rmtree(self.test_db_path)
        os.makedirs(self.test_db_path)
        
        # Mock 环境变量和 Embeddings
        self.env_patcher = patch.dict(os.environ, {"VOLCENGINE_API_KEY": "test_key"})
        self.env_patcher.start()
        
        self.embed_patcher = patch("src.memory_manager.OllamaEmbeddings")
        self.embed_patcher.start()
        
        self.chroma_patcher = patch("src.memory_manager.Chroma")
        self.chroma_patcher.start()
        
        self.manager = MemoryManager(db_path=self.test_db_path)
        # Mock memory store
        self.manager.user_memory_store = MagicMock()

    def tearDown(self):
        self.env_patcher.stop()
        self.embed_patcher.stop()
        self.chroma_patcher.stop()
        if os.path.exists(self.test_db_path):
            shutil.rmtree(self.test_db_path)

    def test_profile_persistence(self):
        """测试用户画像的持久化 (JSON 读写)"""
        # 1. 初始状态应该是空的
        profile = self.manager.load_profile()
        self.assertIsInstance(profile, UserProfile)
        self.assertIsNone(profile.name)
        
        # 2. 保存画像
        new_profile = UserProfile(name="TestUser", home_city="TestCity")
        self.manager.save_profile(new_profile)
        
        # 3. 验证文件是否存在
        profile_path = os.path.join(self.test_db_path, "user_profile.json")
        self.assertTrue(os.path.exists(profile_path))
        
        # 4. 重新加载并验证
        loaded_profile = self.manager.load_profile()
        self.assertEqual(loaded_profile.name, "TestUser")
        self.assertEqual(loaded_profile.home_city, "TestCity")
        
    def test_update_profile(self):
        """测试更新画像字段"""
        # 1. 初始化
        initial_profile = UserProfile(name="OldName", home_city="OldCity")
        self.manager.save_profile(initial_profile)
        
        # 2. 更新
        self.manager.update_profile({"name": "NewName", "current_location": "NewLoc"})
        
        # 3. 验证
        updated = self.manager.load_profile()
        self.assertEqual(updated.name, "NewName")          # 已更新
        self.assertEqual(updated.home_city, "OldCity")     # 保持不变
        self.assertEqual(updated.current_location, "NewLoc") # 新增
        
    def test_smart_caching(self):
        """测试 Smart Caching 逻辑"""
        # 0. 准备：先创建一个文件，确保 exists 返回 True
        profile_path = os.path.join(self.test_db_path, "user_profile.json")
        with open(profile_path, "w") as f:
            json.dump({"name": "Test"}, f)
            
        # 1. 首次加载
        profile1 = self.manager.load_profile()
        # 此时 load_profile 会读取文件并设置缓存
        self.assertIsNotNone(self.manager._profile_cache)
        self.manager._profile_mtime = 100.0 # 强制设置 mtime 以配合后续 Mock
        
        # 2. Mock os.path.getmtime
        with patch("os.path.getmtime", return_value=100.0):
            # mtime 没变，应该返回缓存
            profile2 = self.manager.load_profile()
            self.assertIs(profile1, profile2)  # 对象应该是同一个引用
            
        # 3. mtime 变化
        with patch("os.path.getmtime", return_value=200.0):
            # 必须创建文件 (虽然已经有了，但为了模拟写操作)
            with open(profile_path, "w") as f:
                json.dump({"name": "New"}, f)
                
            profile3 = self.manager.load_profile()
            self.assertIsNot(profile1, profile3)
            self.assertEqual(profile3.name, "New")

    def test_update_profile_tool(self):
        """测试通过 Tool 更新画像 (JSON Patch)"""
        mock_nodes = MagicMock()
        mock_nodes.get_memory_manager.return_value = self.manager
        
        with patch.dict(sys.modules, {'nodes': mock_nodes}):
            # 1. 有效的 JSON
            updates = json.dumps({"home_city": "Shanghai", "name": "Alice"})
            result = update_profile_tool.invoke({"updates": updates})
            self.assertIn("已更新用户画像", result)
            
            profile = self.manager.load_profile()
            self.assertEqual(profile.home_city, "Shanghai")
            self.assertEqual(profile.name, "Alice")
            
            # 2. 无效的 JSON
            result = update_profile_tool.invoke({"updates": "invalid json"})
            self.assertIn("错误", result)
            
            # 3. 验证校验逻辑（update_profile 内部调用 _validate_profile_updates）
            # 尝试更新不支持的字段
            updates = json.dumps({"invalid_field": "xxx", "name": "Bob"})
            result = update_profile_tool.invoke({"updates": updates})
            profile = self.manager.load_profile()
            self.assertEqual(profile.name, "Bob")
            self.assertFalse(hasattr(profile, "invalid_field"))

    def test_query_user_memory_tool(self):
        """测试记忆检索工具"""
        # Mock retrieve_user_memory
        mock_doc = MagicMock()
        mock_doc.page_content = "User likes apples"
        self.manager.retrieve_user_memory = MagicMock(return_value=[mock_doc])
        
        mock_nodes = MagicMock()
        mock_nodes.get_memory_manager.return_value = self.manager
        
        with patch.dict(sys.modules, {'nodes': mock_nodes}):
            # 注意：tool_node 负责注入 history 并调用 rewrite，
            # 但 tool 本身只接收 query。这里测试 tool 函数本身。
            result = query_user_memory_tool.invoke({"query": "food"})
            
            # query_user_memory_tool 的逻辑比较简单，只是调用 retrieve_user_memory
            # history 的注入是在 nodes.py 的 tool_node 中处理的，不是在 tool 函数内部
            # 所以这里只验证 tool 函数本身的行为
            self.assertIn("User likes apples", result)
            self.manager.retrieve_user_memory.assert_called_with("food", k=3)

if __name__ == '__main__':
    unittest.main()
