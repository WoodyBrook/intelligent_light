# memory_manager.py - 记忆管理系统
# 管理向量数据库和记忆操作，实现双路 RAG 系统

import os
import time
import json
import re
import uuid
from datetime import datetime, timedelta
from pathlib import Path

from typing import List, Dict, Optional, Any, Tuple
from langchain_community.vectorstores import Chroma
from langchain_ollama import OllamaEmbeddings
from .model_manager import get_model_manager
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.documents import Document
import jieba

# [Refactor] Standardized RAG components
from langchain_community.retrievers import BM25Retriever
from langchain_classic.retrievers.ensemble import EnsembleRetriever

from .prompt_utils import escape_prompt_input


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

        # 初始化 Embeddings（使用本地 Ollama bge-m3）
        print("初始化 Ollama Embeddings (bge-m3)...")
        self.embeddings = OllamaEmbeddings(
            model="bge-m3",
            base_url="http://localhost:11434"
        )
        print("Ollama Embeddings 初始化完成")

        # 初始化 LLM（使用项目统一的模型管理器）
        model_manager = get_model_manager()
        self.llm = model_manager.get_model("chat")

        # 初始化动作库集合
        self.action_library_path = os.path.join(db_path, "action_library")
        try:
            self.action_store = Chroma(
                collection_name="action_library",
                embedding_function=self.embeddings,
                persist_directory=self.action_library_path
            )
            print("动作库集合已加载")
        except Exception as e:
            print(f"[WARN]  动作库集合初始化失败，将在首次使用时创建: {e}")
            self.action_store = None

        # 初始化用户记忆集合
        self.user_memory_path = os.path.join(db_path, "user_memory")
        try:
            self.user_memory_store = Chroma(
                collection_name="user_memory",
                embedding_function=self.embeddings,
                persist_directory=self.user_memory_path
            )
            print("用户记忆集合(Chroma)已加载")
            
            # [Refactor] 初始化 BM25 Retriever 和 Ensemble Retriever
            self.bm25_retriever = None
            self.ensemble_retriever = None
            self._refresh_bm25()

        except Exception as e:
            print(f"[WARN]  用户记忆集合/BM25初始化失败: {e}")
            self.user_memory_store = None
            self.bm25_retriever = None
            self.ensemble_retriever = None
        
        # 初始化情景记忆集合 (Few-shot Episodes)
        self.episodes_path = os.path.join(db_path, "episodes")
        try:
            self.episodes_store = Chroma(
                collection_name="episodes",
                embedding_function=self.embeddings,
                persist_directory=self.episodes_path
            )
            print("情景记忆集合已加载")
        except Exception as e:
            print(f"[WARN]  情景记忆集合初始化失败: {e}")
            self.episodes_store = None

        print("MemoryManager 初始化完成")
        


        # Profile 缓存
        self._profile_cache = None
        self._profile_mtime = 0.0
        
        # 配置常量
        self.EPISODE_CONFIG = {
            "max_count": 500,           # 最大存储数量
            "cleanup_threshold": 600,   # 触发清理的阈值
            "neutral_ttl_days": 30,     # neutral 记录的 TTL
            "similarity_threshold": 0.9 # 去重相似度阈值
        }
        
        self.SYNTHESIS_CONFIG = {
            "min_interval_hours": 24,    # 最小合成间隔
            "memory_threshold": 10,      # 新增记忆数阈值
            "force_keywords": ["更新画像", "同步偏好"]  # 用户触发关键词
        }
        
        # 触发式更新配置
        self.TRIGGERED_UPDATE_CONFIG = {
            "trigger_keywords": [
                # 显式触发
                "记住", "记得", "别忘了", "以后",
                # 身份相关
                "我叫", "我是", "我的名字是", "我的生日是",
                # 偏好相关
                "我喜欢", "我不喜欢", "我讨厌", "我习惯", "我经常",
                # 地点相关
                "住在", "来自", "常住", "搬到",
                # 纠正
                "其实我", "不是...是", "我改了",
            ],
            "known_cities": [
                "上海", "北京", "深圳", "广州", "杭州", "成都", 
                "武汉", "南京", "苏州", "重庆", "西安", "天津",
                "厦门", "青岛", "大连", "郑州", "长沙", "沈阳",
            ],
        }
        
        # 混合搜索配置 (BM25 + Vector) - 仅用于保留权重配置
        self.HYBRID_SEARCH_CONFIG = {
            "enabled": True,
            "vector_weight": 0.7,
            "bm25_weight": 0.3,
            "candidate_multiplier": 4, 
        }
        
        # 记忆分类体系
        self.VALID_CATEGORIES = [
            "user_profile",      # 身份信息: 姓名、职业、所在地
            "preference",        # 偏好: 食物、音乐、颜色等
            "habit",             # 习惯: 作息、运动
            "recurring_pattern", # 周期事件: 每月10号
            "relationship",      # 社交关系
            "episodic",          # 事件记录
        ]
        
        # LLM 返回的 category -> 标准 category 映射
        self.CATEGORY_MAPPING = {
            # 偏好子类映射到 preference
            "food": "preference",
            "music": "preference",
            "color": "preference",
            "activity": "preference",
            "user_preference": "preference",
            # 习惯子类
            "routine": "habit",
            "daily": "habit",
            # 周期子类
            "schedule": "recurring_pattern",
            "monthly": "recurring_pattern",
            "weekly": "recurring_pattern",
            # 身份子类
            "identity": "user_profile",
            "location": "user_profile",
            # 事件子类
            "event": "episodic",
            "experience": "episodic",
            "trip": "episodic",
        }

        # [延迟刷新] BM25 累积更新后才重建索引
        self._pending_bm25_updates = 0
        self._bm25_refresh_threshold = 10

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
                ("human", "{history_text}\n\n当前用户输入: {user_input}")
            ])

            chain = prompt | self.llm
            rewritten_query = chain.invoke({"history_text": history_text, "user_input": user_input}).content.strip()

            print(f"Query Rewrite: '{user_input}' → '{rewritten_query}'")
            return rewritten_query

        except Exception as e:
            print(f"[ERROR] Query Rewrite 失败: {e}")
            # 降级：返回原始输入
            return user_input

    def _get_dynamic_weights(self, query: str) -> tuple:
        """
        根据查询意图动态调整 Relevance/Recency/Importance 权重
        """
        query_lower = query.lower()
        
        # Recency Boost: 用户询问最近的事
        recency_keywords = ["刚才", "刚刚", "最近", "上次", "之前", "昨天", "今天", "just now", "recently", "last time"]
        if any(kw in query_lower for kw in recency_keywords):
            return (0.3, 0.6, 0.1)  # (Alpha, Beta, Gamma)
        
        # Importance Boost: 用户询问重要的事
        importance_keywords = ["重要", "关键", "核心", "最", "必须", "一定", "永远", "永久", "important", "forever"]
        if any(kw in query_lower for kw in importance_keywords):
            return (0.3, 0.2, 0.5)
        
        # Default weights
        return (0.5, 0.3, 0.2)

    def _calculate_memory_score(self, doc: Document, relevance: float, alpha: float, beta: float, gamma: float) -> float:
        """
        计算记忆综合评分，使用改进后的公式：
        Score = α*Relevance + β*Recency + γ*Importance
        
        - Recency: 使用 max(creation_time, last_accessed) 保护新但未读的记忆
        - Importance: 归一化 (score-1)/9
        """
        import math
        
        metadata = doc.metadata
        now = time.time()
        
        # 1. Recency: max(creation, last_accessed)
        creation_time = metadata.get("creation_time", metadata.get("timestamp", now))
        last_accessed = metadata.get("last_accessed", creation_time)
        t_base = max(creation_time, last_accessed)
        
        hours_passed = (now - t_base) / 3600
        decay_factor = 72  # 72小时衰减到 ~37%
        recency_score = math.exp(-hours_passed / decay_factor)
        
        # 2. Importance: (score - 1) / 9
        raw_importance = metadata.get("importance", 5)  # 默认5分
        importance_score = (min(max(raw_importance, 1), 10) - 1) / 9.0
        
        # 3. Final Score
        final_score = (alpha * relevance) + (beta * recency_score) + (gamma * importance_score)
        return final_score

    def _refresh_bm25(self) -> None:
        """
        [Refactor] 重建 BM25 索引
        BM25Retriever 默认不支持动态添加，需全量重建
        """
        if self.user_memory_store is None:
            return

        try:
            print("正在刷新 BM25 索引...")
            data = self.user_memory_store.get()
            docs = data.get("documents", [])
            metadatas = data.get("metadatas", [])
            ids = data.get("ids", [])

            def _jieba_tokenizer(text: str) -> List[str]:
                return list(jieba.cut(text))

            if not docs:
                # 空索引初始化
                self.bm25_retriever = BM25Retriever.from_documents(
                    [Document(page_content="init", metadata={"id": "init"})],
                    preprocess_func=lambda x: [x]
                )
                self.bm25_retriever.docs = []
            else:
                # 全量重建
                doc_objs = []
                for i, txt in enumerate(docs):
                    meta = metadatas[i] if metadatas else {}
                    if not meta.get("id") and ids:
                        meta["id"] = ids[i]
                    doc_objs.append(Document(page_content=txt, metadata=meta))
                
                self.bm25_retriever = BM25Retriever.from_documents(
                    doc_objs,
                    preprocess_func=_jieba_tokenizer
                )
            
            self.bm25_retriever.k = 20
            
            # 同步更新 EnsembleRetriever 的引用
            if self.ensemble_retriever:
                self.ensemble_retriever.retrievers[0] = self.bm25_retriever
            else:
                # 初始化 Ensemble
                 self.ensemble_retriever = EnsembleRetriever(
                    retrievers=[self.bm25_retriever, self.user_memory_store.as_retriever()],
                    weights=[0.3, 0.7]
                )
            
            print(f"BM25 索引刷新完成 (文档数: {len(docs)})")

        except Exception as e:
            print(f"[ERROR] BM25 索引刷新失败: {e}")

    def _refresh_bm25_if_needed(self) -> None:
        """
        智能刷新：累积到阈值才执行

        延迟刷新策略：
        - 累积 < 阈值：仅计数，不刷新
        - 累积 >= 阈值：触发刷新，重置计数器
        """
        if self._pending_bm25_updates >= self._bm25_refresh_threshold:
            print(f"🔄 累积 {self._pending_bm25_updates} 条更新，触发BM25刷新")
            self._refresh_bm25()
            self._pending_bm25_updates = 0
        else:
            print(f"⏳ BM25待刷新: {self._pending_bm25_updates}/{self._bm25_refresh_threshold}")

    def force_refresh_bm25(self) -> None:
        """
        强制刷新BM25（会话结束时调用）

        确保所有待刷新的记忆都被索引到BM25中
        """
        if self._pending_bm25_updates > 0:
            print(f"🔧 强制刷新BM25（剩余 {self._pending_bm25_updates} 条）")
            self._refresh_bm25()
            self._pending_bm25_updates = 0
        else:
            print("✅ BM25已是最新状态，无需刷新")

    def _detect_exact_query(self, query: str) -> bool:
        """检测是否需要精确匹配（调整权重）"""
        # 日期模式: 2024-01-15, 2024年1月15日
        if re.search(r'\d{4}[-年]\d{1,2}[-月]\d{1,2}', query):
            return True
        
        # 数字模式: 10号, 15日
        if re.search(r'\d+[号日]', query):
            return True
        
        # 英文专有名词 (全大写或驼峰)
        if re.search(r'[A-Z]{2,}|[A-Z][a-z]+[A-Z]', query):
            return True
        
        return False
    
    def _normalize_category(self, raw_category: str) -> str:
        """
        将 LLM 返回的任意 category 标准化为 VALID_CATEGORIES 中的值
        
        Args:
            raw_category: LLM 返回的原始分类
            
        Returns:
            标准化后的分类
        """
        if not raw_category:
            return "preference"  # 默认
        
        raw_lower = raw_category.lower().strip()
        
        # 如果已经是标准分类，直接返回
        if raw_lower in self.VALID_CATEGORIES:
            return raw_lower
        
        # 通过映射表转换
        if raw_lower in self.CATEGORY_MAPPING:
            return self.CATEGORY_MAPPING[raw_lower]
        
        # 未知分类默认为 preference
        return "preference"
    


    def retrieve_user_memory(self, query: str, k: int = 5) -> List[Document]:
        """
        [Refactor] 高级检索：基于 LangChain EnsembleRetriever
        流程:
        1. 混合检索 (BM25 + Vector) 获取候选池
        2. 应用动态权重 (Vector vs BM25)
        3. 重排序 (Re-ranking): 结合 Recency 和 Importance
        4. 返回 Top-K 并注入时间上下文
        """
        if not self.ensemble_retriever:
            print("[WARN] Retriever 未初始化")
            return []

        try:
            # 1. 动态调整混合检索权重 (BM25 vs Vector)
            # ensemble_retriever.retrievers = [bm25, vector]
            if self._detect_exact_query(query):
                self.ensemble_retriever.weights = [0.6, 0.4] # 提高 BM25 权重
                print(f"🔍 精确查询: 调整权重 BM25=0.6, Vector=0.4")
            else:
                self.ensemble_retriever.weights = [0.3, 0.7] # 默认
            
            # 调整候选数量 (fetch more for re-ranking)
            candidate_k = 50
            self.bm25_retriever.k = candidate_k
            # self.ensemble_retriever.retrievers[1] is VectorStoreRetriever
            self.ensemble_retriever.retrievers[1].search_kwargs["k"] = candidate_k

            # 2. 执行混合检索
            docs = self.ensemble_retriever.invoke(query)
            if not docs:
                return []
            
            # 3. 重排序 (Re-ranking)
            # 获取评分权重
            alpha, beta, gamma = self._get_dynamic_weights(query)
            print(f"🎚️ 评分权重: α={alpha} (Rel), β={beta} (Rec), γ={gamma} (Imp)")
            
            scored_memories = []
            total_docs = len(docs)
            
            for i, doc in enumerate(docs):
                # 估算 Relevance: 基于原始 Rank 的线性衰减 (1.0 -> 0.0)
                # 越靠前 relevance 越高
                relevance_score = 1.0 - (i / total_docs)
                
                # 计算综合分数 (复用原有逻辑)
                final_score = self._calculate_memory_score(doc, relevance_score, alpha, beta, gamma)
                
                scored_memories.append({
                    "doc": doc,
                    "score": final_score
                })
            
            # 排序
            scored_memories.sort(key=lambda x: x["score"], reverse=True)
            
            # 4. Top-K 和格式化
            final_docs = []
            print(f"📚 检索结果 (Top {k}):")
            for item in scored_memories[:k]:
                original_doc = item["doc"]
                score = item["score"]
                
                # 注入时间信息
                metadata = original_doc.metadata
                date_str = metadata.get("date", "").split(" ")[0]
                content = original_doc.page_content
                if date_str:
                    enriched_content = f"[{date_str}] {content}"
                else:
                    enriched_content = content
                
                # 注入 Score 到 metadata (便于调试和验证)
                final_metadata = metadata.copy()
                final_metadata["score"] = score
                
                final_doc = Document(page_content=enriched_content, metadata=final_metadata)
                final_docs.append(final_doc)
                print(f"   Score={score:.4f} | {enriched_content[:50]}...")
                
            return final_docs

        except Exception as e:
            print(f"[ERROR] 用户记忆检索失败: {e}")
            import traceback
            traceback.print_exc()
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
                print(f"[ERROR] 动作库集合初始化失败: {e}")
                return []

        try:
            docs = self.action_store.similarity_search(query, k=k)
            print(f"🎭 动作库检索: 找到 {len(docs)} 个相关动作")
            for i, doc in enumerate(docs, 1):
                print(f"   {i}. {doc.page_content[:50]}...")
            return docs
        except Exception as e:
            print(f"[ERROR] 动作库检索失败: {e}")
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

        print(f"记忆上下文: 用户记忆 {len(user_memories)} 条, 动作模式 {len(action_patterns)} 个")

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
                print(f"[ERROR] 用户记忆集合初始化失败: {e}")
                return False

        try:
            now = time.time()
            current_dt = datetime.now()
            # 准备元数据 (v3.0: 增加 creation_time 和 importance 用于高级检索)
            # v3.1: 增加 day_of_month, weekday, month 供 PatternScanner 识别周期性规律
            default_metadata = {
                "timestamp": now,
                "creation_time": now,  # 用于 Recency 计算
                "date": current_dt.strftime("%Y-%m-%d %H:%M:%S"),
                "day_of_month": current_dt.day,      # PatternScanner: 月度模式识别
                "weekday": current_dt.weekday(),     # PatternScanner: 周度模式识别 (0=周一)
                "month": current_dt.month,           # PatternScanner: 年度模式识别
                "category": "user_preference",  # 默认分类
                "source": "conversation",  # 来源：对话
                "importance": 5  # 默认重要性
            }

            if metadata:
                default_metadata.update(metadata)

            # 0. 自动去重检查 (Phase 7)
            try:
                # 仅对非高频变动的数据查重 (如非 relationship/episodic)
                # 其实所有类别都应该查
                existing_doc = self.check_similarity(content)
                if existing_doc:
                    action = self._should_deduplicate(
                        content, 
                        existing_doc.page_content, 
                        existing_doc.metadata.get("score", 1.0)
                    )
                    
                    if action == "overwrite":
                        origin_id = existing_doc.metadata.get("id")
                        if origin_id:
                            print(f"🔄 检测到语义重复 (Score={existing_doc.metadata.get('score', 0):.4f})，执行覆盖...")
                            # 保持 ID 不变，更新内容
                            default_metadata["id"] = origin_id
                            self._update_memory(origin_id, content, default_metadata)
                            return True
                    
                    elif action == "ignore":
                         print(f"🛑 检测到包含关系，保留更详细的旧记忆: {existing_doc.page_content[:20]}...")
                         return True
            except Exception as e:
                print(f"[WARN] 自动去重检查出错: {e}")

            # 序列化复杂元数据 (ChromaDB 不支持嵌套字典/列表)
            for k, v in default_metadata.items():
                if isinstance(v, (dict, list)):
                    default_metadata[k] = json.dumps(v, ensure_ascii=False)

            # 生成 ID
            doc_id = str(uuid.uuid4())
            default_metadata["id"] = doc_id

            # 创建文档
            doc = Document(
                page_content=content,
                metadata=default_metadata
            )

            # 添加到向量数据库
            self.user_memory_store.add_documents([doc], ids=[doc_id])

            print(f"用户记忆已保存: {content[:50]}...")
            print(f"   元数据: day={default_metadata['day_of_month']}, weekday={default_metadata['weekday']}")
            
            # [延迟刷新] 累积更新后统一刷新 BM25
            self._pending_bm25_updates += 1
            self._refresh_bm25_if_needed()
            
            return True

        except Exception as e:
            print(f"[ERROR] 保存用户记忆失败: {e}")
            return False

    def extract_user_preference(self, user_input: str, llm_response: str = "") -> Optional[Dict[str, Any]]:
        """
        从用户输入中提取用户偏好信息
        
        【修复】不再传入 AI 回复，只从用户原文提取
        
        Args:
            user_input: 用户的原始输入
            llm_response: (已废弃，保留参数兼容性)
        """
        try:
            # 只检查用户输入中是否包含偏好信息
            preference_keywords = [
                "喜欢", "偏好", "最爱", "习惯", "经常", "总是",
                "讨厌", "不喜欢", "不习惯", "避免", "不能", "不要", "少吃", "多吃",
                "想吃", "想听", "想要", "希望", "需要"
            ]

            # 【关键修复】只检查用户输入，不再混合 AI 回复
            has_preference = any(keyword in user_input for keyword in preference_keywords)

            if not has_preference:
                return None

            # 使用 LLM 提取具体的用户偏好（只传入用户输入）
            prompt = ChatPromptTemplate.from_messages([
                ("system", """你是一个用户偏好提取器。
从用户的输入中提取用户偏好信息。

【重要规则】
1. 只提取用户**明确表达**的偏好，不要推测
2. 使用第三人称描述，例如："用户喜欢..."、"用户习惯..."
3. 提取内容必须能在用户原文中找到依据

输出格式：JSON 对象
- content: 提取的偏好描述
- category: 偏好分类 (food, music, activity, habit, color, schedule 等)
- confidence: 置信度 (0.0-1.0)
- evidence: 用户原文中的关键证据（必须是用户说的话的片段）

如果用户输入中没有明确的偏好信息，返回 null。

示例：
用户输入: "我喜欢吃火锅，讨厌香菜"
输出: {{
    "content": "用户喜欢吃火锅，讨厌香菜", 
    "category": "food", 
    "confidence": 0.95, 
    "evidence": "喜欢吃火锅，讨厌香菜"
}}

用户输入: "今天好累"
输出: null  (这是状态描述，不是偏好)

只输出JSON，不要解释。"""),
                ("human", "用户输入: {user_input}")
            ])

            from langchain_core.output_parsers import JsonOutputParser
            parser = JsonOutputParser()
            chain = prompt | self.llm | parser
            result = chain.invoke({"user_input": user_input})
            
            result = chain.invoke({})
            
            # 【新增】后置验证：确保 evidence 在用户原文中存在
            if result and isinstance(result, dict):
                content = result.get("content", "")
                evidence = result.get("evidence", "")
                
                if content and len(content) > 5:
                    # 验证 evidence 是否在用户输入中
                    if evidence and evidence in user_input:
                        return result
                    # 如果没有 evidence 字段，尝试验证 content 关键词
                    elif any(word in user_input for word in content.split() if len(word) > 1):
                        return result
                    else:
                        print(f"[WARN] 提取内容无法在用户原文中找到依据，跳过: {content}")
                        return None
            
            return None

        except Exception as e:
            print(f"[ERROR] 提取用户偏好失败: {e}")
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
            print(f"[ERROR] 提取音乐偏好失败: {e}")
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
            print(f"[ERROR] 提取新闻偏好失败: {e}")
            return None

    def extract_episodic_memory(self, user_input: str, llm_response: str) -> Optional[Dict[str, Any]]:
        """
        从对话中提取情境记忆 (Episodic Memory) - 本体论增强版
        即用户经历的具体事件（去过哪里、做了什么、见过谁），包含重要性评分和结构化实体。
        
        Args:
            user_input: 用户输入
            llm_response: AI 回复
            
        Returns:
            事件信息字典: {
                "content": str,       # 事件描述（用户去过公园/吃了火锅）
                "importance": int,    # 重要性评分 (1-10)
                "category": str,      # activity, social, travel, work, daily
                "confidence": float,  # 置信度
                # === 新增：结构化实体 (本体论增强) ===
                "entities": {
                    "persons": [{"name": str, "role": str}],
                    "places": [{"name": str, "type": str}],
                    "objects": [{"name": str}]
                },
                "temporal": {
                    "date": str,           # 具体日期或 null
                    "is_recurring": bool,  # 是否周期性
                    "recurrence_pattern": str  # monthly/weekly/yearly 或 null
                },
                "action": {
                    "verb": str,    # 核心动词
                    "type": str     # visit/receive/meet/do/buy 等
                }
            }
        """
        try:
            # 1. 快速过滤：检查是否包含动作动词或状态描述
            action_keywords = [
                "今天", "昨天", "刚刚", "去了", "看到", "买了", "吃了", "玩了",
                "遇到", "发生", "参加", "完成", "做了", "收到", "见了", "认识",
                "下周", "明天", "即将", "准备", "计划", "打算", "有个"
            ]
            if not any(k in user_input for k in action_keywords):
                return None

            prompt = ChatPromptTemplate.from_messages([
                ("system", """你是一个结构化事件提取器。请从对话中提取用户经历的具体事件，并拆分为结构化实体。

提取规则：
1. **content**: 以第三人称描述用户经历的事件（"用户去了..."）。
2. **importance**: 评分 1-10。
   - 1-3: 日常琐事（"用户去楼下买了瓶水"）
   - 4-6: 一般事件（"用户去公园散步，觉得喷泉很好看"）
   - 7-8: 重要事件（"用户去参加了朋友婚礼"，"用户完成了大项目"）
   - 9-10: 重大人生事件（"用户结婚了"，"用户生病住院"）
3. **category**: 归类为 [activity, social, travel, work, daily] 之一。

4. **entities**: 结构化实体拆分
   - persons: 涉及的人物列表（不包括"用户"本身），包含 name 和 role（如 friend, colleague, family）
   - places: 涉及的地点列表，包含 name 和 type（如 outdoor, indoor, workplace, restaurant）
   - objects: 涉及的物品/事物列表，包含 name

5. **temporal**: 时间信息
   - date: 具体日期（如 "2026-01-21"）或 null
   - is_recurring: 是否周期性事件（如发工资、周会）
   - recurrence_pattern: "monthly" / "weekly" / "yearly" / null

6. **action**: 动作信息
   - verb: 核心动词（去、买、收到、见）
   - type: 动作类型 [visit, buy, receive, meet, do, eat, play, work, travel]

示例1：
用户: "今天去了个公园，里面的喷泉很漂亮"
输出: {{
  "content": "用户去了公园，觉得喷泉很漂亮",
  "importance": 5,
  "category": "activity",
  "confidence": 0.9,
  "entities": {{
    "persons": [],
    "places": [{{"name": "公园", "type": "outdoor"}}],
    "objects": [{{"name": "喷泉"}}]
  }},
  "temporal": {{"date": null, "is_recurring": false, "recurrence_pattern": null}},
  "action": {{"verb": "去", "type": "visit"}}
}}

示例2：
用户: "今天我在公司收到了人才补贴"
输出: {{
  "content": "用户在公司收到了人才补贴",
  "importance": 7,
  "category": "work",
  "confidence": 0.95,
  "entities": {{
    "persons": [],
    "places": [{{"name": "公司", "type": "workplace"}}],
    "objects": [{{"name": "人才补贴"}}]
  }},
  "temporal": {{"date": null, "is_recurring": true, "recurrence_pattern": "monthly"}},
  "action": {{"verb": "收到", "type": "receive"}}
}}

示例3：
用户: "帮我查一下天气"
输出: null (没有具体经历事件)

只输出JSON，如果没有提取到具体事件，返回 null。"""),
                ("human", "用户: {user_input}\nAI: {llm_response}")
            ])

            from langchain_core.output_parsers import JsonOutputParser
            parser = JsonOutputParser()
            chain = prompt | self.llm | parser
            
            result = chain.invoke({"user_input": user_input, "llm_response": llm_response})
            
            if not result or not isinstance(result, dict):
                return None
                
            # 过滤低置信度结果
            if result.get("confidence", 0) < 0.6:
                return None
            
            # 确保向后兼容：如果没有新字段，添加默认值
            if "entities" not in result:
                result["entities"] = {"persons": [], "places": [], "objects": []}
            if "temporal" not in result:
                result["temporal"] = {"date": None, "is_recurring": False, "recurrence_pattern": None}
            if "action" not in result:
                result["action"] = {"verb": None, "type": None}
            
            # 打印提取结果
            entities_summary = []
            for key, items in result.get("entities", {}).items():
                if items:
                    names = [i.get("name", "") for i in items if isinstance(i, dict)]
                    if names:
                        entities_summary.append(f"{key}: {', '.join(names)}")
            
            print(f"   情境记忆提取: {result.get('content', '')[:30]}... (重要性: {result.get('importance', 0)})")
            if entities_summary:
                print(f"   实体: {'; '.join(entities_summary)}")
            
            return result
            
        except Exception as e:
            print(f"[ERROR] 情境记忆提取失败: {e}")
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
            print(f"[ERROR] 检索音乐偏好失败: {e}")
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
            print(f"[ERROR] 检索新闻兴趣失败: {e}")
            return []

    def detect_and_resolve_conflicts(self, new_fact: str, category: str, event_name: Optional[str] = None) -> bool:
        """
        检测新事实是否与已有记忆冲突，如果冲突则删除旧记忆
        支持分类去重：常住地覆盖、当前位置覆盖等
        """
        if not self.user_memory_store:
            return False
        
        try:
            # 1. 尝试提取城市和位置类型 (仅用于 user_profile 类别的地理位置冲突)
            is_location_update = False
            new_city = None
            is_home = False
            is_travel = False

            if category == "user_profile":
                cities = ["上海", "北京", "深圳", "广州", "杭州", "成都", "武汉", "南京", "苏州", "重庆", "西安", "天津", "厦门", "青岛", "大连"]
                for city in cities:
                    if city in new_fact:
                        new_city = city
                        break
                
                if new_city:
                    is_location_update = True
                    # 判断是"常住地"还是"当前/出差"
                    is_home = any(kw in new_fact for kw in ["常住", "住在", "定居", "搬家", "搬到", "搬去", "搬迁", "安家", "落户"])
                    is_travel = any(kw in new_fact for kw in ["出差", "旅游", "现在在", "正在", "临时", "来到", "去了"])
                    
                    if not is_home and not is_travel:
                        is_travel = True

            if is_location_update and category == "user_profile":
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
                    print(f"    已删除 {len(conflicting_ids)} 条旧的{type_str}记忆")
                    return True
            
            # 2. 事件名冲突 (同名事件覆盖)
            if event_name:
                # 实现特定事件名的覆盖
                pass

            # 处理周期性时间模式冲突
            if category == "recurring_pattern" and event_name:
                # 获取所有周期性模式记忆
                all_patterns = self.user_memory_store.get(where={"category": "recurring_pattern"})
                documents = all_patterns.get("documents", [])
                ids = all_patterns.get("ids", [])
                

                
                conflicting_ids = []
                for doc, doc_id in zip(documents, ids):
                    # 如果记忆内容包含事件名称（如"发薪日"），则认为是同名事件冲突，需要覆盖
                    if event_name in doc:
                        conflicting_ids.append(doc_id)
                
                if conflicting_ids:
                    self.user_memory_store.delete(ids=conflicting_ids)
                    print(f"    已删除 {len(conflicting_ids)} 条旧的'{event_name}'周期性记忆")
                    return True
            
            return False
        except Exception as e:
            print(f"[ERROR] 冲突检测失败: {e}")
            return False

    def check_similarity(self, content: str) -> Optional[Document]:
        """检查是否存在高相似度记忆 (用于去重)"""
        # 阈值 distance < 0.5 (适配 L2 Distance, 约等于 Cosine 0.1~0.2)
        try:
            results = self.user_memory_store.similarity_search_with_score(content, k=1)
            if not results:
                return None
            
            doc, score = results[0]
            # distance 越小越相似
            if score < 0.5: 
                doc.metadata["score"] = score  # 注入 score 以便后续使用
                return doc
            return None
        except Exception as e:
            print(f"[WARN] 相似度检查失败: {e}")
            return None

    def _should_deduplicate(self, new_content: str, old_content: str, score: float) -> str:
        """
        判断去重策略
        Returns:
            action: 'overwrite' | 'ignore' | 'keep_both'
        """
        # 1. 包含关系检测 (优先级最高)
        if len(old_content) < len(new_content) and old_content in new_content:
            return "overwrite"
        
        if len(new_content) < len(old_content) and new_content in old_content:
            return "ignore"

        # 2. 极高相似度 (L2 < 0.35) -> 覆盖
        if score < 0.35:
            return "overwrite"
            
        # 3. 简单的序列匹配比率 (防止 Vector 误判)
        from difflib import SequenceMatcher
        ratio = SequenceMatcher(None, new_content, old_content).ratio()
        if ratio > 0.95:
            return "overwrite"
            
        # 4. 默认保留两者
        return "keep_both"

    def _update_memory(self, doc_id: str, content: str, metadata: Dict[str, Any]):
        """更新已有记忆"""
        try:
            self.user_memory_store.update_document(
                document_id=doc_id, 
                document=Document(page_content=content, metadata=metadata)
            )
            print(f"🔄 更新记忆 [{doc_id}]: {content[:30]}...")
            
            # [延迟刷新] 累积更新后统一刷新 BM25
            self._pending_bm25_updates += 1
            self._refresh_bm25_if_needed()

        except Exception as e:
            print(f"[ERROR] 更新记忆失败: {e}")
    
    # ==========================================
    # 触发式记忆更新 (Phase 1)
    # ==========================================
    
    def triggered_memory_update(
        self, 
        user_input: str, 
        llm_response: str,
        extracted_preference: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        触发式记忆更新（后处理阶段调用，尽量不增加额外 LLM 调用）
        
        Args:
            user_input: 用户原始输入
            llm_response: AI 回复
            extracted_preference: 已提取的偏好（避免重复调用 LLM）
        
        Returns:
            {
                "triggered": bool,           # 是否触发了更新
                "updated_fields": List[str], # 更新的字段名
                "conflicts_resolved": int,   # 解决的冲突数
                "log": str                   # 可读日志
            }
        """
        result = {
            "triggered": False,
            "updated_fields": [],
            "conflicts_resolved": 0,
            "log": ""
        }
        
        # 1. 检查是否命中触发词
        triggered_keyword = None
        for kw in self.TRIGGERED_UPDATE_CONFIG["trigger_keywords"]:
            if kw in user_input:
                triggered_keyword = kw
                break
        
        if not triggered_keyword:
            return result
        
        result["triggered"] = True
        print(f"📝 触发式更新检测到关键词: '{triggered_keyword}'")
        
        # 2. 尝试直接映射到 Profile 字段（不需要 LLM，零成本）
        profile = self.load_profile()
        direct_updated = self._try_direct_profile_update(user_input, profile)
        
        if direct_updated:
            result["updated_fields"].extend(direct_updated)
            self.save_profile(profile)
            print(f"   直接更新成功: {direct_updated}")
        
        # 3. 如果有已提取的偏好，处理偏好更新和冲突检测
        if extracted_preference and isinstance(extracted_preference, dict):
            category = extracted_preference.get("category", "habit")
            content = extracted_preference.get("content", "")
            
            if content and category:
                # 冲突检测
                conflicts = self._detect_preference_conflicts(content, category, profile)
                if conflicts:
                    self._resolve_preference_conflicts(conflicts, category, profile)
                    result["conflicts_resolved"] = len(conflicts)
                    print(f"   冲突解决: 移除 {len(conflicts)} 条旧偏好")
                
                # 添加到 preference_summary
                if category in profile.preference_summary:
                    if content not in profile.preference_summary[category]:
                        profile.preference_summary[category].append(content)
                        result["updated_fields"].append(f"preference_summary.{category}")
                        print(f"   新增偏好: [{category}] {content}")
                
                self.save_profile(profile)
        
        result["log"] = f"触发词: {triggered_keyword} → 更新: {result['updated_fields']}, 冲突解决: {result['conflicts_resolved']}"
        return result

    def _try_direct_profile_update(self, user_input: str, profile: "UserProfile") -> List[str]:
        """
        尝试通过正则直接提取并更新 Profile 字段（不调用 LLM，零 Token 成本）
        
        Returns:
            更新的字段名列表
        """
        import re
        updated = []
        
        # 姓名提取
        name_patterns = [
            r"(?:我叫|我是|我的名字是|叫我)\s*[\"']?([^\s\"',，。！？]{2,10})[\"']?",
        ]
        for pattern in name_patterns:
            match = re.search(pattern, user_input)
            if match:
                new_name = match.group(1).strip()
                # 过滤掉明显不是名字的词
                skip_words = ["用户", "助手", "机器人", "AI", "你好", "什么"]
                if new_name not in skip_words and len(new_name) >= 2:
                    if profile.name != new_name:
                        print(f"   直接更新 name: '{profile.name}' → '{new_name}'")
                        profile.name = new_name
                        updated.append("name")
                    break
        
        # 生日提取 (MM-DD 或 X月X日)
        birthday_patterns = [
            r"(?:我的生日是|生日是|我生日)\s*(\d{1,2})[月\-/](\d{1,2})",
            r"(\d{1,2})[月](\d{1,2})[日号].*(?:生日|出生)",
        ]
        for pattern in birthday_patterns:
            match = re.search(pattern, user_input)
            if match:
                month, day = match.groups()
                new_birthday = f"{int(month):02d}-{int(day):02d}"
                if profile.birthday != new_birthday:
                    print(f"   直接更新 birthday: '{profile.birthday}' → '{new_birthday}'")
                    profile.birthday = new_birthday
                    updated.append("birthday")
                break
        
        # 城市提取
        city_patterns = [
            r"(?:我住在|我常住|我搬到|我在|我来自)\s*([^\s,，。！？]{2,4})(?:市|$)",
            r"(?:常住地是|家在)\s*([^\s,，。！？]{2,4})",
        ]
        for pattern in city_patterns:
            match = re.search(pattern, user_input)
            if match:
                potential_city = match.group(1).strip()
                # 验证是否为已知城市
                if potential_city in self.TRIGGERED_UPDATE_CONFIG["known_cities"]:
                    if profile.home_city != potential_city:
                        print(f"   直接更新 home_city: '{profile.home_city}' → '{potential_city}'")
                        profile.home_city = potential_city
                        updated.append("home_city")
                    break
        
        return updated

    def _detect_preference_conflicts(
        self, 
        new_content: str, 
        category: str, 
        profile: "UserProfile"
    ) -> List[str]:
        """
        检测新偏好与已有偏好的冲突
        
        冲突规则:
        - "喜欢X" 和 "不喜欢X" 冲突
        - "习惯早起" 和 "习惯晚睡" 冲突（时间习惯）
        
        Returns:
            冲突的已有偏好列表
        """
        conflicts = []
        
        if category not in profile.preference_summary:
            return conflicts
        
        # 反义词对
        opposite_pairs = [
            ("喜欢", "不喜欢"),
            ("喜欢", "讨厌"),
            ("习惯", "不习惯"),
            ("经常", "很少"),
            ("爱吃", "不吃"),
        ]
        
        # 提取新内容的核心词（去除情感词）
        new_content_lower = new_content.lower()
        
        for existing in profile.preference_summary[category]:
            existing_lower = existing.lower()
            
            # 检查是否存在相反的偏好
            for pos, neg in opposite_pairs:
                # 情况1: 新的是正面，旧的是负面
                if pos in new_content_lower and neg in existing_lower:
                    # 提取核心对象进行比较
                    new_core = new_content_lower.replace(pos, "").replace("用户", "").strip()
                    exist_core = existing_lower.replace(neg, "").replace("用户", "").strip()
                    # 如果核心内容有重叠（至少2个字符），认为冲突
                    if self._has_overlap(new_core, exist_core):
                        conflicts.append(existing)
                        break
                
                # 情况2: 新的是负面，旧的是正面
                elif neg in new_content_lower and pos in existing_lower:
                    new_core = new_content_lower.replace(neg, "").replace("用户", "").strip()
                    exist_core = existing_lower.replace(pos, "").replace("用户", "").strip()
                    if self._has_overlap(new_core, exist_core):
                        conflicts.append(existing)
                        break
        
        return conflicts

    def _has_overlap(self, str1: str, str2: str, min_overlap: int = 2) -> bool:
        """检查两个字符串是否有足够的重叠"""
        if not str1 or not str2:
            return False
        
        # 简单方法：检查是否有共同的连续子串
        shorter = str1 if len(str1) <= len(str2) else str2
        longer = str2 if len(str1) <= len(str2) else str1
        
        for i in range(len(shorter) - min_overlap + 1):
            substring = shorter[i:i + min_overlap]
            if substring in longer:
                return True
        return False

    def _resolve_preference_conflicts(
        self, 
        conflicts: List[str], 
        category: str,
        profile: "UserProfile"
    ):
        """
        解决偏好冲突：删除旧的，保留新的
        
        原则：以用户最新表达为准
        """
        if category not in profile.preference_summary:
            return
        
        for conflict in conflicts:
            if conflict in profile.preference_summary[category]:
                profile.preference_summary[category].remove(conflict)
                print(f"   冲突解决: 移除旧偏好 '{conflict}'")


    def _validate_profile_updates(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        """验证并清洗用户画像更新数据"""
        validated = {}
        
        # 允许更新的字段
        allowed_fields = {"name", "home_city", "core_preferences", "important_dates"}
        
        for key, value in updates.items():
            if key not in allowed_fields:
                print(f"[WARN]  忽略无效的画像字段: {key}")
                continue
                
            if value is None or (isinstance(value, str) and not value.strip()):
                print(f"[WARN]  忽略空值字段: {key}")
                continue
                
            # 特殊清洗逻辑
            if key == "core_preferences" and isinstance(value, list):
                # 过滤空字符串
                validated[key] = [p for p in value if isinstance(p, str) and p.strip()]
            elif key == "important_dates" and isinstance(value, list):
                # 验证 important_dates 格式: [{"day": 10, "name": "发薪日", "type": "monthly"}]
                valid_dates = []
                for item in value:
                    if isinstance(item, dict) and "name" in item:
                        valid_dates.append(item)
                validated[key] = valid_dates
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
                # print("   使用 Profile 缓存")
                return self._profile_cache
            
            # 4. 加载文件并更新缓存
            with open(profile_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                profile = UserProfile(**data)
                
                self._profile_cache = profile
                self._profile_mtime = current_mtime
                print(f"   已从磁盘重新加载用户画像 (v{profile.version})")
                return profile
                
        except Exception as e:
            print(f"[ERROR] 加载用户画像失败: {e}")
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
            print(f"[ERROR] 保存用户画像失败: {e}")
            return False

    def _process_profile_deletions(self, delete_names: List[str], category: str) -> None:
        """
        处理用户画像中的删除意图
        从 Profile RAM (important_dates) 和 ChromaDB 中删除匹配的事件
        
        Args:
            delete_names: 可能的事件名称列表（模糊匹配）
            category: 事件类别
        """
        try:
            deleted_from_profile = False
            deleted_from_chromadb = False
            
            # 1. 从 Profile RAM 删除 (important_dates)
            profile = self.load_profile()
            if profile.important_dates:
                original_count = len(profile.important_dates)
                remaining_dates = []
                
                for date_entry in profile.important_dates:
                    if not isinstance(date_entry, dict):
                        remaining_dates.append(date_entry)
                        continue
                        
                    event_name = date_entry.get("name", "")
                    should_delete = False
                    
                    # 检查是否匹配任何 delete_names（过滤太短的词，要求更精确匹配）
                    for del_name in delete_names:
                        # 过滤太短的词（如"述职"只有2个字，容易误删）
                        if len(del_name) < 3:
                            continue
                        # 要求双向包含或高度重叠
                        if del_name in event_name or event_name in del_name:
                            should_delete = True
                            print(f"    从 Profile 删除事件: {event_name} (匹配: {del_name})")
                            break
                    
                    if not should_delete:
                        remaining_dates.append(date_entry)
                
                if len(remaining_dates) < original_count:
                    profile.important_dates = remaining_dates
                    self.save_profile(profile)
                    deleted_from_profile = True
                    print(f"   Profile RAM 已删除 {original_count - len(remaining_dates)} 个事件")
            
            # 2. 从 ChromaDB 删除相关记忆
            if self.user_memory_store:
                # 获取所有相关类别的记忆
                categories_to_check = ["recurring_pattern", "user_profile"]
                if category not in categories_to_check:
                    categories_to_check.append(category)
                    
                all_memories = self.user_memory_store.get(
                    where={"category": {"$in": categories_to_check}}
                )
                
                documents = all_memories.get("documents", [])
                ids = all_memories.get("ids", [])
                
                ids_to_delete = []
                for doc, doc_id in zip(documents, ids):
                    for del_name in delete_names:
                        # 过滤太短的词（如"述职"只有2个字，容易误删）
                        if len(del_name) < 3:
                            continue
                        if del_name in doc:
                            ids_to_delete.append(doc_id)
                            print(f"    从 ChromaDB 删除记忆: {doc[:50]}... (匹配: {del_name})")
                            break
                
                if ids_to_delete:
                    self.user_memory_store.delete(ids=ids_to_delete)
                    deleted_from_chromadb = True
                    print(f"   ChromaDB 已删除 {len(ids_to_delete)} 条记忆")
            
            if deleted_from_profile or deleted_from_chromadb:
                print(f"   删除操作完成")
            else:
                print(f"[WARN]  未找到匹配的事件进行删除: {delete_names}")
                
        except Exception as e:
            print(f"[ERROR] 处理删除意图失败: {e}")

    def update_profile(self, updates: Dict[str, Any]) -> "UserProfile":
        """更新用户画像字段"""
        # 1. 数据校验
        validated_updates = self._validate_profile_updates(updates)
        if not validated_updates:
            print("[WARN]  更新数据为空或无效，跳过")
            return self.load_profile()
            
        profile = self.load_profile()
        updated = False
        
        for key, value in validated_updates.items():
            if hasattr(profile, key):
                current_value = getattr(profile, key)
                
                # 特殊处理 important_dates：增量合并而非覆盖
                if key == "important_dates" and isinstance(value, list):
                    existing_dates = current_value if current_value else []
                    
                    # 1. 构建索引映射 {name: index}
                    name_to_index = {}
                    for idx, d in enumerate(existing_dates):
                        if isinstance(d, dict) and d.get("name"):
                            name_to_index[d.get("name")] = idx
                            
                    for new_date in value:
                        if not isinstance(new_date, dict):
                            continue
                            
                        name = new_date.get("name")
                        if name in name_to_index:
                            # 更新已有事件
                            idx = name_to_index[name]
                            existing_dates[idx] = new_date
                            updated = True
                            print(f"   更新周期性事件: {name} ({new_date.get('type', 'unknown')})")
                        else:
                            # 添加新事件
                            existing_dates.append(new_date)
                            updated = True
                            name_to_index[name] = len(existing_dates) - 1 # Update index map just in case
                            print(f"   新增周期性事件: {name} ({new_date.get('type', 'unknown')})")
                            
                    setattr(profile, key, existing_dates)
                elif current_value != value:
                    setattr(profile, key, value)
                    updated = True
        
        if updated:
            profile.last_updated = time.time()
            self.save_profile(profile)
            print(f"   用户画像已更新: {validated_updates.keys()}")
            
        return profile

    def extract_and_save_user_profile(self, user_input: str, llm_response: str = "") -> List[Dict[str, Any]]:
        """
        从用户输入中提取长期用户信息（画像、偏好、习惯等）并保存到长期记忆
        
        【修复】不再传入 AI 回复，只从用户原文提取
        """
        try:
            # 【新增】获取已有事件列表，用于保持命名一致性
            existing_events = []
            try:
                profile = self.load_profile()
                if profile.important_dates:
                    existing_events = [d.get("name", "") for d in profile.important_dates if isinstance(d, dict) and d.get("name")]
            except:
                pass
            existing_events_str = ", ".join(existing_events) if existing_events else "暂无"
            
            prompt = ChatPromptTemplate.from_messages([
                ("system", """你是一个资深的用户画像提取专家。你的任务是从用户的输入中识别出：
1. 值得长期保存的【事实性信息】（新增/更新）
2. 用户想要【取消/删除】的已有信息

【关键规则】
- 只提取用户**明确说出**的信息，不要推测
- 提取内容必须能在用户原文中找到依据
- 不要从 AI 回复中推断任何信息

这些信息包括但不限于：
1. 基础画像 (user_profile): 姓名、常住地 (home_city)、当前位置 (current_location)、职业、重要纪念日。
2. 生活规律 (habit): 作息时间、工作习惯、活跃时段。
3. 长期偏好 (preference): 饮食口味、光线/环境偏好、音乐/技术兴趣。
4. 核心关系 (relationship): 提到的人物（朋友/家人）、交互底线。
5. 周期性时间模式 (recurring_pattern): 每月/每周固定发生的事件。

【[WARN] 已有事件列表】（重要！更新或删除时必须使用完全一致的名称）：
{existing_events}

【删除/取消规则】（重要！）：
- 当用户说"以后不用XX了"、"取消XX"、"XX不用了"、"不再XX了"、"XX取消了"时，识别为删除意图。
- [WARN] delete_names 必须足够具体（至少4个字），禁止使用过于宽泛的词！
  - 正确示例: ["老板A述职", "和老板A述职"]（具体到人）
  - [ERROR] 错误示例: ["述职", "汇报"]（太宽泛，会误删其他事件）
- 如果已有事件列表中存在匹配的事件，delete_names 必须包含该事件的完整名称。
- 示例：
  - 已有事件: ["老板A述职", "老板B述职"]
  - 用户："不需要和老板A述职了" -> delete_names: ["老板A述职"]（只删A，不删B）
  - 用户："发薪日改到15号了" -> {{"content": "用户每月15号是发薪日", "category": "recurring_pattern", "confidence": 1.0, "updates": {{"important_dates": [{{"day": 15, "name": "发薪日", "type": "monthly"}}]}}}}

【地理位置提取规则】：
- **常住地（Base 地）**：如果用户说"我住在XX"、"我是XX人"、"我常住XX"、"我搬家到XX了"、"我搬到XX了"、"我在XX安家了"，将其识别为【常住地】(home_city)。
  - 描述格式："用户常住地是XX"、"用户住在XX"
- **当前位置（临时）**：如果用户说"我现在在XX"、"我来XX出差/旅游了"、"我在XX呢"（针对当前对话），将其识别为【当前位置】(current_location)。
  - 描述格式："用户当前正在XX出差"、"用户现在在XX旅游"
- **重要**：只有明确提到"搬家"、"搬到"等永久性迁移词汇时，才更新常住地。否则默认为临时位置。

【周期性时间模式提取规则】：
- **每月固定日期**：如"每个月10号发工资"、"每月15号还信用卡"、"每月1号交房租"。
  - 描述格式："用户每月X号是XX日"
  - updates 格式：{{"important_dates": [{{"day": 10, "name": "发薪日", "type": "monthly"}}]}}
- **每周固定日期**：如"每周三健身"、"周末休息"。
  - 描述格式："用户每周X有XX安排"
  - updates 格式：{{"important_dates": [{{"weekday": 3, "name": "健身日", "type": "weekly"}}]}}
- [WARN] 如果是更新已有事件（如改日期），name 字段必须与已有事件列表中的名称完全一致！
- **重要**：这类信息对于主动提醒非常有价值，请务必识别并提取。

【基础身份提取规则】：
- **姓名/称呼**：如果用户说"我叫XX"、"以后叫我XX"、"把我的名字改为XX"、"我是XX"。
  - 描述格式："用户希望被称呼为XX"
  - updates 格式：{{"name": "XX"}}
  - 示例：
    - 用户："以后叫我456" -> {{"content": "用户希望被称呼为456", "category": "user_profile", "confidence": 1.0, "updates": {{"name": "456"}} }}
    - 用户："我叫张三" -> {{"content": "用户的名字是张三", "category": "user_profile", "confidence": 1.0, "updates": {{"name": "张三"}} }}

输出要求：
- 必须输出有效的 JSON 数组，每个元素包含：
  - content (事实描述)
  - category (分类: user_profile/habit/preference/relationship/recurring_pattern)
  - confidence (置信度 0-1)
  - updates (可选，字典): 如果信息涉及 [name, home_city, important_dates]，请在此字段中提供更新值。
  - delete_names (可选，数组): 如果用户要取消/删除某个事件，请提供可能的事件名称列表（必须足够具体，至少4个字）。
- 如果没有提取到任何有价值的信息（包括删除意图），返回空数组 []。
- 事实描述应该是第三人称事实。
- 不要包含临时的、情绪化的或对话过程中的信息。
- 【重要】每个提取项必须包含 evidence 字段（用户原文片段作为证据）。"""),
                ("human", "用户说: {user_input}")
            ])

            # 使用带有 JSON 输出解析器的链
            from langchain_core.output_parsers import JsonOutputParser
            parser = JsonOutputParser()
            chain = prompt | self.llm | parser
            
            # 正确传入变量，包含已有事件列表（不再传入 llm_response）
            extracted_facts = chain.invoke({
                "user_input": user_input, 
                "existing_events": existing_events_str
            })
            
            # 调试日志：显示 LLM 提取结果
            print(f"[画像提取] LLM 返回: {extracted_facts}")
            
            saved_count = 0
            if isinstance(extracted_facts, list):
                for fact in extracted_facts:
                    # 仅保存高置信度的信息
                    if fact.get("confidence", 0) >= 0.7:
                        content = fact.get("content")
                        category = fact.get("category", "user_profile")
                        if content:
                            # 【新增】在保存前检测并解决冲突
                            # 尝试从 updates 中获取 event_name
                            event_name = None
                            updates = fact.get("updates")
                            if updates and isinstance(updates, dict):
                                important_dates = updates.get("important_dates")
                                if important_dates and isinstance(important_dates, list) and len(important_dates) > 0:
                                    event_name = important_dates[0].get("name")
                                    
                            conflict_resolved = self.detect_and_resolve_conflicts(content, category, event_name)
                            
                            # 标准化 category
                            normalized_category = self._normalize_category(category)
                            
                            # 保存新记忆
                            success = self.save_user_memory(
                                content=content,
                                metadata={
                                    "category": normalized_category,
                                    "source": "profile_extraction",
                                    "confidence": fact.get("confidence")
                                }
                            )
                            
                            # 【新增】同步 core fields 到 Profile RAM
                            updates = fact.get("updates")
                            if updates and isinstance(updates, dict):
                                print(f"   同步核心画像字段到 RAM: {updates}")
                                self.update_profile(updates)
                                
                            if success:
                                saved_count += 1
                                conflict_tag = " [已覆盖旧记忆]" if conflict_resolved else ""
                                print(f"[画像提取] 已存入长期记忆 ({category}): {content}{conflict_tag}")
                        
                        # 【新增】处理删除意图
                        delete_names = fact.get("delete_names")
                        if delete_names and isinstance(delete_names, list):
                            self._process_profile_deletions(delete_names, category)
            
            return extracted_facts if isinstance(extracted_facts, list) else []

        except Exception as e:
            print(f"[ERROR] 提取用户画像失败: {e}")
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
            print(f"[ERROR] 获取用户画像失败: {e}")
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
                print(f"[ERROR] 动作库集合创建失败: {e}")
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
            print(f"[ERROR] 初始化动作库失败: {e}")

    def save_episode(
        self,
        context: str,       # 用户输入的上下文
        action: str,        # Agent 采取的动作
        outcome: str,       # "positive" | "negative" | "neutral"
        tool_used: Optional[str] = None,  # 使用的工具
        metadata: Optional[Dict] = None
    ) -> bool:
        """
        保存一个交互情景作为 Few-shot 示例
        """
        if not self.episodes_store:
            try:
                self.episodes_store = Chroma(
                    collection_name="episodes",
                    embedding_function=self.embeddings,
                    persist_directory=self.episodes_path
                )
            except Exception as e:
                print(f"[ERROR] 情景记忆集合初始化失败: {e}")
                return False
                
        try:
            content = f"Context: {context}\nAction: {action}\nOutcome: {outcome}"
            now = time.time()
            current_dt = datetime.now()
            
            default_metadata = {
                "timestamp": now,
                "creation_time": now,
                "date": current_dt.strftime("%Y-%m-%d %H:%M:%S"),
                "outcome": outcome,
                "tool_used": tool_used
            }
            
            if metadata:
                default_metadata.update(metadata)
                
            doc = Document(
                page_content=content,
                metadata=default_metadata
            )
            
            self.episodes_store.add_documents([doc])
            print(f"情景记忆已保存: {content[:50]}...")
            
            # 检查是否需要清理
            self._cleanup_old_episodes()
            
            return True
            
        except Exception as e:
            print(f"[ERROR] 保存情景记忆失败: {e}")
            return False
            
    def retrieve_similar_episodes(self, query: str, k: int = 2) -> List[Dict]:
        """
        检索相似的历史情景用于 Few-shot
        优先返回 outcome=positive 的案例
        """
        if not self.episodes_store:
            return []
            
        try:
            # 1. 向量检索 Top-10
            results = self.episodes_store.similarity_search_with_score(query, k=10)
            
            if not results:
                return []
                
            # 2. 按 outcome 排序（positive > neutral > negative）
            outcome_score = {
                "positive": 3,
                "neutral": 2,
                "negative": 1
            }
            
            scored_episodes = []
            for doc, distance in results:
                relevance_score = 1.0 / (1.0 + distance)
                outcome = doc.metadata.get("outcome", "neutral")
                total_score = relevance_score * outcome_score.get(outcome, 2)
                
                scored_episodes.append({
                    "doc": doc,
                    "score": total_score,
                    "relevance": relevance_score,
                    "outcome": outcome
                })
                
            # 3. 排序并返回 Top-k
            scored_episodes.sort(key=lambda x: x["score"], reverse=True)
            top_k_episodes = scored_episodes[:k]
            
            # 格式化返回结果
            return [
                {
                    "content": episode["doc"].page_content,
                    "metadata": episode["doc"].metadata,
                    "score": episode["score"]
                }
                for episode in top_k_episodes
            ]
            
        except Exception as e:
            print(f"[ERROR] 检索相似情景记忆失败: {e}")
            return []
            
    def synthesize_profile_from_collection(self) -> bool:
        """
        从 Collection 记忆中合成 Profile 偏好摘要
        使用 LLM 对相似记忆进行归纳
        """
        try:
            profile = self.load_profile()
            categories = ["food", "music", "activity", "habit", "work"]
            preference_summary = {}
            
            for cat in categories:
                memories = self.user_memory_store.get(
                    where={"category": cat},
                    limit=20
                )
                
                if memories["documents"]:
                    # 使用 LLM 归纳总结
                    summary = self._llm_summarize(cat, memories["documents"])
                    preference_summary[cat] = summary
                    
            profile.preference_summary = preference_summary
            profile.last_synthesized = time.time()
            self.save_profile(profile)
            
            print("✅ Profile 合成完成")
            return True
            
        except Exception as e:
            print(f"[ERROR] Profile 合成失败: {e}")
            return False
            
    async def maybe_synthesize_profile_async(self, force: bool = False):
        """
        智能触发 Profile 合成（非阻塞）
        
        触发条件（满足任一）:
        1. force=True（用户手动触发）
        2. 距离上次合成 > 24 小时 AND 新增记忆 > 10 条
        """
        profile = self.load_profile()
        hours_since_last = (time.time() - profile.last_synthesized) / 3600
        
        if not force:
            # 检查是否满足自动触发条件
            if hours_since_last < self.SYNTHESIS_CONFIG["min_interval_hours"]:
                return False
                
            new_count = self._count_new_memories_since(profile.last_synthesized)
            if new_count < self.SYNTHESIS_CONFIG["memory_threshold"]:
                return False
                
        # 异步执行，不阻塞主流程
        import asyncio
        asyncio.create_task(self._do_synthesize_profile())
        print("🔄 后台触发 Profile 合成...")
        return True
        
    async def _do_synthesize_profile(self):
        """实际执行合成的后台任务"""
        try:
            # 1. 获取各类别的偏好记忆
            categories = ["food", "music", "activity", "habit", "work"]
            preference_summary = {}
            
            for cat in categories:
                memories = self.user_memory_store.get(
                    where={"category": cat},
                    limit=20
                )
                if memories["documents"]:
                    # 2. LLM 归纳总结
                    summary = await self._llm_summarize(cat, memories["documents"])
                    preference_summary[cat] = summary
                    
            # 3. 更新 Profile
            profile = self.load_profile()
            profile.preference_summary = preference_summary
            profile.last_synthesized = time.time()
            self.save_profile(profile)
            
            print("✅ Profile 合成完成")
        except Exception as e:
            print(f"[ERROR] Profile 合成失败: {e}")
            
    def _llm_summarize(self, category: str, documents: List[str]) -> List[str]:
        """使用 LLM 总结特定类别的记忆"""
        try:
            content_text = "\n".join(documents)
            
            prompt = ChatPromptTemplate.from_messages([
                ("system", """你是一个用户偏好总结专家。请从用户记忆中提取并总结该类别的偏好信息。
                    
要求：
1. 只提取具体的偏好描述
2. 使用简洁的语言
3. 每个偏好单独成行
4. 不要添加解释性文字
5. 只返回与该类别相关的内容
                    
示例：
类别：food
记忆：["用户喜欢吃火锅", "用户不喜欢辣的食物", "用户喜欢吃海鲜"]
输出：["喜欢火锅", "不喜欢辣的食物", "喜欢海鲜"]
                    
类别：music
记忆：["用户喜欢周杰伦的音乐", "用户喜欢听流行音乐"]
输出：["喜欢周杰伦", "喜欢流行音乐"]
                    
只返回 JSON 格式的数组，不要其他内容。"""),
                ("human", "类别：{category}\n记忆：{documents}")
            ])
            
            from langchain_core.output_parsers import JsonOutputParser
            parser = JsonOutputParser()
            chain = prompt | self.llm | parser
            
            result = chain.invoke({"category": category, "documents": str(documents)})
            
            if isinstance(result, list):
                return result
            else:
                return []
                
        except Exception as e:
            print(f"[ERROR] LLM 总结失败: {e}")
            return []
            
    def _count_new_memories_since(self, timestamp: float) -> int:
        """统计自特定时间以来新增的记忆数量"""
        try:
            all_memories = self.user_memory_store.get()
            count = 0
            
            for metadata in all_memories.get("metadatas", []):
                if metadata.get("creation_time", 0) > timestamp:
                    count += 1
                    
            return count
            
        except Exception as e:
            print(f"[ERROR] 统计新记忆数量失败: {e}")
            return 0
            
    def _cleanup_old_episodes(self):
        """
        清理策略（按优先级）：
        1. 删除 30 天前的 outcome=neutral 记录
        2. 删除重复度 >90% 的相似记录（保留最新）
        3. 如仍超限，删除最旧的 negative 记录
        4. 永不删除 positive 记录（但可降低检索权重）
        """
        if not self.episodes_store:
            return
            
        try:
            now = time.time()
            ttl_cutoff = now - (self.EPISODE_CONFIG["neutral_ttl_days"] * 86400)
            
            # 1. 清理过期 neutral
            self.episodes_store.delete(
                where={"$and": [
                    {"outcome": "neutral"},
                    {"timestamp": {"$lt": ttl_cutoff}}
                ]}
            )
            
            # 2. 去重（保留最新）
            self._deduplicate_similar_episodes()
            
            # 3. 控制总量
            current_count = self._get_episode_count()
            if current_count > self.EPISODE_CONFIG["max_count"]:
                excess = current_count - self.EPISODE_CONFIG["max_count"]
                self._delete_oldest_by_outcome("negative", limit=excess)
                
        except Exception as e:
            print(f"[ERROR] 清理情景记忆失败: {e}")
            
    def _deduplicate_similar_episodes(self):
        """去重相似的情景记忆，保留最新的"""
        # 简化实现：暂时不实现复杂的去重逻辑
        pass
        
    def _get_episode_count(self) -> int:
        """获取情景记忆数量"""
        try:
            return len(self.episodes_store.get()["documents"])
        except:
            return 0
            
    def _delete_oldest_by_outcome(self, outcome: str, limit: int):
        """删除最旧的特定结果的情景记忆"""
        try:
            all_episodes = self.episodes_store.get(where={"outcome": outcome})
            docs = all_episodes.get("documents", [])
            metas = all_episodes.get("metadatas", [])
            ids = all_episodes.get("ids", [])
            
            # 按时间戳排序，最旧的在前
            sorted_episodes = sorted(
                zip(ids, docs, metas),
                key=lambda x: x[2].get("timestamp", 0)
            )
            
            # 删除前 limit 个
            delete_ids = [ep[0] for ep in sorted_episodes[:limit]]
            if delete_ids:
                self.episodes_store.delete(ids=delete_ids)
                print(f"已删除 {len(delete_ids)} 条旧的 {outcome} 情景记忆")
                
        except Exception as e:
            print(f"[ERROR] 删除旧情景记忆失败: {e}")
            
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
        
        # 3. 获取 Profile 摘要
        profile = self.load_profile()
        profile_context = self._format_profile_as_context(profile)
        
        # 4. 获取相似情景记忆（Few-shot）
        similar_episodes = self.retrieve_similar_episodes(user_input, k=2)
        few_shot_examples = self._format_episodes_as_examples(similar_episodes)

        # 5. 合并结果
        memory_context = {
            "search_query": search_query,
            "profile_summary": profile_context,
            "detailed_memories": [doc.page_content for doc in user_memories],
            "action_patterns": [doc.page_content for doc in action_patterns],
            "few_shot_examples": few_shot_examples,
            "retrieved_at": time.time()
        }

        print(f"记忆上下文: 用户记忆 {len(user_memories)} 条, 动作模式 {len(action_patterns)} 个, 情景示例 {len(similar_episodes)} 个")

        return memory_context
        
    def _format_profile_as_context(self, profile: "UserProfile") -> str:
        """格式化用户画像作为上下文"""
        parts = []
        
        # 基础信息
        if profile.name:
            parts.append(f"用户姓名: {profile.name}")
        if profile.home_city:
            parts.append(f"常住地: {profile.home_city}")
        if profile.occupation:
            parts.append(f"职业: {profile.occupation}")
            
        # 核心偏好
        if profile.core_preferences:
            parts.append("核心偏好: " + "; ".join(profile.core_preferences))
            
        # 分类偏好摘要
        for category, preferences in profile.preference_summary.items():
            if preferences:
                category_name = {
                    "food": "饮食",
                    "music": "音乐",
                    "activity": "活动",
                    "habit": "习惯",
                    "work": "工作"
                }.get(category, category)
                
                parts.append(f"{category_name}偏好: " + "; ".join(preferences))
                
        return "\n".join(parts) if parts else "暂无用户画像信息"
        
    def _format_episodes_as_examples(self, episodes: List[Dict]) -> str:
        """格式化情景记忆作为 Few-shot 示例"""
        examples = []
        
        for episode in episodes:
            try:
                content = episode["content"]
                # 简单格式化
                examples.append(content)
            except:
                continue
                
        return "\n\n".join(examples) if examples else ""
    
    # ==========================================
    # Reflection Job 辅助方法 (Phase 2)
    # ==========================================
    
    def get_recent_memories(self, limit: int = 50, since_timestamp: Optional[float] = None) -> List[Dict]:
        """
        获取最近 N 条记忆，用于 Reflection Job
        
        Args:
            limit: 返回的最大记忆数
            since_timestamp: 只返回该时间戳之后的记忆（可选）
        
        Returns:
            记忆列表，每条包含 content, timestamp, date, category
        """
        if not self.user_memory_store:
            return []
        
        try:
            all_memories = self.user_memory_store.get()
            docs = all_memories.get("documents", [])
            metas = all_memories.get("metadatas", [])
            
            # 组合并按时间排序
            memories = []
            for doc, meta in zip(docs, metas):
                timestamp = meta.get("timestamp", 0)
                
                # 如果指定了 since_timestamp，过滤旧记忆
                if since_timestamp and timestamp < since_timestamp:
                    continue
                
                memories.append({
                    "content": doc,
                    "timestamp": timestamp,
                    "date": meta.get("date", ""),
                    "category": meta.get("category", ""),
                    "importance": meta.get("importance", 5),
                })
            
            # 按时间戳降序排序（最新的在前）
            memories.sort(key=lambda x: x["timestamp"], reverse=True)
            
            print(f"📚 获取最近记忆: 共 {len(memories)} 条, 返回 {min(limit, len(memories))} 条")
            return memories[:limit]
            
        except Exception as e:
            print(f"[ERROR] 获取最近记忆失败: {e}")
            return []
    
    def _count_memories_since(self, since_timestamp: float) -> int:
        """统计指定时间戳之后的新记忆数量"""
        if not self.user_memory_store:
            return 0
        
        try:
            all_memories = self.user_memory_store.get()
            metas = all_memories.get("metadatas", [])
            
            count = sum(1 for meta in metas if meta.get("timestamp", 0) > since_timestamp)
            return count
            
        except Exception as e:
            print(f"[ERROR] 统计新记忆数量失败: {e}")
            return 0
            
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

# Singleton instance
_memory_manager = None

def get_memory_manager() -> MemoryManager:
    """获取记忆管理器单例，并确保动作库已初始化"""
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = MemoryManager()
        # V1: 首次使用时自动初始化动作库（如果不存在）
        try:
            _memory_manager.initialize_action_library(force_recreate=False)
        except Exception as e:
            print(f"[WARN]  动作库自动初始化失败: {e}")
    return _memory_manager
