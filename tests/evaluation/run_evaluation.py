#!/usr/bin/env python3
# run_evaluation.py - 一键评估脚本
"""
陪伴智能体评估入口
直接运行即可进行评估并生成报告

用法:
    python run_evaluation.py              # 使用模拟 Agent 测试框架
    python run_evaluation.py --real       # 使用真实 Agent
    python run_evaluation.py --manual     # 包含人工评估
"""

import os
import sys
import argparse
from datetime import datetime

# 添加项目根目录到路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from tests.evaluation.test_runner import EvaluationRunner, MockAgent
from tests.evaluation.report_generator import generate_report
from tests.evaluation.manual_annotation import run_manual_annotation


def create_real_agent():
    """
    创建真实的智能体实例
    
    Returns:
        Agent 实例
    """
    try:
        from tests.evaluation.agent_adapter import create_real_agent as create_adapter
        print("🔧 加载真实 Agent (OODA Workflow)...")
        return create_adapter(verbose=False)
        
    except ImportError as e:
        print(f"⚠️ 无法导入真实 Agent: {e}")
        print("   使用 Mock Agent 代替")
        return MockAgent()
    except Exception as e:
        print(f"⚠️ 真实 Agent 初始化失败: {e}")
        print("   使用 Mock Agent 代替")
        return MockAgent()


def main():
    parser = argparse.ArgumentParser(
        description="🎭 陪伴智能体评估工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    python run_evaluation.py              # 快速测试（模拟 Agent）
    python run_evaluation.py --real       # 真实 Agent 测试
    python run_evaluation.py -d memory    # 只测试记忆维度
    python run_evaluation.py --manual     # 包含人工评估
        """
    )
    
    parser.add_argument(
        "--real", "-r",
        action="store_true",
        help="使用真实 Agent 运行评估"
    )
    
    parser.add_argument(
        "--dimensions", "-d",
        nargs="+",
        default=["memory", "emotion"],
        choices=["memory", "emotion", "entity", "context", "tool"],
        help="要评估的维度 (默认: memory emotion)"
    )
    
    parser.add_argument(
        "--manual", "-m",
        action="store_true",
        help="包含人工评估环节"
    )
    
    parser.add_argument(
        "--output-dir", "-o",
        default=None,
        help="报告输出目录"
    )
    
    parser.add_argument(
        "--annotator",
        default="default",
        help="人工评估时的标注者名称"
    )
    
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="安静模式"
    )
    
    args = parser.parse_args()
    
    # 欢迎信息
    if not args.quiet:
        print("\n" + "="*60)
        print("🎭 陪伴智能体评估系统")
        print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60)
    
    # 创建 Agent
    if args.real:
        print("\n📌 加载真实 Agent...")
        agent = create_real_agent()
    else:
        print("\n📌 使用模拟 Agent（测试评估框架）")
        agent = MockAgent()
    
    # 运行自动化评估
    print(f"\n🚀 开始自动化评估 (维度: {', '.join(args.dimensions)})")
    
    runner = EvaluationRunner(agent=agent)
    results = runner.run_all(dimensions=args.dimensions, verbose=not args.quiet)
    
    # 生成报告
    print("\n📊 生成评估报告...")
    output_dir = args.output_dir or os.path.join(
        os.path.dirname(__file__), "results"
    )
    report_paths = generate_report(results, output_dir)
    
    # 人工评估（可选）
    if args.manual:
        print("\n" + "="*60)
        print("📝 进入人工评估环节")
        print("="*60)
        
        # 收集需要人工评估的用例
        manual_cases = []
        for dim, data in results.items():
            for case_result in data.get("results", []):
                if case_result.get("manual_eval_required", False):
                    manual_cases.append({
                        "case_id": case_result["case_id"],
                        "user_input": case_result["test_input"],
                        "agent_response": case_result["response"]
                    })
        
        if manual_cases:
            print(f"\n共 {len(manual_cases)} 个用例需要人工评估")
            run_manual_annotation(
                manual_cases, 
                session_name="companion_eval",
                annotator=args.annotator
            )
        else:
            print("\n✅ 没有需要人工评估的用例")
    
    # 完成提示
    print("\n" + "="*60)
    print("✅ 评估完成！")
    print(f"📄 报告位置: {report_paths['markdown']}")
    print("="*60 + "\n")
    
    return results


if __name__ == "__main__":
    main()
