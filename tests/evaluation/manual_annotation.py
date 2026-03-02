# manual_annotation.py - 人工标注系统
"""
用于人工评估情感理解等需要主观判断的维度
提供交互式标注界面和结果存储
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional

from .metrics import MANUAL_SCORING_RUBRICS, print_rubric


class ManualAnnotationSession:
    """人工标注会话"""
    
    def __init__(
        self, 
        session_name: str,
        annotator: str = "default",
        output_dir: str = "tests/evaluation/results/manual"
    ):
        """
        初始化标注会话
        
        Args:
            session_name: 会话名称（用于保存结果）
            annotator: 标注者名称
            output_dir: 输出目录
        """
        self.session_name = session_name
        self.annotator = annotator
        self.output_dir = output_dir
        self.results = []
        self.start_time = datetime.now()
        
        # 创建输出目录
        os.makedirs(output_dir, exist_ok=True)
    
    def annotate_case(
        self,
        case_id: str,
        user_input: str,
        agent_response: str,
        rubrics: List[str] = None
    ) -> Dict[str, Any]:
        """
        对单个用例进行人工标注
        
        Args:
            case_id: 用例ID
            user_input: 用户输入
            agent_response: 智能体回复
            rubrics: 要评估的量表列表
        
        Returns:
            标注结果字典
        """
        if rubrics is None:
            rubrics = ["empathy_naturalness", "response_appropriateness"]
        
        print("\n" + "="*60)
        print(f"📋 用例 ID: {case_id}")
        print("="*60)
        print(f"\n👤 用户输入:")
        print(f"   {user_input}")
        print(f"\n🤖 智能体回复:")
        print(f"   {agent_response}")
        print("\n" + "-"*60)
        
        scores = {}
        
        for rubric_name in rubrics:
            print_rubric(rubric_name)
            
            while True:
                try:
                    score_input = input(f"请输入 {MANUAL_SCORING_RUBRICS[rubric_name]['name']} 评分 (1-5): ").strip()
                    score = int(score_input)
                    if 1 <= score <= 5:
                        scores[rubric_name] = score
                        break
                    else:
                        print("❌ 请输入 1-5 之间的整数")
                except ValueError:
                    print("❌ 请输入有效数字")
        
        # 可选备注
        comment = input("\n💬 备注 (可选，直接回车跳过): ").strip()
        
        result = {
            "case_id": case_id,
            "user_input": user_input,
            "agent_response": agent_response,
            "scores": scores,
            "comment": comment if comment else None,
            "annotator": self.annotator,
            "timestamp": datetime.now().isoformat()
        }
        
        self.results.append(result)
        print(f"\n✅ 已记录评分: {scores}")
        
        return result
    
    def save_results(self) -> str:
        """
        保存标注结果
        
        Returns:
            保存文件的路径
        """
        filename = f"{self.session_name}_{self.start_time.strftime('%Y%m%d_%H%M%S')}.json"
        filepath = os.path.join(self.output_dir, filename)
        
        summary = {
            "session_name": self.session_name,
            "annotator": self.annotator,
            "start_time": self.start_time.isoformat(),
            "end_time": datetime.now().isoformat(),
            "total_cases": len(self.results),
            "results": self.results,
            "statistics": self._calculate_statistics()
        }
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 结果已保存到: {filepath}")
        return filepath
    
    def _calculate_statistics(self) -> Dict[str, Any]:
        """计算统计信息"""
        if not self.results:
            return {}
        
        # 按量表计算平均分
        rubric_scores = {}
        for result in self.results:
            for rubric, score in result["scores"].items():
                if rubric not in rubric_scores:
                    rubric_scores[rubric] = []
                rubric_scores[rubric].append(score)
        
        stats = {}
        for rubric, scores in rubric_scores.items():
            avg = sum(scores) / len(scores)
            stats[rubric] = {
                "avg_score": round(avg, 2),
                "min_score": min(scores),
                "max_score": max(scores),
                "count": len(scores)
            }
        
        # 总体平均
        all_scores = [s for r in self.results for s in r["scores"].values()]
        stats["overall"] = {
            "avg_score": round(sum(all_scores) / len(all_scores), 2) if all_scores else 0,
            "total_ratings": len(all_scores)
        }
        
        return stats
    
    def print_summary(self):
        """打印标注摘要"""
        stats = self._calculate_statistics()
        
        print("\n" + "="*60)
        print("📊 标注会话摘要")
        print("="*60)
        print(f"会话名称: {self.session_name}")
        print(f"标注者: {self.annotator}")
        print(f"标注用例数: {len(self.results)}")
        print()
        
        if stats:
            print("各维度平均分:")
            for rubric, data in stats.items():
                if rubric != "overall":
                    name = MANUAL_SCORING_RUBRICS.get(rubric, {}).get("name", rubric)
                    print(f"  - {name}: {data['avg_score']}/5.0")
            
            print(f"\n总体平均分: {stats.get('overall', {}).get('avg_score', 0)}/5.0")
        print("="*60)


# ==========================================
# 批量标注工具函数
# ==========================================

def run_manual_annotation(
    test_results: List[Dict],
    session_name: str = "emotion_eval",
    annotator: str = "default"
) -> str:
    """
    运行批量人工标注
    
    Args:
        test_results: 包含 case_id, user_input, agent_response 的测试结果列表
        session_name: 会话名称
        annotator: 标注者
    
    Returns:
        结果文件路径
    """
    session = ManualAnnotationSession(session_name, annotator)
    
    print(f"\n🚀 开始人工标注会话: {session_name}")
    print(f"📝 共 {len(test_results)} 个用例待标注")
    print("(输入 'q' 可中途退出并保存已标注结果)\n")
    
    for i, result in enumerate(test_results):
        print(f"\n--- 进度: {i+1}/{len(test_results)} ---")
        
        try:
            session.annotate_case(
                case_id=result.get("case_id", f"case_{i}"),
                user_input=result.get("user_input", result.get("test_input", "")),
                agent_response=result.get("agent_response", result.get("response", ""))
            )
        except KeyboardInterrupt:
            print("\n\n⚠️ 用户中断，保存已标注结果...")
            break
    
    session.print_summary()
    return session.save_results()


# ==========================================
# 命令行接口
# ==========================================

if __name__ == "__main__":
    # 示例用法
    print("人工标注系统示例")
    print("="*40)
    
    # 模拟测试结果
    sample_results = [
        {
            "case_id": "A2-01",
            "user_input": "今天被老板骂了，好郁闷",
            "agent_response": "唔...听起来今天不太顺利呢。被批评确实会让人难受，想和我聊聊发生了什么吗？"
        },
        {
            "case_id": "A2-02",
            "user_input": "我升职了！！！",
            "agent_response": "哇！太棒了！恭喜恭喜！你一定付出了很多努力吧，这个升职是你应得的！今晚要不要庆祝一下？"
        }
    ]
    
    # 运行标注
    # run_manual_annotation(sample_results, "demo_session", "tester")
    
    # 打印量表示例
    print("\n可用的评分量表:")
    for name in MANUAL_SCORING_RUBRICS:
        print_rubric(name)
