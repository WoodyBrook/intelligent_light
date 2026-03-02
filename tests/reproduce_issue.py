
import sys
import os
sys.path.append(os.getcwd())

from src.memory_manager import MemoryManager
from src.state import UserProfile

def test_recurring_update():
    print("🚀 Starting Recurring Event Update Test")
    
    # Initialize MemoryManager (using a test specific DB path to avoid messing up real data if possible, 
    # but for reproduction I'll use a temp dir or just be careful. 
    # The user is okay with using the current workspace, but I should be careful.
    # Let's use a temporary path for safety.)
    test_db_path = "./data/test_chroma_db_repro"
    if os.path.exists(test_db_path):
        import shutil
        shutil.rmtree(test_db_path)
    
    mm = MemoryManager(db_path=test_db_path)
    
    # 1. Initial State: Payday is 10th
    print("\n📝 Step 1: Adding initial event 'Payday on 10th'")
    updates_1 = {
        "important_dates": [{"day": 10, "name": "发薪日", "type": "monthly"}]
    }
    mm.update_profile(updates_1)
    
    # Mock extract_and_save_user_profile behavior for ChromaDB
    # We manually call save_user_memory as extract_and_save_user_profile would
    content_1 = "用户每月10号是发薪日"
    mm.save_user_memory(content_1, metadata={"category": "recurring_pattern", "confidence": 0.9})
    
    # Check Profile
    profile = mm.load_profile()
    print(f"   [Profile] Dates: {profile.important_dates}")
    
    # Check Chroma
    results_1 = mm.user_memory_store.similarity_search("发薪日", k=5)
    print(f"   [Chroma] Found {len(results_1)} docs: {[d.page_content for d in results_1]}")
    
    # 2. Update State: Payday changed to 5th
    print("\n📝 Step 2: Updating event 'Payday changed to 5th'")
    updates_2 = {
        "important_dates": [{"day": 5, "name": "发薪日", "type": "monthly"}]
    }
    mm.update_profile(updates_2)
    
    # Mock update conflict resolution
    content_2 = "用户每月5号是发薪日"
    # We mock the correct call that extract_and_save would make now
    mm.detect_and_resolve_conflicts(content_2, "recurring_pattern", event_name="发薪日") 
    mm.save_user_memory(content_2, metadata={"category": "recurring_pattern", "confidence": 0.9})
    
    # Check Profile
    profile = mm.load_profile()
    print(f"   [Profile] Dates: {profile.important_dates}")
    
    # Check Chroma
    results_2 = mm.user_memory_store.similarity_search("发薪日", k=5)
    doc_contents = [d.page_content for d in results_2]
    print(f"   [Chroma] Found {len(results_2)} docs: {doc_contents}")
    
    # Validation
    dates = profile.important_dates
    has_duplicates_profile = len(dates) > 1
    has_duplicates_chroma = len(results_2) > 1
    
    if has_duplicates_profile:
        print("\n❌ FAILED: Profile has duplicate entries for '发薪日'")
    else:
        # Check if it was actually updated
        if dates and dates[0]['day'] == 5:
             print("\n✅ SUCCESS: Profile updated correctly")
        else:
             print("\n❌ FAILED: Profile did not update (kept old value)")

    if has_duplicates_chroma:
         print("❌ FAILED: ChromaDB has duplicate entries")
    else:
         print("✅ SUCCESS: ChromaDB has no duplicates")

if __name__ == "__main__":
    test_recurring_update()
