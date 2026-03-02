# 工具参数提取修复说明

## 问题描述

当用户询问具体新闻事件时（如"微信把元宝的链接屏蔽了"），系统无法正确提取搜索关键词，而是使用默认的"今日热点新闻"进行搜索，导致无法找到相关信息。

## 根本原因

原来的 `news_tool` 参数提取逻辑只匹配预定义的新闻类型关键词（科技、娱乐、体育等），没有提取用户的具体查询内容。

## 解决方案

使用轻量级本地LLM（Ollama llama3.2:3b）进行通用化参数提取：

1. **轻量级**：本地运行，无API调用费用
2. **速度快**：小模型推理快（通常<2秒）
3. **通用化**：能够理解用户意图，提取关键参数
4. **向后兼容**：保留原有的规则提取作为后备方案

## 代码修改

### 1. 新增 `ToolParameterExtractor` 类

位置：`src/nodes.py`

```python
class ToolParameterExtractor:
    """使用轻量级LLM（本地Ollama）提取工具参数"""
    
    def __init__(self, ollama_url: str = "http://localhost:11434", model: str = "llama3.2:3b"):
        self.ollama_url = ollama_url
        self.model = model
        self.timeout = 10
    
    def extract_parameters(self, user_input: str, tool_name: str, tool_schema: dict) -> dict:
        # 构建prompt -> 调用Ollama -> 解析JSON
        ...
```

### 2. 新增工具参数Schema定义

```python
def _get_tool_schema(tool_name: str) -> dict:
    """获取工具的参数schema"""
    schemas = {
        "news_tool": {
            "description": "获取新闻信息",
            "parameters": {
                "keyword": {
                    "type": "string",
                    "description": "搜索关键词，应该是用户关心的具体话题或事件，如'微信屏蔽元宝'、'特斯拉降价'等"
                },
                ...
            }
        },
        ...
    }
```

### 3. 修改 `news_tool` 参数提取逻辑

```python
elif tool_name == "news_tool":
    # 【新】使用LLM提取参数，回退到规则提取
    try:
        extractor = get_parameter_extractor()
        tool_schema = _get_tool_schema("news_tool")
        extracted_args = extractor.extract_parameters(user_input, "news_tool", tool_schema)
        
        if extracted_args and "keyword" in extracted_args:
            tool_args["keyword"] = extracted_args["keyword"]
            print(f"   [LLM提取] news_tool keyword: {extracted_args['keyword']}")
        else:
            # 回退到规则提取
            _extract_news_params_by_rules(user_input, tool_args)
    except Exception as e:
        print(f"[WARN] LLM参数提取失败: {e}，使用规则提取")
        _extract_news_params_by_rules(user_input, tool_args)
    
    tool_args["limit"] = 3
```

## 环境要求

1. **安装Ollama**：https://ollama.com
2. **下载模型**：
   ```bash
   ollama pull llama3.2:3b
   ```
3. **确保Ollama运行**：
   ```bash
   ollama serve
   ```

## 测试

运行演示脚本查看效果：

```bash
python test_prompt_demo.py
```

## 预期效果

**修复前**：
- 用户输入："我今天听到新闻说微信把元宝的链接屏蔽了，发生什么了？"
- 搜索关键词：（空）-> 使用默认"今日热点新闻"
- 结果：找不到相关信息

**修复后**：
- 用户输入："我今天听到新闻说微信把元宝的链接屏蔽了，发生什么了？"
- 搜索关键词："微信屏蔽元宝"
- 结果：找到相关新闻

## 扩展计划

此修复可以扩展到其他工具：
- `weather_tool`: 自动提取城市和时间
- `web_search_tool`: 提取准确的搜索查询
- `create_schedule_tool`: 提取提醒内容和时间

## 注意事项

1. **性能**：轻量级模型通常在1-2秒内响应
2. **容错**：如果LLM提取失败，自动回退到规则提取
3. **配置**：可以通过环境变量配置Ollama URL和模型名称
   ```bash
   export OLLAMA_URL=http://localhost:11434
   export OLLAMA_MODEL=llama3.2:3b
   ```