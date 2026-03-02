"""
情感提取模块

提供两种情感提取方式：
1. 方案B：基于关键词的快速提取（同步，<1ms）
2. 方案A：基于LLM的精细提取（异步）

配置文件：config/emotion_keywords.json
"""

import json
import re
from typing import Optional, Dict, List
from datetime import datetime
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class EmotionExtractor:
    """情感提取器"""
    
    def __init__(self, config_path: str = "config/emotion_keywords.json"):
        """
        初始化情感提取器
        
        Args:
            config_path: 关键词配置文件路径
        """
        config_file = Path(config_path)
        if not config_file.exists():
            raise FileNotFoundError(f"情感关键词配置文件不存在: {config_path}")
        
        with open(config_file, 'r', encoding='utf-8') as f:
            self.config = json.load(f)
        
        self.emotion_types = self.config["emotion_types"]
        self.intensity_modifiers = self.config["intensity_modifiers"]
        self.negation_words = self.config["negation_words"]
        self.filter_config = self.config["filter_conditions"]
        
        logger.info(f"✅ 情感提取器初始化成功 | 情绪类型: {len(self.emotion_types)} | 配置: {config_path}")
    
    def should_skip(self, text: str) -> bool:
        """
        过滤条件：判断是否跳过情感提取
        
        Args:
            text: 用户输入文本
            
        Returns:
            True 表示跳过，False 表示继续处理
        """
        # 长度检查
        if len(text) < self.filter_config["min_text_length"]:
            return True
        if len(text) > self.filter_config["max_text_length"]:
            return True
        
        # 模式检查（跳过命令式输入）
        for pattern in self.filter_config["skip_patterns"]:
            if re.match(pattern, text):
                return True
        
        return False
    
    def extract_emotion_by_keywords(self, text: str) -> Optional[Dict]:
        """
        方案B：基于关键词的快速情感提取（同步）
        
        Args:
            text: 用户输入文本
            
        Returns:
            情感元数据字典，如果无情感则返回 None
        """
        if self.should_skip(text):
            return None
        
        # 检测否定词
        has_negation = any(neg in text for neg in self.negation_words)
        
        # 匹配情绪类型
        matched_emotions = []
        for emotion_type, config in self.emotion_types.items():
            matched_kw = [kw for kw in config["keywords"] if kw in text]
            matched_em = [em for em in config.get("emoji", []) if em in text]
            
            if matched_kw or matched_em:
                matched_emotions.append({
                    "type": emotion_type,
                    "label": config["label"],
                    "keywords": matched_kw,
                    "emoji": matched_em,
                    "response_tone": config["response_tone"]
                })
        
        if not matched_emotions:
            return None
        
        # 选择最匹配的情绪（关键词数量最多）
        best_match = max(matched_emotions, 
                        key=lambda x: len(x["keywords"]) + len(x["emoji"]))
        
        # 检测强度
        intensity = "medium"
        for level, config in self.intensity_modifiers.items():
            if any(kw in text for kw in config["keywords"]):
                intensity = level
                break
        
        # 否定词处理：降低置信度
        confidence = 0.8 if not has_negation else 0.5
        
        result = {
            "type": best_match["type"],
            "label": best_match["label"],
            "intensity": intensity,
            "confidence": confidence,
            "source": "keyword",
            "matched_keywords": best_match["keywords"],
            "matched_emoji": best_match["emoji"],
            "timestamp": datetime.now().isoformat(),
            "duration": None,
            "triggers": None,
            "context": None,
            "intensity_score": None,
            "response_tone": best_match["response_tone"]
        }
        
        logger.debug(f"关键词提取 | 文本: {text[:20]}... | 情绪: {result['label']} | 强度: {intensity}")
        return result
    
    def should_trigger_llm(self, keyword_result: Optional[Dict]) -> bool:
        """
        判断是否需要调用 LLM（过滤条件）
        
        Args:
            keyword_result: 关键词提取结果
            
        Returns:
            True 表示需要调用 LLM
        """
        if not self.filter_config["llm_trigger_threshold"]["require_keyword_match"]:
            return True
        
        if keyword_result is None:
            return False
        
        # 仅当置信度高于阈值时调用 LLM
        min_confidence = self.filter_config["llm_trigger_threshold"]["min_confidence"]
        return keyword_result.get("confidence", 0) >= min_confidence
    
    async def extract_emotion_by_llm(
        self, 
        text: str, 
        response: str,
        keyword_result: Optional[Dict] = None
    ) -> Optional[Dict]:
        """
        方案A：基于LLM的精细情感提取（异步，带 Regex 清洗）
        
        Args:
            text: 用户输入文本
            response: 系统回复内容
            keyword_result: 关键词提取结果（用于判断是否调用 LLM）
            
        Returns:
            精细情感元数据字典，如果不满足条件则返回 None
        """
        # 过滤条件：仅当关键词匹配时调用
        if not self.should_trigger_llm(keyword_result):
            logger.debug(f"跳过 LLM 提取 | 置信度不足: {keyword_result.get('confidence', 0) if keyword_result else 'N/A'}")
            return None
        
        try:
            # 使用项目统一的 LLM（豆包 API）
            from .model_manager import get_model_manager
            model_manager = get_model_manager()
            llm = model_manager.get_model("chat")
            
            from .emotion_utils import extract_and_clean_json, normalize_emotion_values, validate_emotion_schema
            prompt = f"""分析用户输入和系统回复，提取精细的情感信息。

用户输入：{text}
系统回复：{response}

【重要】直接返回 JSON 对象，不要添加任何解释。格式如下：
{{
    "type": "情绪类型（happy/sad/angry/tired/anxious/excited/confused/grateful）",
    "label": "中文标签",
    "intensity": "强度（high/medium/low）",
    "confidence": 0.0-1.0,
    "triggers": ["触发因素1", "触发因素2"],
    "context": "情绪上下文描述（一句话）",
    "intensity_score": 0.0-1.0,
    "duration": 预估持续时间（秒，整数）
}}"""
            
            result = await llm.ainvoke(prompt)
            
            # ========== Regex 清洗 ==========
            llm_data = extract_and_clean_json(result.content)
            if not llm_data:
                logger.warning(f"LLM 输出清洗失败: {result.content[:200]}")
                return None
            
            # ========== 字段标准化 ==========
            llm_data = normalize_emotion_values(llm_data)
            
            # ========== Schema 验证 ==========
            if not validate_emotion_schema(llm_data):
                logger.warning(f"LLM 输出 Schema 验证失败")
                return None
            
            # ========== 合并关键词结果 ==========
            merged_result = {
                **llm_data,
                "source": "llm",
                "matched_keywords": keyword_result.get("matched_keywords", []) if keyword_result else [],
                "matched_emoji": keyword_result.get("matched_emoji", []) if keyword_result else [],
                "timestamp": datetime.now().isoformat(),
                "response_tone": self.emotion_types.get(llm_data["type"], {}).get("response_tone", "")
            }
            
            logger.info(f"✅ LLM 提取成功 | 情绪: {merged_result['label']} | 置信度: {merged_result['confidence']}")
            return merged_result
            
        except Exception as e:
            logger.error(f"❌ LLM 情感提取失败: {e}", exc_info=True)
            return None


# 全局单例
_extractor: Optional[EmotionExtractor] = None


def get_emotion_extractor() -> EmotionExtractor:
    """
    获取情感提取器单例
    
    Returns:
        EmotionExtractor 实例
    """
    global _extractor
    if _extractor is None:
        _extractor = EmotionExtractor()
    return _extractor
