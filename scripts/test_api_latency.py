#!/usr/bin/env python3
"""
DeepSeek API 延迟独立测试脚本

用于测试 API 本身的响应时间，排除系统架构的影响。
"""

import os
import sys
import time
import statistics
from typing import List, Dict, Any

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from langchain_openai import ChatOpenAI
    from langchain_core.prompts import ChatPromptTemplate
except ImportError:
    print("❌ 请先安装依赖: pip install langchain-openai")
    sys.exit(1)


def get_api_client():
    """获取 API 客户端"""
    api_key = os.environ.get("VOLCENGINE_API_KEY")
    if not api_key:
        print("❌ 请设置 VOLCENGINE_API_KEY 环境变量")
        sys.exit(1)
    
    return ChatOpenAI(
        model="deepseek-v3-1-terminus",
        temperature=0.7,
        api_key=api_key,
        base_url="https://ark.cn-beijing.volces.com/api/v3",
        timeout=60
    )


def measure_latency(llm, prompt: str, num_trials: int = 3) -> Dict[str, Any]:
    """
    测量 API 响应延迟
    
    Args:
        llm: LangChain LLM 客户端
        prompt: 测试 prompt
        num_trials: 测试次数
        
    Returns:
        延迟统计信息
    """
    latencies = []
    errors = []
    
    for i in range(num_trials):
        try:
            start_time = time.perf_counter()
            response = llm.invoke(prompt)
            end_time = time.perf_counter()
            
            latency = end_time - start_time
            latencies.append(latency)
            print(f"  第 {i+1} 次: {latency:.2f}s")
            
        except Exception as e:
            errors.append(str(e))
            print(f"  第 {i+1} 次: ❌ 错误 - {e}")
    
    if not latencies:
        return {
            "success": False,
            "errors": errors
        }
    
    return {
        "success": True,
        "latencies": latencies,
        "avg": statistics.mean(latencies),
        "min": min(latencies),
        "max": max(latencies),
        "std": statistics.stdev(latencies) if len(latencies) > 1 else 0
    }


def test_simple_query(llm, num_trials: int = 3):
    """测试简单查询"""
    print("\n📝 测试 1: 简单查询（短输入短输出）")
    prompt = "你好"
    return measure_latency(llm, prompt, num_trials)


def test_medium_query(llm, num_trials: int = 3):
    """测试中等复杂度查询"""
    print("\n📝 测试 2: 中等查询（含上下文）")
    prompt = """
用户资料：
- 名字：小明
- 城市：上海
- 喜好：喜欢听轻音乐

对话历史：
用户：今天天气怎么样？
助手：上海今天晴天，温度25度。

当前用户输入：那推荐一首适合的歌吧
"""
    return measure_latency(llm, prompt, num_trials)


def test_json_output(llm, num_trials: int = 3):
    """测试 JSON 输出（模拟系统实际调用）"""
    print("\n📝 测试 3: JSON 输出（模拟系统实际调用）")
    
    prompt_template = ChatPromptTemplate.from_messages([
        ("system", """你是一个智能台灯助手。请根据用户输入生成回复。
输出格式为 JSON：
{{
    "voice_content": "你要说的话",
    "action_plan": {{"light": {{"brightness": 80}}, "motor": {{"vibration": "gentle"}}}},
    "intimacy_delta": 0.5,
    "intimacy_reason": "chat"
}}"""),
        ("human", "{query}")
    ])
    
    chain = prompt_template | llm
    
    latencies = []
    errors = []
    
    for i in range(num_trials):
        try:
            start_time = time.perf_counter()
            response = chain.invoke({"query": "今天心情不太好"})
            end_time = time.perf_counter()
            
            latency = end_time - start_time
            latencies.append(latency)
            print(f"  第 {i+1} 次: {latency:.2f}s")
            
        except Exception as e:
            errors.append(str(e))
            print(f"  第 {i+1} 次: ❌ 错误 - {e}")
    
    if not latencies:
        return {
            "success": False,
            "errors": errors
        }
    
    return {
        "success": True,
        "latencies": latencies,
        "avg": statistics.mean(latencies),
        "min": min(latencies),
        "max": max(latencies),
        "std": statistics.stdev(latencies) if len(latencies) > 1 else 0
    }


