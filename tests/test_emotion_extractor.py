"""
情感提取器单元测试
"""

import pytest
from src.emotion_extractor import EmotionExtractor


class TestEmotionExtractor:
    """情感提取器测试类"""
    
    @pytest.fixture
    def extractor(self):
        """创建提取器实例"""
        return EmotionExtractor()
    
    # === 基础功能测试 ===
    
    def test_keyword_extraction_happy(self, extractor):
        """测试开心情绪识别"""
        result = extractor.extract_emotion_by_keywords("今天太开心了！")
        assert result is not None
        assert result["type"] == "happy"
        assert result["intensity"] == "high"
        assert "开心" in result["matched_keywords"]
        assert result["source"] == "keyword"
    
    def test_keyword_extraction_tired(self, extractor):
        """测试疲惫情绪识别"""
        result = extractor.extract_emotion_by_keywords("好累啊")
        assert result is not None
        assert result["type"] == "tired"
        assert result["intensity"] == "medium"  # "好" 不是强度修饰词，默认 medium
        assert "累" in result["matched_keywords"]
    
    def test_keyword_extraction_sad(self, extractor):
        """测试难过情绪识别"""
        result = extractor.extract_emotion_by_keywords("今天有点难过")
        assert result is not None
        assert result["type"] == "sad"
        assert result["intensity"] == "low"  # "有点" 是低强度修饰词
        assert "难过" in result["matched_keywords"]
    
    def test_keyword_extraction_angry(self, extractor):
        """测试生气情绪识别"""
        result = extractor.extract_emotion_by_keywords("真的很生气")
        assert result is not None
        assert result["type"] == "angry"
        assert result["intensity"] == "high"  # "很" 是高强度修饰词
    
    # === 过滤条件测试 ===
    
    def test_filter_skip_short_text(self, extractor):
        """测试过滤短文本"""
        result = extractor.extract_emotion_by_keywords("累")
        assert result is None  # 长度 < 2，应该被过滤
    
    def test_filter_skip_command(self, extractor):
        """测试过滤命令式输入"""
        result = extractor.extract_emotion_by_keywords("/help")
        assert result is None
        
        result = extractor.extract_emotion_by_keywords(".config")
        assert result is None
    
    def test_filter_skip_long_text(self, extractor):
        """测试过滤超长文本"""
        long_text = "测试" * 300  # 超过 500 字符
        result = extractor.extract_emotion_by_keywords(long_text)
        assert result is None
    
    # === 强度检测测试 ===
    
    def test_intensity_high(self, extractor):
        """测试高强度情绪"""
        result = extractor.extract_emotion_by_keywords("非常开心")
        assert result["intensity"] == "high"
        
        result = extractor.extract_emotion_by_keywords("超级累")
        assert result["intensity"] == "high"
    
    def test_intensity_low(self, extractor):
        """测试低强度情绪"""
        result = extractor.extract_emotion_by_keywords("有点累")
        assert result["intensity"] == "low"
        
        result = extractor.extract_emotion_by_keywords("稍微有点难过")
        assert result["intensity"] == "low"
    
    def test_intensity_medium_default(self, extractor):
        """测试中等强度（默认）"""
        result = extractor.extract_emotion_by_keywords("我很开心")
        # "很" 是高强度修饰词
        assert result["intensity"] == "high"
        
        result = extractor.extract_emotion_by_keywords("我开心")
        # 没有强度修饰词，默认中等
        assert result["intensity"] == "medium"
    
    # === 表情符号测试 ===
    
    def test_emoji_detection(self, extractor):
        """测试表情符号识别"""
        # 单个表情符号长度为1，会被过滤（min_length=2）
        result = extractor.extract_emotion_by_keywords("好开心😊")
        assert result is not None
        assert result["type"] == "happy"
        assert "😊" in result["matched_emoji"]
        
        result = extractor.extract_emotion_by_keywords("好难过😭😭😭")
        assert result is not None
        assert result["type"] == "sad"
    
    # === 否定词处理测试 ===
    
    def test_negation_lowers_confidence(self, extractor):
        """测试否定词降低置信度"""
        result_positive = extractor.extract_emotion_by_keywords("我很开心")
        result_negative = extractor.extract_emotion_by_keywords("我不开心")
        
        assert result_positive["confidence"] > result_negative["confidence"]
        assert result_negative["confidence"] == 0.5  # 否定词降低到 0.5
    
    # === 混合情绪测试 ===
    
    def test_mixed_emotions(self, extractor):
        """测试混合情绪（选择关键词最多的）"""
        result = extractor.extract_emotion_by_keywords("今天又累又开心")
        assert result is not None
        # 应该选择关键词数量最多的情绪
        assert result["type"] in ["tired", "happy"]
    
    # === LLM 触发条件测试 ===
    
    def test_llm_trigger_condition_high_confidence(self, extractor):
        """测试高置信度触发 LLM"""
        keyword_result = {"confidence": 0.8}
        assert extractor.should_trigger_llm(keyword_result) == True
    
    def test_llm_trigger_condition_low_confidence(self, extractor):
        """测试低置信度不触发 LLM"""
        keyword_result = {"confidence": 0.2}
        assert extractor.should_trigger_llm(keyword_result) == False
    
    def test_llm_trigger_condition_threshold(self, extractor):
        """测试阈值边界"""
        keyword_result = {"confidence": 0.3}  # 正好等于阈值
        assert extractor.should_trigger_llm(keyword_result) == True
        
        keyword_result = {"confidence": 0.29}  # 略低于阈值
        assert extractor.should_trigger_llm(keyword_result) == False
    
    def test_llm_trigger_condition_none_result(self, extractor):
        """测试无关键词结果不触发 LLM"""
        assert extractor.should_trigger_llm(None) == False
    
    # === 元数据完整性测试 ===
    
    def test_metadata_completeness(self, extractor):
        """测试元数据完整性"""
        result = extractor.extract_emotion_by_keywords("今天好累啊")
        
        # 检查所有必需字段
        assert "type" in result
        assert "label" in result
        assert "intensity" in result
        assert "confidence" in result
        assert "source" in result
        assert "matched_keywords" in result
        assert "matched_emoji" in result
        assert "timestamp" in result
        assert "response_tone" in result
        
        # 检查可选字段（关键词提取时应为 None）
        assert result["duration"] is None
        assert result["triggers"] is None
        assert result["context"] is None
        assert result["intensity_score"] is None
    
    # === 边界情况测试 ===
    
    def test_empty_string(self, extractor):
        """测试空字符串"""
        result = extractor.extract_emotion_by_keywords("")
        assert result is None
    
    def test_whitespace_only(self, extractor):
        """测试纯空格"""
        result = extractor.extract_emotion_by_keywords("   ")
        assert result is None
    
    def test_no_emotion_keywords(self, extractor):
        """测试无情绪关键词的文本"""
        # "不错" 可能被识别为 happy 的关键词，使用更中性的文本
        result = extractor.extract_emotion_by_keywords("今天天气很好")
        # "好" 可能在 happy 关键词中，改用完全中性的表达
        result = extractor.extract_emotion_by_keywords("今天是星期三")
        assert result is None
    
    # === 实际场景测试 ===
    
    def test_real_scenario_work_stress(self, extractor):
        """真实场景：工作压力"""
        result = extractor.extract_emotion_by_keywords("加班到现在，累死了，好想休息")
        assert result is not None
        assert result["type"] == "tired"
        assert result["intensity"] == "high"
    
    def test_real_scenario_achievement(self, extractor):
        """真实场景：成就感"""
        result = extractor.extract_emotion_by_keywords("终于完成了项目，太棒了！")
        assert result is not None
        assert result["type"] in ["happy", "excited"]
    
    def test_real_scenario_confusion(self, extractor):
        """真实场景：困惑"""
        result = extractor.extract_emotion_by_keywords("我有点搞不清楚这是什么意思")
        assert result is not None
        assert result["type"] == "confused"
        assert result["intensity"] == "low"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
