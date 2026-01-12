# MCP 工具文档实现总结

## 概述

已完成 MCP 工具文档的完善，为所有工具（本地工具 + MCP 工具）生成详细的 XML 格式文档，包含参数说明、使用示例、错误处理指南等，大幅提升 LLM 工具调用的准确性。

## 改进内容

### 1. 创建工具文档生成器 (`tool_documentation.py`)

**核心功能**：
- `ToolDocumentationGenerator`：统一管理所有工具的文档
- `ToolDocumentation`：工具文档数据类，包含完整信息
- XML 格式化：所有文档使用 XML 标签结构化

**文档包含内容**：
- **描述**：工具的功能说明
- **参数**：详细的参数说明（类型、是否必需、默认值、示例）
- **使用示例**：输入输出示例
- **错误处理**：常见错误和应对方法
- **返回格式**：工具返回的数据格式
- **使用提示**：最佳实践和注意事项

### 2. 本地工具文档（预定义）

为所有本地工具创建了详细文档：

#### weather_tool（天气工具）
- **参数**：`city`（城市名称）
- **示例**：北京、上海天气查询
- **错误处理**：城市不存在、API 失败的处理方法
- **使用提示**：可以从用户画像中获取城市信息

#### news_tool（新闻工具）
- **参数**：`keyword`（关键词，可选）、`limit`（数量，默认3）
- **示例**：关键词过滤、通用新闻列表
- **错误处理**：API 失败、无匹配结果的处理
- **使用提示**：可以根据用户兴趣自动设置关键词

#### time_tool（时间工具）
- **参数**：`timezone`（时区，默认"北京"）
- **示例**：北京、纽约、伦敦时间查询
- **错误处理**：时区不支持的处理
- **使用提示**：默认使用"北京"时区

#### calculator_tool（计算器工具）
- **参数**：`expression`（数学表达式）
- **示例**：基本运算、带括号的计算
- **错误处理**：不安全字符、无效表达式的处理
- **安全限制**：只允许数字、运算符和括号

#### wikipedia_tool（维基百科工具）
- **参数**：`query`（搜索关键词）
- **示例**：知识性查询
- **错误处理**：查询失败、无结果的处理
- **使用提示**：适合回答知识性问题

### 3. MCP 工具文档（动态生成）

**支持格式**：
- JSON Schema 格式（标准 MCP 工具）
- 简单字典格式（兼容其他格式）

**自动提取**：
- 工具名称和描述
- 参数类型和说明
- 必需参数列表
- 枚举值（如果有）

### 4. XML 格式输出

**XML 结构**：
```xml
<available_tools>
<local_tools>
  <tool name="weather_tool">
    <description>获取指定城市的天气信息...</description>
    <parameters>
      <parameter name="city" type="string" required="required">
        <description>城市名称，如'北京'、'上海'、'深圳'</description>
        <examples>北京, 上海, 深圳</examples>
      </parameter>
    </parameters>
    <examples>
      <example number="1">
        <description>查询北京天气</description>
        <input>{"city": "北京"}</input>
        <output>北京天气：\n温度：25°C...</output>
      </example>
    </examples>
    <error_handling>
      - 如果城市名称不存在或无法查询，返回"未知"状态
      - 如果 API 调用失败，返回友好的错误提示
    </error_handling>
    <return_format>字符串格式的天气信息...</return_format>
    <usage_tips>如果用户没有指定城市，可以从用户画像中获取常住地或当前位置</usage_tips>
  </tool>
  ...
</local_tools>
<mcp_tools>
  <tool name="check_unread_emails" type="mcp">
    <description>检查未读邮件</description>
    <parameters>...</parameters>
    <usage_tips>...</usage_tips>
  </tool>
  ...
</mcp_tools>
</available_tools>
```

### 5. 集成到系统

**修改文件**：
- `mcp_manager.py`：添加 `get_enhanced_tool_descriptions()` 方法
- `nodes.py`：使用增强的工具文档替代简单描述

**使用方式**：
```python
# 在 reasoning_node 中
mcp_manager = get_mcp_manager()
tool_descriptions = mcp_manager.get_enhanced_tool_descriptions()
# 自动生成包含所有工具的 XML 格式文档
```

## 优势

### 1. 提升工具调用准确性
- **详细参数说明**：LLM 能准确理解每个参数的类型和用途
- **使用示例**：提供输入输出示例，帮助 LLM 理解工具用法
- **错误处理指南**：LLM 知道如何处理错误情况

