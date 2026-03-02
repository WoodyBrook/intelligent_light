
import sys
import os
sys.path.append(os.getcwd())

from src.memory_manager import MemoryManager

def reproduce_name_update_issue():
    print("🚀 Starting Name Update Reproduction")
    
    # Use a test DB path
    test_db_path = "./data/test_chroma_db_name_repro"
    if os.path.exists(test_db_path):
        import shutil
        shutil.rmtree(test_db_path)
        
    mm = MemoryManager(db_path=test_db_path)
    
    user_input = "以后叫我456"
    llm_response = "好呀，456~以后我就这么叫你啦！"
    
    print(f"\n📝 User Input: {user_input}")
    print(f"🤖 LLM Response: {llm_response}")
    
    print("\n🔍 Extracting profile information...")
    results = mm.extract_and_save_user_profile(user_input, llm_response)
    
    print(f"\n📊 Extraction Results: {results}")
    
    # Check if name update was extracted
    name_update_found = False
    for item in results:
        updates = item.get("updates", {})
        if "name" in updates and updates["name"] == "456":
            name_update_found = True
            break
            
    if name_update_found:
        print("\n✅ SUCCESS: Name update extracted correctly")
    else:
        print("\n❌ FAILED: Name update NOT extracted")

if __name__ == "__main__":
    reproduce_name_update_issue()
