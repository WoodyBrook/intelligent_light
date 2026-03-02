# agent_adapter.py - 真实 Agent 适配器
"""
将 Neko-Light 的 LangGraph 工作流包装成评估框架需要的接口
"""

import os
import sys
import time
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 添加项目根目录到路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)


class RealAgentAdapter:
    """
    真实 Agent 适配器
    
    将 Neko-Light 的 OODA 工作流包装成评估框架需要的简单接口：
    - chat(user_input) -> response
    - reset() -> None
    - get_last_emotion() -> Optional[str]
    """
    
    def __init__(self, verbose: bool = False):
        """
        初始化 Agent 适配器
        
        Args:
            verbose: 是否打印详细日志
        """
        self.verbose = verbose
        self.app = None
        self.state_manager = None
        self.current_state = None
        self.last_emotion = None
        
        self._initialize()
    
    def _initialize(self):
        """初始化工作流和状态"""
        if self.verbose:
            print("🔧 初始化 Agent 适配器...")
        
        try:
            from src.graph import build_graph
            from src.state_manager import StateManager
            
            # 构建工作流图
            self.app = build_graph()
            
            # 初始化状态管理器
            self.state_manager = StateManager()
            
            # 初始化状态
            self.reset()
            
            if self.verbose:
                print("✅ Agent 适配器初始化完成")
                
        except Exception as e:
            raise RuntimeError(f"Agent 适配器初始化失败: {e}")
    
    def reset(self):
        """
        重置 Agent 状态（用于每个测试用例开始前）
        清除对话历史，但保留用户画像的结构
        """
        if self.state_manager is None:
            return
        
        import time as time_module
        
        # 获取初始状态
        self.current_state = self.state_manager.initialize_state()
        
        # 清除对话历史
        self.current_state["history"] = []
        
        # 清除临时字段
        self.current_state["user_input"] = ""
        self.current_state["voice_content"] = None
        self.current_state["action_plan"] = {}
        self.current_state["memory_context"] = None
        self.current_state["tool_calls"] = None
        self.current_state["tool_results"] = None
        
        # 重置用户画像为空（评估时从零开始）
        self.current_state["user_profile"] = {
            "version": "2.0",
            "name": None,
            "core_preferences": [],
            "preference_summary": {
                "food": [],
                "music": [],
                "activity": [],
                "habit": [],
                "work": [],
            },
            "important_dates": [],
        }
        
        # === 关键修复：防止"回家欢迎仪式"干扰测试 ===
        # 设置最近交互时间，模拟用户"刚刚在场"
        current_time = time_module.time()
        self.current_state["context_signals"] = {
            "last_interaction_time": current_time,
            "last_seen_time": current_time,
            "activity_level": "active",
            "time_of_day": "day",
        }
        
        # 设置内部驱动力为正常状态
        self.current_state["internal_drives"] = {
            "boredom": 0,
            "energy": 80,
        }
        
        # 禁用专注模式
        self.current_state["focus_mode"] = False
        
        self.last_emotion = None
        
        if self.verbose:
            print("🔄 Agent 状态已重置（测试模式）")
    
    def chat(self, user_input: str) -> str:
        """
        发送消息给 Agent 并获取回复
        
        Args:
            user_input: 用户输入文本
        
        Returns:
            智能体的回复文本
        """
        if self.app is None:
            raise RuntimeError("Agent 未初始化")
        
        try:
            # 准备输入状态
            self.current_state["user_input"] = user_input
            self.current_state["event_type"] = "user_input"
            self.current_state["should_proceed"] = True
            
            if self.verbose:
                print(f"📤 发送: {user_input[:50]}...")
            
            # 执行工作流
            result = self.app.invoke(self.current_state)
            
            # 提取回复
            voice_content = result.get("voice_content", "")
            
            # 更新状态（保留持久化字段）
            self._update_state_from_result(result)
            
            # 提取情绪（如果有）
            self._extract_emotion_from_result(result)
            
            if self.verbose:
                print(f"📥 回复: {voice_content[:50] if voice_content else '(无回复)'}...")
            
            return voice_content or ""
            
        except Exception as e:
            if self.verbose:
                print(f"❌ 执行错误: {e}")
            return f"[错误] {str(e)}"
    
    def _update_state_from_result(self, result: Dict):
        """从工作流结果中更新状态"""
        persistent_fields = [
            "history", "user_profile", "internal_drives",
            "user_preferences", "context_signals",
            "intimacy_level", "intimacy_rank", "intimacy_history",
            "memory_context", "current_emotion"
        ]
        
        for field in persistent_fields:
            if field in result:
                self.current_state[field] = result[field]
        
        # 清空临时字段
        self.current_state["user_input"] = ""
        self.current_state["voice_content"] = None
        self.current_state["action_plan"] = {}
    
    def _extract_emotion_from_result(self, result: Dict):
        """从结果中提取情绪信息"""
        # 尝试从 current_emotion 字段获取
        current_emotion = result.get("current_emotion")
        if current_emotion and isinstance(current_emotion, dict):
            self.last_emotion = current_emotion.get("type") or current_emotion.get("category")
            return
        
        # 尝试从 memory_context 获取
        memory_context = result.get("memory_context")
        if memory_context and isinstance(memory_context, dict):
            emotion = memory_context.get("detected_emotion")
            if emotion:
                self.last_emotion = emotion
                return
        
        self.last_emotion = None
    
    def get_last_emotion(self) -> Optional[str]:
        """
        获取上一次对话中检测到的情绪
        
        Returns:
            情绪标签，如 "happy", "sad", "anxious" 等
        """
        return self.last_emotion
    
    def get_user_profile(self) -> Dict:
        """获取当前用户画像"""
        return self.current_state.get("user_profile", {})
    
    def get_history(self) -> List:
        """获取对话历史"""
        return self.current_state.get("history", [])
    
    def get_intimacy_level(self) -> float:
        """获取当前亲密度"""
        return self.current_state.get("intimacy_level", 30.0)


def create_real_agent(verbose: bool = False) -> RealAgentAdapter:
    """
    创建真实 Agent 实例
    
    Args:
        verbose: 是否打印详细日志
    
    Returns:
        RealAgentAdapter 实例
    """
    return RealAgentAdapter(verbose=verbose)


# ==========================================
# 测试代码
# ==========================================

if __name__ == "__main__":
    print("测试 Agent 适配器...")
    
    try:
        agent = create_real_agent(verbose=True)
        
        # 简单对话测试
        print("\n--- 测试对话 1 ---")
        response1 = agent.chat("你好，我叫小明")
        print(f"回复: {response1}")
        
        print("\n--- 测试对话 2 ---")
        response2 = agent.chat("我叫什么名字？")
        print(f"回复: {response2}")
        
        print("\n--- 测试重置 ---")
        agent.reset()
        response3 = agent.chat("我叫什么名字？")
        print(f"重置后回复: {response3}")
        
        print("\n✅ 适配器测试完成")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
