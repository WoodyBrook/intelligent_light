# entity_registry.py
"""
实体注册表模块 - 本体论增强记忆架构的核心组件

管理所有识别的实体（人物、地点、事件、物品），支持：
- 实体注册与去重
- 别名解析
- 跨会话实体引用
- 渐进式信息合并
"""

import os
import json
import time
import uuid
from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from difflib import SequenceMatcher


class EntityType(str, Enum):
    """实体类型枚举"""
    PERSON = "person"      # 人物：小明、妈妈、领导
    PLACE = "place"        # 地点：公司、北京、咖啡店
    EVENT = "event"        # 事件类型：发工资、开会、聚会
    OBJECT = "object"      # 物品：手机、咖啡、书
    TIME = "time"          # 时间实体：每月10号、周五


class Entity(BaseModel):
    """实体数据模型"""
    id: str = Field(default_factory=lambda: f"entity_{uuid.uuid4().hex[:8]}")
    type: EntityType
    name: str                           # 主名称
    aliases: List[str] = []             # 别名列表
    attributes: Dict[str, Any] = {}     # 属性字典
    relations: List[Dict[str, str]] = []  # 关系列表 [{"type": "friend_of", "target_id": "..."}]
    first_mentioned: float = Field(default_factory=time.time)
    last_mentioned: float = Field(default_factory=time.time)
    mention_count: int = 1


