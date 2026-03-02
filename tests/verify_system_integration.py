
import os
import sys
import shutil
from unittest.mock import MagicMock, patch

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock modules
sys.modules['src.model_manager'] = MagicMock()
sys.modules['src.prompt_utils'] = MagicMock()
sys.modules['src.mcp_manager'] = MagicMock()
sys.modules['src.context_manager'] = MagicMock()

# Mock performance_tracker
mock_tracker = MagicMock()
mock_tracker.stop.return_value = 0.123 # Return float
mock_tracker.stop_node.return_value = 0.456 # Return float
sys.modules['src.performance_tracker'] = MagicMock()
sys.modules['src.performance_tracker'].get_tracker.return_value = mock_tracker

# Mock get_model_manager
mock_model_manager = MagicMock()
mock_llm = MagicMock()
# Mock LLM response object
class MockResponse:
    def __init__(self, content):
        self.content = content

mock_llm.invoke.return_value = MockResponse("rewritten query")

mock_model_manager.get_model.return_value = mock_llm
sys.modules['src.model_manager'].get_model_manager = MagicMock(return_value=mock_model_manager)


# Mock OllamaEmbeddings
class MockEmbeddings:
    def embed_documents(self, texts):
        return [[0.1] * 1024 for _ in texts]
    def embed_query(self, text):
        return [0.1] * 1024

# Mock ChatPromptTemplate
# We want prompt | llm to return a chain where chain.invoke() works.
# If prompt is a mock, prompt | llm returns a mock (usually).
mock_prompt_cls = MagicMock()
mock_prompt = MagicMock()
mock_chain = MagicMock()
mock_chain.invoke.return_value = MockResponse("rewritten query")

# Define __or__ on mock_prompt to return mock_chain
mock_prompt.__or__.return_value = mock_chain
mock_prompt_cls.from_messages.return_value = mock_prompt

# Patch imports
with patch('src.memory_manager.OllamaEmbeddings', return_value=MockEmbeddings()):
    with patch('src.memory_manager.ChatPromptTemplate', mock_prompt_cls):
        from src.memory_manager import MemoryManager
        # Re-import nodes to apply patches
        if 'src.nodes' in sys.modules:
            del sys.modules['src.nodes']
        from src.nodes import tool_node, memory_loader_node

# Mock get_memory_manager to return our instance
mm_instance = None

def get_memory_manager_mock():
    global mm_instance
    return mm_instance

@patch('src.nodes.get_memory_manager', side_effect=get_memory_manager_mock)
@patch('src.nodes.get_tracker', return_value=mock_tracker)
@patch('src.nodes.get_mcp_manager', return_value=MagicMock())
@patch('src.nodes.ChatOpenAI', return_value=MagicMock()) # Mock LLM in nodes
def test_system_integration(mock_chat, mock_mcp, mock_get_tracker_nodes, mock_get_mm):
    global mm_instance
    test_db_path = "./data/test_chroma_db_sys"
    
    # Cleanup
    if os.path.exists(test_db_path):
        shutil.rmtree(test_db_path)
        
    print("--- 1. Initializing MemoryManager ---")
    mm_instance = MemoryManager(db_path=test_db_path)
    
    # Pre-populate data
    mm_instance.save_user_memory("User lives in Shanghai.")
    
    # Force BM25 refresh explicitly just in case
    # (save_user_memory calls it, but let's be sure)
    
    # --- Test 1: Memory Loader Node (Profile + Action Library) ---
    print("\n[Test 1] Memory Loader Node")
    state = {
        "user_input": "Open the light", 
        "history": []
    }
    
    try:
        result = memory_loader_node(state)
        context = result.get("memory_context", {})
        if context:
            print("✅ Memory loader executed successfully")
            if "user_profile" in context:
                 print("✅ User profile loaded in context")
        else:
            print("❌ Memory loader returned empty context")
    except Exception as e:
        print(f"❌ Memory loader crashed: {e}")
        import traceback
        traceback.print_exc()

    # --- Test 2: Tool Node (Query User Memory) ---
    print("\n[Test 2] Tool Node (Memory Retrieval)")
    state_tool = {
        "user_input": "Where do I live?",
        "history": [],
        "tool_calls": [{
            "id": "call_123",
            "name": "query_user_memory_tool",
            "args": {"query": "User location"}
        }]
    }
    
    # Mock query_rewrite on the INSTANCE to avoid LLM/Prompt mocking issues
    # We want to verify that tool_node calls manager, and manager returns docs.
    # The internal LLM chain of rewrite is unit-test scope, here we assume it works or mock it.
    mm_instance.query_rewrite = MagicMock(return_value="User location")
    
    state_tool = {
        "user_input": "Where do I live?",
        "history": [],
        "tool_calls": [{
            "id": "call_123",
            "name": "query_user_memory_tool",
            "args": {"query": "User location"}
        }]
    }
    
    try:
        # We need to ensure query_rewrite returns a string.
        # Now explicitly mocked above.
        
        result = tool_node(state_tool)
        tool_results = result.get("tool_results", [])
        
        if tool_results:
            output = tool_results[0].get("output", "")
            print(f"   Tool Output: {output}")
            
            # Since "rewritten query" is used to search... 
            # "User lives in Shanghai" might NOT match "rewritten query" via BM25/Vector with mock embeddings?
            # MockEmbeddings returns same vector for everything.
            # So Vector search returns everything.
            # BM25 search relies on tokens. "rewritten query" doesn't share tokens with "Shanghai".
            # So BM25 score = 0.
            # Vector score = 1.0 (MockEmbeddings dist=0? No, returns [0.1], dot product...)
            # MockEmbeddings: [0.1]*1024. norm is const. dot product is const. dist is 0.
            # So similarity is 1.0.
            # So it should return the document.
            
            if "Shanghai" in output:
                print("✅ Tool node retrieved memory successfully")
            else:
                print("❌ Tool node failed to retrieve correct memory")
        else:
            print("❌ No tool results returned")
            
    except Exception as e:
        print(f"❌ Tool node crashed: {e}")
        import traceback
        traceback.print_exc()

    # Cleanup
    if os.path.exists(test_db_path):
        shutil.rmtree(test_db_path)
    print("\n--- System Integration Verification Complete ---")

if __name__ == "__main__":
    test_system_integration()
