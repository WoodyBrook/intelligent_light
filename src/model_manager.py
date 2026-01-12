# model_manager.py
"""
模型管理器 - 支持多模型切换策略（三级模型）

根据任务类型自动选择最合适的模型：
- Fast 模型：用于超快响应（问候、确认、简单回复）
- Chat 模型：用于日常对话、情感陪伴、闲聊
- Reasoning 模型：用于复杂推理、条件逻辑、工具调用
"""

import os
import re
from typing import Optional, Literal, Tuple, Dict, Any
from langchain_openai import ChatOpenAI


# 模型类型定义
ModelTier = Literal["fast", "chat", "reasoning"]
TaskType = Literal["fast", "chat", "reasoning", "auto"]


class ModelManager:
    """模型管理器：管理多个 LLM 实例，支持三级智能切换"""
    
    # 模型成本估算（每 1K tokens，单位：人民币）
    MODEL_COSTS = {
        "doubao-lite-32k-character-250228": {"input": 0.0003, "output": 0.0006},
        "deepseek-chat": {"input": 0.001, "output": 0.002},
        "deepseek-v3-1-terminus": {"input": 0.005, "output": 0.01},
    }
    
    # 超快响应场景的模式（精确匹配）
    FAST_PATTERNS = [
        r"^你好[!！~]?$",
        r"^嗨[!！~]?$",
        r"^早上好[!！~]?$",
        r"^晚上好[!！~]?$",
        r"^下午好[!！~]?$",
        r"^hello[!]?$",
        r"^hi[!]?$",
        r"^hey[!]?$",
        r"^谢谢[你您]?[!！~]?$",
        r"^不客气[!！~]?$",
        r"^再见[!！~]?$",
        r"^拜拜[!！~]?$",
        r"^thanks[!]?$",
        r"^bye[!]?$",
        r"^好的[!！~]?$",
        r"^好[!！~]?$",
        r"^嗯[!！。~]?$",
        r"^哦[!！。~]?$",
        r"^ok[!]?$",
        r"^okay[!]?$",
        r"^知道了[!！~]?$",
        r"^明白[了]?[!！~]?$",
        r"^收到[!！~]?$",
        r"^对[!！~]?$",
        r"^是的[!！~]?$",
        r"^没事[!！~]?$",
        r"^没问题[!！~]?$",
    ]
    
    def __init__(
        self,
        fast_model: str = "doubao-lite-32k-character-250228",
        chat_model: str = "doubao-1-5-pro-32k-250115",  # 豆包 1.5 Pro，快速对话，无深度思考
        reasoning_model: str = "deepseek-v3-1-terminus",
        base_url: str = "https://ark.cn-beijing.volces.com/api/v3",
        api_key: Optional[str] = None,
        default_strategy: Literal["conservative", "aggressive"] = "aggressive"
    ):
        """
        初始化模型管理器
        
        Args:
            fast_model: 快速模型名称（用于超快响应）
            chat_model: 聊天模型名称（用于日常对话）
            reasoning_model: 推理模型名称（用于复杂任务）
            base_url: API 基础 URL
            api_key: API 密钥（如果为 None，从环境变量读取）
            default_strategy: 默认策略
                - "conservative": 不确定时使用 Reasoning（更安全）
                - "aggressive": 不确定时使用 Chat（更快、更便宜）
        """
        self.api_key = api_key or os.environ.get("VOLCENGINE_API_KEY") or os.environ.get("ARK_API_KEY")
        if not self.api_key:
            raise ValueError("请设置 VOLCENGINE_API_KEY 或 ARK_API_KEY 环境变量")
        
        self.base_url = base_url
        self.fast_model_name = fast_model
        self.chat_model_name = chat_model
        self.reasoning_model_name = reasoning_model
        self.default_strategy = default_strategy
        
        # 延迟初始化模型实例（按需创建）
        self._fast_llm: Optional[ChatOpenAI] = None
        self._chat_llm: Optional[ChatOpenAI] = None
        self._reasoning_llm: Optional[ChatOpenAI] = None
        
        # 调用统计
        self._stats: Dict[str, Dict[str, Any]] = {
            "fast": {"calls": 0, "total_time": 0.0, "estimated_tokens": 0},
            "chat": {"calls": 0, "total_time": 0.0, "estimated_tokens": 0},
            "reasoning": {"calls": 0, "total_time": 0.0, "estimated_tokens": 0}
        }
        
        print(f"🔧 模型管理器初始化（三级模型）:")
        print(f"   - ⚡ Fast 模型: {fast_model}")
        print(f"   - 💬 Chat 模型: {chat_model}")
        print(f"   - 🧠 Reasoning 模型: {reasoning_model}")
        print(f"   - 默认策略: {default_strategy}")
    
    @property
    def fast_llm(self) -> ChatOpenAI:
        """获取 Fast 模型实例（延迟初始化）"""
        if self._fast_llm is None:
            self._fast_llm = ChatOpenAI(
                model=self.fast_model_name,
                temperature=0.7,
                api_key=self.api_key,
                base_url=self.base_url,
                timeout=15  # Fast 模型超快，设置最短超时
            )
        return self._fast_llm
    
    @property
    def chat_llm(self) -> ChatOpenAI:
        """获取 Chat 模型实例（延迟初始化）"""
        if self._chat_llm is None:
            self._chat_llm = ChatOpenAI(
                model=self.chat_model_name,
                temperature=0.7,
                api_key=self.api_key,
                base_url=self.base_url,
                timeout=30  # Chat 模型较快
            )
        return self._chat_llm
    
    @property
    def reasoning_llm(self) -> ChatOpenAI:
        """获取 Reasoning 模型实例（延迟初始化）"""
        if self._reasoning_llm is None:
            self._reasoning_llm = ChatOpenAI(
                model=self.reasoning_model_name,
                temperature=0.7,
                api_key=self.api_key,
                base_url=self.base_url,
                timeout=60  # Reasoning 模型可能需要更长时间
            )
        return self._reasoning_llm
    
    def select_model(
        self,
        task_type: TaskType = "auto",
        user_input: str = "",
        conversation_history: Optional[list] = None,
        has_tools: bool = False
    ) -> Tuple[ChatOpenAI, str]:
        """
        根据任务类型选择模型
        
        Args:
            task_type: 任务类型
                - "fast": 强制使用 fast 模型
                - "chat": 强制使用 chat 模型
                - "reasoning": 强制使用 reasoning 模型
                - "auto": 自动判断
            user_input: 用户输入（用于自动判断）
            conversation_history: 对话历史（用于自动判断）
            has_tools: 是否需要工具调用
        
        Returns:
            (llm_instance, model_name) 元组
        """
        if task_type == "fast":
            return self.fast_llm, self.fast_model_name
        
        if task_type == "chat":
            return self.chat_llm, self.chat_model_name
        
        if task_type == "reasoning":
            return self.reasoning_llm, self.reasoning_model_name
        
        # 自动判断
        if task_type == "auto":
            tier = self._select_model_tier(
                user_input, conversation_history, has_tools
            )
            
            if tier == "fast":
                return self.fast_llm, self.fast_model_name
            elif tier == "chat":
                return self.chat_llm, self.chat_model_name
            else:
                return self.reasoning_llm, self.reasoning_model_name
        
        # 默认使用 chat 模型
        return self.chat_llm, self.chat_model_name
    
    def _select_model_tier(
        self,
        user_input: str,
        conversation_history: list = None,
        has_tools: bool = False
    ) -> ModelTier:
        """
        智能选择模型层级
        
        决策流程：
        1. 需要工具调用 → reasoning
        2. 超简单输入（问候、确认） → fast
        3. 复杂任务关键词 → reasoning
        4. 条件逻辑/多步骤 → reasoning
        5. 长对话历史 → reasoning
        6. 其他情况 → chat（默认）
        
        Args:
            user_input: 用户输入
            conversation_history: 对话历史
            has_tools: 是否需要工具调用
        
        Returns:
            "fast" | "chat" | "reasoning"
        """
        # === 1. 需要工具调用 → reasoning ===
        if has_tools:
            return "reasoning"
        
        input_lower = user_input.lower().strip()
        
        # === 2. 超简单输入 → fast ===
        for pattern in self.FAST_PATTERNS:
            if re.match(pattern, input_lower, re.IGNORECASE):
                return "fast"
        
        # === 3. 复杂任务关键词 → reasoning ===
        complex_keywords = [
            "分析", "解释", "为什么", "如何", "怎么", "计划", "策略",
            "比较", "对比", "总结", "归纳", "推理", "判断", "评估",
            "analyze", "explain", "why", "how", "plan", "strategy",
            "compare", "summarize", "reason", "judge", "evaluate"
        ]
        if any(kw in input_lower for kw in complex_keywords):
            return "reasoning"
        
        # === 4. 条件逻辑关键词 → reasoning ===
        conditional_patterns = [
            r"如果.+",
            r"当(?!然).+",
            r"若(?!是).+",
            r"要是.+",
            r"假如.+",
            r"万一.+",
            r"\bif\b.+",
            r"\bwhen\b.+",
            r"\bunless\b.+",
        ]
        for pattern in conditional_patterns:
            if re.search(pattern, input_lower, re.IGNORECASE):
                return "reasoning"
        
        # === 5. 多步骤任务关键词 → reasoning ===
        multi_step_patterns = [
            r"然后.+",
            r"之后.+",
            r"接着.+",
            r"再(?!见).+",
            r"并且.+",
            r"同时.+",
            r"先.+然后",
            r"最后.+",
            r"\bthen\b",
            r"\bafter\b",
            r"\bfirst\b.+\bthen\b",
            r"\bfinally\b",
        ]
        for pattern in multi_step_patterns:
            if re.search(pattern, input_lower, re.IGNORECASE):
                return "reasoning"
        
        # === 6. 工具相关关键词 → reasoning ===
        tool_keywords = [
            "查", "搜", "播放", "音乐", "天气", "时间", "几点",
            "提醒", "定时", "闹钟", "日程", "邮件", "新闻"
        ]
        if any(kw in input_lower for kw in tool_keywords):
            return "reasoning"
        
        # === 7. 长对话历史 → reasoning ===
        if conversation_history:
            conversation_count = sum(
                1 for conv in conversation_history
                if isinstance(conv, dict) and conv.get("type") == "conversation"
            )
            if conversation_count > 5:
                return "reasoning"
        
        # === 8. 情感/闲聊场景 → chat ===
        emotion_keywords = [
            "累", "开心", "难过", "伤心", "烦", "无聊", "想你",
            "喜欢", "爱", "讨厌", "害怕", "紧张", "焦虑", "压力",
            "心情", "感觉", "觉得", "想", "希望"
        ]
        if any(kw in input_lower for kw in emotion_keywords):
            return "chat"
        
        # === 9. 默认策略 ===
        if self.default_strategy == "conservative":
            return "reasoning"
        else:
            return "chat"
    
    def get_model_tier(self, model_name: str) -> ModelTier:
        """根据模型名称返回层级"""
        if model_name == self.fast_model_name:
            return "fast"
        elif model_name == self.chat_model_name:
            return "chat"
        else:
            return "reasoning"
    
    def record_call(
        self,
        model_type: ModelTier,
        elapsed_time: float,
        estimated_tokens: int = 0
    ):
        """
        记录模型调用统计
        
        Args:
            model_type: 模型类型 ("fast" | "chat" | "reasoning")
            elapsed_time: 调用耗时（秒）
            estimated_tokens: 估算的 token 数
        """
        if model_type in self._stats:
            self._stats[model_type]["calls"] += 1
            self._stats[model_type]["total_time"] += elapsed_time
            self._stats[model_type]["estimated_tokens"] += estimated_tokens
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取调用统计
        
        Returns:
            包含调用次数、总耗时、估算成本的字典
        """
        fast_stats = self._stats["fast"]
        chat_stats = self._stats["chat"]
        reasoning_stats = self._stats["reasoning"]
        
        # 估算成本
        fast_cost = self._estimate_cost(self.fast_model_name, fast_stats["estimated_tokens"])
        chat_cost = self._estimate_cost(self.chat_model_name, chat_stats["estimated_tokens"])
        reasoning_cost = self._estimate_cost(self.reasoning_model_name, reasoning_stats["estimated_tokens"])
        
        total_calls = fast_stats["calls"] + chat_stats["calls"] + reasoning_stats["calls"]
        total_time = fast_stats["total_time"] + chat_stats["total_time"] + reasoning_stats["total_time"]
        total_cost = fast_cost + chat_cost + reasoning_cost
        
        return {
            "fast": {
                "calls": fast_stats["calls"],
                "total_time": round(fast_stats["total_time"], 3),
                "avg_time": round(fast_stats["total_time"] / max(1, fast_stats["calls"]), 3),
                "estimated_tokens": fast_stats["estimated_tokens"],
                "estimated_cost": round(fast_cost, 6)
            },
            "chat": {
                "calls": chat_stats["calls"],
                "total_time": round(chat_stats["total_time"], 3),
                "avg_time": round(chat_stats["total_time"] / max(1, chat_stats["calls"]), 3),
                "estimated_tokens": chat_stats["estimated_tokens"],
                "estimated_cost": round(chat_cost, 6)
            },
            "reasoning": {
                "calls": reasoning_stats["calls"],
                "total_time": round(reasoning_stats["total_time"], 3),
                "avg_time": round(reasoning_stats["total_time"] / max(1, reasoning_stats["calls"]), 3),
                "estimated_tokens": reasoning_stats["estimated_tokens"],
                "estimated_cost": round(reasoning_cost, 6)
            },
            "total": {
                "calls": total_calls,
                "total_time": round(total_time, 3),
                "estimated_cost": round(total_cost, 6)
            }
        }
    
    def _estimate_cost(self, model_name: str, tokens: int) -> float:
        """
        估算成本
        
        Args:
            model_name: 模型名称
            tokens: token 数量
        
        Returns:
            估算成本（人民币）
        """
        if model_name in self.MODEL_COSTS:
            cost_per_1k = self.MODEL_COSTS[model_name]
            input_cost = (tokens / 2 / 1000) * cost_per_1k["input"]
            output_cost = (tokens / 2 / 1000) * cost_per_1k["output"]
            return input_cost + output_cost
        return 0.0
    
    def reset_stats(self):
        """重置调用统计"""
        self._stats = {
            "fast": {"calls": 0, "total_time": 0.0, "estimated_tokens": 0},
            "chat": {"calls": 0, "total_time": 0.0, "estimated_tokens": 0},
            "reasoning": {"calls": 0, "total_time": 0.0, "estimated_tokens": 0}
        }
    
    def print_stats(self):
        """打印调用统计报告"""
        stats = self.get_stats()
        
        print("\n" + "=" * 60)
        print("📊 模型调用统计报告（三级模型）")
        print("=" * 60)
        
        print(f"\n⚡ Fast 模型 ({self.fast_model_name}):")
        print(f"   - 调用次数: {stats['fast']['calls']}")
        print(f"   - 总耗时: {stats['fast']['total_time']:.3f}s")
        print(f"   - 平均耗时: {stats['fast']['avg_time']:.3f}s")
        print(f"   - 估算 Tokens: {stats['fast']['estimated_tokens']}")
        print(f"   - 估算成本: ¥{stats['fast']['estimated_cost']:.6f}")
        
        print(f"\n💬 Chat 模型 ({self.chat_model_name}):")
        print(f"   - 调用次数: {stats['chat']['calls']}")
        print(f"   - 总耗时: {stats['chat']['total_time']:.3f}s")
        print(f"   - 平均耗时: {stats['chat']['avg_time']:.3f}s")
        print(f"   - 估算 Tokens: {stats['chat']['estimated_tokens']}")
        print(f"   - 估算成本: ¥{stats['chat']['estimated_cost']:.6f}")
        
        print(f"\n🧠 Reasoning 模型 ({self.reasoning_model_name}):")
        print(f"   - 调用次数: {stats['reasoning']['calls']}")
        print(f"   - 总耗时: {stats['reasoning']['total_time']:.3f}s")
        print(f"   - 平均耗时: {stats['reasoning']['avg_time']:.3f}s")
        print(f"   - 估算 Tokens: {stats['reasoning']['estimated_tokens']}")
        print(f"   - 估算成本: ¥{stats['reasoning']['estimated_cost']:.6f}")
        
        print(f"\n📈 总计:")
        print(f"   - 总调用次数: {stats['total']['calls']}")
        print(f"   - 总耗时: {stats['total']['total_time']:.3f}s")
        print(f"   - 总估算成本: ¥{stats['total']['estimated_cost']:.6f}")
        
        # 计算占比
        if stats['total']['calls'] > 0:
            fast_ratio = stats['fast']['calls'] / stats['total']['calls'] * 100
            chat_ratio = stats['chat']['calls'] / stats['total']['calls'] * 100
            reasoning_ratio = stats['reasoning']['calls'] / stats['total']['calls'] * 100
            print(f"\n📉 使用比例:")
            print(f"   - ⚡ Fast: {fast_ratio:.1f}%")
            print(f"   - 💬 Chat: {chat_ratio:.1f}%")
            print(f"   - 🧠 Reasoning: {reasoning_ratio:.1f}%")
        
        print("=" * 60 + "\n")
    
    def get_model_info(self) -> dict:
        """获取模型配置信息"""
        return {
            "fast_model": self.fast_model_name,
            "chat_model": self.chat_model_name,
            "reasoning_model": self.reasoning_model_name,
            "base_url": self.base_url,
            "default_strategy": self.default_strategy,
            "fast_initialized": self._fast_llm is not None,
            "chat_initialized": self._chat_llm is not None,
            "reasoning_initialized": self._reasoning_llm is not None
        }


# 全局单例
_model_manager: Optional[ModelManager] = None


def get_model_manager(
    default_strategy: Literal["conservative", "aggressive"] = "aggressive"
) -> ModelManager:
    """
    获取全局模型管理器单例
    
    Args:
        default_strategy: 首次创建时使用的默认策略
    """
    global _model_manager
    if _model_manager is None:
        _model_manager = ModelManager(default_strategy=default_strategy)
    return _model_manager


def reset_model_manager():
    """重置全局模型管理器（用于测试）"""
    global _model_manager
    _model_manager = None
