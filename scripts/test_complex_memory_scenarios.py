#!/usr/bin/env python3
"""
Complex Memory Scenarios Test Script (Chinese)
Tests implicit preference extraction, episodic memory with entities, and context-aware retrieval.
"""
import os
import sys
import tempfile
import json
import time
from typing import Dict, Any

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.memory_manager import MemoryManager

def print_separator(title: str):
    print(f"\n{'='*20} {title} {'='*20}")

def pretty_print(data: Any):
    print(json.dumps(data, indent=2, ensure_ascii=False))

def test_implicit_preferences(manager: MemoryManager):
    print_separator("Scenario 1: Implicit Preference Extraction")
    
    scenarios = [
        {
            "user": "其实我最近在控糖，所以不要给我吃蛋糕。",
            "ai": "明白了，我会注意控制甜食推荐。",
            "desc": "Dietary restriction (Low Sugar)"
        },
        {
            "user": "我不喜欢太吵的地方，会让我焦虑。",
            "ai": "那我们可以选一个安静的咖啡馆。",
            "desc": "Environment preference (Quiet)"
        }
    ]

    for s in scenarios:
        print(f"\nTest Case: {s['desc']}")
        print(f"User: {s['user']}")
        print(f"AI: {s['ai']}")
        
        result = manager.extract_user_preference(s['user'], s['ai'])
        
        if result:
            print("✅ Extracted Preference:")
            pretty_print(result)
            manager.save_user_memory(result['content'], metadata={"category": result['category'], "importance": 8})
        else:
            print("❌ Failed to extract preference")

def test_episodic_memory(manager: MemoryManager):
    print_separator("Scenario 2: Episodic Memory with Rich Entities")
    
    scenarios = [
        {
            "user": "上周末我和Bob去了国家博物馆，看了古代陶器展。",
            "ai": "听起来很有趣！展览怎么样？",
            "desc": "Museum visit with Friend"
        },
         {
            "user": "下周一我在总部有个关于Q3能力的演示汇报。",
            "ai": "祝你好运！需要帮忙准备吗？",
            "desc": "Work presentation (Future event)"
        }
    ]

    for s in scenarios:
        print(f"\nTest Case: {s['desc']}")
        print(f"User: {s['user']}")
        
        result = manager.extract_episodic_memory(s['user'], s['ai'])
        
        if result:
            print("✅ Extracted Episode:")
            pretty_print(result)
            # Save it
            if result:
                manager.save_user_memory(result['content'], metadata=result)
        else:
            print("❌ Failed to extract episode")

def test_context_retrieval(manager: MemoryManager):
    print_separator("Scenario 3: Context-Aware Retrieval")
    
    queries = [
        "我应该避免吃什么？",
        "我和谁去的博物馆？",
        "最近有什么重要的工作吗？"
    ]

    for q in queries:
        print(f"\nQuery: '{q}'")
        results = manager.retrieve_user_memory(q, k=1)
        
        if results:
            print(f"✅ Retrieved: {results[0].page_content}")
            print(f"   Score: {results[0].metadata.get('score', 'N/A')}")
        else:
            print("❌ No relevant memory found")

def main():
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = os.path.join(temp_dir, "test_complex_db_cn")
        print(f"Initializing MemoryManager at {db_path}...")
        
        try:
            manager = MemoryManager(db_path=db_path)
            
            # Run Scenarios
            test_implicit_preferences(manager)
            test_episodic_memory(manager)
            test_context_retrieval(manager)
            
        except Exception as e:
            print(f"Fatal Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    main()
