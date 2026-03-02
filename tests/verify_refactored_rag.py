
import os
import sys
import shutil
from unittest.mock import MagicMock, patch

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock modules
sys.modules['src.model_manager'] = MagicMock()
sys.modules['src.prompt_utils'] = MagicMock()

# Mock get_model_manager to return a mock LLM
mock_model_manager = MagicMock()
mock_llm = MagicMock()
mock_model_manager.get_model.return_value = mock_llm
sys.modules['src.model_manager'].get_model_manager = MagicMock(return_value=mock_model_manager)

# Mock OllamaEmbeddings
class MockEmbeddings:
    def embed_documents(self, texts):
        return [[0.1] * 1024 for _ in texts]
    def embed_query(self, text):
        return [0.1] * 1024

# Patch the import
with patch('src.memory_manager.OllamaEmbeddings', return_value=MockEmbeddings()):
    from src.memory_manager import MemoryManager

def test_rag_scenarios():
    test_db_path = "./data/test_chroma_db_advanced"
    
    # Cleanup
    if os.path.exists(test_db_path):
        shutil.rmtree(test_db_path)
        
    print("--- Initializing MemoryManager ---")
    mm = MemoryManager(db_path=test_db_path)
    
    # --- Scenario 1: Basic Save & Retrieve ---
    print("\n[Scenario 1] Basic Save & Retrieve")
    mm.save_user_memory("User loves coding in Python.")
    results = mm.retrieve_user_memory("coding Python", k=1)
    if results and "coding in Python" in results[0].page_content:
        print("✅ Basic retrieval passed")
    else:
        print("❌ Basic retrieval failed")

    # --- Scenario 2: Chinese Support (Jieba) ---
    print("\n[Scenario 2] Chinese Support (Jieba)")
    mm.save_user_memory("用户喜欢吃麻辣火锅")
    # BM25 should capture "火锅"
    results_cn = mm.retrieve_user_memory("火锅", k=1)
    if results_cn and "麻辣火锅" in results_cn[0].page_content:
        print("✅ Chinese retrieval passed")
    else:
        print("❌ Chinese retrieval failed")

    # --- Scenario 3: Deduplication / Update ---
    print("\n[Scenario 3] Deduplication & Update")
    # Simulate finding existing doc
    # We need to spy on 'check_similarity' to trick it into returning an existing doc
    # But for a simpler test, we can manually call _update_memory or rely on exact match?
    # Let's try explicitly updating a doc using _update_memory to verify BM25 sync
    doc_id = results[0].metadata["id"]
    new_content = "User loves coding in Python and Rust."
    mm._update_memory(doc_id, new_content, results[0].metadata)
    
    # Verify retrieval gets updated content
    results_upd = mm.retrieve_user_memory("Rust", k=1)
    # Note: Vector store update might take time or be instant MockEmbeddings makes it easy.
    # BM25 refresh is synchronous.
    if results_upd and "Rust" in results_upd[0].page_content:
         print("✅ Update sync to BM25 passed (Retrieved updated content)")
    else:
         print(f"❌ Update sync failed. Got: {results_upd[0].page_content if results_upd else 'None'}")

    # --- Scenario 4: Date/Metadata Context ---
    print("\n[Scenario 4] Date Context")
    # Inject memory with date metadata
    mm.save_user_memory("Meeting on 2026-02-02", metadata={"date": "2026-02-02 10:00:00"})
    
    # Query with date string
    results_date = mm.retrieve_user_memory("2026-02-02", k=1)
    # Should trigger _detect_exact_query -> boost BM25
    if results_date and "Meeting" in results_date[0].page_content:
        print("✅ Date-based retrieval passed")
        print(f"   (Enriched Content: {results_date[0].page_content})")
    else:
        print("❌ Date-based retrieval failed")

    # Cleanup
    if os.path.exists(test_db_path):
        shutil.rmtree(test_db_path)
    print("\n--- All Scenarios Complete ---")

if __name__ == "__main__":
    test_rag_scenarios()
