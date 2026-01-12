#!/usr/bin/env python3
"""
清理 ChromaDB 中错误的新闻偏好数据

删除 topics 为 "A", "I", "AI" 等错误数据的记录
"""

import os
import sys

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.memory_manager import MemoryManager


def clean_bad_news_preferences():
    """清理错误的新闻偏好数据"""
    
    print("🔧 初始化 MemoryManager...")
    try:
        memory_manager = MemoryManager()
        print("✅ MemoryManager 初始化完成")
    except Exception as e:
        print(f"❌ 初始化失败: {e}")
        return
    
    if not memory_manager.user_memory_store:
        print("⚠️  用户记忆集合不存在，无需清理")
        return
    
    # 获取所有新闻类别的记忆
    try:
        # 查询所有 category 为 "news" 的记录
        results = memory_manager.user_memory_store.get(
            where={"category": "news"}
        )
        
        documents = results.get("documents", [])
        metadatas = results.get("metadatas", [])
        ids = results.get("ids", [])
        
        print(f"📊 找到 {len(documents)} 条新闻偏好记录")
        
        # 查找需要删除的错误记录
        bad_ids = []
        bad_topics = ["A", "I"]  # 错误拆分的单个字符
        
        for i, metadata in enumerate(metadatas):
            topics = metadata.get("topics", "")
            
            # 检查 topics 是否为错误数据
            if isinstance(topics, str):
                # 检查是否为单个字符 "A" 或 "I"
                if topics in bad_topics:
                    bad_ids.append(ids[i])
                    print(f"   🗑️  发现错误记录: ID={ids[i][:8]}..., topics='{topics}', content='{documents[i][:50]}...'")
                # 检查是否为逗号分隔的字符串，但被错误拆分（如 "A,I"）
                elif "," in topics:
                    topic_list = [t.strip() for t in topics.split(",")]
                    if any(t in bad_topics for t in topic_list):
                        bad_ids.append(ids[i])
                        print(f"   🗑️  发现错误记录: ID={ids[i][:8]}..., topics='{topics}', content='{documents[i][:50]}...'")
            elif isinstance(topics, list):
                # 检查列表中是否包含单个字符
                if any(t in bad_topics for t in topics):
                    bad_ids.append(ids[i])
                    print(f"   🗑️  发现错误记录: ID={ids[i][:8]}..., topics={topics}, content='{documents[i][:50]}...'")
        
        # 删除错误记录
        if bad_ids:
            print(f"\n🗑️  准备删除 {len(bad_ids)} 条错误记录...")
            memory_manager.user_memory_store.delete(ids=bad_ids)
            print(f"✅ 已删除 {len(bad_ids)} 条错误的新闻偏好记录")
        else:
            print("✅ 没有发现需要清理的错误记录")
            
    except Exception as e:
        print(f"❌ 清理失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("=" * 60)
    print("清理错误的新闻偏好数据")
    print("=" * 60)
    clean_bad_news_preferences()
    print("=" * 60)
    print("清理完成")
    print("=" * 60)
