# test_entity_registry.py
"""
EntityRegistry 模块的单元测试
测试实体注册、别名解析、信息合并和引用解析
"""

import pytest
import os
import json
import tempfile
import sys

# 添加 src 到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from src.entity_registry import (
    EntityRegistry, 
    Entity, 
    EntityType, 
    get_entity_registry
)


@pytest.fixture
def temp_registry():
    """创建临时注册表用于测试"""
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        temp_path = f.name
    
    registry = EntityRegistry(storage_path=temp_path)
    yield registry
    
    # 清理
    if os.path.exists(temp_path):
        os.remove(temp_path)


class TestEntityRegistration:
    """测试实体注册功能"""
    
    def test_register_new_entity(self, temp_registry):
        """测试注册新实体"""
        entity_id = temp_registry.register_entity(
            entity_type=EntityType.PERSON,
            name="小明",
            attributes={"occupation": "程序员"}
        )
        
        assert entity_id is not None
        assert entity_id.startswith("entity_")
        
        # 验证实体已保存
        entity = temp_registry.get_entity_by_id(entity_id)
        assert entity is not None
        assert entity.name == "小明"
        assert entity.type == EntityType.PERSON
        assert entity.attributes.get("occupation") == "程序员"
    
    def test_register_duplicate_updates_existing(self, temp_registry):
        """测试重复注册会更新已有实体"""
        # 第一次注册
        entity_id1 = temp_registry.register_entity(
            entity_type=EntityType.PERSON,
            name="小明",
            attributes={"occupation": "程序员"}
        )
        
        # 第二次注册（同名）
        entity_id2 = temp_registry.register_entity(
            entity_type=EntityType.PERSON,
            name="小明",
            attributes={"company": "腾讯"}
        )
        
        # 应该返回同一个ID
        assert entity_id1 == entity_id2
        
        # 验证属性已合并
        entity = temp_registry.get_entity_by_id(entity_id1)
        assert entity.attributes.get("occupation") == "程序员"
        assert entity.attributes.get("company") == "腾讯"
        assert entity.mention_count == 2


class TestEntityLookup:
    """测试实体查找功能"""
    
    def test_find_entity_by_name(self, temp_registry):
        """测试通过名称查找实体"""
        temp_registry.register_entity(
            entity_type=EntityType.PLACE,
            name="公园"
        )
        
        entity = temp_registry.find_entity("公园")
        assert entity is not None
        assert entity.name == "公园"
    
    def test_find_entity_by_alias(self, temp_registry):
        """测试通过别名查找实体"""
        temp_registry.register_entity(
            entity_type=EntityType.PERSON,
            name="小明",
            aliases=["明哥", "那个朋友"]
        )
        
        # 通过别名查找
        entity1 = temp_registry.find_entity("明哥")
        entity2 = temp_registry.find_entity("那个朋友")
        
        assert entity1 is not None
        assert entity2 is not None
        assert entity1.name == "小明"
        assert entity1.id == entity2.id
    
    def test_find_entity_with_type_filter(self, temp_registry):
        """测试按类型过滤查找"""
        # 注册同名不同类型的实体
        temp_registry.register_entity(EntityType.PERSON, "Apple")
        temp_registry.register_entity(EntityType.OBJECT, "Apple")
        
        # 按类型查找
        person = temp_registry.find_entity("Apple", EntityType.PERSON)
        obj = temp_registry.find_entity("Apple", EntityType.OBJECT)
        
        assert person is not None
        assert obj is not None
        assert person.type == EntityType.PERSON
        assert obj.type == EntityType.OBJECT
    
    def test_find_nonexistent_entity(self, temp_registry):
        """测试查找不存在的实体"""
        entity = temp_registry.find_entity("不存在的实体")
        assert entity is None


class TestEntityRelations:
    """测试实体关系功能"""
    
    def test_add_relation(self, temp_registry):
        """测试添加实体关系"""
        person_id = temp_registry.register_entity(EntityType.PERSON, "小明")
        place_id = temp_registry.register_entity(EntityType.PLACE, "腾讯")
        
        # 添加关系
        success = temp_registry.add_relation(person_id, "works_at", place_id)
        assert success
        
        # 验证关系
        person = temp_registry.get_entity_by_id(person_id)
        assert len(person.relations) == 1
        assert person.relations[0]["type"] == "works_at"
        assert person.relations[0]["target_id"] == place_id
    
    def test_get_related_entities(self, temp_registry):
        """测试获取相关实体"""
        person_id = temp_registry.register_entity(EntityType.PERSON, "小明")
        place1_id = temp_registry.register_entity(EntityType.PLACE, "公司")
        place2_id = temp_registry.register_entity(EntityType.PLACE, "家")
        
        temp_registry.add_relation(person_id, "works_at", place1_id)
        temp_registry.add_relation(person_id, "lives_at", place2_id)
        
        related = temp_registry.get_related_entities(person_id)
        assert len(related) == 2


class TestReferenceResolution:
    """测试引用解析功能"""
    
    def test_resolve_pronoun_with_context(self, temp_registry):
        """测试代词解析（结合上下文）"""
        person_id = temp_registry.register_entity(EntityType.PERSON, "小明")
        
        # 使用最近实体列表解析代词
        entity = temp_registry.resolve_reference("他", recent_entities=[person_id])
        
        assert entity is not None
        assert entity.name == "小明"
    
    def test_resolve_direct_reference(self, temp_registry):
        """测试直接引用解析"""
        temp_registry.register_entity(EntityType.PLACE, "公园")
        
        entity = temp_registry.resolve_reference("公园")
        assert entity is not None
        assert entity.name == "公园"


class TestBatchRegistration:
    """测试批量注册功能"""
    
    def test_register_from_extraction(self, temp_registry):
        """测试从 LLM 提取结果批量注册"""
        entities_dict = {
            "persons": [
                {"name": "小明", "role": "friend"},
                {"name": "小红", "role": "colleague"}
            ],
            "places": [
                {"name": "公园", "type": "outdoor"},
                {"name": "公司", "type": "workplace"}
            ],
            "objects": [
                {"name": "咖啡"}
            ]
        }
        
        entity_ids = temp_registry.register_from_extraction(entities_dict)
        
        # 应该注册 5 个实体（跳过"用户"）
        assert len(entity_ids) == 5
        
        # 验证统计
        stats = temp_registry.get_stats()
        assert stats["person"] == 2
        assert stats["place"] == 2
        assert stats["object"] == 1
    
    def test_register_from_extraction_skips_user(self, temp_registry):
        """测试批量注册会跳过'用户'实体"""
        entities_dict = {
            "persons": [
                {"name": "用户", "role": "subject"},
                {"name": "小明", "role": "friend"}
            ]
        }
        
        entity_ids = temp_registry.register_from_extraction(entities_dict)
        
        # 只应该注册 1 个实体（小明）
        assert len(entity_ids) == 1
        
        stats = temp_registry.get_stats()
        assert stats["person"] == 1


class TestPersistence:
    """测试持久化功能"""
    
    def test_save_and_load(self):
        """测试保存和加载"""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            temp_path = f.name
        
        try:
            # 创建注册表并添加实体
            registry1 = EntityRegistry(storage_path=temp_path)
            entity_id = registry1.register_entity(
                EntityType.PERSON, 
                "小明",
                attributes={"age": 25}
            )
            
            # 创建新的注册表实例（从文件加载）
            registry2 = EntityRegistry(storage_path=temp_path)
            
            # 验证数据已加载
            entity = registry2.get_entity_by_id(entity_id)
            assert entity is not None
            assert entity.name == "小明"
            assert entity.attributes.get("age") == 25
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
