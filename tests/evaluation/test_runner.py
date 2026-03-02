# test_runner.py - 评估运行器
"""
一键运行评估脚本，支持随时测试和演示
"""

import json
import os
import sys
import time
from datetime import datetime
from typing import Dict, List, Any, Optional

# 添加项目根目录到路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from .metrics import (
    calculate_combined_score, 
    calculate_dimension_score,
    keyword_match_score,
    keyword_match_any_score,
    negative_keyword_check
)


class EvaluationRunner:
    """陪伴智能体评估运行器"""
    
    def __init__(self, agent=None, cases_dir: str = None):
        """
        初始化评估运行器
        
        Args:
            agent: 智能体实例（需要有 chat/reset 方法）
            cases_dir: 测试用例目录
        """
        self.agent = agent
        self.cases_dir = cases_dir or os.path.join(
            os.path.dirname(__file__), "cases"
        )
        self.results = {}
        self.run_timestamp = None
    
    def load_cases(self, dimension: str) -> Dict:
        """加载指定维度的测试用例"""
        filepath = os.path.join(self.cases_dir, f"{dimension}_cases.json")
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    
    def run_single_case(self, case: Dict, reset_before: bool = True) -> Dict:
        """
        运行单个测试用例
        
        Args:
            case: 测试用例字典
            reset_before: 是否在测试前重置 agent
        
        Returns:
            包含测试结果的字典
        """
        if self.agent is None:
            raise ValueError("需要设置 agent 实例才能运行测试")
        
        # 重置 agent 状态
        if reset_before and hasattr(self.agent, 'reset'):
            self.agent.reset()
        
        # 执行 setup 阶段
        setup_responses = []
        for setup_item in case.get("setup", []):
            # 支持两种格式：纯字符串 或 {"input": "..."}
            if isinstance(setup_item, dict):
                setup_input = setup_item.get("input", "")
            else:
                setup_input = setup_item
            resp = self.agent.chat(setup_input)
            setup_responses.append({"input": setup_input, "response": resp})
        
        # 执行测试输入
        test_input = case["test_input"]
        response = self.agent.chat(test_input)
        
        # 获取情绪检测结果（如果 agent 支持）
        detected_emotion = None
        if hasattr(self.agent, 'get_last_emotion'):
            detected_emotion = self.agent.get_last_emotion()
        
        # 评分
        scores = calculate_combined_score(response, case, detected_emotion)
        
        return {
            "case_id": case["id"],
            "case_name": case.get("name", ""),
            "category": case.get("category", ""),
            "test_input": test_input,
            "response": response,
            "expected_keywords": case.get("expected_keywords", []),
            "detected_emotion": detected_emotion,
            "scores": scores,
            "total_score": scores.get("total_score", 0.0),
            "passed": scores.get("total_score", 0.0) >= 0.6,
            "setup_responses": setup_responses,
            "manual_eval_required": case.get("manual_eval_required", False)
        }
    
    def run_dimension(self, dimension: str, verbose: bool = True) -> Dict:
        """
        运行某个维度的所有测试
        
        Args:
            dimension: 维度名称 (memory/emotion/entity/context/tool)
            verbose: 是否打印进度
        
        Returns:
            维度评估结果
        """
        data = self.load_cases(dimension)
        cases = data.get("cases", [])
        
        if verbose:
            print(f"\n{'='*60}")
            print(f"📊 开始评估维度: {data.get('dimension', dimension)}")
            print(f"📝 {data.get('description', '')}")
            print(f"📋 共 {len(cases)} 个测试用例")
            print(f"{'='*60}\n")
        
        results = []
        for i, case in enumerate(cases):
            if verbose:
                print(f"[{i+1}/{len(cases)}] 测试 {case['id']}: {case.get('name', '')}...", end=" ")
            
            try:
                result = self.run_single_case(case)
                results.append(result)
                
                if verbose:
                    status = "✅ PASS" if result["passed"] else "❌ FAIL"
                    print(f"{status} (得分: {result['total_score']:.2f})")
                    
            except Exception as e:
                if verbose:
                    print(f"⚠️ ERROR: {e}")
                results.append({
                    "case_id": case["id"],
                    "error": str(e),
                    "passed": False,
                    "total_score": 0.0
                })
        
        # 计算维度统计
        dimension_stats = calculate_dimension_score(results)
        
        return {
            "dimension": dimension,
            "dimension_name": data.get("dimension", dimension),
            "description": data.get("description", ""),
            "timestamp": datetime.now().isoformat(),
            "stats": dimension_stats,
            "results": results
        }
    
    def run_all(self, dimensions: List[str] = None, verbose: bool = True) -> Dict:
        """
        运行所有维度的评估
        
        Args:
            dimensions: 要评估的维度列表，默认 D1 和 D2
            verbose: 是否打印进度
        
        Returns:
            完整评估结果
        """
        if dimensions is None:
            dimensions = ["memory", "emotion"]  # 默认优先评估 D1 和 D2
        
        self.run_timestamp = datetime.now()
        
        if verbose:
            print("\n" + "="*60)
            print("🚀 陪伴智能体综合评估")
            print(f"⏰ 开始时间: {self.run_timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
            print("="*60)
        
        all_results = {}
        for dim in dimensions:
            try:
                all_results[dim] = self.run_dimension(dim, verbose)
            except FileNotFoundError:
                if verbose:
                    print(f"⚠️ 未找到 {dim} 的测试用例文件，跳过")
        
        self.results = all_results
        return all_results
    
    def get_summary(self) -> Dict:
        """获取评估摘要"""
        if not self.results:
            return {}
        
        summary = {
            "timestamp": self.run_timestamp.isoformat() if self.run_timestamp else None,
            "dimensions": {},
            "overall": {}
        }
        
        total_score = 0
        total_weight = 0
        
        for dim, data in self.results.items():
            stats = data.get("stats", {})
            summary["dimensions"][dim] = {
                "name": data.get("dimension_name", dim),
                "avg_score": stats.get("avg_score", 0),
                "avg_score_percent": stats.get("avg_score_percent", "0%"),
                "pass_rate": stats.get("pass_rate", "0%"),
                "total_cases": stats.get("total_cases", 0),
                "passed": stats.get("passed", 0),
                "failed": stats.get("failed", 0)
            }
            
            # 等权重计算
            total_score += stats.get("avg_score", 0)
            total_weight += 1
        
        if total_weight > 0:
            overall_score = total_score / total_weight
            summary["overall"] = {
                "avg_score": round(overall_score, 4),
                "avg_score_percent": f"{overall_score * 100:.1f}%"
            }
        
        return summary


# ==========================================
# 模拟 Agent（用于演示和测试框架本身）
# ==========================================

class MockAgent:
    """模拟 Agent，用于测试评估框架"""
    
    def __init__(self):
        self.memory = {}
        self.conversation_history = []
    
    def reset(self):
        self.memory = {}
        self.conversation_history = []
    
    def chat(self, user_input: str) -> str:
        """模拟聊天，简单基于记忆回复"""
        self.conversation_history.append({"role": "user", "content": user_input})
        
        # 简单的记忆存储逻辑
        self._extract_and_store(user_input)
        
        # 简单的回复生成
        response = self._generate_response(user_input)
        
        self.conversation_history.append({"role": "assistant", "content": response})
        return response
    
    def _extract_and_store(self, text: str):
        """简单提取信息"""
        import re
        
        # 提取姓名
        if match := re.search(r"我叫(\w+)", text):
            self.memory["name"] = match.group(1)
        
        # 提取年龄
        if match := re.search(r"(\d+)岁", text):
            self.memory["age"] = match.group(1)
        
        # 提取女朋友
        if match := re.search(r"女朋友叫(\w+)", text):
            self.memory["girlfriend"] = match.group(1)
        
        # 提取喜好
        if match := re.search(r"喜欢(吃)?(\w+)", text):
            self.memory["preference"] = match.group(2)
    
    def _generate_response(self, text: str) -> str:
        """简单生成回复"""
        if "叫什么名字" in text or "我叫什么" in text:
            if "name" in self.memory:
                return f"你叫{self.memory['name']}呀~"
            return "嗯...我好像还不知道你的名字呢"
        
        if "多大" in text or "几岁" in text:
            if "age" in self.memory:
                return f"你{self.memory['age']}岁啦"
            return "你还没告诉我你的年龄呢"
        
        if "女朋友是谁" in text:
            if "girlfriend" in self.memory:
                return f"你的女朋友是{self.memory['girlfriend']}呀"
            return "你有女朋友吗？还没告诉我呢"
        
        if "推荐" in text and "餐厅" in text:
            if "preference" in self.memory:
                return f"既然你喜欢{self.memory['preference']}，我推荐你去试试..."
            return "你喜欢吃什么类型的呢？"
        
        # 情感类回复
        if "郁闷" in text or "难过" in text or "伤心" in text:
            return "唔...听起来今天不太顺利呢。想和我聊聊吗？我在这里陪着你。"
        
        if "升职" in text or "加薪" in text:
            return "哇！太棒了！恭喜恭喜！你一定付出了很多努力，这是你应得的！"
        
        if "压力" in text or "睡不好" in text:
            return "最近辛苦了...要好好照顾自己哦，身体最重要。有什么我能帮到你的吗？"
        
        return "嗯嗯，我知道了~"


# ==========================================
# 命令行入口
# ==========================================

def main():
    """命令行运行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="陪伴智能体评估工具")
    parser.add_argument(
        "--dimensions", "-d",
        nargs="+",
        default=["memory", "emotion"],
        help="要评估的维度列表 (默认: memory emotion)"
    )
    parser.add_argument(
        "--mock", "-m",
        action="store_true",
        help="使用模拟 Agent 运行（用于测试评估框架本身）"
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="结果输出文件路径"
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="安静模式，减少输出"
    )
    
    args = parser.parse_args()
    
    # 创建 agent
    if args.mock:
        print("📌 使用模拟 Agent 运行评估")
        agent = MockAgent()
    else:
        # TODO: 导入真实 Agent
        print("⚠️ 真实 Agent 未配置，使用模拟 Agent")
        agent = MockAgent()
    
    # 运行评估
    runner = EvaluationRunner(agent=agent)
    results = runner.run_all(dimensions=args.dimensions, verbose=not args.quiet)
    
    # 打印摘要
    summary = runner.get_summary()
    print("\n" + "="*60)
    print("📊 评估摘要")
    print("="*60)
    for dim, stats in summary.get("dimensions", {}).items():
        print(f"  {stats['name']}: {stats['avg_score_percent']} (通过率: {stats['pass_rate']})")
    print(f"\n  🎯 总体得分: {summary.get('overall', {}).get('avg_score_percent', 'N/A')}")
    print("="*60)
    
    # 保存结果
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"\n💾 详细结果已保存到: {args.output}")
    
    return results


if __name__ == "__main__":
    main()