class EntityRegistry:
    """
    实体注册表：管理所有识别的实体
    
    功能：
    - 注册新实体 / 更新已有实体
    - 通过名称或别名查找实体
    - 合并实体属性
    - 解析代词引用（结合上下文）
    """
    
    def __init__(self, storage_path: str = "./data/entity_registry.json"):
        """
        初始化实体注册表
        
        Args:
            storage_path: 实体存储文件路径
        """
        self.storage_path = storage_path
        self.entities: Dict[str, Entity] = {}
        self._load()
        print(f"EntityRegistry 初始化完成，已加载 {len(self.entities)} 个实体")
    
    def _load(self) -> None:
        """从文件加载实体"""
        if not os.path.exists(self.storage_path):
            # 创建目录
            os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
            return
        
        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                entities_data = data.get("entities", {})
                for entity_id, entity_dict in entities_data.items():
                    # 转换 type 字符串回 EntityType
                    entity_dict["type"] = EntityType(entity_dict["type"])
                    self.entities[entity_id] = Entity(**entity_dict)
        except Exception as e:
            print(f"[WARN] 加载实体注册表失败: {e}")
    
    def _save(self) -> None:
        """保存实体到文件"""
        try:
            os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
            data = {
                "version": "1.0",
                "entities": {
                    eid: entity.model_dump() 
                    for eid, entity in self.entities.items()
                },
                "last_updated": time.time()
            }
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)
        except Exception as e:
            print(f"[ERROR] 保存实体注册表失败: {e}")
    
    def register_entity(
        self, 
        entity_type: EntityType, 
        name: str, 
        attributes: Optional[Dict[str, Any]] = None,
        aliases: Optional[List[str]] = None
    ) -> str:
        """
        注册新实体或更新已有实体
        
        Args:
            entity_type: 实体类型
            name: 实体名称
            attributes: 实体属性
            aliases: 别名列表
            
        Returns:
            实体ID
        """
        # 1. 检查是否已存在（通过名称或别名）
        existing = self.find_entity(name, entity_type)
        
        if existing:
            # 更新已有实体
            self.merge_entity_info(existing.id, attributes or {})
            if aliases:
                for alias in aliases:
                    if alias not in existing.aliases and alias != existing.name:
                        existing.aliases.append(alias)
            existing.last_mentioned = time.time()
            existing.mention_count += 1
            self._save()
            print(f"   更新实体: {existing.name} (ID: {existing.id})")
            return existing.id
        
        # 2. 创建新实体
        entity = Entity(
            type=entity_type,
            name=name,
            aliases=aliases or [],
            attributes=attributes or {}
        )
        self.entities[entity.id] = entity
        self._save()
        print(f"   注册新实体: {name} (类型: {entity_type.value}, ID: {entity.id})")
        return entity.id
    
    def find_entity(
        self, 
        name_or_alias: str, 
        entity_type: Optional[EntityType] = None,
        fuzzy_threshold: float = 0.8
    ) -> Optional[Entity]:
        """
        通过名称或别名查找实体
        
        Args:
            name_or_alias: 名称或别名
            entity_type: 可选的类型过滤
            fuzzy_threshold: 模糊匹配阈值
            
        Returns:
            找到的实体，或 None
        """
        name_lower = name_or_alias.lower().strip()
        
        for entity in self.entities.values():
            # 类型过滤
            if entity_type and entity.type != entity_type:
                continue
            
            # 精确匹配
            if entity.name.lower() == name_lower:
                return entity
            
            # 别名精确匹配
            for alias in entity.aliases:
                if alias.lower() == name_lower:
                    return entity
            
            # 模糊匹配（针对较长名称）
            if len(name_or_alias) >= 2:
                similarity = SequenceMatcher(None, entity.name.lower(), name_lower).ratio()
                if similarity >= fuzzy_threshold:
                    return entity
        
        return None
    
    def merge_entity_info(self, entity_id: str, new_attributes: Dict[str, Any]) -> bool:
        """
        合并新属性到已有实体
        
        Args:
            entity_id: 实体ID
            new_attributes: 新属性
            
        Returns:
            是否成功合并
        """
        if entity_id not in self.entities:
            return False
        
        entity = self.entities[entity_id]
        for key, value in new_attributes.items():
            if value is not None:
                # 如果是列表，追加而非覆盖
                if isinstance(value, list) and key in entity.attributes:
                    existing = entity.attributes[key]
                    if isinstance(existing, list):
                        entity.attributes[key] = list(set(existing + value))
                        continue
                entity.attributes[key] = value
        
        self._save()
        return True
    
    def add_relation(
        self, 
        source_id: str, 
        relation_type: str, 
        target_id: str
    ) -> bool:
        """
        添加实体间关系
        
        Args:
            source_id: 源实体ID
            relation_type: 关系类型 (如 "friend_of", "works_at", "located_in")
            target_id: 目标实体ID
            
        Returns:
            是否成功添加
        """
        if source_id not in self.entities or target_id not in self.entities:
            return False
        
        relation = {"type": relation_type, "target_id": target_id}
        
        # 避免重复
        if relation not in self.entities[source_id].relations:
            self.entities[source_id].relations.append(relation)
            self._save()
            print(f"   添加关系: {self.entities[source_id].name} --[{relation_type}]--> {self.entities[target_id].name}")
        
        return True
    
    def get_related_entities(self, entity_id: str) -> List[Entity]:
        """
        获取与指定实体相关的所有实体
        
        Args:
            entity_id: 实体ID
            
        Returns:
            相关实体列表
        """
        if entity_id not in self.entities:
            return []
        
        related = []
        for relation in self.entities[entity_id].relations:
            target_id = relation.get("target_id")
            if target_id in self.entities:
                related.append(self.entities[target_id])
        
        return related
    
    def resolve_reference(
        self, 
        reference: str, 
        recent_entities: Optional[List[str]] = None
    ) -> Optional[Entity]:
        """
        解析代词或模糊引用
        
        Args:
            reference: 引用词（如 "他", "那个朋友", "上次提到的人"）
            recent_entities: 最近提到的实体ID列表（用于代词解析）
            
        Returns:
            解析到的实体，或 None
        """
        reference_lower = reference.lower().strip()
        
        # 1. 代词映射
        pronouns_to_type = {
            "他": EntityType.PERSON,
            "她": EntityType.PERSON,
            "它": EntityType.OBJECT,
            "那里": EntityType.PLACE,
            "那个地方": EntityType.PLACE,
            "那个人": EntityType.PERSON,
            "那个朋友": EntityType.PERSON,
        }
        
        if reference_lower in pronouns_to_type and recent_entities:
            target_type = pronouns_to_type[reference_lower]
            # 从最近实体中找符合类型的
            for eid in reversed(recent_entities):
                if eid in self.entities and self.entities[eid].type == target_type:
                    return self.entities[eid]
        
        # 2. 尝试直接查找
        return self.find_entity(reference)
    
    def register_from_extraction(self, entities_dict: Dict[str, List[Dict]]) -> List[str]:
        """
        从 LLM 提取结果批量注册实体
        
        Args:
            entities_dict: LLM 提取的实体字典，格式：
                {
                    "persons": [{"name": "小明", "role": "friend"}],
                    "places": [{"name": "公园", "type": "outdoor"}],
                    "objects": [{"name": "手机"}]
                }
                
        Returns:
            注册的实体ID列表
        """
        entity_ids = []
        
        type_mapping = {
            "persons": EntityType.PERSON,
            "places": EntityType.PLACE,
            "objects": EntityType.OBJECT,
            "events": EntityType.EVENT
        }
        
        for key, entities in entities_dict.items():
            entity_type = type_mapping.get(key)
            if not entity_type:
                continue
            
            for entity_info in entities:
                if not isinstance(entity_info, dict):
                    continue
                
                name = entity_info.get("name")
                if not name or name == "用户":  # 跳过"用户"本身
                    continue
                
                # 提取属性（排除 name 和 role）
                attributes = {k: v for k, v in entity_info.items() if k not in ["name", "role"]}
                
                entity_id = self.register_entity(
                    entity_type=entity_type,
                    name=name,
                    attributes=attributes
                )
                entity_ids.append(entity_id)
        
        return entity_ids
    
    def get_all_entities(self, entity_type: Optional[EntityType] = None) -> List[Entity]:
        """
        获取所有实体（可按类型过滤）
        
        Args:
            entity_type: 可选的类型过滤
            
        Returns:
            实体列表
        """
        if entity_type:
            return [e for e in self.entities.values() if e.type == entity_type]
        return list(self.entities.values())
    
    def get_entity_by_id(self, entity_id: str) -> Optional[Entity]:
        """获取指定ID的实体"""
        return self.entities.get(entity_id)
    
    def get_stats(self) -> Dict[str, int]:
        """获取实体统计信息"""
        stats = {t.value: 0 for t in EntityType}
        for entity in self.entities.values():
            stats[entity.type.value] += 1
        stats["total"] = len(self.entities)
        return stats


# 全局单例
_entity_registry: Optional[EntityRegistry] = None


def get_entity_registry(storage_path: str = "./data/entity_registry.json") -> EntityRegistry:
    """获取实体注册表单例"""
    global _entity_registry
    if _entity_registry is None:
        _entity_registry = EntityRegistry(storage_path)
    return _entity_registry
