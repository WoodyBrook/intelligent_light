"""
测试基于模型的路由分类器 (Model-Based Router)
验证 Doubao-Lite 是否能正确区分 FAST/CHAT/REASONING 场景
"""
import sys
import os
import time

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.model_manager import ModelManager

def test_router_classification():
    print("=== Model-Based Router Classification Test ===")
    
    # 初始化 ModelManager
    # 注意：运行此测试需要真实 API Key
    try:
        mm = ModelManager()
    except Exception as e:
        print(f"Skipping test: ModelManager initialization failed ({e})")
        return

    test_cases = [
        # --- FAST Cases ---
        ("Hi", "fast"),
        ("Hello", "fast"),
        ("OK", "fast"),
        ("Thanks", "fast"),
        ("Bye", "fast"),
        
        # --- CHAT Cases ---
        ("I feel a bit sad today.", "chat"),
        ("What do you think about love?", "chat"),
        ("Im so bored", "chat"),
        
        # --- REASONING Cases ---
        ("Plan a 3-day trip to Tokyo", "reasoning"),
        ("Compare Python and Rust performance", "reasoning"),
        ("Why is the sky blue? Explain in physics.", "reasoning"),
        ("What time is it now?", "reasoning"), # Tool dependent query usually reasoning
        ("Solve this math problem: 24 * 14", "reasoning"),
    ]
    
    correct_count = 0
    total_time = 0
    
    print(f"\nRunning {len(test_cases)} test cases...\n")
    
    for input_text, expected_tier in test_cases:
        start_time = time.time()
        
        # Call select_model logic (simulating auto mode)
        llm, model_name = mm.select_model(task_type="auto", user_input=input_text)
        tier = mm.get_model_tier(model_name)
        
        elapsed = time.time() - start_time
        total_time += elapsed
        
        status = "✅" if tier == expected_tier else f"❌ (Expected {expected_tier})"
        print(f"{status} [{elapsed:.2f}s] Input: '{input_text}' -> {tier.upper()}")
        
        if tier == expected_tier:
            correct_count += 1
            
    print(f"\nAccuracy: {correct_count}/{len(test_cases)} ({correct_count/len(test_cases)*100:.1f}%)")
    print(f"Avg Latency: {total_time/len(test_cases):.3f}s")
    
    if correct_count / len(test_cases) > 0.8:
        print("\n✅ Router Logic Verification Passed")
    else:
        print("\n❌ Router Logic Verification Failed (< 80% accuracy)")

if __name__ == "__main__":
    test_router_classification()
