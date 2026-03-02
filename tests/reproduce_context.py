
import sys
import os
import json

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.context_manager import ContextManager

def test_context_generation():
    # Mock history
    # Turn 1: User asks about Kobe, System answers detailed info
    history = [
        {
            "user": "我叫什么名字？",
            "assistant": "你是789呀。",
            "type": "conversation",
            "timestamp": 1234567890
        },
        {
            "user": "帮我查一下科比的信息",
            "assistant": "我查到了一些关于科比的信息！科比·布莱恩特是美国传奇篮球运动员，整个职业生涯都效力于洛杉矶湖人队，获得了5次NBA总冠军。他的职业生涯分为8号时期和24号时期，8号时期他展现了惊人的天赋和潜力，与奥尼尔组成'OK组合'获得三连冠；24号时期他变得更加成熟全面，又获得了2次总冠军。很遗憾的是，他在2020年因直升机事故不幸去世，年仅41岁。",
            "type": "conversation",
            "timestamp": 1234567990
        }
    ]

    cm = ContextManager()

    # Test Step 1: Compress History
    print("--- Testing History Compression ---")
    compression_result = cm.compress_conversation_history(history)
    formatted_history = cm.format_compressed_history(compression_result)
    print("Formatted History:\n", formatted_history)
    print("-" * 20)

    # Test Step 2: XML Generation
    print("--- Testing XML Generation ---")
    user_profile = "- 姓名: 789\n- 每月5号: 发薪日"
    recent_memories = []
    action_patterns = ["[场景] 用户疲惫/累了..."]

    xml_context = cm.format_context_with_xml(
        user_profile=user_profile,
        recent_memories=recent_memories,
        action_patterns=action_patterns,
        conversation_history=formatted_history,
        current_state={"intimacy_level": 50, "focus_mode": False}
    )

    print("XML Context:\n", xml_context)

if __name__ == "__main__":
    try:
        test_context_generation()
    except Exception as e:
        print(f"Error: {e}")
