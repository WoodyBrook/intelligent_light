# context_manager.py
"""
上下文管理模块
负责对话历史压缩、去重、分层内存管理等上下文工程功能
"""

import os
from typing import List, Dict, Optional, Any
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate


class ContextManager:
    """上下文管理器：负责对话历史压缩、去重等功能"""
    
    def __init__(self):
        """初始化上下文管理器"""
        api_key = os.environ.get("VOLCENGINE_API_KEY")
        if not api_key:
            raise ValueError("请设置 VOLCENGINE_API_KEY 环境变量")
        
        # 使用更便宜、更快的模型进行压缩
        self.llm = ChatOpenAI(
            model="deepseek-v3-1-terminus",
            temperature=0.3,  # 较低温度，保证压缩质量
            api_key=api_key,
            base_url="https://ark.cn-beijing.volces.com/api/v3",
            timeout=30
        )
        
        # 压缩阈值配置
        self.compression_threshold = 2000  # 字符数阈值
        self.keep_recent_turns = 2  # 保留最近 N 轮完整对话
        self.compress_range = (3, 10)  # 压缩第 3-10 轮对话
        self.archive_threshold = 20  # 超过 20 轮归档到向量库
    
    def estimate_context_size(self, history: List[Dict]) -> int:
        """
        估算对话历史的字符数大小
        
        Args:
            history: 对话历史列表
            
        Returns:
            总字符数
        """
        total_chars = 0
        for conv in history:
            if isinstance(conv, dict) and conv.get("type") == "conversation":
                user_msg = conv.get("user", "")
                assistant_msg = conv.get("assistant", "")
                total_chars += len(user_msg) + len(assistant_msg)
        return total_chars
    
    def compress_conversation_history(
        self, 
        history: List[Dict], 
        force: bool = False
    ) -> Dict[str, Any]:
        """
        压缩对话历史
        
        策略：
        - 最近 2 轮：完整保留
        - 3-10 轮：压缩为摘要
        - 10 轮以上：归档到向量库（由调用方处理）
        
        Args:
            history: 对话历史列表
            force: 是否强制压缩（忽略阈值检查）
            
        Returns:
            {
                "compressed": bool,  # 是否进行了压缩
                "recent_history": List[Dict],  # 最近的完整对话
                "summary": str,  # 压缩摘要
                "should_archive": List[Dict],  # 需要归档的对话
                "original_size": int,  # 原始字符数
                "compressed_size": int  # 压缩后字符数
            }
        """
        if not history:
            return {
                "compressed": False,
                "recent_history": [],
                "summary": "",
                "should_archive": [],
                "original_size": 0,
                "compressed_size": 0
            }
        
        # 估算当前大小
        original_size = self.estimate_context_size(history)
        
        # 检查是否需要压缩
        if not force and original_size < self.compression_threshold:
            return {
                "compressed": False,
                "recent_history": history,
                "summary": "",
                "should_archive": [],
                "original_size": original_size,
                "compressed_size": original_size
            }
        
        # 分层处理对话历史
        total_turns = len(history)
        
        # 1. 最近 N 轮：完整保留
        recent_history = history[-self.keep_recent_turns:] if total_turns > self.keep_recent_turns else history
        
        # 2. 需要归档的对话（超过 20 轮的部分）
        should_archive = []
        if total_turns > self.archive_threshold:
            should_archive = history[:total_turns - self.archive_threshold]
        
        # 3. 中间部分：压缩为摘要
        compress_start = max(0, total_turns - self.compress_range[1])
        compress_end = max(0, total_turns - self.keep_recent_turns)
        
        to_compress = history[compress_start:compress_end] if compress_end > compress_start else []
        
        summary = ""
        if to_compress:
            print(f"   🗜️  压缩对话历史: {len(to_compress)} 轮 -> 摘要")
            summary = self._generate_summary(to_compress)
        
        # 计算压缩后大小
        compressed_size = self.estimate_context_size(recent_history) + len(summary)
        
        return {
            "compressed": True,
            "recent_history": recent_history,
            "summary": summary,
            "should_archive": should_archive,
            "original_size": original_size,
            "compressed_size": compressed_size,
            "compression_ratio": f"{(1 - compressed_size/original_size)*100:.1f}%" if original_size > 0 else "0%"
        }
    
    def _generate_summary(self, conversations: List[Dict]) -> str:
        """
        使用 LLM 生成对话摘要
        
        保留：关键事实、用户偏好、未完成任务
        删除：闲聊细节、重复信息
        
        Args:
            conversations: 需要压缩的对话列表
            
        Returns:
            压缩后的摘要文本
        """
        # 构建对话文本
        conversation_text = []
        for i, conv in enumerate(conversations, 1):
            if isinstance(conv, dict) and conv.get("type") == "conversation":
                user_msg = conv.get("user", "")
                assistant_msg = conv.get("assistant", "")
                conversation_text.append(f"第{i}轮：")
                conversation_text.append(f"用户: {user_msg}")
                conversation_text.append(f"助手: {assistant_msg}")
                conversation_text.append("")
        
        full_text = "\n".join(conversation_text)
        
        # 构建压缩提示词
        prompt = ChatPromptTemplate.from_messages([
            ("system", """你是一个专业的对话摘要助手。你的任务是将多轮对话压缩为简洁的摘要。

压缩原则：
1. **保留关键信息**：
   - 用户的明确需求或问题
   - 重要的事实信息（时间、地点、天气、数据等）
   - 用户偏好和习惯
   - 未完成的任务或待办事项
   - 情感变化（如用户表扬、抱怨等）

2. **删除冗余信息**：
   - 闲聊寒暄的细节
   - 重复的信息
   - 已解决的临时问题
   - 无关紧要的对话

3. **输出格式**：
   - 使用简洁的要点形式
   - 每个要点一行，以 "- " 开头
   - 保持时间顺序
   - 总字数控制在原文的 30% 以内

示例输出：
- 用户询问了上海的天气，当时是晴天 22°C
- 用户要求调整灯光亮度到 80%
- 用户表扬了助手的回答，亲密度提升
- 用户提到明天要出差去北京"""),
            ("human", "请压缩以下对话：\n\n{conversation_text}")
        ])
        
        try:
            chain = prompt | self.llm
            response = chain.invoke({"conversation_text": full_text})
            summary = response.content.strip()
            
            # 验证摘要质量
            if len(summary) > len(full_text) * 0.5:
                print("   ⚠️  摘要过长，使用简化版本")
                # 如果摘要太长，使用简化策略
                summary = self._simple_summary(conversations)
            
            return summary
        
        except Exception as e:
            print(f"   ⚠️  LLM 压缩失败: {e}，使用简化策略")
            return self._simple_summary(conversations)
    
    def _simple_summary(self, conversations: List[Dict]) -> str:
        """
        简化的摘要策略（不依赖 LLM）
        当 LLM 调用失败或摘要质量不佳时使用
        
        Args:
            conversations: 需要压缩的对话列表
            
        Returns:
            简化摘要
        """
        summary_points = []
        
        for conv in conversations:
            if isinstance(conv, dict) and conv.get("type") == "conversation":
                user_msg = conv.get("user", "")
                
                # 提取关键信息
                if any(keyword in user_msg for keyword in ["天气", "温度", "几度"]):
                    summary_points.append(f"- 用户询问天气信息")
                elif any(keyword in user_msg for keyword in ["时间", "几点", "现在"]):
                    summary_points.append(f"- 用户询问时间")
                elif any(keyword in user_msg for keyword in ["灯", "亮度", "色温"]):
                    summary_points.append(f"- 用户调整灯光设置")
                elif any(keyword in user_msg for keyword in ["音乐", "播放", "歌"]):
                    summary_points.append(f"- 用户请求播放音乐")
                elif len(user_msg) > 10:  # 其他有意义的对话
                    summary_points.append(f"- 用户: {user_msg[:30]}...")
        
        # 去重
        summary_points = list(dict.fromkeys(summary_points))
        
        return "\n".join(summary_points[:5])  # 最多保留 5 个要点
    
    def deduplicate_user_profile(self, user_memories: List[str]) -> List[str]:
        """
        对用户画像进行去重和清洗
        
        策略：
        1. 完全重复的事实：只保留一条
        2. 语义重复的事实：保留最详细的一条
        3. 冲突的事实：保留最新的一条（由 MemoryManager 处理）
        
        Args:
            user_memories: 用户画像列表
            
        Returns:
            去重后的用户画像列表
        """
        if not user_memories:
            return []
        
        # 1. 完全重复去重（保留顺序）
        seen = set()
        unique_memories = []
        for memory in user_memories:
            memory_clean = memory.strip()
            if memory_clean and memory_clean not in seen:
                seen.add(memory_clean)
                unique_memories.append(memory_clean)
        
        # 2. 语义去重：检测高度相似的描述
        # 改进：针对中文优化关键词提取
        def extract_keywords(text: str) -> set:
            """提取关键词：针对中文优化"""
            keywords = set()
            
            # 先标准化文本：统一城市名称（移除"市"字）
            cities = ["上海", "北京", "深圳", "广州", "杭州", "成都", "武汉", "南京", "苏州", 
                      "重庆", "西安", "天津", "厦门", "青岛", "大连", "长沙", "郑州", "济南"]
            text_normalized = text
            for city in cities:
                if f"{city}市" in text_normalized:
                    text_normalized = text_normalized.replace(f"{city}市", city)
            
            # 提取颜色词
            colors = ["红色", "蓝色", "绿色", "黄色", "白色", "黑色", "紫色", "粉色", "橙色", "灰色", "棕色"]
            for color in colors:
                if color in text_normalized:
                    keywords.add(color)
                    keywords.add("颜色")  # 添加通用标签
            
            # 提取城市名（使用标准化后的文本）
            for city in cities:
                if city in text_normalized:
                    keywords.add(city)  # 统一使用城市名（不带"市"）
                    # 如果提到地点相关词，添加通用标签
                    if any(kw in text_normalized for kw in ["所在地", "常住", "住在", "居住"]):
                        keywords.add("地点信息")
            
            # 提取食物类型（添加通用标签）
            foods = ["火锅", "日料", "川菜", "粤菜", "西餐", "烧烤", "海鲜", "面食", "米饭", "咖啡", "茶"]
            for food in foods:
                if food in text_normalized:
                    keywords.add(food)
                    # 如果提到喜好相关词，添加通用标签
                    if any(kw in text_normalized for kw in ["喜欢", "爱吃", "偏好", "爱", "吃"]):
                        keywords.add("食物喜好")
            
            # 提取音乐类型
            music_types = ["轻音乐", "古典", "流行", "摇滚", "爵士", "电子", "民谣", "说唱"]
            for music in music_types:
                if music in text_normalized:
                    keywords.add(music)
                    keywords.add("音乐")
            
            # 提取动作/状态词（用于识别相似表达）
            # "喜欢" vs "爱" vs "偏好"
            if any(word in text_normalized for word in ["喜欢", "爱", "偏好", "最爱"]):
                keywords.add("喜好表达")
            
            # "所在地" vs "住在" vs "居住"
            if any(word in text_normalized for word in ["所在地", "住在", "居住", "常住"]):
                keywords.add("居住表达")
            
            # 移除常见停用词后提取其他关键词
            stopwords = {"用户", "的", "是", "在", "有", "和", "与", "或", "但", "而", 
                         "最", "喜欢", "爱", "经常", "总是", "习惯", "偏好", "吃", "所", "住", "地"}
            
            # 提取其他关键词（长度 >= 2 的连续字符）
            # 使用标准化后的文本（城市名已统一）
            current_word = ""
            for char in text_normalized:
                if char not in stopwords and char not in ["，", "。", "、", "：", "；", " "]:
                    current_word += char
                else:
                    if len(current_word) >= 2 and current_word not in stopwords:
                        # 过滤掉"用户X"这样的组合
                        if not current_word.startswith("用户"):
                            keywords.add(current_word)
                    current_word = ""
            if len(current_word) >= 2 and current_word not in stopwords:
                if not current_word.startswith("用户"):
                    keywords.add(current_word)
            
            return keywords
        
        final_memories = []
        skip_indices = set()
        
        for i, mem1 in enumerate(unique_memories):
            if i in skip_indices:
                continue
            
            # 提取关键词
            words1 = extract_keywords(mem1)
            
            should_skip = False
            for j, mem2 in enumerate(unique_memories[i+1:], start=i+1):
                if j in skip_indices:
                    continue
                
                words2 = extract_keywords(mem2)
                
                # 计算 Jaccard 相似度
                if words1 and words2:
                    intersection = len(words1 & words2)
                    union = len(words1 | words2)
                    similarity = intersection / union if union > 0 else 0
                    
                    # 如果相似度 > 0.6（降低阈值，更敏感），认为是重复
                    if similarity > 0.6:
                        # 保留更长的那条（通常更详细）
                        if len(mem2) > len(mem1):
                            should_skip = True
                            break
                        else:
                            skip_indices.add(j)
            
            if not should_skip:
                final_memories.append(mem1)
        
        if len(final_memories) < len(user_memories):
            print(f"   🧹 去重: {len(user_memories)} 条 -> {len(final_memories)} 条")
        
        return final_memories
    
    def clean_memory_context(self, memory_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        清洗记忆上下文
        
        清洗内容：
        1. 去重用户画像
        2. 移除空白或无效条目
        3. 限制总长度（避免超过 token 限制）
        
        Args:
            memory_context: 原始记忆上下文
            
        Returns:
            清洗后的记忆上下文
        """
        cleaned = memory_context.copy()
        
        # 1. 去重用户画像
        if "user_memories" in cleaned:
            user_memories = cleaned["user_memories"]
            if isinstance(user_memories, list):
                cleaned["user_memories"] = self.deduplicate_user_profile(user_memories)
        
        # 2. 清理动作模式（移除空白）
        if "action_patterns" in cleaned:
            action_patterns = cleaned["action_patterns"]
            if isinstance(action_patterns, list):
                cleaned["action_patterns"] = [
                    pattern.strip() for pattern in action_patterns 
                    if pattern and pattern.strip()
                ]
        
        # 3. 限制总长度（每个列表最多保留前 5 条）
        if "user_memories" in cleaned and len(cleaned["user_memories"]) > 5:
            print(f"   ✂️  用户画像过长，截取前 5 条")
            cleaned["user_memories"] = cleaned["user_memories"][:5]
        
        if "action_patterns" in cleaned and len(cleaned["action_patterns"]) > 3:
            print(f"   ✂️  动作模式过长，截取前 3 条")
            cleaned["action_patterns"] = cleaned["action_patterns"][:3]
        
        return cleaned
    
    def format_compressed_history(self, compression_result: Dict[str, Any]) -> str:
        """
        将压缩结果格式化为可用于 Prompt 的文本
        
        Args:
            compression_result: compress_conversation_history 的返回结果
            
        Returns:
            格式化的历史文本
        """
        parts = []
        
        # 添加摘要部分
        if compression_result.get("summary"):
            parts.append("【历史摘要】")
            parts.append(compression_result["summary"])
            parts.append("")
        
        # 添加最近对话
        recent_history = compression_result.get("recent_history", [])
        if recent_history:
            parts.append("【最近对话】")
            for i, conv in enumerate(recent_history, 1):
                if isinstance(conv, dict) and conv.get("type") == "conversation":
                    user_msg = conv.get("user", "")
                    assistant_msg = conv.get("assistant", "")
                    parts.append(f"{i}. 用户: {user_msg}")
                    parts.append(f"   助手: {assistant_msg}")
        
        return "\n".join(parts)
    
    def format_context_with_xml(
        self,
        user_profile: str,
        recent_memories: List[str],
        action_patterns: List[str],
        conversation_history: str,
        current_state: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        使用 XML 标签格式化完整的上下文
        
        XML 结构化的好处：
        1. 清晰的层次结构，减少 "Lost in the Middle" 问题
        2. LLM 更容易定位和关注特定信息
        3. 便于调试和观察上下文组成
        
        Args:
            user_profile: 用户画像文本
            recent_memories: 最近相关记忆列表
            action_patterns: 相关动作模式列表
            conversation_history: 压缩后的对话历史
            current_state: 当前状态信息（可选）
            
        Returns:
            XML 格式化的上下文文本
        """
        xml_parts = []
        
        # 1. 上下文部分
        xml_parts.append("<context>")
        
        # 1.1 用户画像（最高优先级） - RAM
        if user_profile and user_profile.strip():
            xml_parts.append("  <core_memory_ram>")
            xml_parts.append(user_profile)
            xml_parts.append("  </core_memory_ram>")
        
        # 1.2 最近相关记忆
        if recent_memories:
            xml_parts.append("  <recent_memories>")
            for memory in recent_memories:
                xml_parts.append(f"    - {memory}")
            xml_parts.append("  </recent_memories>")
        
        # 1.3 相关动作模式
        if action_patterns:
            xml_parts.append("  <action_patterns>")
            for pattern in action_patterns:
                xml_parts.append(f"    {pattern}")
            xml_parts.append("  </action_patterns>")
        
        # 1.4 当前状态
        if current_state:
            xml_parts.append("  <current_state>")
            if "intimacy_level" in current_state:
                xml_parts.append(f"    亲密度: {current_state['intimacy_level']}/100")
            if "focus_mode" in current_state:
                xml_parts.append(f"    专注模式: {'开启' if current_state['focus_mode'] else '关闭'}")
            if "conflict_state" in current_state and current_state["conflict_state"]:
                conflict = current_state["conflict_state"]
                if conflict.get("offense_level") != "L0":
                    xml_parts.append(f"    冲突状态: {conflict.get('offense_level')} 级")
            xml_parts.append("  </current_state>")
        
        xml_parts.append("</context>")
        xml_parts.append("")
        
        # 2. 对话历史部分
        if conversation_history and conversation_history.strip():
            xml_parts.append("<conversation_history>")
            xml_parts.append(conversation_history)
            xml_parts.append("</conversation_history>")
        
        return "\n".join(xml_parts)


# 全局单例
_context_manager = None

def get_context_manager() -> ContextManager:
    """获取上下文管理器单例"""
    global _context_manager
    if _context_manager is None:
        _context_manager = ContextManager()
    return _context_manager