### 2. 统一的文档格式
- **XML 结构化**：与 System Prompt 的 XML 结构化保持一致
- **统一接口**：本地工具和 MCP 工具使用相同的文档格式
- **易于扩展**：新增工具只需添加文档定义

### 3. 更好的可维护性
- **集中管理**：所有工具文档在一个文件中管理
- **类型安全**：使用 `ToolDocumentation` 数据类确保结构正确
- **易于更新**：修改工具文档只需更新一个地方

### 4. 智能提示
- **使用提示**：帮助 LLM 更好地使用工具（如从用户画像获取城市）
- **最佳实践**：指导 LLM 在什么场景下使用哪个工具

## 测试覆盖

已创建 `tests/unit/test_tool_documentation.py`，包含 7 个测试用例：

1. ✅ `test_tool_doc_generator_init` - 生成器初始化
2. ✅ `test_format_tool_doc_xml` - XML 格式化
3. ✅ `test_get_local_tool_docs_xml` - 本地工具文档
4. ✅ `test_format_mcp_tool_doc` - MCP 工具文档格式化
5. ✅ `test_get_all_tools_xml` - 所有工具文档
6. ✅ `test_tool_doc_examples` - 使用示例
7. ✅ `test_tool_doc_error_handling` - 错误处理说明

所有测试通过 ✅

## 使用示例

### 在 Prompt 中的效果

**改进前**：
```
🔧 可用工具：
- weather_tool: 获取天气信息，参数：city（城市名，如'北京'）
- news_tool: 获取新闻，参数：keyword（关键词，可选）, limit（数量，默认3）
```

**改进后**：
```xml
<available_tools>
<local_tools>
  <tool name="weather_tool">
    <description>获取指定城市的天气信息，包括温度、天气状况、湿度、风力等</description>
    <parameters>
      <parameter name="city" type="string" required="required">
        <description>城市名称，如'北京'、'上海'、'深圳'</description>
        <examples>北京, 上海, 深圳</examples>
      </parameter>
    </parameters>
    <examples>
      <example number="1">
        <description>查询北京天气</description>
        <input>{"city": "北京"}</input>
        <output>北京天气：\n温度：25°C\n天气：晴...</output>
      </example>
    </examples>
    <error_handling>
      - 如果城市名称不存在或无法查询，返回"未知"状态
      - 如果 API 调用失败，返回友好的错误提示
    </error_handling>
    <return_format>字符串格式的天气信息，包含温度、天气状况、湿度、风力、建议</return_format>
    <usage_tips>如果用户没有指定城市，可以从用户画像中获取常住地或当前位置</usage_tips>
  </tool>
  ...
</local_tools>
</available_tools>
```

## 对比分析

### 改进前的问题

1. **描述过于简单**：只有工具名称和基本参数
2. **缺少示例**：LLM 不知道如何正确调用
3. **缺少错误处理**：LLM 不知道如何处理错误
4. **格式不统一**：本地工具和 MCP 工具格式不一致

### 改进后的优势

1. **详细文档**：包含完整的参数说明、示例、错误处理
2. **XML 结构化**：与 System Prompt 保持一致，提升 LLM 理解
3. **统一格式**：本地工具和 MCP 工具使用相同的文档格式
4. **智能提示**：帮助 LLM 更好地使用工具

## 修改的文件

1. **`tool_documentation.py`**（新建）
   - `ToolDocumentationGenerator` 类
   - `ToolDocumentation` 数据类
   - XML 格式化方法

2. **`mcp_manager.py`**
   - 添加 `get_enhanced_tool_descriptions()` 方法

3. **`nodes.py`**
   - 使用增强的工具文档替代简单描述

4. **`tests/unit/test_tool_documentation.py`**（新建）
   - 完整的测试覆盖

## 向后兼容性

- ✅ 现有工具调用逻辑不变
- ✅ `get_tool_descriptions()` 方法保留（用于向后兼容）
- ✅ 新增 `get_enhanced_tool_descriptions()` 方法（推荐使用）

## 下一步

MCP 工具文档已完成，可以继续：
1. **增强 ContextManager，支持任务指令的动态注入**（建议在 XML 结构化之后）
2. **自建轻量级技能系统**（可选，建议在动态注入之后）

---

**完成时间**：2025-01-04  
**状态**：✅ 已完成并通过测试

