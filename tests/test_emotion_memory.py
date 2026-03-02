import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.memory_manager import MemoryManager

def test_emotion_extraction():
    print("--- Testing Emotion Extraction ---")
    mm = MemoryManager()
    
    # Test Case 1: High Intensity Negative Emotion
    user_input = "我今天工作太累了，老板还一直骂我，真的好想哭，烦死了！"
    llm_response = "听起来你今天真的很辛苦，抱抱你。"
    
    print(f"\n📝 Input: {user_input}")
    result = mm.extract_user_emotion(user_input, llm_response)
    print(f"📊 Result: {result}")
    
    if result:
        print(f"✅ Extracted: {result.get('emotion')} (Intensity: {result.get('intensity')})")
        if result.get('intensity', 0) >= 6:
            print("   💾 Triggered Long-term Memory Save logic (validated by intensity)")
        else:
            print("   ⚠️ Intensity too low for long-term save")
    else:
        print("❌ Failed to extract emotion")

    # Test Case 2: Neutral Input
    user_input_neutral = "今天天气怎么样？"
    print(f"\n📝 Input: {user_input_neutral}")
    result_neutral = mm.extract_user_emotion(user_input_neutral, "今天天气不错。")
    print(f"📊 Result: {result_neutral}")
    
    if result_neutral is None:
        print("✅ Correctly ignored neutral input")
    else:
        print(f"❌ Should be None, but got: {result_neutral}")

if __name__ == "__main__":
    test_emotion_extraction()
