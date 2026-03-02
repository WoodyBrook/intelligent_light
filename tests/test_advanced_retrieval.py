"""
测试高级记忆检索功能 (Advanced Memory Retrieval)
- 情境记忆提取 (Episodic Memory)
- Recency/Importance 评分
- 动态权重调整
"""
import sys
import os
import time
from datetime import datetime

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.memory_manager import MemoryManager
from langchain_core.documents import Document


def test_episodic_extraction():
    """测试情境记忆提取"""
    print("=== 1. 情境记忆提取测试 ===")
    mm = MemoryManager()
    
    # Case 1: 应该提取到情境记忆
    input_event = "今天下午和朋友去了环球影城，玩了过山车，排队排了一个小时。"
    result = mm.extract_episodic_memory(input_event, "哇，听起来很刺激，但也挺累的吧？")
    print(f"Input: {input_event}")
    print(f"Result: {result}")
    
    if result and result.get("category") in ["activity", "travel", "social"]:
        print("✅ Pass: 成功提取情境记忆")
    else:
        print("❌ Fail: 未提取到情境记忆或分类错误")
    
    # Case 2: 不应该提取（非事件描述）
    input_neutral = "帮我查一下天气"
    result_neutral = mm.extract_episodic_memory(input_neutral, "今天北京气温5度。")
    print(f"\nInput: {input_neutral}")
    print(f"Result: {result_neutral}")
    
    if result_neutral is None:
        print("✅ Pass: 正确忽略非事件输入")
    else:
        print("❌ Fail: 不应该提取非事件输入")


def test_memory_scoring():
    """测试记忆评分逻辑"""
    print("\n=== 2. 记忆评分测试 ===")
    mm = MemoryManager()
    
    now = time.time()
    
    # Doc A: 很新，中等重要性
    doc_a = Document(
        page_content="User ate an apple",
        metadata={"creation_time": now - 3600, "importance": 5, "date": "2024-01-01"}
    )
    
    # Doc B: 很旧，高重要性
    doc_b = Document(
        page_content="User got married",
        metadata={"creation_time": now - 86400*30, "importance": 10, "date": "2023-12-01"}
    )
    
    # Doc C: 很旧，低重要性
    doc_c = Document(
        page_content="User bought a pen",
        metadata={"creation_time": now - 86400*30, "importance": 2, "date": "2023-12-01"}
    )
    
    # Default weights: α=0.5, β=0.3, γ=0.2
    alpha, beta, gamma = 0.5, 0.3, 0.2
    relevance = 0.8  # 假设相同 relevance
    
    score_a = mm._calculate_memory_score(doc_a, relevance, alpha, beta, gamma)
    score_b = mm._calculate_memory_score(doc_b, relevance, alpha, beta, gamma)
    score_c = mm._calculate_memory_score(doc_c, relevance, alpha, beta, gamma)
    
    print(f"Doc A (Recent/Medium): Score = {score_a:.4f}")
    print(f"Doc B (Old/High):      Score = {score_b:.4f}")
    print(f"Doc C (Old/Low):       Score = {score_c:.4f}")
    
    # 验证：新记忆（即使重要性一般）应该比旧+低重要性的高
    if score_a > score_c:
        print("✅ Pass: 新记忆 > 旧+低重要性记忆")
    else:
        print("❌ Fail: Recency 未正确影响排序")
    
    # 验证：高重要性记忆（即使旧）应该比旧+低重要性的高
    if score_b > score_c:
        print("✅ Pass: 高重要性 > 低重要性")
    else:
        print("❌ Fail: Importance 未正确影响排序")


def test_dynamic_weights():
    """测试动态权重调整"""
    print("\n=== 3. 动态权重测试 ===")
    mm = MemoryManager()
    
    # Default (无特殊关键词)
    w1 = mm._get_dynamic_weights("你记得我说的事情吗？")  # 移除了"之前"
    print(f"Query: 你记得我说的事情吗？ → Weights: {w1}")
    
    # Recency Boost
    w2 = mm._get_dynamic_weights("刚才我说了什么？")
    print(f"Query: 刚才我说了什么？ → Weights: {w2}")
    if w2[1] > w1[1]:  # Beta (Recency) should be higher
        print("✅ Pass: Recency keyword triggered β boost")
    else:
        print("❌ Fail: Recency keyword did not boost β")
    
    # Importance Boost
    w3 = mm._get_dynamic_weights("最重要的事情是什么？")
    print(f"Query: 最重要的事情是什么？ → Weights: {w3}")
    if w3[2] > w1[2]:  # Gamma (Importance) should be higher
        print("✅ Pass: Importance keyword triggered γ boost")
    else:
        print("❌ Fail: Importance keyword did not boost γ")


if __name__ == "__main__":
    test_episodic_extraction()
    test_memory_scoring()
    test_dynamic_weights()
    print("\n=== 所有测试完成 ===")
