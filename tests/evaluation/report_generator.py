# report_generator.py - 评估报告生成器
"""
生成美观的评估报告，适合演示展示
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional


class ReportGenerator:
    """评估报告生成器"""
    
    def __init__(self, results: Dict, output_dir: str = None):
        """
        初始化报告生成器
        
        Args:
            results: 评估结果字典
            output_dir: 输出目录
        """
        self.results = results
        self.output_dir = output_dir or os.path.join(
            os.path.dirname(__file__), "results"
        )
        os.makedirs(self.output_dir, exist_ok=True)
    
    def generate_markdown_report(self, filename: str = None) -> str:
        """
        生成 Markdown 格式的评估报告
        
        Args:
            filename: 输出文件名（不含扩展名）
        
        Returns:
            生成的报告文件路径
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"evaluation_report_{timestamp}"
        
        report_lines = []
        
        # 标题
        report_lines.append("# 🎭 陪伴智能体评估报告")
        report_lines.append("")
        report_lines.append(f"**评估时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append(f"**Agent 版本**: v2.0 - Context Engineering")
        report_lines.append("")
        report_lines.append("---")
        report_lines.append("")
        
        # 综合评分表格
        report_lines.append("## 📊 综合评分")
        report_lines.append("")
        report_lines.append("| 维度 | 得分 | 通过率 | 测试用例数 |")
        report_lines.append("|------|------|--------|------------|")
        
        total_score = 0
        dimension_count = 0
        
        for dim, data in self.results.items():
            stats = data.get("stats", {})
            dim_name = data.get("dimension_name", dim)
            score_percent = stats.get("avg_score_percent", "N/A")
            pass_rate = stats.get("pass_rate", "N/A")
            total_cases = stats.get("total_cases", 0)
            
            # 添加表情符号
            score_val = stats.get("avg_score", 0)
            emoji = "🟢" if score_val >= 0.8 else "🟡" if score_val >= 0.6 else "🔴"
            
            report_lines.append(f"| {dim_name} | {emoji} {score_percent} | {pass_rate} | {total_cases} |")
            
            total_score += score_val
            dimension_count += 1
        
        # 计算总分
        if dimension_count > 0:
            overall = total_score / dimension_count * 100
            overall_emoji = "🏆" if overall >= 80 else "⭐" if overall >= 60 else "📈"
            report_lines.append(f"| **总体** | {overall_emoji} **{overall:.1f}%** | - | - |")
        
        report_lines.append("")
        report_lines.append("---")
        report_lines.append("")
        
        # 各维度详细分析
        report_lines.append("## 📋 详细分析")
        report_lines.append("")
        
        for dim, data in self.results.items():
            dim_name = data.get("dimension_name", dim)
            stats = data.get("stats", {})
            results_list = data.get("results", [])
            
            report_lines.append(f"### {dim_name}")
            report_lines.append("")
            
            # 统计摘要
            report_lines.append(f"- **平均得分**: {stats.get('avg_score_percent', 'N/A')}")
            report_lines.append(f"- **通过/失败**: {stats.get('passed', 0)} / {stats.get('failed', 0)}")
            report_lines.append("")
            
            # 失败用例列表
            failed_cases = [r for r in results_list if not r.get("passed", False)]
            if failed_cases:
                report_lines.append("#### ❌ 失败用例")
                report_lines.append("")
                report_lines.append("| Case ID | 名称 | 用户输入 | 得分 |")
                report_lines.append("|---------|------|----------|------|")
                for case in failed_cases[:5]:  # 最多显示5个
                    case_id = case.get("case_id", "")
                    case_name = case.get("case_name", "")[:20]
                    test_input = case.get("test_input", "")[:30]
                    score = case.get("total_score", 0)
                    report_lines.append(f"| {case_id} | {case_name} | {test_input}... | {score:.2f} |")
                report_lines.append("")
            
            # 待人工评估的用例
            manual_cases = [r for r in results_list if r.get("manual_eval_required", False)]
            if manual_cases:
                report_lines.append(f"#### 📝 待人工评估: {len(manual_cases)} 个用例")
                report_lines.append("")
            
            report_lines.append("---")
            report_lines.append("")
        
        # 建议改进
        report_lines.append("## 💡 改进建议")
        report_lines.append("")
        report_lines.append("*（根据失败用例自动生成）*")
        report_lines.append("")
        
        for dim, data in self.results.items():
            results_list = data.get("results", [])
            failed_cases = [r for r in results_list if not r.get("passed", False)]
            
            if failed_cases:
                dim_name = data.get("dimension_name", dim)
                report_lines.append(f"### {dim_name}")
                
                # 按 category 分组
                categories = {}
                for case in failed_cases:
                    cat = case.get("category", "other")
                    if cat not in categories:
                        categories[cat] = 0
                    categories[cat] += 1
                
                for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
                    report_lines.append(f"- **{cat}** 类失败 {count} 个，建议重点优化")
                
                report_lines.append("")
        
        # 页脚
        report_lines.append("---")
        report_lines.append("")
        report_lines.append(f"*报告生成于 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
        
        # 保存文件
        report_content = "\n".join(report_lines)
        filepath = os.path.join(self.output_dir, f"{filename}.md")
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(report_content)
        
        return filepath
    
    def generate_json_report(self, filename: str = None) -> str:
        """生成 JSON 格式的详细报告"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"evaluation_report_{timestamp}"
        
        filepath = os.path.join(self.output_dir, f"{filename}.json")
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)
        
        return filepath
    
    def print_console_summary(self):
        """在控制台打印美观的摘要"""
        print("\n")
        print("╔" + "═"*58 + "╗")
        print("║" + " 🎭 陪伴智能体评估报告 ".center(56) + "║")
        print("╠" + "═"*58 + "╣")
        
        total_score = 0
        dimension_count = 0
        
        for dim, data in self.results.items():
            stats = data.get("stats", {})
            dim_name = data.get("dimension_name", dim)
            score = stats.get("avg_score", 0)
            score_percent = stats.get("avg_score_percent", "N/A")
            pass_rate = stats.get("pass_rate", "N/A")
            
            emoji = "🟢" if score >= 0.8 else "🟡" if score >= 0.6 else "🔴"
            
            line = f"  {emoji} {dim_name}: {score_percent} (通过率: {pass_rate})"
            print("║" + line.ljust(57) + "║")
            
            total_score += score
            dimension_count += 1
        
        print("╠" + "═"*58 + "╣")
        
        if dimension_count > 0:
            overall = total_score / dimension_count * 100
            overall_emoji = "🏆" if overall >= 80 else "⭐" if overall >= 60 else "📈"
            overall_line = f"  {overall_emoji} 总体得分: {overall:.1f}%"
            print("║" + overall_line.ljust(57) + "║")
        
        print("╚" + "═"*58 + "╝")
        print()


def generate_report(results: Dict, output_dir: str = None) -> Dict[str, str]:
    """
    一键生成所有格式的报告
    
    Args:
        results: 评估结果
        output_dir: 输出目录
    
    Returns:
        各格式报告的文件路径
    """
    generator = ReportGenerator(results, output_dir)
    
    # 打印控制台摘要
    generator.print_console_summary()
    
    # 生成报告文件
    md_path = generator.generate_markdown_report()
    json_path = generator.generate_json_report()
    
    print(f"📄 Markdown 报告: {md_path}")
    print(f"📊 JSON 详细数据: {json_path}")
    
    return {
        "markdown": md_path,
        "json": json_path
    }
