
import os
import sys
import shutil
from unittest.mock import MagicMock, patch

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock modules
sys.modules['src.model_manager'] = MagicMock()
# sys.modules['src.prompt_utils'] = MagicMock() # Let's try not to aggressive mock everything first

# Mock get_model_manager
mock_model_manager = MagicMock()
sys.modules['src.model_manager'].get_model_manager = MagicMock(return_value=mock_model_manager)


# Mock OllamaEmbeddings
class MockEmbeddings:
    def embed_documents(self, texts):
        return [[0.1] * 1024 for _ in texts]
    def embed_query(self, text):
        return [0.1] * 1024

# Patch imports
# We need patches to apply when importing modules
with patch('src.memory_manager.OllamaEmbeddings', return_value=MockEmbeddings()):
    from src.memory_manager import MemoryManager
    from src.pattern_scanner import PatternScanner

def test_extended_impact():
    test_db_path = "./data/test_chroma_db_extended"
    
    # Cleanup
    if os.path.exists(test_db_path):
        shutil.rmtree(test_db_path)
        
    print("--- Initializing MemoryManager ---")
    mm = MemoryManager(db_path=test_db_path)
    
    # --- Test 1: Pattern Scanner Direct Access ---
    print("\n[Test 1] Pattern Scanner Direct Access")
    # Pattern Scanner reads accessing mm.user_memory_store.get()
    
    # 1.1 Populate pattern data (bypass deduplication by mocking check_similarity)
    print("   Populating pattern data...")
    # Add monthly pattern: "发工资" on 10th
    with patch.object(mm, 'check_similarity', return_value=None):
        for i in range(3):
            # Batch i
            mm.save_user_memory(f"发工资啦! (第 {i} 批)", metadata={"day_of_month": 10})
        
        # Add weekly pattern: "周五好开心" (Contains "开心", which is a registered keyword)
        for i in range(3):
             mm.save_user_memory(f"周五好开心! (第 {i} 周)", metadata={"weekday": 4})

    # 1.2 Run Scanner
    print("   Running PatternScanner...")
    scanner = PatternScanner(mm)
    patterns = scanner.scan_all_patterns()
    
    print(f"   Patterns found: {len(patterns)}")
    for p in patterns:
        print(f"   - {p['type']}: {p['frequency']} ({p['sample_content']})")
        
    # Validation
    monthly_found = any(p['type'] == 'monthly' and p['day_of_month'] == 10 for p in patterns)
    weekly_found = any(p['type'] == 'weekly' and p['weekday'] == 4 for p in patterns)
    
    if monthly_found and weekly_found:
        print("✅ Pattern Scanner works (Direct Chroma access logic preserved)")
    else:
        print("❌ Pattern Scanner failed to find inserted patterns")
        
    # --- Test 2: State Manager Profile Sync ---
    print("\n[Test 2] State Manager Profile Retrieve")
    # State Manager calls retrieve_user_profile() during init
    
    # 2.1 Populate profile data
    mm.save_user_memory("我的名字叫爱丽丝", metadata={"category": "user_profile"})
    mm.save_user_memory("我住在上海", metadata={"category": "user_profile"})
    
    # 2.2 Call retrieve_user_profile
    profile_text = mm.retrieve_user_profile()
    print(f"   Retrieved Profile Text:\n{profile_text}")
    
    # Validation
    # retrieve_user_profile uses complex filtering logic (category $in [...])
    if "爱丽丝" in profile_text and "上海" in profile_text:
        print("✅ retrieve_user_profile works (Chroma filtering logic preserved)")
    else:
         print("❌ retrieve_user_profile failed to return data")

    # Cleanup
    if os.path.exists(test_db_path):
        shutil.rmtree(test_db_path)
    print("\n--- Extended Impact Verification Complete ---")

if __name__ == "__main__":
    test_extended_impact()
