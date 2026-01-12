# performance_tracker.py
"""
性能追踪器 - 用于测量系统各环节的耗时

使用方式：
    from src.performance_tracker import get_tracker, track_time
    
    # 方式1：使用装饰器
    @track_time("memory_loader")
    def memory_loader_node(state):
        ...
    
    # 方式2：使用上下文管理器
    tracker = get_tracker()
    with tracker.track("llm_call"):
        response = llm.invoke(prompt)
    
    # 方式3：手动记录
    tracker = get_tracker()
    tracker.start("compression")
    # ... 执行代码 ...
    tracker.stop("compression")
    
    # 获取报告
    report = tracker.get_report()
    tracker.print_report()
"""

import time
from typing import Dict, List, Optional, Any
from contextlib import contextmanager
from functools import wraps
from datetime import datetime


class PerformanceTracker:
    """性能追踪器单例"""
    
    def __init__(self):
        self.reset()
    
    def reset(self):
        """重置追踪器"""
        self._timings: Dict[str, List[float]] = {}
        self._current: Dict[str, float] = {}
        self._start_time: Optional[float] = None
        self._node_timings: Dict[str, Dict[str, float]] = {}
        self._current_node: Optional[str] = None
    
    def start_session(self):
        """开始一个新的追踪会话"""
        self.reset()
        self._start_time = time.perf_counter()
    
    def start(self, key: str):
        """开始计时"""
        self._current[key] = time.perf_counter()
    
    def stop(self, key: str) -> float:
        """
        停止计时并记录
        
        Returns:
            耗时（秒）
        """
        if key not in self._current:
            return 0.0
        
        elapsed = time.perf_counter() - self._current[key]
        del self._current[key]
        
        # 记录到全局统计
        if key not in self._timings:
            self._timings[key] = []
        self._timings[key].append(elapsed)
        
        # 记录到当前节点
        if self._current_node:
            if self._current_node not in self._node_timings:
                self._node_timings[self._current_node] = {}
            self._node_timings[self._current_node][key] = elapsed
        
        return elapsed
    
    @contextmanager
    def track(self, key: str):
        """上下文管理器方式追踪"""
        self.start(key)
        try:
            yield
        finally:
            self.stop(key)
    
    def start_node(self, node_name: str):
        """开始追踪一个节点"""
        self._current_node = node_name
        self.start(f"node_{node_name}")
    
    def stop_node(self, node_name: str) -> float:
        """停止追踪一个节点"""
        elapsed = self.stop(f"node_{node_name}")
        self._current_node = None
        return elapsed
    
    @contextmanager
    def track_node(self, node_name: str):
        """上下文管理器方式追踪节点"""
        self.start_node(node_name)
        try:
            yield
        finally:
            self.stop_node(node_name)
    
    def record(self, key: str, value: float):
        """直接记录一个耗时值"""
        if key not in self._timings:
            self._timings[key] = []
        self._timings[key].append(value)
        
        # 记录到当前节点
        if self._current_node:
            if self._current_node not in self._node_timings:
                self._node_timings[self._current_node] = {}
            self._node_timings[self._current_node][key] = value
    
    def get_total_time(self) -> float:
        """获取总耗时"""
        if self._start_time is None:
            return 0.0
        return time.perf_counter() - self._start_time
    
    def get_timing(self, key: str) -> Optional[float]:
        """获取某个键的最后一次耗时"""
        if key in self._timings and self._timings[key]:
            return self._timings[key][-1]
        return None
    
    def get_all_timings(self) -> Dict[str, List[float]]:
        """获取所有计时数据"""
        return self._timings.copy()
    
    def get_node_timings(self) -> Dict[str, Dict[str, float]]:
        """获取节点级别的计时数据"""
        return self._node_timings.copy()
    
    def get_report(self) -> Dict[str, Any]:
        """
        生成性能报告
        
        Returns:
            性能报告字典
        """
        total_time = self.get_total_time()
        
        # 计算 LLM 调用总时间
        llm_keys = [k for k in self._timings if "llm" in k.lower()]
        llm_total = sum(
            sum(self._timings[k]) for k in llm_keys
        )
        
        # 计算节点耗时
        node_total = {}
        for key, values in self._timings.items():
            if key.startswith("node_"):
                node_name = key[5:]  # 去掉 "node_" 前缀
                node_total[node_name] = sum(values)
        
        return {
            "total_time": total_time,
            "llm_total": llm_total,
            "llm_percentage": (llm_total / total_time * 100) if total_time > 0 else 0,
            "node_timings": self._node_timings,
            "node_total": node_total,
            "all_timings": {k: sum(v) for k, v in self._timings.items()},
            "timestamp": datetime.now().isoformat()
        }
    
    def print_report(self, detailed: bool = True):
        """
        打印性能报告
        
        Args:
            detailed: 是否显示详细信息
        """
        report = self.get_report()
        
        print("\n" + "=" * 60)
        print("⏱️  本轮处理耗时报告")
        print("=" * 60)
        
        # 按节点打印
        if detailed and report["node_timings"]:
            for node_name, timings in report["node_timings"].items():
                print(f"\n📦 {node_name}:")
                for key, value in timings.items():
                    if not key.startswith("node_"):
                        print(f"    - {key}: {value:.3f}s")
                
                # 打印节点总耗时
                node_key = f"node_{node_name}"
                if node_key in report["all_timings"]:
                    print(f"    ⏱️  节点总耗时: {report['all_timings'][node_key]:.3f}s")
        
        print("\n" + "-" * 60)
        print("📊 汇总统计:")
        print(f"    总耗时: {report['total_time']:.3f}s")
        print(f"    LLM 调用耗时: {report['llm_total']:.3f}s")
        print(f"    LLM 调用占比: {report['llm_percentage']:.1f}%")
        
        # 非 LLM 耗时
        non_llm_time = report['total_time'] - report['llm_total']
        print(f"    其他开销: {non_llm_time:.3f}s ({100 - report['llm_percentage']:.1f}%)")
        
        print("=" * 60 + "\n")
    
    def get_summary_line(self) -> str:
        """获取单行摘要"""
        report = self.get_report()
        return f"⏱️ 总耗时: {report['total_time']:.2f}s | LLM: {report['llm_total']:.2f}s ({report['llm_percentage']:.0f}%)"


# 全局单例
_tracker: Optional[PerformanceTracker] = None


def get_tracker() -> PerformanceTracker:
    """获取全局性能追踪器单例"""
    global _tracker
    if _tracker is None:
        _tracker = PerformanceTracker()
    return _tracker


def reset_tracker():
    """重置全局追踪器"""
    global _tracker
    if _tracker:
        _tracker.reset()


def track_time(key: str):
    """
    装饰器：追踪函数执行时间
    
    Usage:
        @track_time("my_function")
        def my_function():
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            tracker = get_tracker()
            tracker.start(key)
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                elapsed = tracker.stop(key)
                print(f"    ⏱️ {key}: {elapsed:.3f}s")
        return wrapper
    return decorator


def track_node(node_name: str):
    """
    装饰器：追踪节点执行时间
    
    Usage:
        @track_node("reasoning_node")
        def reasoning_node(state):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            tracker = get_tracker()
            tracker.start_node(node_name)
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                elapsed = tracker.stop_node(node_name)
                print(f"    ⏱️ {node_name} 总耗时: {elapsed:.3f}s")
        return wrapper
    return decorator

