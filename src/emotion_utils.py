"""
情感分析工具函数
包含 Regex 清洗、字段标准化等辅助功能
"""

import re
import json
from typing import Optional, Dict, List
import logging

logger = logging.getLogger(__name__)


def clean_llm_json_output(llm_output: str) -> Optional[str]:
    """
    使用 Regex 清洗 LLM 输出，提取纯净的 JSON 字符串
    
    处理场景：
    1. Markdown 代码块 (```json ... ```)
    2. 前后缀文本 ("好的，这是结果：{...}谢谢")
    3. 注释 (// 或 /* */)
    4. 多余空白字符
    5. 尾随逗号
    6. 中文引号
    7. 无引号键名
    
    Returns:
        清洗后的 JSON 字符串，如果失败则返回 None
    """
    
    if not llm_output or not isinstance(llm_output, str):
        return None
    
    original = llm_output
    
    # ========== 步骤 1: 移除 Markdown 代码块 ==========
    code_block_patterns = [
        r'```(?:json|javascript|js)\s*([\s\S]*?)\s*```',  # 带语言标识
        r'```\s*([\s\S]*?)\s*```',  # 不带语言标识
    ]
    
    for pattern in code_block_patterns:
        match = re.search(pattern, llm_output)
        if match:
            llm_output = match.group(1)
            break
    
    # ========== 步骤 2: 移除前缀文本 ==========
    llm_output = re.sub(r'^[^{]*', '', llm_output)
    
    # ========== 步骤 3: 移除后缀文本 ==========
    last_brace = llm_output.rfind('}')
    if last_brace != -1:
        llm_output = llm_output[:last_brace + 1]
    
    # ========== 步骤 4: 移除注释 ==========
    llm_output = re.sub(r'//.*?$', '', llm_output, flags=re.MULTILINE)
    llm_output = re.sub(r'/\*.*?\*/', '', llm_output, flags=re.DOTALL)
    
    # ========== 步骤 5: 处理尾随逗号 ==========
    llm_output = re.sub(r',(\s*[}\]])', r'\1', llm_output)
    
    # ========== 步骤 6: 标准化引号 ==========
    llm_output = llm_output.replace('"', '"').replace('"', '"')
    llm_output = llm_output.replace(''', "'").replace(''', "'")
    
    # ========== 步骤 7: 修复无引号键名 ==========
    llm_output = re.sub(
        r'(\s*)([a-zA-Z_][a-zA-Z0-9_]*)\s*:',
        r'\1"\2":',
        llm_output
    )
    
    # ========== 步骤 8: 清理多余空白 ==========
    llm_output = re.sub(r'\n\s*\n', '\n', llm_output)
    
    # ========== 步骤 9: 验证基本结构 ==========
    llm_output = llm_output.strip()
    if not llm_output.startswith('{') or not llm_output.endswith('}'):
        logger.warning(f"清洗后不是有效的 JSON 对象结构")
        return None
    
    # ========== 步骤 10: 尝试解析验证 ==========
    try:
        json.loads(llm_output)
        return llm_output
    except json.JSONDecodeError as e:
        logger.warning(f"清洗后仍无法解析 JSON: {e}")
        logger.debug(f"原始输出: {original[:200]}...")
        logger.debug(f"清洗结果: {llm_output[:200]}...")
        return None


def extract_and_clean_json(llm_output: str) -> Optional[Dict]:
    """
    提取并清洗 LLM 输出中的 JSON
    
    Returns:
        解析后的字典，如果失败则返回 None
    """
    cleaned = clean_llm_json_output(llm_output)
    if not cleaned:
        return None
    
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return None


def normalize_emotion_values(data: Dict) -> Dict:
    """
    使用 Regex 标准化情感字段值
    
    处理：
    1. type: 中文映射到英文
    2. intensity: 模糊匹配到标准值
    3. confidence: 百分比转小数
    4. 字符串字段: 去除多余空格
    """
    if not data:
        return data
    
    # ========== 标准化 type ==========
    if "type" in data:
        type_value = str(data["type"]).lower().strip()
        
        # 中文到英文映射
        type_map = {
            "开心": "happy", "快乐": "happy", "高兴": "happy",
            "难过": "sad", "伤心": "sad", "悲伤": "sad",
            "生气": "angry", "愤怒": "angry", "恼火": "angry",
            "疲惫": "tired", "累": "tired", "困": "tired",
            "焦虑": "anxious", "紧张": "anxious", "担心": "anxious",
            "兴奋": "excited", "激动": "excited",
            "困惑": "confused", "迷茫": "confused",
            "感激": "grateful", "感谢": "grateful",
        }
        
        data["type"] = type_map.get(type_value, type_value)
    
    # ========== 标准化 intensity ==========
    if "intensity" in data:
        intensity_value = str(data["intensity"]).lower().strip()
        
        # 使用 Regex 匹配模式
        if re.search(r'(high|高|very|super|extremely|非常|超级|特别)', intensity_value, re.IGNORECASE):
            data["intensity"] = "high"
        elif re.search(r'(low|低|bit|slightly|有点|稍微|一点)', intensity_value, re.IGNORECASE):
            data["intensity"] = "low"
        else:
            data["intensity"] = "medium"
    
    # ========== 标准化 confidence ==========
    if "confidence" in data:
        try:
            conf = float(data["confidence"])
            # 如果是百分比形式（如 92 而不是 0.92）
            if conf > 1.0:
                conf = conf / 100.0
            data["confidence"] = round(conf, 2)
        except (ValueError, TypeError):
            data["confidence"] = 0.5  # 默认值
    
    # ========== 清理字符串字段 ==========
    string_fields = ["label", "context"]
    for field in string_fields:
        if field in data and isinstance(data[field], str):
            data[field] = re.sub(r'\s+', ' ', data[field]).strip()
    
    return data


def validate_emotion_schema(data: Optional[Dict]) -> bool:
    """
    验证情感元数据 Schema 完整性
    
    检查：
    1. 必需字段存在
    2. 枚举值有效
    3. 数值范围正确
    """
    if not data or not isinstance(data, dict):
        return False
    
    # 检查必需字段
    required_fields = ["type", "label", "intensity", "confidence"]
    if not all(field in data for field in required_fields):
        logger.warning(f"缺少必需字段: {[f for f in required_fields if f not in data]}")
        return False
    
    # 检查 type 枚举值
    valid_types = ["happy", "sad", "angry", "tired", "anxious", "excited", "confused", "grateful"]
    if data["type"] not in valid_types:
        logger.warning(f"无效的 type: {data['type']}")
        return False
    
    # 检查 intensity 枚举值
    valid_intensities = ["high", "medium", "low"]
    if data["intensity"] not in valid_intensities:
        logger.warning(f"无效的 intensity: {data['intensity']}")
        return False
    
    # 检查 confidence 范围
    try:
        conf = float(data["confidence"])
        if not (0.0 <= conf <= 1.0):
            logger.warning(f"confidence 超出范围: {conf}")
            return False
    except (ValueError, TypeError):
        logger.warning(f"confidence 不是有效数字: {data['confidence']}")
        return False
    
    return True
