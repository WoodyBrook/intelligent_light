# tool_documentation.py - 工具文档生成器
# 为 MCP 工具和本地工具生成详细的文档，提升 LLM 工具调用准确性

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import json

@dataclass
class ToolDocumentation:
    """工具文档数据类"""
    name: str
    description: str
    parameters: Dict[str, Any]
    examples: List[Dict[str, Any]]
    error_handling: str
    return_format: str
    usage_tips: Optional[str] = None

class ToolDocumentationGenerator:
    """工具文档生成器"""
    
    def __init__(self):
        # 本地工具文档（预定义）
        self.local_tool_docs = self._init_local_tool_docs()
    
    def _init_local_tool_docs(self) -> Dict[str, ToolDocumentation]:
        """初始化本地工具文档"""
        return {
            "weather_tool": ToolDocumentation(
                name="weather_tool",
                description="获取指定城市的天气信息，包括温度、天气状况、湿度、风力等",
                parameters={
                    "city": {
                        "type": "string",
                        "description": "城市名称，如'北京'、'上海'、'深圳'",
                        "required": True,
                        "examples": ["北京", "上海", "深圳"]
                    }
                },
                examples=[
                    {
                        "input": {"city": "北京"},
                        "output": "北京天气：\n温度：25°C\n天气：晴\n湿度：45%\n风力：3级\n建议：天气不错，适合外出",
                        "description": "查询北京天气"
                    },
                    {
                        "input": {"city": "上海"},
                        "output": "上海天气：\n温度：28°C\n天气：多云\n湿度：65%\n风力：2级\n建议：湿度稍高，注意补水",
                        "description": "查询上海天气"
                    }
                ],
                error_handling="""
- 如果城市名称不存在或无法查询，返回"未知"状态
- 如果 API 调用失败，返回友好的错误提示："抱歉，获取{city}天气信息失败了。"
- 建议：如果用户只说了"天气"，应该询问具体城市或使用用户画像中的城市信息
                """,
                return_format="字符串格式的天气信息，包含温度、天气状况、湿度、风力、建议",
                usage_tips="如果用户没有指定城市，可以从用户画像中获取常住地或当前位置"
            ),
            
            "news_tool": ToolDocumentation(
                name="news_tool",
                description="获取最新新闻信息，支持关键词过滤",
                parameters={
                    "keyword": {
                        "type": "string",
                        "description": "搜索关键词，可选，用于过滤新闻",
                        "required": False,
                        "default": "",
                        "examples": ["科技", "AI", "人工智能"]
                    },
                    "limit": {
                        "type": "integer",
                        "description": "返回新闻数量，默认3条",
                        "required": False,
                        "default": 3,
                        "examples": [3, 5, 10]
                    }
                },
                examples=[
                    {
                        "input": {"keyword": "科技", "limit": 3},
                        "output": "📰 最新新闻（关于科技）：\n\n1. 科技公司发布最新AI模型\n   ...",
                        "description": "获取科技相关新闻"
                    },
                    {
                        "input": {"keyword": "", "limit": 5},
                        "output": "📰 最新新闻：\n\n1. 科技公司发布最新AI模型\n   ...",
                        "description": "获取最新5条新闻（无关键词过滤）"
                    }
                ],
                error_handling="""
- 如果 API 调用失败，返回："抱歉，获取新闻信息失败了。"
- 如果没有找到匹配的新闻，返回："没有找到关于'{keyword}'的新闻。"
- 建议：如果用户没有指定关键词，返回通用新闻列表
                """,
                return_format="格式化的新闻列表，每条包含标题、摘要、时间、来源",
                usage_tips="可以根据用户兴趣（从记忆中提取）自动设置关键词"
            ),
            
            "time_tool": ToolDocumentation(
                name="time_tool",
                description="获取指定时区的时间信息",
                parameters={
                    "timezone": {
                        "type": "string",
                        "description": "时区名称，如'北京'、'纽约'、'伦敦'",
                        "required": False,
                        "default": "北京",
                        "examples": ["北京", "纽约", "伦敦"]
                    }
                },
                examples=[
                    {
                        "input": {"timezone": "北京"},
                        "output": "🕐 北京时间：2025年01月04日 14:30:00（星期五）",
                        "description": "获取北京时间"
                    },
                    {
                        "input": {"timezone": "纽约"},
                        "output": "🕐 纽约时间：2025-01-04 00:30:00",
                        "description": "获取纽约时间"
                    }
                ],
                error_handling="""
- 如果时区不支持，返回："当前时间：{time}（{timezone}时区暂不支持）"
- 如果查询失败，返回："抱歉，获取时间信息失败了。"
                """,
                return_format="格式化的时间字符串，包含日期、时间、星期",
                usage_tips="如果用户只说'现在几点'，默认使用'北京'时区"
            ),
            
            "calculator_tool": ToolDocumentation(
                name="calculator_tool",
                description="执行基本数学计算，支持加减乘除和括号",
                parameters={
                    "expression": {
                        "type": "string",
                        "description": "数学表达式，如'2+3*4'、'(10+5)/3'",
                        "required": True,
                        "examples": ["2+3*4", "(10+5)/3", "100-50"]
                    }
                },
                examples=[
                    {
                        "input": {"expression": "2+3*4"},
                        "output": "🧮 计算结果：2+3*4 = 14",
                        "description": "基本数学运算"
                    },
                    {
                        "input": {"expression": "(10+5)/3"},
                        "output": "🧮 计算结果：(10+5)/3 = 5.0",
                        "description": "带括号的计算"
                    }
                ],
                error_handling="""
- 如果表达式包含不安全字符，返回："抱歉，只支持基本的数学运算。"
- 如果表达式无效，返回："抱歉，无法计算 '{expression}'。请检查表达式是否正确。"
- 安全限制：只允许数字、运算符（+-*/）和括号，不允许其他字符
                """,
                return_format="计算结果字符串，格式：'🧮 计算结果：{expression} = {result}'",
                usage_tips="如果用户说'算一下'，需要从对话历史中提取数学表达式"
            ),
            
            "wikipedia_tool": ToolDocumentation(
                name="wikipedia_tool",
                description="在维基百科中搜索信息，获取知识性内容",
                parameters={
                    "query": {
                        "type": "string",
                        "description": "搜索关键词，如'人工智能'、'机器学习'",
                        "required": True,
                        "examples": ["人工智能", "机器学习", "深度学习"]
                    }
                },
                examples=[
                    {
                        "input": {"query": "人工智能"},
                        "output": "📖 维基百科：人工智能\n人工智能（Artificial Intelligence，AI）是指...",
                        "description": "搜索人工智能相关信息"
                    }
                ],
                error_handling="""
- 如果查询失败，返回："抱歉，维基百科搜索失败了。"
- 如果没有找到结果，返回："关于'{query}'的维基百科信息暂不可用。"
                """,
                return_format="维基百科条目内容，包含标题和详细说明",
                usage_tips="适合回答知识性问题，如'什么是AI'、'机器学习是什么'"
            ),
            
            "web_search_tool": ToolDocumentation(
                name="web_search_tool",
                description="在互联网上搜索实时信息，获取最新的网络内容。适合查询当前事件、新闻、最新资讯等需要实时数据的场景",
                parameters={
                    "query": {
                        "type": "string",
                        "description": "搜索关键词或问题，如'今天北京天气'、'最新AI新闻'、'Python教程'",
                        "required": True,
                        "examples": ["今天北京天气", "最新AI新闻", "Python教程", "2024年科技趋势"]
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "最大返回结果数，默认5条",
                        "required": False,
                        "default": 5,
                        "examples": [3, 5, 10]
                    }
                },
                examples=[
                    {
                        "input": {"query": "今天北京天气", "max_results": 3},
                        "output": "🔍 搜索结果（今天北京天气）：\n\n[搜索结果内容，包含温度、天气状况等信息]",
                        "description": "搜索实时天气信息"
                    },
                    {
                        "input": {"query": "最新AI新闻", "max_results": 5},
                        "output": "🔍 搜索结果（最新AI新闻）：\n\n[最新的AI相关新闻和资讯]",
                        "description": "搜索最新新闻"
                    }
                ],
                error_handling="""
- 如果未配置 BAIDU_SEARCH_API_KEY，返回提示信息，引导用户配置 API Key
- 如果 API Key 无效或过期，返回："抱歉，网络搜索 API Key 无效或已过期。请检查 BAIDU_SEARCH_API_KEY 环境变量。"
- 如果达到使用限额，返回："抱歉，网络搜索已达到使用限额（每日免费100次）。请稍后再试或升级 API 套餐。"
- 如果搜索失败，返回友好的错误提示
- 如果没有找到结果，返回："抱歉，没有找到关于'{query}'的相关信息。"
                """,
                return_format="格式化的搜索结果字符串，包含搜索关键词和相关信息摘要",
                usage_tips="""
- 适合查询需要实时信息的场景，如天气、新闻、最新事件等
- 不适合查询静态知识（这种情况应该使用 wikipedia_tool）
- 如果用户问"查一下"、"搜索一下"等，应该使用此工具
- 注意：需要配置 BAIDU_SEARCH_API_KEY 环境变量才能使用（每日免费100次，国内服务访问稳定）
                """
            )
        }
    
    def format_tool_doc_xml(self, doc: ToolDocumentation) -> str:
        """将工具文档格式化为 XML 格式"""
        xml_parts = [f'<tool name="{doc.name}">']
        
        # 描述
        xml_parts.append(f"  <description>{doc.description}</description>")
        
        # 参数
        xml_parts.append("  <parameters>")
        for param_name, param_info in doc.parameters.items():
            required = "required" if param_info.get("required", False) else "optional"
            default = param_info.get("default", "")
            param_desc = param_info.get("description", "")
            examples = param_info.get("examples", [])
            
            param_type = param_info.get("type", "string")
            xml_parts.append(f'    <parameter name="{param_name}" type="{param_type}" required="{required}">')
            xml_parts.append(f"      <description>{param_desc}</description>")
            if default:
                xml_parts.append(f"      <default>{default}</default>")
            if examples:
                xml_parts.append(f"      <examples>{', '.join(map(str, examples))}</examples>")
            xml_parts.append(f"    </parameter>")
        xml_parts.append("  </parameters>")
        
        # 使用示例
        if doc.examples:
            xml_parts.append("  <examples>")
            for i, example in enumerate(doc.examples, 1):
                xml_parts.append(f"    <example number=\"{i}\">")
                xml_parts.append(f"      <description>{example.get('description', '')}</description>")
                xml_parts.append(f"      <input>{json.dumps(example['input'], ensure_ascii=False)}</input>")
                xml_parts.append(f"      <output>{example['output'][:200]}...</output>")
                xml_parts.append(f"    </example>")
            xml_parts.append("  </examples>")
        
        # 错误处理
        if doc.error_handling:
            xml_parts.append("  <error_handling>")
            xml_parts.append(f"    {doc.error_handling.strip()}")
            xml_parts.append("  </error_handling>")
        
        # 返回格式
        xml_parts.append(f"  <return_format>{doc.return_format}</return_format>")
        
        # 使用提示
        if doc.usage_tips:
            xml_parts.append(f"  <usage_tips>{doc.usage_tips}</usage_tips>")
        
        xml_parts.append("</tool>")
        return "\n".join(xml_parts)
    
    def get_local_tool_docs_xml(self) -> str:
        """获取所有本地工具的 XML 格式文档"""
        xml_parts = ["<local_tools>"]
        for tool_name, doc in self.local_tool_docs.items():
            xml_parts.append(self.format_tool_doc_xml(doc))
        xml_parts.append("</local_tools>")
        return "\n".join(xml_parts)
    
    def format_mcp_tool_doc(self, tool_info: Dict[str, Any]) -> str:
        """格式化 MCP 工具文档为 XML"""
        name = tool_info.get("name", "unknown")
        description = tool_info.get("description", "无描述")
        parameters = tool_info.get("parameters", {})
        
        xml_parts = [f'<tool name="{name}" type="mcp">']
        xml_parts.append(f"  <description>{description}</description>")
        
        # 参数
        if parameters:
            xml_parts.append("  <parameters>")
            if isinstance(parameters, dict):
                # 处理 JSON Schema 格式的参数
                if "properties" in parameters:
                    for param_name, param_schema in parameters["properties"].items():
                        param_type = param_schema.get("type", "string")
                        param_desc = param_schema.get("description", "")
                        required = param_name in parameters.get("required", [])
                        
                        xml_parts.append(f'    <parameter name="{param_name}" type="{param_type}" required="{"required" if required else "optional"}">')
                        if param_desc:
                            xml_parts.append(f"      <description>{param_desc}</description>")
                        if "enum" in param_schema:
                            xml_parts.append(f"      <allowed_values>{', '.join(map(str, param_schema['enum']))}</allowed_values>")
                        xml_parts.append(f"    </parameter>")
                else:
                    # 简单字典格式
                    for param_name, param_info in parameters.items():
                        if isinstance(param_info, dict):
                            param_type = param_info.get("type", "string")
                            param_desc = param_info.get("description", "")
                            xml_parts.append(f'    <parameter name="{param_name}" type="{param_type}">')
                            if param_desc:
                                xml_parts.append(f"      <description>{param_desc}</description>")
                            xml_parts.append(f"    </parameter>")
            xml_parts.append("  </parameters>")
        
        # 通用使用提示
        xml_parts.append("  <usage_tips>")
        xml_parts.append("    - 调用前请确保参数类型和格式正确")
        xml_parts.append("    - 如果调用失败，检查参数是否正确或服务是否可用")
        xml_parts.append("  </usage_tips>")
        
        xml_parts.append("</tool>")
        return "\n".join(xml_parts)
    
    def get_all_tools_xml(self, mcp_tools: List[Dict[str, Any]]) -> str:
        """获取所有工具（本地 + MCP）的 XML 格式文档"""
        xml_parts = ["<available_tools>"]
        
        # 本地工具
        xml_parts.append(self.get_local_tool_docs_xml())
        
        # MCP 工具
        if mcp_tools:
            xml_parts.append("<mcp_tools>")
            for tool in mcp_tools:
                xml_parts.append(self.format_mcp_tool_doc(tool))
            xml_parts.append("</mcp_tools>")
        
        xml_parts.append("</available_tools>")
        return "\n".join(xml_parts)
    
    def get_tool_summary(self) -> str:
        """获取工具摘要（简化版，用于快速参考）"""
        summary = ["<tools_summary>"]
        for tool_name, doc in self.local_tool_docs.items():
            summary.append(f"  <tool name=\"{tool_name}\">")
            summary.append(f"    <description>{doc.description}</description>")
            param_names = list(doc.parameters.keys())
            summary.append(f"    <parameters>{', '.join(param_names)}</parameters>")
            summary.append(f"  </tool>")
        summary.append("</tools_summary>")
        return "\n".join(summary)

# 全局单例
_tool_doc_generator = None

def get_tool_doc_generator() -> ToolDocumentationGenerator:
    """获取工具文档生成器单例"""
    global _tool_doc_generator
    if _tool_doc_generator is None:
        _tool_doc_generator = ToolDocumentationGenerator()
    return _tool_doc_generator

