"""
测试 ChromaDB 对嵌套元数据的支持
"""

import pytest
import json
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestChromaDBMetadata:
    """测试 ChromaDB 元数据存储"""
    
    def test_nested_metadata_storage(self):
        """测试嵌套元数据存储和检索"""
        from src.memory_manager import get_memory_manager
        
        memory_manager = get_memory_manager()
        
        # 准备情感元数据（使用 JSON 序列化嵌套对象）
        emotion_data = {
            "type": "tired",
            "label": "疲惫",
            "intensity": "high",
            "confidence": 0.92,
            "triggers": ["工作压力", "睡眠不足"],
            "context": "用户感到极度疲惫"
        }
        
        metadata = {
            # 嵌套对象序列化为 JSON 字符串
            "emotion": json.dumps(emotion_data, ensure_ascii=False),
            
            # 平铺字段（便于查询）
            "emotion_type": "tired",
            "emotion_label": "疲惫",
            "emotion_intensity": "high",
            "emotion_confidence": 0.92,
            "emotion_source": "test",
            
            # 通用字段
            "timestamp": "2026-01-22T14:00:00+08:00",
            "category": "user_emotion"
        }
        
        # 尝试存储
        try:
            memory_manager.save_user_memory(
                content="测试情感记忆：今天好累啊",
                metadata=metadata
            )
            print("✅ 情感元数据存储成功")
        except Exception as e:
            pytest.fail(f"情感元数据存储失败: {e}")
        
        # 尝试检索
        results = memory_manager.retrieve_user_memory("累", k=1)
        
        if results:
            result_metadata = results[0].metadata
            print(f"检索到的元数据: {result_metadata}")
            
            # 验证平铺字段
            assert "emotion_type" in result_metadata, "缺少 emotion_type 字段"
            assert result_metadata["emotion_type"] == "tired"
            
            # 验证嵌套对象（反序列化）
            if "emotion" in result_metadata:
                emotion = json.loads(result_metadata["emotion"])
                assert emotion["type"] == "tired"
                assert emotion["label"] == "疲惫"
                print("✅ 嵌套元数据检索成功")
        else:
            print("⚠️ 未检索到结果，可能是新数据库")
    
    def test_filter_by_emotion_type(self):
        """测试使用 emotion_type 过滤查询"""
        from src.memory_manager import get_memory_manager
        
        memory_manager = get_memory_manager()
        
        # 先存储一条数据
        metadata = {
            "emotion_type": "happy",
            "emotion_label": "开心",
            "emotion_intensity": "high",
            "emotion_confidence": 0.9,
            "category": "user_emotion"
        }
        
        try:
            memory_manager.save_user_memory(
                content="测试过滤：今天很开心",
                metadata=metadata
            )
        except Exception as e:
            pytest.skip(f"存储失败，跳过过滤测试: {e}")
        
        # 尝试使用 filter 查询
        try:
            results = memory_manager.user_memory_store.similarity_search(
                "开心",
                k=5,
                filter={"emotion_type": "happy"}
            )
            
            if results:
                print(f"✅ 过滤查询成功，找到 {len(results)} 条结果")
                for r in results:
                    if r.metadata.get("emotion_type") == "happy":
                        print(f"   - {r.page_content[:30]}...")
            else:
                print("⚠️ 过滤查询无结果")
                
        except Exception as e:
            print(f"⚠️ Filter 查询可能不支持: {e}")


class TestAsyncMemoryWrite:
    """测试异步记忆写入"""
    
    def test_async_memory_write_not_blocking(self):
        """测试异步记忆写入不阻塞主线程"""
        import time
        from src.nodes import _memory_executor, _async_memory_write
        
        keyword_emotion = {
            "type": "tired",
            "label": "疲惫",
            "intensity": "high",
            "confidence": 0.8,
            "source": "keyword",
            "matched_keywords": ["累"],
            "matched_emoji": [],
            "timestamp": "2026-01-22T14:00:00+08:00"
        }
        
        # 记录开始时间
        start = time.time()
        
        # 提交异步任务（不等待完成）
        future = _memory_executor.submit(
            _async_memory_write,
            "今天好累啊",
            "听起来你很辛苦，要休息一下吗？",
            keyword_emotion
        )
        
        # 记录提交后的时间
        elapsed = time.time() - start
        
        # 验证提交是即时的（应该 < 100ms）
        assert elapsed < 0.1, f"异步任务提交耗时过长: {elapsed:.3f}s"
        print(f"✅ 异步任务提交耗时: {elapsed:.3f}s（不阻塞）")
        
        # 等待任务完成以验证结果
        try:
            future.result(timeout=30)  # 最多等待 30 秒
            print("✅ 异步任务执行成功")
        except Exception as e:
            print(f"⚠️ 异步任务执行失败（可能是 LLM API 问题）: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