def test_long_context(llm, num_trials: int = 3):
    """测试长上下文"""
    print("\n📝 测试 4: 长上下文（模拟多轮对话）")
    
    # 模拟 10 轮对话历史
    history = "\n".join([
        f"第{i}轮：\n用户：这是第{i}轮对话的用户输入内容，包含一些详细的描述。\n助手：这是第{i}轮对话的助手回复，也包含详细的回复内容。"
        for i in range(1, 11)
    ])
    
    prompt = f"""
对话历史：
{history}

当前用户输入：基于我们之前的对话，帮我总结一下重点。
"""
    return measure_latency(llm, prompt, num_trials)


def print_summary(results: Dict[str, Dict[str, Any]]):
    """打印测试总结"""
    print("\n" + "=" * 60)
    print("📊 DeepSeek API 延迟测试总结")
    print("=" * 60)
    
    for test_name, result in results.items():
        if result.get("success"):
            print(f"\n{test_name}:")
            print(f"  平均延迟: {result['avg']:.2f}s")
            print(f"  最小延迟: {result['min']:.2f}s")
            print(f"  最大延迟: {result['max']:.2f}s")
            if result['std'] > 0:
                print(f"  标准差:   {result['std']:.2f}s")
        else:
            print(f"\n{test_name}: ❌ 全部失败")
            for error in result.get("errors", []):
                print(f"  错误: {error}")
    
    # 计算总体统计
    all_latencies = []
    for result in results.values():
        if result.get("success"):
            all_latencies.extend(result.get("latencies", []))
    
    if all_latencies:
        print("\n" + "-" * 60)
        print("📈 总体统计:")
        print(f"  所有测试平均延迟: {statistics.mean(all_latencies):.2f}s")
        print(f"  所有测试最小延迟: {min(all_latencies):.2f}s")
        print(f"  所有测试最大延迟: {max(all_latencies):.2f}s")
        
        # 诊断结论
        avg_latency = statistics.mean(all_latencies)
        print("\n" + "-" * 60)
        print("🔍 诊断结论:")
        if avg_latency < 2:
            print("  ✅ API 响应正常（< 2s）")
            print("  💡 如果系统整体延迟高，问题可能在架构层面（多次调用、向量检索等）")
        elif avg_latency < 4:
            print("  ⚠️ API 响应中等（2-4s）")
            print("  💡 API 延迟占比较高，但仍需检查系统是否有额外开销")
        else:
            print("  ❌ API 响应较慢（> 4s）")
            print("  💡 API 本身延迟较高，考虑：")
            print("     - 检查网络连接")
            print("     - 尝试不同时段测试")
            print("     - 考虑更换 API 提供商")
    
    print("\n" + "=" * 60)


def main():
    """主函数"""
    print("=" * 60)
    print("🚀 DeepSeek API 延迟独立测试")
    print("=" * 60)
    print(f"API 地址: https://ark.cn-beijing.volces.com/api/v3")
    print(f"模型: deepseek-v3-1-terminus")
    print(f"每项测试次数: 3")
    
    # 获取 API 客户端
    llm = get_api_client()
    print("\n✅ API 客户端初始化成功")
    
    # 运行测试
    results = {}
    
    # 测试 1: 简单查询
    results["简单查询"] = test_simple_query(llm)
    
    # 测试 2: 中等查询
    results["中等查询"] = test_medium_query(llm)
    
    # 测试 3: JSON 输出
    results["JSON输出"] = test_json_output(llm)
    
    # 测试 4: 长上下文
    results["长上下文"] = test_long_context(llm)
    
    # 打印总结
    print_summary(results)


if __name__ == "__main__":
    main()

