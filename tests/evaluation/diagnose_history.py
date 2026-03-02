#!/usr/bin/env python3
"""
诊断对话历史传递问题
验证 setup 阶段的对话历史是否正确传递到 test 阶段
"""

import os
import sys

# 添加项目根目录到路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from dotenv import load_dotenv
load_dotenv()

def run_diagnosis():
    """运行诊断"""
    print("=" * 60)
    print("🔍 对话历史传递诊断")
    print("=" * 60)
    
    # 1. 初始化 Agent
    print("\n[Step 1] 初始化 Agent...")
    from tests.evaluation.agent_adapter import RealAgentAdapter
    agent = RealAgentAdapter(verbose=True)
    
    # 2. Reset 后检查初始状态
    print("\n[Step 2] Reset 后检查初始状态...")
    agent.reset()
    print(f"   History 长度: {len(agent.current_state.get('history', []))}")
    print(f"   History 内容: {agent.current_state.get('history', [])}")
    
    # 3. 执行 Setup 对话
    print("\n[Step 3] 执行 Setup 对话...")
    setup_input = "我昨天去看电影了"
    print(f"   发送: {setup_input}")
    response1 = agent.chat(setup_input)
    print(f"   收到: {response1[:100]}...")
    
    # 检查状态
    print(f"\n   [检查点 A] Setup 后的 History:")
    history = agent.current_state.get('history', [])
    print(f"   - 长度: {len(history)}")
    for i, conv in enumerate(history):
        print(f"   - [{i}] user: {conv.get('user', '')[:50]}")
        print(f"         assistant: {conv.get('assistant', '')[:50]}")
    
    # 4. 执行 Test 对话
    print("\n[Step 4] 执行 Test 对话...")
    test_input = "好看吗？"
    print(f"   发送: {test_input}")
    
    # 在 invoke 之前检查状态
    print(f"\n   [检查点 B] Test 前的 state.history:")
    pre_history = agent.current_state.get('history', [])
    print(f"   - 长度: {len(pre_history)}")
    
    response2 = agent.chat(test_input)
    print(f"   收到: {response2[:100]}...")
    
    # 5. 分析结果
    print("\n" + "=" * 60)
    print("📊 诊断结果")
    print("=" * 60)
    
    if len(pre_history) == 0:
        print("❌ 问题确认：Setup 后的 history 没有被保留到 Test 阶段")
        print("   根本原因：_update_state_from_result 可能没有正确更新 history")
    elif "电影" in response2 or "影" in response2:
        print("✅ 对话历史传递正常，LLM 正确理解了上下文")
    else:
        print("⚠️ 对话历史传递正常，但 LLM 没有正确利用上下文")
        print(f"   期望回复中包含 '电影' 相关内容")
        print(f"   实际回复: {response2}")
    
    # 6. 最终状态检查
    print(f"\n   [检查点 C] Test 后的 History:")
    final_history = agent.current_state.get('history', [])
    print(f"   - 长度: {len(final_history)}")
    for i, conv in enumerate(final_history):
        print(f"   - [{i}] user: {conv.get('user', '')[:50]}")
        print(f"         assistant: {conv.get('assistant', '')[:50]}")


if __name__ == "__main__":
    run_diagnosis()
