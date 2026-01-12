import pytest
from src.tool_documentation import ToolDocumentationGenerator, ToolDocumentation

def test_tool_doc_generator_init():
    """测试工具文档生成器初始化"""
    generator = ToolDocumentationGenerator()
    assert len(generator.local_tool_docs) > 0
    assert "weather_tool" in generator.local_tool_docs
    assert "news_tool" in generator.local_tool_docs

def test_format_tool_doc_xml():
    """测试工具文档 XML 格式化"""
    generator = ToolDocumentationGenerator()
    doc = generator.local_tool_docs["weather_tool"]
    
    xml = generator.format_tool_doc_xml(doc)
    
    assert "<tool name=\"weather_tool\">" in xml
    assert "<description>" in xml
    assert "<parameters>" in xml
    assert "parameter name=\"city\"" in xml  # 可能包含其他属性
    assert "<examples>" in xml
    assert "<error_handling>" in xml
    assert "<return_format>" in xml

def test_get_local_tool_docs_xml():
    """测试获取所有本地工具的 XML 文档"""
    generator = ToolDocumentationGenerator()
    xml = generator.get_local_tool_docs_xml()
    
    assert "<local_tools>" in xml
    assert "</local_tools>" in xml
    assert "weather_tool" in xml
    assert "news_tool" in xml
    assert "time_tool" in xml

def test_format_mcp_tool_doc():
    """测试 MCP 工具文档格式化"""
    generator = ToolDocumentationGenerator()
    
    mcp_tool = {
        "name": "check_unread_emails",
        "description": "检查未读邮件",
        "parameters": {
            "properties": {
                "important_only": {
                    "type": "boolean",
                    "description": "是否只检查重要邮件"
                }
            },
            "required": []
        }
    }
    
    xml = generator.format_mcp_tool_doc(mcp_tool)
    
    assert "<tool name=\"check_unread_emails\"" in xml
    assert 'type="mcp"' in xml
    assert "<description>检查未读邮件</description>" in xml
    assert "parameter name=\"important_only\"" in xml  # 可能包含其他属性

def test_get_all_tools_xml():
    """测试获取所有工具的 XML 文档"""
    generator = ToolDocumentationGenerator()
    
    mcp_tools = [
        {
            "name": "test_mcp_tool",
            "description": "测试 MCP 工具",
            "parameters": {}
        }
    ]
    
    xml = generator.get_all_tools_xml(mcp_tools)
    
    assert "<available_tools>" in xml
    assert "</available_tools>" in xml
    assert "<local_tools>" in xml
    assert "<mcp_tools>" in xml
    assert "test_mcp_tool" in xml

def test_tool_doc_examples():
    """测试工具文档包含使用示例"""
    generator = ToolDocumentationGenerator()
    doc = generator.local_tool_docs["weather_tool"]
    
    assert len(doc.examples) > 0
    assert "input" in doc.examples[0]
    assert "output" in doc.examples[0]
    assert "description" in doc.examples[0]

def test_tool_doc_error_handling():
    """测试工具文档包含错误处理说明"""
    generator = ToolDocumentationGenerator()
    doc = generator.local_tool_docs["weather_tool"]
    
    assert doc.error_handling
    assert "错误" in doc.error_handling or "失败" in doc.error_handling

