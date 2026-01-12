import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from src.mcp_manager import MCPManager, ToolInfo

@pytest.fixture
def mcp_manager():
    return MCPManager(token_file="test_tokens.json")

@pytest.mark.asyncio
async def test_add_stdio_server(mcp_manager):
    # Mock stdio_client and ClientSession
    mock_read = MagicMock()
    mock_write = MagicMock()
    
    mock_cm = AsyncMock()
    mock_cm.__aenter__.return_value = (mock_read, mock_write)
    
    mock_session = AsyncMock()
    mock_tool = MagicMock()
    mock_tool.name = "test_tool"
    mock_tool.description = "A test tool"
    mock_tool.inputSchema = {}
    mock_session.list_tools.return_value = MagicMock(tools=[mock_tool])
    
    with patch('mcp_manager.stdio_client', return_value=mock_cm), \
         patch('mcp_manager.ClientSession', return_value=mock_session):
        
        await mcp_manager.add_stdio_server("test_server", "python", ["--version"])
        
        assert "test_server" in mcp_manager.clients
        assert "test_tool" in mcp_manager.tool_registry
        assert mcp_manager.tool_registry["test_tool"].server_name == "test_server"

def test_setup_oauth_client(mcp_manager):
    mcp_manager.setup_oauth_client(
        "google", "client_id", "client_secret", 
        "https://auth.url", "https://token.url", ["scope1"]
    )
    
    assert "google" in mcp_manager.server_configs
    assert mcp_manager.server_configs["google"]["client_id"] == "client_id"

def test_tokens_save_load(mcp_manager):
    mcp_manager.tokens = {"google": {"access_token": "abc"}}
    mcp_manager._save_tokens()
    
    new_manager = MCPManager(token_file="test_tokens.json")
    assert new_manager.tokens["google"]["access_token"] == "abc"
    
    # Cleanup
    import os
    if os.path.exists("test_tokens.json"):
        os.remove("test_tokens.json")

