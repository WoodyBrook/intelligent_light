#!/usr/bin/env python3
"""
本体论增强记忆系统 - 端到端测试脚本
测试 extract_episodic_memory 的结构化提取和实体注册
"""

import os
import sys
import json

# 确保项目根目录在路径中
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# 加载环境变量
from dotenv import load_dotenv
load_dotenv()

def test_entity_extraction():
    """测试实体提取功能"""
    print("=" * 60)
    print("🧪 本体论增强记忆系统 - 端到端测试")
    print("=" * 60)
    
    # 初始化 MemoryManager
    print("\n📦 初始化 MemoryManager...")
    from src.memory_manager import MemoryManager
    
    try:
        memory_manager = MemoryManager()
    except Exception as e:
        print(f"❌ MemoryManager 初始化失败: {e}")
        return
    
    # 测试用例
    test_cases = [
        {
            "user_input": "今天我在公司收到了人才补贴",
            "llm_response": "恭喜你收到人才补贴！这是对你能力的认可。",
            "description": "工作事件 + 地点 + 周期性"
        },
        {
            "user_input": "刚刚和小明在咖啡店聊了聊工作的事",
            "llm_response": "和朋友聊天放松一下挺好的",
            "description": "社交事件 + 人物 + 地点"
        },
        {
            "user_input": "今天去了趟公园，喷泉很漂亮",
            "llm_response": "公园散步确实很惬意",
            "description": "休闲活动 + 地点 + 物品"
        }
    ]
    
    print(f"\n🔬 将测试 {len(test_cases)} 个场景\n")
    
    for i, case in enumerate(test_cases, 1):
        print("-" * 60)
        print(f"📝 测试 {i}: {case['description']}")
        print(f"   用户输入: \"{case['user_input']}\"")
        print("-" * 60)
        
        result = memory_manager.extract_episodic_memory(
            case["user_input"], 
            case["llm_response"]
        )
        
        if result:
            print(f"\n   ✅ 提取成功!")
            print(f"   📄 内容: {result.get('content', 'N/A')}")
            print(f"   ⭐ 重要性: {result.get('importance', 'N/A')}")
            print(f"   📂 分类: {result.get('category', 'N/A')}")
            
            # 显示实体
            entities = result.get("entities", {})
            if any(entities.values()):
                print(f"\n   🏷️ 提取的实体:")
                for etype, items in entities.items():
                    if items:
                        names = [item.get("name", "?") for item in items]
                        print(f"      - {etype}: {', '.join(names)}")
            
            # 显示时间信息
            temporal = result.get("temporal", {})
            if temporal.get("is_recurring"):
                print(f"\n   🔄 周期性: {temporal.get('recurrence_pattern', '?')}")
            
            # 显示动作信息
            action = result.get("action", {})
            if action.get("verb"):
                print(f"   🎬 动作: {action.get('verb')} ({action.get('type', '?')})")
        else:
            print(f"\n   ⚠️ 未提取到事件信息")
        
        print()
    
    # 测试实体注册
    print("=" * 60)
    print("🏷️ 测试实体注册功能")
    print("=" * 60)
    
    from src.entity_registry import get_entity_registry
    
    # 使用临时路径避免污染正式数据
    import tempfile
    temp_path = os.path.join(tempfile.gettempdir(), "test_entity_registry.json")
    
    from src.entity_registry import EntityRegistry
    registry = EntityRegistry(storage_path=temp_path)
    
    # 模拟从提取结果注册实体
    sample_entities = {
        "persons": [{"name": "小明", "role": "friend"}],
        "places": [
            {"name": "公司", "type": "workplace"},
            {"name": "咖啡店", "type": "restaurant"}
        ],
        "objects": [{"name": "人才补贴"}]
    }
    
    print(f"\n📥 注册实体...")
    entity_ids = registry.register_from_extraction(sample_entities)
    print(f"   注册了 {len(entity_ids)} 个实体")
    
    # 显示统计
    stats = registry.get_stats()
    print(f"\n📊 实体统计:")
    for etype, count in stats.items():
        if count > 0:
            print(f"   - {etype}: {count}")
    
    # 测试查找
    print(f"\n🔍 测试查找功能:")
    entity = registry.find_entity("小明")
    if entity:
        print(f"   找到实体: {entity.name} (ID: {entity.id})")
    
    # 清理临时文件
    if os.path.exists(temp_path):
        os.remove(temp_path)
    
    print("\n" + "=" * 60)
    print("✅ 测试完成!")
    print("=" * 60)


if __name__ == "__main__":
    test_entity_extraction()
