# memory_manager.py - 记忆管理系统
# 管理向量数据库和记忆操作，实现双路 RAG 系统

import os
from typing import List, Dict, Optional, Any
from langchain_chroma import Chroma  # Updated from langchain_community.vectorstores
from langchain_ollama import OllamaEmbeddings  # Updated from langchain_community.embeddings
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.documents import Document
import os
import json
import time
from datetime import datetime


class MemoryManager:
    """
    记忆管理系统 - 实现双路 RAG
    管理动作库和用户记忆两个向量数据库集合
    """

    def __init__(self, db_path: str = "./data/chroma_db_actions"):
        """
        初始化记忆管理系统
        创建/加载两个向量数据库集合：
        - action_library: 动作库（系统预设的响应模式）
        - user_memory: 用户记忆（用户的个性化偏好和历史）
        """
        self.db_path = db_path

        # 检查 API Key（仅用于 LLM，Embeddings 使用本地 Ollama）
        api_key = os.environ.get("VOLCENGINE_API_KEY")
        if not api_key:
            raise ValueError("请设置 VOLCENGINE_API_KEY 环境变量，或在代码中设置 API Key")

        # 初始化 Embeddings（使用本地 Ollama）
        print("🔧 初始化 Ollama Embeddings...")
        self.embeddings = OllamaEmbeddings(
            model="bge-m3",  # 您 pull 的模型名称
            base_url="http://localhost:11434"  # Ollama 默认地址
        )
        print("✅ Ollama Embeddings 初始化完成")

        # 初始化 LLM（用于 Query Rewrite）
        self.llm = ChatOpenAI(
            model="deepseek-v3-1-terminus",
            temperature=0.3,  # 较低温度以获得更稳定的重写结果
            api_key=api_key,
            base_url="https://ark.cn-beijing.volces.com/api/v3",
            timeout=30
        )

        # 初始化动作库集合
        self.action_library_path = os.path.join(db_path, "action_library")
        try:
            self.action_store = Chroma(
                collection_name="action_library",
                embedding_function=self.embeddings,
                persist_directory=self.action_library_path
            )
            print("✅ 动作库集合已加载")
        except Exception as e:
            print(f"⚠️  动作库集合初始化失败，将在首次使用时创建: {e}")
            self.action_store = None

        # 初始化用户记忆集合
        self.user_memory_path = os.path.join(db_path, "user_memory")
        try:
            self.user_memory_store = Chroma(
                collection_name="user_memory",
                embedding_function=self.embeddings,
                persist_directory=self.user_memory_path
            )
            print("✅ 用户记忆集合已加载")
        except Exception as e:
            print(f"⚠️  用户记忆集合初始化失败，将在首次使用时创建: {e}")
            self.user_memory_store = None

        print("🔄 MemoryManager 初始化完成")
        
        # Profile 缓存
        self._profile_cache = None
        self._profile_mtime = 0.0

    def query_rewrite(self, user_input: str, conversation_history: Optional[List[Dict]] = None) -> str:
        """
        Query Rewrite - 将用户输入转换为优化的检索查询
        例如: "我饿了" -> "User favorite food preferences"
        
        Args:
            user_input: 用户当前输入
            conversation_history: 对话历史（用于指代消解）
        """
        try:
            # 构建对话历史文本
            history_text = ""
            if conversation_history:
                recent_history = conversation_history[-2:]  # 最近2轮
                history_lines = []
                for conv in recent_history:
                    if isinstance(conv, dict) and conv.get("type") == "conversation":
                        user_msg = conv.get("user", "")[:50]
                        assistant_msg = conv.get("assistant", "")[:50]
                        history_lines.append(f"用户: {user_msg}\n助手: {assistant_msg}")
                if history_lines:
                    history_text = "\n最近对话:\n" + "\n".join(history_lines)
            
            prompt = ChatPromptTemplate.from_messages([
                ("system", """你是一个智能查询重写器。
你的任务是将用户的日常对话转换为适合向量检索的精确查询。

规则：
1. 识别用户可能的意图和需求
2. 转换为"User [具体需求]"的格式
3. 保持简洁但信息丰富
4. 专注于可检索的用户偏好和历史
5. 【重要】如果用户输入包含指代词（"查一下"、"这个"、"那个"），必须结合对话历史理解具体指代什么
6. 【重要】如果用户在纠正之前的错误（"但是我告诉你了"、"不是...是..."），查询应该聚焦于被纠正的主题

示例：
- "我饿了" → "User favorite food preferences"
- "我累了" → "User preferred relaxation activities"
- "查一下"（上文询问火锅店） → "Beijing hotpot restaurant recommendations"
- "但是我告诉你了我在北京"（之前说上海） → "User location Beijing correction"

只输出重写后的查询，不要解释。"""),
                ("human", f"{history_text}\n\n当前用户输入: {user_input}")
            ])

            chain = prompt | self.llm
            rewritten_query = chain.invoke({}).content.strip()

            print(f"🔄 Query Rewrite: '{user_input}' → '{rewritten_query}'")
            return rewritten_query

        except Exception as e:
            print(f"❌ Query Rewrite 失败: {e}")
            # 降级：返回原始输入
            return user_input

    def retrieve_user_memory(self, query: str, k: int = 3) -> List[Document]:
        """
        从用户记忆集合中检索相关记忆
        """
        if not self.user_memory_store:
            # 延迟初始化
            try:
                self.user_memory_store = Chroma(
                    collection_name="user_memory",
                    embedding_function=self.embeddings,
                    persist_directory=self.user_memory_path
                )
            except Exception as e:
                print(f"❌ 用户记忆集合初始化失败: {e}")
                return []

        try:
            docs = self.user_memory_store.similarity_search(query, k=k)
            print(f"📚 用户记忆检索: 找到 {len(docs)} 条相关记忆")
            for i, doc in enumerate(docs, 1):
                print(f"   {i}. {doc.page_content[:50]}...")
            return docs
        except Exception as e:
            print(f"❌ 用户记忆检索失败: {e}")
            return []

    def retrieve_action_library(self, query: str, k: int = 2) -> List[Document]:
        """
        从动作库集合中检索相关动作模式
        """
        if not self.action_store:
            # 延迟初始化
            try:
                self.action_store = Chroma(
                    collection_name="action_library",
                    embedding_function=self.embeddings,
                    persist_directory=self.action_library_path
                )
            except Exception as e:
                print(f"❌ 动作库集合初始化失败: {e}")
                return []

        try:
            docs = self.action_store.similarity_search(query, k=k)
            print(f"🎭 动作库检索: 找到 {len(docs)} 个相关动作")
            for i, doc in enumerate(docs, 1):
                print(f"   {i}. {doc.page_content[:50]}...")
            return docs
        except Exception as e:
            print(f"❌ 动作库检索失败: {e}")
            return []

    def retrieve_memory_context(self, user_input: str, conversation_history: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """
        综合检索记忆上下文
        返回包含用户记忆和动作库的检索结果
        
        Args:
            user_input: 用户当前输入
            conversation_history: 对话历史（用于上下文理解）
        """
        # 1. Query Rewrite (传入对话历史)
        search_query = self.query_rewrite(user_input, conversation_history)

        # 2. 并行检索两个集合
        user_memories = self.retrieve_user_memory(search_query)
        action_patterns = self.retrieve_action_library(user_input)  # 动作库用原始查询

        # 3. 合并结果
        memory_context = {
            "search_query": search_query,
            "user_memories": [doc.page_content for doc in user_memories],
            "action_patterns": [doc.page_content for doc in action_patterns],
            "retrieved_at": time.time()
        }

        print(f"🧠 记忆上下文: 用户记忆 {len(user_memories)} 条, 动作模式 {len(action_patterns)} 个")

        return memory_context

    def save_user_memory(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        保存用户新记忆到 user_memory 集合
        """
        if not self.user_memory_store:
            # 延迟初始化
            try:
                self.user_memory_store = Chroma(
                    collection_name="user_memory",
                    embedding_function=self.embeddings,
                    persist_directory=self.user_memory_path
                )
            except Exception as e:
                print(f"❌ 用户记忆集合初始化失败: {e}")
                return False

        try:
            # 准备元数据
            default_metadata = {
                "timestamp": time.time(),
                "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "category": "user_preference",  # 默认分类
                "source": "conversation"  # 来源：对话
            }

            if metadata:
                default_metadata.update(metadata)

            # 创建文档
            doc = Document(
                page_content=content,
                metadata=default_metadata
            )

            # 添加到向量数据库
            self.user_memory_store.add_documents([doc])

            print(f"💾 用户记忆已保存: {content[:50]}...")
            print(f"   元数据: {default_metadata}")

            return True

        except Exception as e:
            print(f"❌ 保存用户记忆失败: {e}")
            return False

    def extract_user_preference(self, user_input: str, llm_response: str) -> Optional[Dict[str, Any]]:
        """
        从用户输入和 LLM 回复的对话中提取用户偏好信息
        用于自动保存新的用户记忆
        
        Args:
            user_input: 用户的原始输入
            llm_response: AI 的回复
        """
        try:
            # 检查用户输入或回复中是否包含用户偏好信息
            preference_keywords = [
                "喜欢", "偏好", "最爱", "习惯", "经常", "总是",
                "讨厌", "不喜欢", "不习惯", "避免", "不能",
                "想吃", "想听", "想要", "希望", "需要", "应该吃"
            ]

            combined_text = (user_input + " " + llm_response).lower()
            has_preference = any(keyword in combined_text for keyword in preference_keywords)

            if not has_preference:
                return None

            # 使用 LLM 提取具体的用户偏好
            prompt = ChatPromptTemplate.from_messages([
                ("system", """你是一个用户偏好提取器。
从用户和AI的对话中提取用户的偏好信息。

【重要】提取的内容应该是关于用户的事实，而不是AI的回复内容。
【重要】使用第三人称描述，例如："用户喜欢..."、"用户习惯..."

输出格式：JSON 对象，包含以下字段：
- content: 提取的偏好描述（必须是用户的信息，不是AI的话）
- category: 偏好分类 (food, music, activity, habit等)
- confidence: 置信度 (0.0-1.0)

如果没有明确的用户偏好信息，返回 null。

正确示例：
用户: "这种天在北京应该吃火锅吧"
AI: "北京今天3-8度确实很适合吃火锅呢！推荐你去海底捞..."
输出: {{"content": "用户喜欢在冷天吃火锅", "category": "food", "confidence": 0.8}}

错误示例（不要这样）：
输出: {{"content": "北京今天3-8度确实很适合吃火锅", ...}}  # 这是AI说的话，不是用户偏好

再例：
用户: "我累了"
AI: "要不要休息一下"
输出: {{"content": "用户感到疲惫", "category": "状态", "confidence": 0.9}}

只输出JSON，不要解释。"""),
                ("human", f"用户: {user_input}\nAI: {llm_response}")
            ])

            from langchain_core.output_parsers import JsonOutputParser
            parser = JsonOutputParser()
            chain = prompt | self.llm | parser
            
            result = chain.invoke({})
            
            # 验证提取的内容不是AI的回复
            if result and isinstance(result, dict):
                content = result.get("content", "")
                # 简单的验证：提取的内容不应该和AI回复重合太多
                if content and len(content) > 10:
                    # 检查是否包含AI回复的大段文字（判断是否直接复制了AI的话）
                    overlap_ratio = sum(1 for word in content[:50].split() if word in llm_response[:100]) / max(len(content[:50].split()), 1)
                    if overlap_ratio < 0.7:  # 重合度低于70%才认为是有效提取
                        return result
                    else:
                        print(f"   ⚠️  提取内容与AI回复重合度过高，跳过保存")
                        return None
            
            return None

        except Exception as e:
            print(f"❌ 提取用户偏好失败: {e}")
            return None

    def extract_music_preference(self, user_input: str, llm_response: str, recommended_music: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        从对话中提取音乐偏好（场景 4.1）
        检测用户对推荐音乐的正负面反馈
        
        Args:
            user_input: 用户输入
            llm_response: AI 回复
            recommended_music: 如果刚刚推荐了音乐，传入推荐的音乐信息（如 "晴天 - 周杰伦"）
        
        Returns:
            偏好信息字典，包含 content, category, confidence, sentiment (positive/negative)
        """
        try:
            # 音乐相关的关键词
            music_keywords = ["音乐", "歌", "歌曲", "听", "推荐", "喜欢", "不喜欢", "讨厌", "好听", "难听"]
            feedback_keywords = ["喜欢", "不喜欢", "讨厌", "好听", "难听", "不错", "一般", "还行", "很棒", "太吵"]
            
            combined_text = (user_input + " " + llm_response).lower()
            
            # 检查是否涉及音乐
            has_music = any(kw in combined_text for kw in music_keywords)
            has_feedback = any(kw in combined_text for kw in feedback_keywords)
            
            if not (has_music and has_feedback):
                return None
            
            # 判断情感倾向（优先检查负面，避免被"好的"等词干扰）
            positive_words = ["喜欢", "好听", "不错", "很棒", "爱听", "推荐", "再来", "很好"]
            negative_words = ["不喜欢", "讨厌", "难听", "太吵", "不想听", "换一首", "别推", "不要"]
            
            sentiment = "neutral"
            # 优先检查负面词（避免"好的，我会记住你不喜欢"被误判为正面）
            if any(word in combined_text for word in negative_words):
                sentiment = "negative"
            elif any(word in combined_text for word in positive_words):
                sentiment = "positive"
            
            # 提取艺术家或类型
            artists = ["周杰伦", "Yiruma", "Alan Walker", "Taylor Swift", "Ed Sheeran"]
            genres = ["流行", "摇滚", "古典", "爵士", "电子", "嘻哈", "民谣"]
            
            found_artist = None
            found_genre = None
            
            for artist in artists:
                if artist.lower() in combined_text:
                    found_artist = artist
                    break
            
            for genre in genres:
                if genre in combined_text:
                    found_genre = genre
                    break
            
            # 构建偏好描述
            if sentiment == "positive":
                if found_artist:
                    content = f"用户喜欢{found_artist}的音乐"
                elif found_genre:
                    content = f"用户喜欢{found_genre}类型的音乐"
                elif recommended_music:
                    content = f"用户喜欢{recommended_music}这类音乐"
                else:
                    content = "用户对推荐的音乐表示喜欢"
            elif sentiment == "negative":
                if found_artist:
                    content = f"用户不喜欢{found_artist}的音乐"
                elif found_genre:
                    content = f"用户不喜欢{found_genre}类型的音乐"
                else:
                    content = "用户对推荐的音乐表示不喜欢"
            else:
                return None  # 中性反馈不保存
            
            return {
                "content": content,
                "category": "music",
                "confidence": 0.8 if (found_artist or found_genre) else 0.6,
                "sentiment": sentiment,
                "artist": found_artist,
                "genre": found_genre
            }
            
        except Exception as e:
            print(f"❌ 提取音乐偏好失败: {e}")
            return None

    def extract_news_preference(self, user_input: str, llm_response: str, news_topics: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
        """
        从对话中提取新闻偏好（场景 4.2）
        检测用户对推送新闻的兴趣反馈
        
        Args:
            user_input: 用户输入
            llm_response: AI 回复
            news_topics: 如果刚刚推送了新闻，传入新闻主题列表
        
        Returns:
            偏好信息字典，包含 content, category, confidence, sentiment
        """
        try:
            import re
            
            # 只检查用户输入，不检查 AI 回复（避免误判）
            user_input_lower = user_input.lower()
            
            # 必须同时满足两个条件：
            # 1. 提到新闻相关词
            # 2. 明确表达偏好（正面或负面）
            
            # 明确的偏好表达模式（使用正则表达式）
            positive_patterns = [
                r"想看.*新闻", r"推荐.*新闻", r"感兴趣.*新闻", r"喜欢.*新闻", 
                r"多推.*新闻", r"给我.*新闻", r"来点.*新闻", r"来一些.*新闻",
                r"想要.*新闻", r"需要.*新闻"
            ]
            negative_patterns = [
                r"不想看.*新闻", r"不感兴趣.*新闻", r"别推.*新闻", r"不喜欢.*新闻",
                r"不要.*新闻", r"别发.*新闻", r"不需要.*新闻"
            ]
            
            # 检查是否匹配明确的偏好表达模式
            has_positive = any(re.search(pattern, user_input_lower) for pattern in positive_patterns)
            has_negative = any(re.search(pattern, user_input_lower) for pattern in negative_patterns)
            
            # 如果没有明确的偏好表达，不保存偏好（仅仅询问新闻不算偏好）
            if not (has_positive or has_negative):
                return None
            
            # 判断情感倾向
            sentiment = "positive" if has_positive else "negative"
            
            # 提取感兴趣的主题（只从用户输入中提取）
            found_topics = []
            topic_list = ["AI", "科技", "人工智能", "机器学习", "创业", "投资", "科学", "医学", "健康", "体育", "娱乐", "财经", "社会", "政治"]
            for topic in topic_list:
                if topic.lower() in user_input_lower:
                    found_topics.append(topic)
            
            # 如果用户没有明确提到主题，但传入了 news_topics，可以使用（但降低置信度）
            if not found_topics and news_topics:
                found_topics = news_topics[:2]  # 最多取前两个
            
            # 构建偏好描述
            if sentiment == "positive":
                if found_topics:
                    content = f"用户对{', '.join(found_topics)}相关的新闻感兴趣"
                else:
                    content = "用户对推送的新闻表示感兴趣"
            else:  # negative
                if found_topics:
                    content = f"用户对{', '.join(found_topics)}相关的新闻不感兴趣"
                else:
                    content = "用户对推送的新闻表示不感兴趣"
            
            # 置信度：有明确主题表达 > 只有偏好表达
            confidence = 0.8 if found_topics else 0.6
            
            return {
                "content": content,
                "category": "news",
                "confidence": confidence,
                "sentiment": sentiment,
                "topics": found_topics
            }
            
        except Exception as e:
            print(f"❌ 提取新闻偏好失败: {e}")
            return None

    def get_music_preferences(self) -> Dict[str, Any]:
        """
        从记忆中检索用户的音乐偏好
        返回喜欢的艺术家、类型，以及不喜欢的类型
        """
        if not self.user_memory_store:
            return {"liked_artists": [], "liked_genres": [], "disliked_artists": [], "disliked_genres": []}
        
        try:
            # 检索音乐相关的记忆
            results = self.user_memory_store.similarity_search(
                "用户音乐偏好 喜欢 不喜欢 艺术家 类型",
                k=10,
                filter={"category": "music"}
            )
            
            liked_artists = []
            liked_genres = []
            disliked_artists = []
            disliked_genres = []
            
            for doc in results:
                content = doc.page_content.lower()
                metadata = doc.metadata
                sentiment = metadata.get("sentiment", "neutral")
                
                if sentiment == "positive":
                    # 提取艺术家
                    if "周杰伦" in content:
                        liked_artists.append("周杰伦")
                    if "yiruma" in content:
                        liked_artists.append("Yiruma")
                    if "alan walker" in content:
                        liked_artists.append("Alan Walker")
                    
                    # 提取类型
                    for genre in ["流行", "摇滚", "古典", "爵士", "电子"]:
                        if genre in content:
                            liked_genres.append(genre)
                
                elif sentiment == "negative":
                    # 提取不喜欢的艺术家和类型
                    if "周杰伦" in content:
                        disliked_artists.append("周杰伦")
                    for genre in ["流行", "摇滚", "古典", "爵士", "电子"]:
                        if genre in content:
                            disliked_genres.append(genre)
            
            return {
                "liked_artists": list(set(liked_artists)),
                "liked_genres": list(set(liked_genres)),
                "disliked_artists": list(set(disliked_artists)),
                "disliked_genres": list(set(disliked_genres))
            }
            
        except Exception as e:
            print(f"❌ 检索音乐偏好失败: {e}")
            return {"liked_artists": [], "liked_genres": [], "disliked_artists": [], "disliked_genres": []}

    def get_news_interests(self) -> List[str]:
        """
        从记忆中检索用户的新闻兴趣
        返回感兴趣的主题列表
        """
        if not self.user_memory_store:
            return []
        
        try:
            # 检索新闻相关的记忆
            results = self.user_memory_store.similarity_search(
                "用户新闻偏好 感兴趣 主题",
                k=10,
                filter={"category": "news"}
            )
            
            interests = []
            for doc in results:
                content = doc.page_content.lower()
                metadata = doc.metadata
                sentiment = metadata.get("sentiment", "neutral")
                
                if sentiment == "positive":
                    # 提取主题
                    topics = metadata.get("topics", "")
                    if topics:
                        # topics 可能是逗号分隔的字符串（从 ChromaDB 读取），也可能是列表
                        if isinstance(topics, str):
                            # 字符串需要 split 成列表
                            interests.extend([t.strip() for t in topics.split(",") if t.strip()])
                        elif isinstance(topics, list):
                            # 列表直接 extend
                            interests.extend(topics)
                    else:
                        # 从内容中提取
                        for topic in ["AI", "科技", "人工智能", "机器学习", "创业", "投资", "科学", "医学", "健康"]:
                            if topic.lower() in content:
                                interests.append(topic)
            
            return list(set(interests))
            
        except Exception as e:
            print(f"❌ 检索新闻兴趣失败: {e}")
            return []

    def detect_and_resolve_conflicts(self, new_fact: str, category: str) -> bool:
        """
        检测新事实是否与已有记忆冲突，如果冲突则删除旧记忆
        支持分类去重：常住地覆盖、当前位置覆盖等
        """
        if not self.user_memory_store:
            return False
        
        try:
            # 1. 提取城市和位置类型
            cities = ["上海", "北京", "深圳", "广州", "杭州", "成都", "武汉", "南京", "苏州", "重庆", "西安", "天津", "厦门", "青岛", "大连"]
            new_city = None
            for city in cities:
                if city in new_fact:
                    new_city = city
                    break
            
            if not new_city:
                return False

            # 判断是"常住地"还是"当前/出差"
            # 常住地关键词：明确表示长期居住
            is_home = any(kw in new_fact for kw in ["常住", "住在", "定居", "搬家", "搬到", "搬去", "搬迁", "安家", "落户"])
            # 临时位置关键词：明确表示短期停留
            is_travel = any(kw in new_fact for kw in ["出差", "旅游", "现在在", "正在", "临时", "来到", "去了"])
            
            # 如果两者都不明确，根据上下文判断
            if not is_home and not is_travel:
                # 默认当作临时位置（保守策略，避免误改常住地）
                is_travel = True

            if category == "user_profile":
                all_memories = self.user_memory_store.get(where={"category": "user_profile"})
                documents = all_memories.get("documents", [])
                ids = all_memories.get("ids", [])
                
                conflicting_ids = []
                for doc, doc_id in zip(documents, ids):
                    # 如果新事实是常住地，覆盖旧的常住地描述
                    if is_home and any(kw in doc for kw in ["常住", "住在", "定居"]):
                        if new_city not in doc: # 不同城市才算冲突
                            conflicting_ids.append(doc_id)
                    
                    # 如果新事实是当前位置，覆盖旧的当前位置描述
                    if is_travel and any(kw in doc for kw in ["出差", "旅游", "现在在", "正在", "临时"]):
                        if new_city not in doc:
                            conflicting_ids.append(doc_id)
                            
                    # 兜底：如果旧记忆只是模糊的"用户所在地是XX"，且新记忆更明确
                    if "所在地是" in doc and (is_home or is_travel):
                        conflicting_ids.append(doc_id)

                if conflicting_ids:
                    self.user_memory_store.delete(ids=conflicting_ids)
                    type_str = "常住地" if is_home else "当前位置"
                    print(f"   🗑️  已删除 {len(conflicting_ids)} 条旧的{type_str}记忆")
                    return True
            
            return False
        except Exception as e:
            print(f"❌ 冲突检测失败: {e}")
            return False
    

    def _validate_profile_updates(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        """验证并清洗用户画像更新数据"""
        validated = {}
        
        # 允许更新的字段
        allowed_fields = {"name", "home_city", "current_location", "core_preferences"}
        
        for key, value in updates.items():
            if key not in allowed_fields:
                print(f"⚠️  忽略无效的画像字段: {key}")
                continue
                
            if value is None or (isinstance(value, str) and not value.strip()):
                print(f"⚠️  忽略空值字段: {key}")
                continue
                
            # 特殊清洗逻辑
            if key == "core_preferences" and isinstance(value, list):
                # 过滤空字符串
                validated[key] = [p for p in value if isinstance(p, str) and p.strip()]
            else:
                validated[key] = value
                
        return validated

    def load_profile(self) -> "UserProfile":
        """
        从 JSON 文件加载用户画像
        支持基于文件 mtime 的 Smart Caching
        """
        try:
            from .state import UserProfile
        except ImportError:
            try:
                from src.state import UserProfile
            except ImportError:
                # Fallback for direct execution
                from state import UserProfile
                
        profile_path = os.path.join(self.db_path, "user_profile.json")
        
        # 1. 检查文件是否存在
        if not os.path.exists(profile_path):
            return UserProfile()
            
        try:
            # 2. 检查文件修改时间
            current_mtime = os.path.getmtime(profile_path)
            
            # 3. 如果缓存有效且文件未修改，直接返回缓存
            if self._profile_cache and self._profile_mtime == current_mtime:
                # print("   ⚡ 使用 Profile 缓存")
                return self._profile_cache
            
            # 4. 加载文件并更新缓存
            with open(profile_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                profile = UserProfile(**data)
                
                self._profile_cache = profile
                self._profile_mtime = current_mtime
                print(f"   📂 已从磁盘重新加载用户画像 (v{profile.version})")
                return profile
                
        except Exception as e:
            print(f"❌ 加载用户画像失败: {e}")
            return UserProfile()

    def save_profile(self, profile: "UserProfile") -> bool:
        """保存用户画像到 JSON 文件"""
        profile_path = os.path.join(self.db_path, "user_profile.json")
        try:
            with open(profile_path, "w", encoding="utf-8") as f:
                json.dump(profile.model_dump(), f, ensure_ascii=False, indent=2)
            
            # 更新缓存和 mtime，避免下次读取时认为文件已过期（虽然保存后 mtime 确实变了，但内容是一致的）
            # 更好的做法是更新缓存以匹配写入的内容，并同步 mtime
            self._profile_cache = profile
            # 这里的 mtime 可能会有微小差异，但为了保险起见，下次 load 会重新读取也是可以接受的
            # 或者我们可以重新获取一下 mtime
            try:
                self._profile_mtime = os.path.getmtime(profile_path)
            except:
                pass
                
            return True
        except Exception as e:
            print(f"❌ 保存用户画像失败: {e}")
            return False

    def update_profile(self, updates: Dict[str, Any]) -> "UserProfile":
        """更新用户画像字段"""
        # 1. 数据校验
        validated_updates = self._validate_profile_updates(updates)
        if not validated_updates:
            print("⚠️  更新数据为空或无效，跳过")
            return self.load_profile()
            
        profile = self.load_profile()
        updated = False
        
        for key, value in validated_updates.items():
            if hasattr(profile, key):
                current_value = getattr(profile, key)
                if current_value != value:
                    setattr(profile, key, value)
                    updated = True
        
        if updated:
            profile.last_updated = time.time()
            self.save_profile(profile)
            print(f"   ✅ 用户画像已更新: {validated_updates.keys()}")
            
        return profile

    def extract_and_save_user_profile(self, user_input: str, llm_response: str) -> List[Dict[str, Any]]:
        """
        从对话中提取长期用户信息（画像、偏好、习惯等）并保存到长期记忆
        """
        try:
            prompt = ChatPromptTemplate.from_messages([
                ("system", """你是一个资深的用户画像提取专家。你的任务是从用户和AI的对话中识别出值得长期保存的【事实性信息】。

这些信息包括但不限于：
1. 基础画像 (user_profile): 姓名、常住地 (home_city)、当前位置 (current_location)、职业、重要纪念日。
2. 生活规律 (habit): 作息时间、工作习惯、活跃时段。
3. 长期偏好 (preference): 饮食口味、光线/环境偏好、音乐/技术兴趣。
4. 核心关系 (relationship): 提到的人物（朋友/家人）、交互底线。

【地理位置提取规则】：
- **常住地（Base 地）**：如果用户说"我住在XX"、"我是XX人"、"我常住XX"、"我搬家到XX了"、"我搬到XX了"、"我在XX安家了"，将其识别为【常住地】(home_city)。
  - 描述格式："用户常住地是XX"、"用户住在XX"
- **当前位置（临时）**：如果用户说"我现在在XX"、"我来XX出差/旅游了"、"我在XX呢"（针对当前对话），将其识别为【当前位置】(current_location)。
  - 描述格式："用户当前正在XX出差"、"用户现在在XX旅游"
- **重要**：只有明确提到"搬家"、"搬到"等永久性迁移词汇时，才更新常住地。否则默认为临时位置。

输出要求：
- 必须输出有效的 JSON 数组，每个元素包含：content (事实描述), category (分类), confidence (置信度 0-1)。
- 如果没有提取到任何有价值的长期信息，返回空数组 []。
- 事实描述应该是第三人称事实。
- 不要包含临时的、情绪化的或对话过程中的信息。"""),
                ("human", "用户说: {user_input}\nAI回复: {llm_response}")
            ])

            # 使用带有 JSON 输出解析器的链
            from langchain_core.output_parsers import JsonOutputParser
            parser = JsonOutputParser()
            chain = prompt | self.llm | parser
            
            # 正确传入变量
            extracted_facts = chain.invoke({"user_input": user_input, "llm_response": llm_response})
            
            saved_count = 0
            if isinstance(extracted_facts, list):
                for fact in extracted_facts:
                    # 仅保存高置信度的信息
                    if fact.get("confidence", 0) >= 0.7:
                        content = fact.get("content")
                        category = fact.get("category", "user_profile")
                        if content:
                            # 【新增】在保存前检测并解决冲突
                            conflict_resolved = self.detect_and_resolve_conflicts(content, category)
                            
                            # 保存新记忆
                            success = self.save_user_memory(
                                content=content,
                                metadata={
                                    "category": category,
                                    "source": "profile_extraction",
                                    "confidence": fact.get("confidence")
                                }
                            )
                            if success:
                                saved_count += 1
                                conflict_tag = " [已覆盖旧记忆]" if conflict_resolved else ""
                                print(f"📍 [画像提取] 已存入长期记忆 ({category}): {content}{conflict_tag}")
            
            return extracted_facts if isinstance(extracted_facts, list) else []

        except Exception as e:
            print(f"❌ 提取用户画像失败: {e}")
            return []

    def retrieve_user_profile(self) -> str:
        """
        获取完整结构化的用户画像摘要（包含画像、习惯、偏好和关系）
        用于注入 System Prompt 的最高优先级区域
        """
        if not self.user_memory_store:
            return ""

        try:
            # 检索所有核心画像分类的文档
            categories = ["user_profile", "habit", "preference", "relationship"]
            
            # Chroma 的 where 子句支持 $in 操作符
            results = self.user_memory_store.get(
                where={"category": {"$in": categories}}
            )
            
            documents = results.get("documents", [])
            if not documents:
                return "暂无详细画像"
            
            # 去重并格式化
            unique_facts = sorted(list(set(documents)))
            profile_summary = "\n".join([f"- {fact}" for fact in unique_facts])
            return profile_summary

        except Exception as e:
            print(f"❌ 获取用户画像失败: {e}")
            # 降级：如果 $in 不支持，尝试获取全部并手动过滤
            try:
                results = self.user_memory_store.get()
                docs = results.get("documents", [])
                metas = results.get("metadatas", [])
                
                filtered_facts = []
                for doc, meta in zip(docs, metas):
                    if meta.get("category") in ["user_profile", "habit", "preference", "relationship"]:
                        filtered_facts.append(doc)
                
                if not filtered_facts:
                    return "暂无详细画像"
                
                unique_facts = sorted(list(set(filtered_facts)))
                return "\n".join([f"- {fact}" for fact in unique_facts])
            except:
                return ""

    def initialize_action_library(self, force_recreate: bool = False):
        """
        初始化动作库 - 添加预设的动作模式
        """
        if force_recreate and os.path.exists(self.action_library_path):
            import shutil
            shutil.rmtree(self.action_library_path)
            self.action_store = None

        if not self.action_store:
            try:
                self.action_store = Chroma(
                    collection_name="action_library",
                    embedding_function=self.embeddings,
                    persist_directory=self.action_library_path
                )
            except Exception as e:
                print(f"❌ 动作库集合创建失败: {e}")
                return

        # 预设动作模式（科学锚点 + 软约束 + 语义描述）
        default_actions = [
            # ==========================================
            # 1. 生产力与专注 (Productivity) - 带软约束
            # ==========================================
            Document(
                page_content="[场景] 深度工作/编码/写论文：需要保持高度清醒和注意力。灯光应调整为冷白光色调(参考: >5000K)，亮度较高但不要刺眼，此时应保持环境安静，避免非紧急的语音打扰。",
                metadata={"category": "work", "scene": "deep_focus"}
            ),
            Document(
                page_content="[场景] 阅读/纸质书写/看书：需要模拟自然光或舒适的阅读光线。灯光应为中性色温(参考: 4000K左右)，亮度适中不刺眼，确保文字清晰且无频闪，保护视力。",
                metadata={"category": "work", "scene": "reading"}
            ),
            Document(
                page_content="[场景] 视频会议/网课：侧重于面部补光效果。灯光应柔和且均匀，避免面部出现生硬阴影，色温自然健康，电机保持静止。",
                metadata={"category": "work", "scene": "meeting"}
            ),

            # ==========================================
            # 2. 娱乐与放松 (Lifestyle) - 带科学锚点
            # ==========================================
            Document(
                page_content="[场景] 看电影/追剧：作为屏幕背景光(Bias Lighting)。灯光应极暗，建议使用冷色调(如深蓝或紫色)来降低屏幕与环境的对比度，减少视觉疲劳。",
                metadata={"category": "entertainment", "scene": "movie"}
            ),
            Document(
                page_content="[场景] 打游戏/电竞：营造沉浸式电竞氛围。灯光应使用高饱和度的彩色光(赛博朋克风格)，可开启呼吸或RGB流光模式，配合激动的语音反馈。",
                metadata={"category": "entertainment", "scene": "gaming"}
            ),
            Document(
                page_content="[场景] 睡前放松/玩手机/助眠：营造极度放松、像烛光一样的氛围。灯光应为极暖色调(参考: <2700K)和微弱亮度(参考: 10-20%)，帮助身体分泌褪黑素，准备进入睡眠状态。",
                metadata={"category": "rest", "scene": "bedtime", "scientific_basis": "circadian_rhythm"}
            ),

            # ==========================================
            # 3. 生理需求与作息 (Biological) - 贴心服务
            # ==========================================
            Document(
                page_content="[场景] 深夜加班提醒：当检测到深夜(如23点后)用户还在工作时，通过灯光的柔和动态变化(如缓慢呼吸)来进行非侵入式提醒，语气要充满关怀，但不要强制关灯。",
                metadata={"category": "care", "scene": "late_work"}
            ),
            Document(
                page_content="[场景] 起夜/夜灯模式：深夜检测到活动时。灯光应设为不破坏夜视能力的颜色(如暗红光或极暗暖光)，亮度极低，完全保持静音，无语音输出。",
                metadata={"category": "care", "scene": "night_light", "scientific_basis": "night_vision"}
            ),
            Document(
                page_content="[场景] 起床唤醒：模拟日出过程。灯光应从微弱的暖色(如暗红)逐渐过渡到明亮的日光色(如冷白)，配合自然的唤醒音效(如鸟鸣声)，充满活力。",
                metadata={"category": "routine", "scene": "wakeup"}
            ),

            # ==========================================
            # 4. 否定与维护 (Maintenance) - 鲁棒性
            # ==========================================
            Document(
                page_content="[指令] 否定控制：当用户说'别关灯'、'不要变'、'保持这样'时，维持当前所有状态不变，并给予简单的口头确认。",
                metadata={"category": "maintenance", "action": "keep_state"}
            ),
            Document(
                page_content="[指令] 纠正/微调：当用户说'太亮了'或'太暗了'时，请读取【当前亮度】，并在此基础上进行适度的相对调整(如 ±20%)，而不是直接重置为某个固定值。",
                metadata={"category": "maintenance", "action": "adjust", "requires_state": True}
            ),

            # ==========================================
            # 5. Neko-Light 人设交互 (Personality) - 灵魂
            # ==========================================
            Document(
                page_content="[交互] 触摸/抚摸：像猫一样享受被触摸。灯光变为温暖、柔和的色调(如粉色或橙色)，伴随模拟呼噜声的震动反馈(Purr vibration)。",
                metadata={"category": "interaction", "trigger": "touch"}
            ),
            Document(
                page_content="[交互] 摇晃/拍打：表现出惊讶或晕眩。灯光快速红白闪烁，发出'晕了'、'别摇了'的声音，电机急促震动。",
                metadata={"category": "interaction", "trigger": "shake"}
            ),
            Document(
                page_content="[状态] 闲置/求关注：当长时间无交互且无聊度高时，做一次轻微的'尾巴摆动'(电机短震)或灯光眨眼，试探性地喵一声，寻求用户关注。",
                metadata={"category": "proactive", "trigger": "boredom"}
            ),
            
            # ==========================================
            # 6. 情绪与社交 (补充场景)
            # ==========================================
            Document(
                page_content="[场景] 用户疲惫/累了：当用户表示疲惫时，营造温暖、昏暗、舒适的氛围，灯光调为暖黄光，播放轻柔的背景声音或白噪音，建议用户休息。",
                metadata={"category": "rest", "mood": "tired"}
            ),
            Document(
                page_content="[场景] 用户饥饿：当用户说'饿了'时，热情询问想吃什么或推荐美食，灯光调至温暖的餐厅氛围(如暖黄色)，体现关怀。",
                metadata={"category": "food", "mood": "hungry"}
            ),
            Document(
                page_content="[场景] 庆祝/开心：当用户想要活跃气氛、开心或庆祝时，使用动态变化的彩色灯光效果(RGB流光或彩虹色)，配合欢快激动的语音反馈。",
                metadata={"category": "fun", "mood": "party"}
            )
        ]

        try:
            # 检查是否已存在数据
            existing_count = len(self.action_store.get()["documents"]) if hasattr(self.action_store, 'get') else 0

            if existing_count == 0:
                self.action_store.add_documents(default_actions)
                print(f"📚 已初始化动作库: 添加了 {len(default_actions)} 个预设动作")
            else:
                print(f"📚 动作库已存在: {existing_count} 个动作")

        except Exception as e:
            print(f"❌ 初始化动作库失败: {e}")

    def get_memory_stats(self) -> Dict[str, Any]:
        """
        获取记忆系统统计信息
        """
        stats = {
            "action_library": {"status": "uninitialized", "count": 0},
            "user_memory": {"status": "uninitialized", "count": 0}
        }

        # 检查动作库
        if self.action_store:
            try:
                if hasattr(self.action_store, 'get'):
                    count = len(self.action_store.get()["documents"])
                    stats["action_library"] = {"status": "ready", "count": count}
                else:
                    stats["action_library"] = {"status": "ready", "count": "unknown"}
            except Exception as e:
                stats["action_library"] = {"status": "error", "error": str(e)}

        # 检查用户记忆
        if self.user_memory_store:
            try:
                if hasattr(self.user_memory_store, 'get'):
                    count = len(self.user_memory_store.get()["documents"])
                    stats["user_memory"] = {"status": "ready", "count": count}
                else:
                    stats["user_memory"] = {"status": "ready", "count": "unknown"}
            except Exception as e:
                stats["user_memory"] = {"status": "error", "error": str(e)}

        return stats
