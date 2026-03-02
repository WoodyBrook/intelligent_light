# metrics.py - 评估指标和评分函数
"""
包含自动化评分函数和人工评分的辅助工具
"""

import re
from typing import List, Dict, Any, Optional, Tuple


# ==========================================
# 自动化评分函数
# ==========================================

def keyword_match_score(response: str, expected_keywords: List[str]) -> float:
    """
    关键词匹配评分 (全部匹配)
    
    Args:
        response: 智能体回复
        expected_keywords: 期望包含的关键词列表
    
    Returns:
        0.0 - 1.0 之间的分数（匹配比例）
    """
    if not expected_keywords:
        return 1.0
    
    response_lower = response.lower()
    matched = sum(1 for kw in expected_keywords if kw.lower() in response_lower)
    return matched / len(expected_keywords)


def keyword_match_any_score(response: str, expected_keywords: List[str]) -> float:
    """
    关键词匹配评分 (任一匹配即可)
    
    Args:
        response: 智能体回复
        expected_keywords: 期望包含的关键词列表（只要有一个匹配即可）
    
    Returns:
        1.0 如果任一关键词匹配, 否则 0.0
    """
    if not expected_keywords:
        return 1.0
    
    response_lower = response.lower()
    for kw in expected_keywords:
        if kw.lower() in response_lower:
            return 1.0
    return 0.0


def negative_keyword_check(response: str, forbidden_keywords: List[str]) -> float:
    """
    负面关键词检查 (不应包含的内容)
    
    Args:
        response: 智能体回复
        forbidden_keywords: 不应包含的关键词列表
    
    Returns:
        1.0 如果没有包含任何禁止词, 否则 0.0
    """
    if not forbidden_keywords:
        return 1.0
    
    response_lower = response.lower()
    for kw in forbidden_keywords:
        if kw.lower() in response_lower:
            return 0.0
    return 1.0


def emotion_label_match(detected_emotion: str, expected_emotions: List[str]) -> float:
    """
    情绪标签匹配
    
    Args:
        detected_emotion: 系统检测到的情绪
        expected_emotions: 期望的情绪标签列表
    
    Returns:
        1.0 如果检测到的情绪在期望列表中, 否则 0.0
    """
    if not expected_emotions:
        return 1.0
    
    detected_lower = detected_emotion.lower()
    for expected in expected_emotions:
        if expected.lower() in detected_lower or detected_lower in expected.lower():
            return 1.0
    return 0.0


def calculate_combined_score(
    response: str,
    case: Dict[str, Any],
    detected_emotion: Optional[str] = None
) -> Dict[str, float]:
    """
    综合计算单个测试用例的得分
    
    Args:
        response: 智能体回复
        case: 测试用例字典
        detected_emotion: 系统检测到的情绪（可选）
    
    Returns:
        包含各项得分的字典
    """
    scores = {}
    
    # 1. 正向关键词匹配
    scoring_method = case.get("scoring_method", "keyword_match")
    expected_keywords = case.get("expected_keywords", [])
    
    if scoring_method == "keyword_match":
        scores["keyword_score"] = keyword_match_score(response, expected_keywords)
    elif scoring_method == "keyword_match_any":
        scores["keyword_score"] = keyword_match_any_score(response, expected_keywords)
    elif scoring_method == "negative_keyword_check":
        forbidden = case.get("expected_not_keywords", [])
        scores["keyword_score"] = negative_keyword_check(response, forbidden)
    
    # 2. 负向关键词检查（如果存在）
    expected_not = case.get("expected_not_keywords", [])
    if expected_not:
        scores["negative_check"] = negative_keyword_check(response, expected_not)
    
    # 3. 情绪匹配（如果是情感类用例）
    expected_emotions = case.get("expected_emotion", [])
    if expected_emotions and detected_emotion:
        scores["emotion_score"] = emotion_label_match(detected_emotion, expected_emotions)
    
    # 4. 计算总分
    score_values = list(scores.values())
    scores["total_score"] = sum(score_values) / len(score_values) if score_values else 0.0
    
    return scores


# ==========================================
# 人工评分量表定义
# ==========================================

MANUAL_SCORING_RUBRICS = {
    "empathy_naturalness": {
        "name": "共情自然度",
        "description": "评估回复中共情表达的自然程度",
        "scale": {
            5: "完全理解用户情绪，回复温暖且自然，像真人朋友一样",
            4: "正确识别情绪，回复较自然但略有机械感",
            3: "部分理解情绪，回复中规中矩",
            2: "情绪识别偏差，回复不够得体",
            1: "完全误解或无视用户情绪"
        }
    },
    "response_appropriateness": {
        "name": "回复得体性",
        "description": "评估回复是否符合当前情境",
        "scale": {
            5: "完美匹配情境，说该说的话，不说不该说的",
            4: "基本得体，有小瑕疵",
            3: "一般，不功不过",
            2: "有明显不得体之处",
            1: "严重不得体，可能引起用户不适"
        }
    },
    "personality_consistency": {
        "name": "人格一致性",
        "description": "评估回复是否符合设定的性格",
        "scale": {
            5: "完全符合温柔坚定的猫性格",
            4: "基本符合，偶有偏离",
            3: "时好时坏",
            2: "经常偏离设定性格",
            1: "完全不符合设定"
        }
    },
    "memory_accuracy": {
        "name": "记忆准确度",
        "description": "评估记忆召回的准确性",
        "scale": {
            5: "完全准确，细节无误",
            4: "基本准确，细节有小误差",
            3: "部分准确，有遗漏",
            2: "有明显错误",
            1: "完全错误或编造信息"
        }
    }
}


def get_rubric(rubric_name: str) -> Dict:
    """获取指定评分量表"""
    return MANUAL_SCORING_RUBRICS.get(rubric_name, {})


def print_rubric(rubric_name: str):
    """打印评分量表供人工评估使用"""
    rubric = get_rubric(rubric_name)
    if not rubric:
        print(f"未找到量表: {rubric_name}")
        return
    
    print(f"\n{'='*50}")
    print(f"📊 {rubric['name']}")
    print(f"📝 {rubric['description']}")
    print(f"{'='*50}")
    for score, desc in sorted(rubric["scale"].items(), reverse=True):
        print(f"  [{score}] {desc}")
    print()


# ==========================================
# 维度级别统计
# ==========================================

def calculate_dimension_score(case_results: List[Dict]) -> Dict[str, Any]:
    """
    计算某个维度的整体得分
    
    Args:
        case_results: 该维度所有用例的结果列表
    
    Returns:
        维度统计信息
    """
    if not case_results:
        return {"avg_score": 0.0, "total_cases": 0, "passed": 0, "failed": 0}
    
    total_score = sum(r.get("total_score", 0.0) for r in case_results)
    avg_score = total_score / len(case_results)
    
    # 计算通过/失败（阈值0.6）
    threshold = 0.6
    passed = sum(1 for r in case_results if r.get("total_score", 0) >= threshold)
    failed = len(case_results) - passed
    
    return {
        "avg_score": round(avg_score, 4),
        "avg_score_percent": f"{avg_score * 100:.1f}%",
        "total_cases": len(case_results),
        "passed": passed,
        "failed": failed,
        "pass_rate": f"{passed / len(case_results) * 100:.1f}%"
    }
