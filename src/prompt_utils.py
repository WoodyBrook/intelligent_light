# prompt_utils.py - Prompt 工具函数
"""
提供 LangChain Prompt 相关的工具函数，防止注入和格式错误
"""


def escape_prompt_input(text: str) -> str:
    """
    转义用户输入中的特殊字符，防止 LangChain Prompt 模板注入
    
    LangChain 的 ChatPromptTemplate 会将 {xxx} 识别为变量占位符，
    如果用户输入中包含花括号，会导致 "missing variables" 错误。
    
    这个函数将 { 替换为 {{ ，将 } 替换为 }}，使其成为字面值。
    
    Args:
        text: 用户输入的原始文本
        
    Returns:
        转义后的安全文本
        
    Example:
        >>> escape_prompt_input("我喜欢{川菜}")
        "我喜欢{{川菜}}"
    """
    if not text:
        return text
    
    # 替换花括号为双花括号（LangChain 的转义语法）
    return text.replace("{", "{{").replace("}", "}}")


def safe_format_human_message(template: str, **kwargs) -> str:
    """
    安全地格式化 human message 模板
    
    会自动转义所有 kwargs 中的用户输入值
    
    Args:
        template: 包含 {key} 占位符的模板字符串
        **kwargs: 要填充的变量
        
    Returns:
        格式化后的字符串
        
    Example:
        >>> safe_format_human_message("用户说: {user_input}", user_input="你好{世界}")
        "用户说: 你好{{世界}}"
    """
    # 转义所有用户输入
    escaped_kwargs = {
        key: escape_prompt_input(value) if isinstance(value, str) else value
        for key, value in kwargs.items()
    }
    
    return template.format(**escaped_kwargs)


def create_safe_human_message(user_input: str, prefix: str = "用户输入: ") -> str:
    """
    创建安全的 human message 内容
    
    这是最常用的便捷函数，直接用于 ChatPromptTemplate
    
    Args:
        user_input: 用户的原始输入
        prefix: 消息前缀
        
    Returns:
        安全的消息内容
        
    Example:
        ChatPromptTemplate.from_messages([
            ("system", "..."),
            ("human", create_safe_human_message(user_input))
        ])
    """
    return prefix + escape_prompt_input(user_input)
