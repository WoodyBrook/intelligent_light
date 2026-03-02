"""
测试 emotion_utils 模块的 Regex 清洗和字段标准化功能
"""

import pytest
import json
from src.emotion_utils import (
    clean_llm_json_output,
    extract_and_clean_json,
    normalize_emotion_values,
    validate_emotion_schema
)


class TestCleanLlmJsonOutput:
    """测试 LLM 输出清洗"""
    
    def test_clean_markdown_code_block(self):
        """测试清理 Markdown 代码块"""
        input_text = '''```json
{
    "type": "happy",
    "label": "开心",
    "intensity": "high",
    "confidence": 0.9
}
```'''
        result = clean_llm_json_output(input_text)
        assert result is not None
        parsed = json.loads(result)
        assert parsed["type"] == "happy"
    
    def test_clean_prefix_suffix(self):
        """测试清理前后缀文本"""
        input_text = '''好的，这是分析结果：
{
    "type": "sad",
    "label": "难过",
    "intensity": "medium",
    "confidence": 0.85
}
希望对你有帮助！'''
        result = clean_llm_json_output(input_text)
        assert result is not None
        parsed = json.loads(result)
        assert parsed["type"] == "sad"
    
    def test_clean_trailing_comma(self):
        """测试清理尾随逗号"""
        input_text = '''{
    "type": "tired",
    "label": "疲惫",
    "intensity": "high",
    "confidence": 0.8,
}'''
        result = clean_llm_json_output(input_text)
        assert result is not None
        parsed = json.loads(result)
        assert parsed["type"] == "tired"
    
    def test_clean_chinese_quotes(self):
        """测试清理中文引号"""
        input_text = '''{
    "type": "happy",
    "label": "开心",
    "intensity": "medium",
    "confidence": 0.9
}'''
        result = clean_llm_json_output(input_text)
        assert result is not None
        parsed = json.loads(result)
        assert parsed["label"] == "开心"
    
    def test_invalid_json_returns_none(self):
        """测试无效 JSON 返回 None"""
        input_text = "这不是 JSON 格式"
        result = clean_llm_json_output(input_text)
        assert result is None
    
    def test_empty_input_returns_none(self):
        """测试空输入返回 None"""
        assert clean_llm_json_output("") is None
        assert clean_llm_json_output(None) is None


class TestNormalizeEmotionValues:
    """测试情感字段标准化"""
    
    def test_normalize_chinese_type(self):
        """测试中文情绪类型映射"""
        data = {"type": "开心", "label": "快乐", "intensity": "high", "confidence": 0.9}
        result = normalize_emotion_values(data)
        assert result["type"] == "happy"
    
    def test_normalize_intensity_chinese(self):
        """测试中文强度匹配"""
        data = {"type": "sad", "label": "难过", "intensity": "非常高", "confidence": 0.8}
        result = normalize_emotion_values(data)
        assert result["intensity"] == "high"
        
        data2 = {"type": "sad", "label": "难过", "intensity": "有点低", "confidence": 0.8}
        result2 = normalize_emotion_values(data2)
        assert result2["intensity"] == "low"
    
    def test_normalize_confidence_percentage(self):
        """测试百分比置信度转换"""
        data = {"type": "happy", "label": "开心", "intensity": "medium", "confidence": 92}
        result = normalize_emotion_values(data)
        assert result["confidence"] == 0.92
    
    def test_normalize_confidence_decimal(self):
        """测试小数置信度保持不变"""
        data = {"type": "happy", "label": "开心", "intensity": "medium", "confidence": 0.85}
        result = normalize_emotion_values(data)
        assert result["confidence"] == 0.85


class TestValidateEmotionSchema:
    """测试 Schema 验证"""
    
    def test_valid_schema(self):
        """测试有效 Schema"""
        data = {
            "type": "happy",
            "label": "开心",
            "intensity": "high",
            "confidence": 0.9
        }
        assert validate_emotion_schema(data) is True
    
    def test_missing_required_field(self):
        """测试缺少必需字段"""
        data = {
            "type": "happy",
            "label": "开心",
            "intensity": "high"
            # 缺少 confidence
        }
        assert validate_emotion_schema(data) is False
    
    def test_invalid_type_enum(self):
        """测试无效的 type 枚举值"""
        data = {
            "type": "unknown_emotion",
            "label": "未知",
            "intensity": "high",
            "confidence": 0.9
        }
        assert validate_emotion_schema(data) is False
    
    def test_invalid_intensity_enum(self):
        """测试无效的 intensity 枚举值"""
        data = {
            "type": "happy",
            "label": "开心",
            "intensity": "very_high",  # 无效值
            "confidence": 0.9
        }
        assert validate_emotion_schema(data) is False
    
    def test_confidence_out_of_range(self):
        """测试 confidence 超出范围"""
        data = {
            "type": "happy",
            "label": "开心",
            "intensity": "high",
            "confidence": 1.5  # 超出 0-1 范围
        }
        assert validate_emotion_schema(data) is False
    
    def test_none_input(self):
        """测试 None 输入"""
        assert validate_emotion_schema(None) is False


class TestExtractAndCleanJson:
    """测试完整的提取和清洗流程"""
    
    def test_complete_flow(self):
        """测试完整流程"""
        llm_output = '''根据分析，用户情绪如下：
```json
{
    "type": "tired",
    "label": "疲惫",
    "intensity": "high",
    "confidence": 0.92,
    "triggers": ["工作压力", "睡眠不足"],
    "context": "用户因工作而感到疲惫"
}
```
希望这个分析对你有帮助！'''
        
        result = extract_and_clean_json(llm_output)
        assert result is not None
        assert result["type"] == "tired"
        assert result["confidence"] == 0.92
        assert "工作压力" in result["triggers"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
