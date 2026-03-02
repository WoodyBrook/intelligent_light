#!/usr/bin/env python3
"""
演示工具参数提取的Prompt生成
"""

def build_extraction_prompt(user_input: str, tool_name: str, tool_schema: dict) -> str:
    """构建参数提取的prompt"""
    
    prompt = f"""You are a parameter extraction assistant. Extract parameters from the user's input for the specified tool.

User Input: "{user_input}"

Tool Name: {tool_name}
Tool Description: {tool_schema.get('description', '')}

Available Parameters:
"""
    
    # 添加参数说明
    for param_name, param_info in tool_schema.get('parameters', {}).items():
        optional = " (optional)" if param_info.get('optional') else " (required)"
        prompt += f"- {param_name}: {param_info.get('description', '')}{optional}\n"
    
    prompt += """
Extract the parameters and return them as a JSON object. Do not include any other explanation. Format:
{
    "parameter_name1": "extracted_value1",
    "parameter_name2": "extracted_value2"
}

If you cannot extract a parameter:
- For optional parameters: omit them from the JSON
- For required parameters: return an empty string ""

Return only the JSON:
"""
    
    return prompt


def get_tool_schema(tool_name: str) -> dict:
    """获取工具的参数schema"""
    schemas = {
        "news_tool": {
            "description": "获取新闻信息",
            "parameters": {
                "keyword": {
                    "type": "string",
                    "description": "搜索关键词，应该是用户关心的具体话题或事件，如'微信屏蔽元宝'、'特斯拉降价'等"
                },
                "category": {
                    "type": "string",
                    "description": "新闻分类，可选值：tech(科技)、sports(体育)、entertainment(娱乐)、finance(财经)、general(时事)",
                    "optional": True
                }
            }
        }
    }
    return schemas.get(tool_name, {})


def main():
    print("=" * 80)
    print("工具参数提取 - Prompt演示")
    print("=" * 80)
    
    # 测试用例
    test_cases = [
        "我今天听到新闻说微信把元宝的链接屏蔽了，发生什么了？",
        "最近有什么科技新闻吗？",
        "特斯拉降价了，是真的吗？",
        "告诉我今天的财经新闻",
    ]
    
    tool_schema = get_tool_schema("news_tool")
    
    for i, user_input in enumerate(test_cases, 1):
        print(f"\n{'─' * 80}")
        print(f"测试用例 {i}:")
        print(f"用户输入: {user_input}")
        print(f"{'─' * 80}")
        
        prompt = build_extraction_prompt(user_input, "news_tool", tool_schema)
        print("\n生成的Prompt:")
        print(prompt)
        
        print("\n" + "=" * 80)
        print("期望的LLM输出示例:")
        print("=" * 80)
        
        # 期望的输出示例
        if "微信" in user_input and "元宝" in user_input:
            print('{\n    "keyword": "微信屏蔽元宝"\n}')
        elif "科技" in user_input:
            print('{\n    "keyword": "科技",\n    "category": "tech"\n}')
        elif "特斯拉" in user_input:
            print('{\n    "keyword": "特斯拉降价"\n}')
        elif "财经" in user_input:
            print('{\n    "keyword": "财经新闻",\n    "category": "finance"\n}')
        else:
            print('{\n    "keyword": ""\n}')


if __name__ == "__main__":
    main()