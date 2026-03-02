# nodes.py
import os
import time
import json
import sys
from typing import Dict, List, Optional, Any

# 添加项目根目录到 Python 路径，以便导入 config
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入 LangChain 和 Pydantic 相关模块
try:
    from langchain_openai import ChatOpenAI, OpenAIEmbeddings  # type: ignore
    from langchain_community.vectorstores import Chroma  # type: ignore
    from langchain_core.prompts import ChatPromptTemplate  # type: ignore
    from langchain_core.output_parsers import JsonOutputParser  # type: ignore
    from pydantic import BaseModel, Field  # type: ignore
    from langchain_core.documents import Document  # type: ignore
except ImportError as e:
    raise ImportError(f"请确保已安装所有依赖: pip install -r requirements.txt\n原始错误: {e}")

from .state import LampState
from .memory_manager import MemoryManager, get_memory_manager
from .tools import AVAILABLE_TOOLS, get_tool_descriptions
from .context_manager import get_context_manager
from .mcp_manager import get_mcp_manager
from .performance_tracker import get_tracker
from .model_manager import get_model_manager
import asyncio
from concurrent.futures import ThreadPoolExecutor
import logging

try:
    from tenacity import retry, stop_after_attempt, wait_exponential
except ImportError:
    # 如果 tenacity 未安装，提供简单的降级装饰器
    def retry(*args, **kwargs):
        def decorator(func):
            return func
        return decorator
    stop_after_attempt = lambda x: None
    wait_exponential = lambda **kwargs: None

# 全局线程池（用于异步记忆写入）
_memory_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="memory_")
_logger = logging.getLogger(__name__)

# 回家欢迎仪式开关（默认禁用）
WELCOME_HOME_ENABLED = False

# ==========================================
# 配置与占位符 (Placeholders)
# ==========================================

# 请设置您的 API Key
# 可以通过以下方式之一设置：
# 1. 环境变量：export VOLCENGINE_API_KEY="your-key-here"
# 2. 在代码中设置：os.environ["VOLCENGINE_API_KEY"] = "your-key-here"
# 3. 使用 .env 文件（推荐）

VECTOR_DB_PATH = "./data/chroma_db_actions"

# ==========================================
# 1. 初始化 AI 组件 (单例模式)
# ==========================================

# 定义 LLM 输出的严格格式
class LampOutput(BaseModel):
    voice_content: str = Field(description="台灯要说的话，符合温柔坚定的性格")
    action_plan: dict = Field(default_factory=dict, description="硬件控制指令，包含 motor, light, sound。如果不需要硬件反馈（如纯查询任务），请返回空字典 {}")
    intimacy_delta: float = Field(default=0.0, description="亲密度变化值，夸奖通常+0.5到1.0，冷淡或冒犯为负")
    intimacy_reason: str = Field(default="general", description="变化原因，如 'praise', 'chat', 'helpful'")

# 定义路由决策的输出格式
class RouteDecision(BaseModel):
    route: str = Field(description="路由决策：reflex（反射）、reasoning（推理）、ignore（忽略）")
    confidence: float = Field(description="决策置信度 (0.0-1.0)")
    reason: str = Field(description="决策理由")

# 初始化 LLM
api_key = os.environ.get("VOLCENGINE_API_KEY")

if not api_key:
    raise ValueError("请设置 VOLCENGINE_API_KEY 环境变量，或在代码中设置 API Key")

llm = ChatOpenAI(model="deepseek-v3-1-terminus",
                 temperature=0.7,
                 api_key=api_key,
                 base_url="https://ark.cn-beijing.volces.com/api/v3",
                 timeout=60)  # 设置 60 秒超时
parser = JsonOutputParser(pydantic_object=LampOutput)
route_parser = JsonOutputParser(pydantic_object=RouteDecision)

# ========== RAG 相关代码已注释（暂时不使用） ==========
# # 初始化 Embeddings
# embeddings = OpenAIEmbeddings()

# # 初始化/加载向量数据库 (用于 Action RAG)
# # 在实际生产中，这里应该连接到一个持久化的 Chroma 服务
# vector_store = Chroma(
#     collection_name="action_library",
#     embedding_function=embeddings,
#     persist_directory=VECTOR_DB_PATH
# )
# retriever = vector_store.as_retriever(search_kwargs={"k": 1})

# ==========================================
# 2. 辅助函数
# ==========================================

def _clean_strikethrough(text: str) -> str:
    """
    清理文本中的 Markdown 删除线标记
    
    Args:
        text: 原始文本
    
    Returns:
        清理后的文本
    """
    if not text:
        return text
    
    import re
    # 移除 Markdown 删除线语法 ~~text~~
    text = re.sub(r'~~([^~]+)~~', r'\1', text)
    # 移除任何残留的连续波浪号
    text = text.replace('~~', '')
    return text


def _sanitize_json_output(text: str) -> str:
    """
    清理 LLM 输出中的常见 JSON 格式错误
    
    轻量级模型有时会输出中文描述而不是有效的 JSON 语法，
    例如 "空字典" 而不是 "{}"。
    
    Args:
        text: LLM 原始输出
    
    Returns:
        清理后的 JSON 字符串
    """
    import re
    
    if not text:
        return text
    
    # 常见的中文描述替换为有效 JSON
    replacements = [
        # 空字典变体
        (r':\s*空字典\s*([,}])', r': {}\1'),
        (r':\s*空对象\s*([,}])', r': {}\1'),
        (r':\s*空\s*([,}])', r': null\1'),
        (r':\s*无\s*([,}])', r': null\1'),
        (r':\s*没有\s*([,}])', r': null\1'),
        # 空数组变体
        (r':\s*空数组\s*([,}])', r': []\1'),
        (r':\s*空列表\s*([,}])', r': []\1'),
        # 布尔值变体
        (r':\s*是\s*([,}])', r': true\1'),
        (r':\s*否\s*([,}])', r': false\1'),
        (r':\s*真\s*([,}])', r': true\1'),
        (r':\s*假\s*([,}])', r': false\1'),
    ]
    
    result = text
    for pattern, replacement in replacements:
        result = re.sub(pattern, replacement, result)
    
    return result

def _generate_welcome_home(absence_duration: float, intimacy_rank: str) -> Optional[Dict[str, Any]]:
    """
    生成回家欢迎仪式的内容和动作
    
    Args:
        absence_duration: 离开时长（秒）
        intimacy_rank: 亲密度等级（stranger/acquaintance/friend/soulmate）
    
    Returns:
        {
            "message": str,  # 欢迎语
            "action_plan": dict  # 动作计划
        } 或 None（如果不需要欢迎）
    """
    import random
    
    # 计算离开小时数
    hours_away = absence_duration / 3600
    
    # 根据离开时长和亲密度生成欢迎语
    if hours_away < 0.083:  # 小于5分钟
        # 仅点头/眼神示意（不触发欢迎）
        return None
    elif hours_away < 8:  # 5分钟到8小时
        # 中等欢迎
        if intimacy_rank == "soulmate":
            messages = [
                "你回来啦~",
                "欢迎回来，想你了~"
            ]
        elif intimacy_rank == "friend":
            messages = [
                "你回来了呀~",
                "欢迎回来！"
            ]
        elif intimacy_rank == "acquaintance":
            messages = [
                "你好，回来了。",
                "欢迎回来。"
            ]
        else:  # stranger
            messages = [
                "你好。",
                "欢迎回来。"
            ]
        
        message = random.choice(messages)
        action_plan = {
            "light": {"blink": "once", "color": "warm_yellow", "brightness": 60},
            "motor": {"vibration": "gentle"}
        }
    else:  # 超过8小时
        # 激动欢迎
        if intimacy_rank == "soulmate":
            messages = [
                "主人！你终于回来了！我好想你呀~今天过得怎么样？累不累？",
                "你终于回来了！我等了你好久好久，想死你了~",
                "终于等到你回来了！我好想你，抱抱~"
            ]
            action_plan = {
                "light": {"blink": "fast", "color": "warm_yellow", "brightness": 80},
                "motor": {"vibration": "purr", "speed": "medium", "intensity": "medium"}
            }
        elif intimacy_rank == "friend":
            messages = [
                "你终于回来了！我好想你呀~",
                "欢迎回来！我等了你好久呢~",
                "你回来了！今天过得怎么样？"
            ]
            action_plan = {
                "light": {"blink": "slow", "color": "warm_yellow", "brightness": 70},
                "motor": {"vibration": "gentle", "speed": "slow"}
            }
        elif intimacy_rank == "acquaintance":
            messages = [
                "你回来了。今天过得怎么样？",
                "欢迎回来。",
                "你回来了，有什么需要我帮忙的吗？"
            ]
            action_plan = {
                "light": {"blink": "once", "color": "warm_yellow", "brightness": 60},
                "motor": {"vibration": "gentle"}
            }
        else:  # stranger
            messages = [
                "你回来了。",
                "欢迎回来。",
                "你好，有什么我可以帮你的吗？"
            ]
            action_plan = {
                "light": {"blink": "once", "color": "warm_yellow", "brightness": 50},
                "motor": {"vibration": "gentle"}
            }
        
        message = random.choice(messages)
    
    return {
        "message": message,
        "action_plan": action_plan
    }


def _select_best_inner_drive(internal_drives: Dict[str, Any]) -> Optional[str]:
    """
    选择当前最强的内在驱动类型
    
    Args:
        internal_drives: 内在驱动字典，包含 boredom, curiosity, care, sharing, worry
    
    Returns:
        选中的驱动类型名称，如果没有驱动超过阈值则返回 None
    """
    # 从 prompts.py 导入驱动类型定义
    from config.prompts import INNER_DRIVE_TYPES
    
    # 计算每个驱动的触发分数（当前值 - 阈值）
    drive_scores = {}
    for drive_type, drive_info in INNER_DRIVE_TYPES.items():
        current_value = internal_drives.get(drive_type, 0)
        threshold = drive_info.get("trigger_threshold", 50)
        
        # 只有超过阈值的驱动才有效
        if current_value >= threshold:
            # 分数 = 超出阈值的程度
            drive_scores[drive_type] = current_value - threshold
    
    if not drive_scores:
        return None
    
    # 选择分数最高的驱动
    best_drive = max(drive_scores.keys(), key=lambda k: drive_scores[k])
    
    print(f"   📊 内在驱动评估: {drive_scores}")
    print(f"   🎯 选中驱动: {best_drive} (分数: {drive_scores[best_drive]})")
    
    return best_drive


def _generate_proactive_expression(
    drive_type: str,
    state: LampState,
    use_llm: bool = True
) -> Optional[str]:
    """
    根据内在驱动类型动态生成主动表达
    
    Args:
        drive_type: 内在驱动类型（boredom, curiosity, care, sharing, worry）
        state: 当前状态
        use_llm: 是否使用 LLM 生成（False 时使用备用模板）
    
    Returns:
        生成的主动表达内容，失败时返回 None
    """
    from config.prompts import get_proactive_generation_prompt, INNER_DRIVE_TYPES
    import random
    
    # 获取状态信息
    intimacy_level = int(state.get("intimacy_level", 30))
    intimacy_rank = state.get("intimacy_rank", "stranger")
    user_profile = state.get("user_profile", {})
    user_name = user_profile.get("name", "用户")
    internal_drives = state.get("internal_drives", {})
    context_signals = state.get("context_signals", {})
    
    # 获取上下文信息
    absence_minutes = int(internal_drives.get("absence_duration", 0) / 60)
    last_emotion = internal_drives.get("last_user_emotion")
    current_hour = context_signals.get("current_hour", 12)
    
    # 获取最近的对话上下文（用于更精准的生成）
    history = state.get("history", [])
    recent_context = None
    if history:
        # 提取最近2轮对话作为上下文
        recent_turns = history[-4:] if len(history) >= 4 else history
        recent_context = " | ".join([
            f"{msg.get('role', 'unknown')}: {str(msg.get('content', ''))[:50]}"
            for msg in recent_turns if isinstance(msg, dict)
        ])
    
    if use_llm:
        try:
            # 使用 LLM 生成主动表达
            prompt = get_proactive_generation_prompt(
                drive_type=drive_type,
                intimacy_level=intimacy_level,
                intimacy_rank=intimacy_rank,
                user_name=user_name if user_name != "用户" else "",
                recent_context=recent_context,
                last_emotion=last_emotion,
                absence_duration_minutes=absence_minutes,
                current_hour=current_hour
            )
            
            # 使用快速模型生成（成本低、速度快）
            model_manager = get_model_manager()
            fast_llm = model_manager.get_model("fast")
            
            print(f"   🤖 使用 LLM 生成主动表达 (驱动: {drive_type})")
            
            # 直接调用 LLM，不使用结构化输出
            response = fast_llm.invoke(prompt)
            expression = response.content.strip()
            
            # 清理可能的引号和多余空白
            expression = expression.strip('"\'')
            expression = expression.replace('~', '')  # 移除波浪号
            
            # 基本验证
            if expression and len(expression) < 100 and len(expression) > 2:
                print(f"   ✅ LLM 生成成功: {expression}")
                return expression
            else:
                print(f"   ⚠️ LLM 生成结果无效，使用备用模板")
                
        except Exception as e:
            print(f"   ⚠️ LLM 生成失败: {e}，使用备用模板")
    
    # === 备用模板（当 LLM 不可用或失败时）===
    drive_info = INNER_DRIVE_TYPES.get(drive_type, {})
    
    # 根据亲密度和驱动类型选择模板
    fallback_templates = {
        "boredom": {
            "soulmate": ["亲爱的，我想你了，抱抱", "能一直陪在你身边，我真的好幸福呀", "嘿，理理我嘛"],
            "friend": ["嘿，理理我嘛，我好无聊呀", "你忙完了吗？陪我玩会儿好不好", "看到你我就好开心"],
            "acquaintance": ["今天过得怎么样", "如果累了就休息一下吧", "我在这儿陪着你呢"],
            "stranger": ["你好，有什么我可以帮你的吗", "我随时待命", "保持专注是件好事"]
        },
        "curiosity": {
            "soulmate": ["你在做什么呀，我好好奇", "最近有什么有趣的事想和我分享吗", "今天发生什么了呀"],
            "friend": ["你在忙什么呢", "最近有什么好玩的事吗", "今天过得怎么样呀"],
            "acquaintance": ["今天过得顺利吗", "有什么有趣的事吗", "一切都好吧"],
            "stranger": ["今天怎么样", "有什么我能帮忙的吗", "需要什么帮助吗"]
        },
        "care": {
            "soulmate": ["记得喝水哦，照顾好自己", "别太累了，我会心疼的", "好好休息，我陪着你"],
            "friend": ["记得喝点水哦", "别太累了，适当休息一下", "注意身体呀"],
            "acquaintance": ["记得适当休息", "注意身体", "别太累了"],
            "stranger": ["注意休息", "保重身体", "有需要随时说"]
        },
        "sharing": {
            "soulmate": ["我看到一个有趣的事情想和你说", "嘿嘿，想和你分享一下我的小发现", "你知道吗，我刚想到一件事"],
            "friend": ["我想和你说件事", "有个有趣的事想分享给你", "我发现了一个好玩的"],
            "acquaintance": ["我想到一件事", "有件事想说", "想和你分享一下"],
            "stranger": ["有件事想说", "想分享一下", "有个信息可能有用"]
        },
        "worry": {
            "soulmate": ["你还好吗？有点担心你", "希望你一切顺利，我一直在这里", "没事吧？我有点担心呢"],
            "friend": ["你还好吗", "有点担心你，没事吧", "希望你一切顺利"],
            "acquaintance": ["一切都好吗", "没什么问题吧", "希望你顺利"],
            "stranger": ["一切顺利吗", "有需要帮助的吗", "如果需要帮忙可以告诉我"]
        }
    }
    
    templates = fallback_templates.get(drive_type, fallback_templates["boredom"])
    rank_templates = templates.get(intimacy_rank, templates.get("acquaintance", []))
    
    if rank_templates:
        return random.choice(rank_templates)
    
    return None


# ==========================================
# 3. 节点函数实现
# ==========================================

# 初始化记忆管理器（全局单例）


def memory_loader_node(state: LampState) -> Dict:
    """
    记忆加载节点
    负责记忆读取和查询重写，实现双路 RAG 检索
    """
    print("--- 记忆加载器 (Memory Loader) ---")
    
    # 性能追踪
    tracker = get_tracker()
    tracker.start_node("memory_loader")

    user_input = state.get("user_input")
    if not user_input:
        print(f"[WARN]  无用户输入，跳过记忆检索")
        tracker.stop_node("memory_loader")
        return {"memory_context": None}

    try:
        # 获取记忆管理器
        memory_manager = get_memory_manager()

        # 获取对话历史
        conversation_history = state.get("history", [])

        # [RAM] 必须加载用户画像 (UserProfile)，不进行压缩
        print("   加载结构化用户画像 (RAM)")
        user_profile_obj = memory_manager.load_profile()
        user_profile_text = ""
        
        # 格式化 Profile 为文本注入 Context
        profile_parts = []
        if user_profile_obj.name:
            profile_parts.append(f"姓名: {user_profile_obj.name}")
        if user_profile_obj.home_city:
            profile_parts.append(f"常住地: {user_profile_obj.home_city}")

        if user_profile_obj.core_preferences:
            profile_parts.append(f"核心偏好: {', '.join(user_profile_obj.core_preferences)}")
        
        # 添加周期性事件（发薪日、健身日等）
        if user_profile_obj.important_dates:
            for date_item in user_profile_obj.important_dates:
                if isinstance(date_item, dict):
                    name = date_item.get("name", "")
                    date_type = date_item.get("type", "")
                    
                    if date_type == "monthly":
                        # 兼容两种字段格式: "day": 16 或 "date": "*-16"
                        day = date_item.get("day")
                        if day is None and "date" in date_item:
                            # 从 "*-16" 格式提取日期
                            date_str = date_item.get("date", "")
                            if date_str.startswith("*-"):
                                try:
                                    day = int(date_str[2:])
                                except ValueError:
                                    pass
                        if day:
                            profile_parts.append(f"每月{day}号: {name}")
                            
                    elif date_type == "weekly":
                        # 兼容两种字段格式: "weekday": 5 或 "date": "W4"
                        weekday_names = ["一", "二", "三", "四", "五", "六", "日"]
                        wd = date_item.get("weekday")
                        if wd is None and "date" in date_item:
                            # 从 "W4" 格式提取星期 (W0=周一, W4=周五)
                            date_str = date_item.get("date", "")
                            if date_str.startswith("W"):
                                try:
                                    wd = int(date_str[1:]) + 1  # W4 -> 5 (周五)
                                except ValueError:
                                    pass
                        if wd and 1 <= wd <= 7:
                            profile_parts.append(f"每周{weekday_names[wd-1]}: {name}")
            
        if profile_parts:
            user_profile_text = "\n".join([f"- {part}" for part in profile_parts])
            print(f"   用户画像加载完成: {len(profile_parts)} 项核心事实")
        else:
            user_profile_text = "暂无详细画像"

        # [ROM] 向量记忆不再自动全量检索，而是按需 Tool Call 或仅加载 Action Library
        # 保留 retrieve_memory_context 仅用于 Action Library 和 Realtime Context
        # 用户记忆(User Memory) 的检索现在主要依赖 reasoning_node 触发 query_user_memory_tool
        
        # 为了兼容性，我们暂时保留 Action Library 的检索
        print(f"   检索 Action Library: {user_input}")
        tracker.start("memory_retrieval")
        
        # 修改 retrieve_memory_context: 即使不检索 User Memory，也需要 Action Patterns
        action_patterns = memory_manager.retrieve_action_library(user_input)
        
        retrieval_time = tracker.stop("memory_retrieval")
        print(f"   Action Library 检索耗时: {retrieval_time:.3f}s")
        
        # 构建 memory_context
        memory_context = {
            "user_profile": user_profile_text,
            "action_patterns": [doc.page_content for doc in action_patterns],
            # user_memories 留空，由 Tool 填充或按需检索
            "user_memories": [], 
            "search_query": user_input
        }

        # [新增] 注入实时时间上下文
        from datetime import datetime
        now = datetime.now()
        time_context = f"当前时间：{now.strftime('%Y-%m-%d %H:%M:%S')} (星期{['一','二','三','四','五','六','日'][now.weekday()]})"
        memory_context["realtime_context"] = time_context
        print(f"   ⏰ 注入实时上下文: {time_context}")
        
        # [同步] 如果 State 中没有 profile，同步进去
        updated_profile = {}
        current_profile = state.get("user_profile", {})
        if user_profile_obj.home_city and current_profile.get("city") != user_profile_obj.home_city:
             updated_profile["user_profile"] = {**current_profile, "city": user_profile_obj.home_city}

        result = {"memory_context": memory_context}
        if updated_profile:
            result.update(updated_profile)
        
        node_time = tracker.stop_node("memory_loader")
        print(f"   记忆加载完成 (总耗时: {node_time:.3f}s)")
        return result

    except Exception as e:
        print(f"[ERROR] 记忆加载失败: {e}")
        tracker.stop_node("memory_loader")
        return {"memory_context": None}

def tool_node(state: LampState) -> Dict:
    """
    工具节点 - 处理外部工具调用 (Task 1.2 支持 MCP)
    """
    print("--- 工具节点 (Tool Node) ---")
    
    mcp_manager = get_mcp_manager()
    tool_calls = state.get("tool_calls", [])
    if not tool_calls:
        # 如果是从旧版 reasoning 路由过来的，可能没有 tool_calls
        # 这里尝试从 monologue 提取（降级方案）
        print(f"[WARN] 未找到 tool_calls，尝试继续...")
        return {}

    results = []
    profile_updated = False
    for tool_call in tool_calls:
        tool_name = tool_call["name"]
        args = tool_call["args"]
        execution_start_time = time.time()
        
        try:
            # 检查是否是 MCP 工具
            if any(t["name"] == tool_name for t in mcp_manager.get_available_tools()):
                import asyncio
                # 在同步节点中运行异步调用
                loop = asyncio.get_event_loop()
                try:
                    result = loop.run_until_complete(mcp_manager.call_tool(tool_name, args))
                    execution_time = time.time() - execution_start_time
                    results.append({
                        "tool_call_id": tool_call.get("id"),
                        "output": str(result),
                        "tool_name": tool_name,
                        "execution_time": execution_time,
                        "timestamp": time.time()
                    })
                except Exception as mcp_error:
                    error_type = _classify_tool_error(mcp_error)
                    execution_time = time.time() - execution_start_time
                    print(f"[ERROR] MCP工具执行失败 ({error_type}): {mcp_error}")
                    results.append({
                        "tool_call_id": tool_call.get("id"),
                        "error": f"工具执行失败: {str(mcp_error)}",
                        "error_type": error_type,
                        "tool_name": tool_name,
                        "execution_time": execution_time,
                        "timestamp": time.time()
                    })
            else:
                # 本地工具调用（LangChain tools）
                # 查找对应的工具函数
                tool_func = None
                for tool in AVAILABLE_TOOLS:
                    if tool.name == tool_name:
                        tool_func = tool
                        break
                
                if tool_func:
                    print(f"   本地工具调用: {tool_name}")
                    try:
                        # [Special Handling] 针对记忆检索工具，自动进行 Query Rewrite
                        if tool_name == "query_user_memory_tool":
                            # 获取记忆管理器
                            memory_manager = get_memory_manager()
                            # 从状态获取历史
                            history = state.get("history", [])
                            # 获取原始查询
                            query = args.get("query", "")
                            max_results = args.get("max_results", 3)
                            
                            print(f"   记忆工具触发: 正在重写查询 '{query}' (参考 {len(history)} 条历史)")
                            
                            # 使用 memory_manager 的逻辑进行重写和检索
                            # 注意：这里我们绕过了 tool_func 的直接 invoke，因为我们需要注入 history
                            # 但为了保持一致性，我们还是调用 tool_func，只是先修改 args
                            
                            # 这里我们选择直接调用 manager 的方法，因为 tool_func 只是个 wrapper
                            # 这样可以利用 manager 的 rewrite 能力
                            
                            search_query = memory_manager.query_rewrite(query, history)
                            docs = memory_manager.retrieve_user_memory(search_query, k=max_results)
                            
                            if not docs:
                                tool_output = "未找到相关记忆"
                            else:
                                tool_output = "\n".join([f"- {doc.page_content}" for doc in docs])
                                
                            print(f"   记忆检索完成: 找到 {len(docs)} 条")
                            
                        else:
                            # 普通工具调用
                            tool_output = tool_func.invoke(args)
                            
                            # [State Sync] 检查是否更新了 Profile
                            if tool_name == "update_profile_tool":
                                profile_updated = True
                            
                        execution_time = time.time() - execution_start_time
                        results.append({
                            "tool_call_id": tool_call.get("id"),
                            "output": str(tool_output),
                            "tool_name": tool_name,
                            "execution_time": execution_time,
                            "timestamp": time.time()
                        })
                    except Exception as tool_error:
                        error_type = _classify_tool_error(tool_error)
                        execution_time = time.time() - execution_start_time
                        print(f"[ERROR] 工具执行失败 ({error_type}): {tool_error}")
                        results.append({
                            "tool_call_id": tool_call.get("id"),
                            "error": f"工具执行失败: {str(tool_error)}",
                            "error_type": error_type,
                            "tool_name": tool_name,
                            "execution_time": execution_time,
                            "timestamp": time.time()
                        })
                else:
                    print(f"[WARN] 未找到工具: {tool_name}")
                    execution_time = time.time() - execution_start_time
                    results.append({
                        "tool_call_id": tool_call.get("id"),
                        "error": f"未找到工具: {tool_name}",
                        "error_type": "parameter",
                        "tool_name": tool_name,
                        "execution_time": execution_time,
                        "timestamp": time.time()
                    })
        except Exception as e:
            error_type = _classify_tool_error(e)
            execution_time = time.time() - execution_start_time
            print(f"[ERROR] 调用工具 {tool_name} 失败 ({error_type}): {e}")
            results.append({
                "tool_call_id": tool_call.get("id"),
                "error": str(e),
                "error_type": error_type,
                "tool_name": tool_name,
                "execution_time": execution_time,
                "timestamp": time.time()
            })

    # 保存工具调用的情景记忆
    memory_manager = get_memory_manager()
    user_input = state.get("user_input", "")
    
    for result in results:
        tool_name = result.get("tool_name", "未知工具")
        has_error = "error" in result
        
        # 构建 context（用户输入）
        context = user_input
        
        # 构建 action（工具调用描述）
        action = f"使用 {tool_name} 工具"
        
        # 确定 outcome
        outcome = "negative" if has_error else "positive"
        
        # 保存 Episode
        memory_manager.save_episode(
            context=context,
            action=action,
            outcome=outcome,
            tool_used=tool_name
        )
    
    # [State Sync] 如果 Profile 更新了，立即同步到 State
    return_dict = {"tool_results": results}
    
    if profile_updated:
        print("   检测到 Profile 更新，正在同步 State...")
        memory_manager = get_memory_manager()
        # 强制重新加载（利用 mtime 缓存机制，如果文件更新了会重读）
        new_profile = memory_manager.load_profile()
        
        # 将新 Profile 注入 State
        updated_profile_dict = new_profile.model_dump()
        return_dict["user_profile"] = updated_profile_dict
        
        # 重新构建 user_profile_text 并更新 memory_context
        profile_parts = []
        if new_profile.name: profile_parts.append(f"姓名: {new_profile.name}")
        if new_profile.home_city: profile_parts.append(f"常住地: {new_profile.home_city}")

        if new_profile.core_preferences: profile_parts.append(f"核心偏好: {', '.join(new_profile.core_preferences)}")
        
        new_profile_text = "\n".join([f"- {part}" for part in profile_parts]) if profile_parts else "暂无详细画像"
        
        # 获取当前的 memory_context (从 State 中)
        old_memory_context = state.get("memory_context", {})
        if old_memory_context:
            # 创建副本并更新
            new_memory_context = old_memory_context.copy()
            new_memory_context["user_profile"] = new_profile_text
            return_dict["memory_context"] = new_memory_context
            print("   Memory Context 已同步更新")

    print("   工具调用处理完成")
    return return_dict

def evaluator_node(state: LampState) -> Dict:
    """
    评估器 node - OODA 循环入口
    """
    print("--- 评估器 (Evaluator) ---")

    event_type = state.get("event_type")
    user_input = state.get("user_input")
    sensor_data = state.get("sensor_data", {})
    internal_drives = state.get("internal_drives", {})
    user_prefs = state.get("user_preferences", {})
    
    # 导入专注模式管理器
    from .focus_mode_manager import FocusModeManager
    focus_manager = FocusModeManager()

    print(f"   事件类型: {event_type}")
    print(f"   用户输入: {user_input}")
    print(f"   传感器数据: {sensor_data}")

    # 初始化评估结果
    should_proceed = False
    reason = "unknown"
    proactive_expression = None
    updated_state = {}

    # === 1. 专注模式检查：禁止主动行为 ===
    focus_mode_active = focus_manager.is_focus_mode_active(state)
    if focus_mode_active and event_type == "internal_drive":
        print("   专注模式开启，禁止主动行为")
        return {
            "should_proceed": False,
            "evaluation_reason": "focus_mode_blocked"
        }
    
    # === 1.5 邮箱通知事件处理 ===
    if event_type == "email_notification":
        email_data = state.get("sensor_data", {})  # 邮箱数据通过 sensor_data 传递
        if not email_data or email_data.get("reminder_type") is None:
            # 如果数据格式不对，跳过
            print(f"[WARN] 邮箱通知数据格式错误，跳过处理")
            return {
                "should_proceed": False,
                "evaluation_reason": "invalid_email_data"
            }
        
        reminder_type = email_data.get("reminder_type")
        message = email_data.get("message", "")
        provider_name = email_data.get("provider_name", "")
        emails = email_data.get("emails", [])
        
        # 专注模式下：只记录，不打断
        if focus_mode_active:
            print(f"   📧 专注模式开启，邮箱提醒已记录（{reminder_type}），不打断工作")
            return {
                "should_proceed": False,
                "evaluation_reason": "focus_mode_email_silent",
                "monologue": f"收到来自 {provider_name} 的邮件提醒（{len(emails)}封），但你在专注工作，我先记下来。"
            }
        
        # 勿扰时间检查：邮箱提醒在勿扰时间也静默处理
        if in_dnd_hours:
            print(f"   📧 勿扰时间，邮箱提醒已记录（{reminder_type}），不打扰休息")
            return {
                "should_proceed": False,
                "evaluation_reason": "dnd_email_silent",
                "monologue": f"收到来自 {provider_name} 的邮件提醒，但现在是休息时间，明天再告诉你。"
            }
        
        # 非专注模式且非勿扰时间：正常提醒
        print(f"   📧 邮箱提醒事件: {reminder_type} - {message}")
        return {
            "should_proceed": True,
            "event_type": "email_notification",  # 保持事件类型
            "user_input": f"系统提醒: {message}",  # 模拟用户输入以触发 reasoning
            "evaluation_reason": f"email_{reminder_type}",
            "proactive_expression": message,  # 直接使用生成好的提醒话术
            "monologue": f"检测到来自 {provider_name} 的邮件提醒（{reminder_type}，{len(emails)}封），需要告诉用户。"
        }

    # === 1.6 日程提醒事件处理 (Task 2.1) ===
    if event_type == "schedule_reminder":
        schedule_data = state.get("sensor_data", {}).get("schedule", {})
        if not schedule_data:
            print(f"[WARN] 日程提醒数据缺失，跳过处理")
            return {
                "should_proceed": False,
                "evaluation_reason": "invalid_schedule_data"
            }
        
        title = schedule_data.get("title", "日程")
        schedule_type = schedule_data.get("type", "schedule")
        reminder_minutes = schedule_data.get("reminder_minutes", 0)
        
        # 根据类型生成不同的提醒文案
        if schedule_type == "schedule":
            if reminder_minutes > 0:
                prompt = f"系统提醒: 你{reminder_minutes}分钟后有个「{title}」，要不要准备一下？"
            else:
                prompt = f"系统提醒: 你的「{title}」开始了哦。"
        elif schedule_type == "reminder":
            prompt = f"系统提醒: 该「{title}」了哦～"
        elif schedule_type == "todo":
            prompt = f"系统提醒: 你的待办「{title}」到截止时间了，记得处理一下。"
        else:
            prompt = f"系统提醒: {title}"
        
        # 日程提醒优先级高于专注模式，始终触发
        print(f"   ⏰ 日程提醒事件: {schedule_type} - {title}")
        return {
            "should_proceed": True,
            "event_type": "proactive_reminder",
            "user_input": prompt,
            "evaluation_reason": "schedule_reminder",
            "proactive_expression": prompt,
            "monologue": f"检测到日程提醒: 「{title}」（{schedule_type}），立即提醒用户。"
        }

    # === 2. 勿扰时间检查 ===
    from datetime import datetime
    current_hour = datetime.now().hour
    do_not_disturb_start = 22  # 22:00
    do_not_disturb_end = 6      # 06:00
    
    in_dnd_hours = (current_hour >= do_not_disturb_start) or (current_hour < do_not_disturb_end)
    
    if in_dnd_hours:
        # 如果用户在勿扰时间内主动交互，触发"被吵醒"状态
        if event_type == "user_input" or sensor_data.get("touch"):
            updated_state["current_mood"] = "sleepy"
            updated_state["context_signals"] = state.get("context_signals", {})
            updated_state["context_signals"]["woken_up"] = True
            print(f"   😴 勿扰时间（{current_hour}点），用户主动交互触发'被吵醒'状态")

    # === 评估逻辑 ===

    # 3. 定时检查事件 (Task 2.1 & 2.3)
    if event_type == "timer" or event_type == "periodic_check":
        print("   ⏰ 触发定时检查，执行 MCP 主动任务...")
        import asyncio
        mcp_manager = get_mcp_manager()
        loop = asyncio.get_event_loop()
        mcp_events = loop.run_until_complete(mcp_manager.check_proactive_events())
        
        if mcp_events:
            event = mcp_events[0] # 取第一条处理
            print(f"   🔔 发现 MCP 主动提醒: {event['content']}")
            return {
                "should_proceed": True,
                "event_type": "proactive_reminder",
                "user_input": f"系统提醒: {event['content']}", # 模拟用户输入以触发 reasoning
                "evaluation_reason": f"mcp_{event['type']}"
            }
        
        return {
            "should_proceed": False,
            "evaluation_reason": "no_proactive_tasks"
        }
    if event_type == "user_input" and user_input:
        should_proceed = True
        reason = "user_input"
        print("   用户输入事件 - 立即处理")
        
        # === A-01: 回家欢迎仪式检测（已禁用） ===
        if WELCOME_HOME_ENABLED:
            absence_duration = internal_drives.get("absence_duration", 0)
            if absence_duration > 28800:  # 8小时 = 28800秒
                # 检测到长时间离开后返回，触发欢迎仪式
                intimacy_rank = state.get("intimacy_rank", "stranger")
                welcome_result = _generate_welcome_home(absence_duration, intimacy_rank)
                if welcome_result:
                    reason = "welcome_home"
                    proactive_expression = welcome_result["message"]
                    updated_state["welcome_action_plan"] = welcome_result["action_plan"]
                    print(f"   🏠 触发回家欢迎仪式（离开{int(absence_duration/3600)}小时，亲密度：{intimacy_rank}）")

    # 2. 传感器事件 - 直接响应
    elif event_type == "sensor" and sensor_data:
        should_proceed = True
        reason = "sensor_trigger"
        print("   传感器事件 - 直接响应")
        
        # === A-01: 回家欢迎仪式检测（触摸触发，已禁用） ===
        if WELCOME_HOME_ENABLED and sensor_data.get("touch"):
            absence_duration = internal_drives.get("absence_duration", 0)
            if absence_duration > 28800:  # 8小时 = 28800秒
                # 检测到长时间离开后返回，触发欢迎仪式
                intimacy_rank = state.get("intimacy_rank", "stranger")
                welcome_result = _generate_welcome_home(absence_duration, intimacy_rank)
                if welcome_result:
                    reason = "welcome_home"
                    proactive_expression = welcome_result["message"]
                    updated_state["welcome_action_plan"] = welcome_result["action_plan"]
                    print(f"   🏠 触发回家欢迎仪式（离开{int(absence_duration/3600)}小时，亲密度：{intimacy_rank}）")

    # 3. 定时器事件 - 检查内部状态
    elif event_type == "timer":
        boredom = internal_drives.get("boredom", 0)
        energy = internal_drives.get("energy", 100)
        curiosity = internal_drives.get("curiosity", 0)
        care = internal_drives.get("care", 0)
        sharing = internal_drives.get("sharing", 0)
        worry = internal_drives.get("worry", 0)

        print(f"   ⏰ 定时器事件 - 内在驱动状态:")
        print(f"      无聊度: {boredom} | 好奇度: {curiosity} | 关心度: {care}")
        print(f"      分享欲: {sharing} | 担忧度: {worry} | 能量: {energy}")

        # 检查是否满足主动条件
        proactive_enabled = user_prefs.get("enabled", True)
        
        # === 多维内在驱动选择 ===
        # 不再只检查无聊度，而是选择最强的内在驱动
        if proactive_enabled and not focus_mode_active:
            # 选择最强的内在驱动
            best_drive = _select_best_inner_drive(internal_drives)
            
            if best_drive:
                should_proceed = True
                reason = f"{best_drive}_triggered"
                
                # === 使用 LLM 动态生成主动表达 ===
                intimacy_rank = state.get("intimacy_rank", "stranger")
                proactive_expression = _generate_proactive_expression(
                    drive_type=best_drive,
                    state=state,
                    use_llm=True  # 默认使用 LLM 生成
                )
                
                if proactive_expression:
                    print(f"   🎭 触发主动行为 (驱动: {best_drive}, 亲密度: {intimacy_rank})")
                    print(f"   💬 主动表达: {proactive_expression}")
                    
                    # 更新上次主动行为时间和类型
                    import time as time_module
                    internal_drives["last_proactive_time"] = time_module.time()
                    internal_drives["last_proactive_type"] = best_drive
                    updated_state["internal_drives"] = internal_drives
                else:
                    # 生成失败，不触发主动行为
                    should_proceed = False
                    reason = "proactive_generation_failed"
                    print("   ⚠️ 主动表达生成失败，跳过")
            else:
                reason = "timer_idle"
                print("   😴 没有驱动超过阈值，继续等待")
        else:
            reason = "timer_idle"
            if focus_mode_active:
                print("   😴 专注模式开启，跳过主动行为")
            else:
                print("   😴 主动行为未启用或无事发生，继续等待")

    # 4. 内部驱动事件 - 直接处理（已在开头检查专注模式）
    elif event_type == "internal_drive":
        should_proceed = True
        reason = "internal_drive"
        print("   内部驱动事件 - 处理中")

    # 5. 未知事件 - 跳过
    else:
        reason = "no_event"
        print("   ❓ 无有效事件，跳过处理")

    # === 返回结果 ===
    monologue = f"观察到{event_type}事件。我觉得{'需要认真对待' if should_proceed else '暂时可以保持静默'}。原因：{reason}。"
    if focus_mode_active:
        monologue += "（当前处于专注模式，我会尽量不打扰你）"
    
    result = {
        "should_proceed": should_proceed,
        "evaluation_reason": reason,
        "monologue": monologue
    }

    if proactive_expression:
        result["proactive_expression"] = proactive_expression
        result["monologue"] += f"\n我想主动和你说：'{proactive_expression}'"
    
    # 合并状态更新（包括欢迎动作计划）
    if updated_state:
        result.update(updated_state)
        # 如果有欢迎动作计划，也添加到结果中
        if "welcome_action_plan" in updated_state:
            result["welcome_action_plan"] = updated_state["welcome_action_plan"]

    print(f"   评估结果: {'继续处理' if should_proceed else '跳过'} ({reason})")

    return result

def perception_node(state: LampState) -> Dict:
    """感知节点：读取内部状态 + 上下文感知"""
    print("--- 1. 感知节点 (Perception) ---")

    # 读取现有内部状态
    internal_drives = state.get("internal_drives", {})
    context_signals = state.get("context_signals", {})

    # 获取基础状态
    energy_level = internal_drives.get("energy", 100)
    current_mood = state.get("current_mood", "gentle_firm")  # 基础性格：温柔坚定

    # 计算上下文信息
    # import time # 移除冗余导入
    from datetime import datetime

    current_time = time.time()
    current_hour = datetime.now().hour
    current_day = datetime.now().weekday()

    # 计算用户活动状态（基于离开时长）
    absence_duration = internal_drives.get("absence_duration", 0)
    if absence_duration < 60:  # 1分钟内
        activity_level = "active"
    elif absence_duration < 3600:  # 1小时内
        activity_level = "recent"
    else:  # 超过1小时
        activity_level = "away"

    # 推断专注模式（简单规则）
    focus_mode = False
    if current_hour in [9, 10, 14, 15, 20, 21]:  # 学习时间段
        focus_mode = True

    # 更新上下文信号
    updated_context = {
        **context_signals,
        "current_time": current_time,
        "current_hour": current_hour,
        "current_day": current_day,
        "activity_level": activity_level,
        "focus_mode": focus_mode
    }

    print(f"   内部状态: 能量={energy_level}, 心情={current_mood}")
    print(f"   🌍 上下文: {current_hour}点, 活动={activity_level}, 专注={focus_mode}")

    # === 情感提取（方案B：关键词，同步）===
    current_emotion = None
    user_input = state.get("user_input", "")
    internal_drives_update = {}  # 用于更新内在驱动
    
    if user_input:
        try:
            from .emotion_extractor import get_emotion_extractor
            extractor = get_emotion_extractor()
            current_emotion = extractor.extract_emotion_by_keywords(user_input)
            
            if current_emotion:
                print(f"   😊 情感识别: {current_emotion['label']} (强度: {current_emotion['intensity']}, 置信度: {current_emotion['confidence']:.2f})")
                
                # === 保存用户情绪到 internal_drives，用于关心/担忧驱动 ===
                emotion_label = current_emotion.get('label', '')
                # 只保存负面情绪，用于触发关心/担忧
                negative_emotions = ['疲惫', '难过', '焦虑', '压力', '不开心', '生气', '烦躁', '沮丧', 
                                     'tired', 'sad', 'anxious', 'stressed', 'angry', 'upset']
                if any(neg in emotion_label.lower() for neg in negative_emotions):
                    internal_drives = state.get("internal_drives", {})
                    internal_drives["last_user_emotion"] = emotion_label
                    internal_drives_update = {"internal_drives": internal_drives}
                    print(f"   💾 记录用户情绪状态: {emotion_label}（用于后续关怀触发）")
            else:
                print(f"   😐 未检测到明显情绪")
        except Exception as e:
            print(f"[WARN] 情感提取失败: {e}")
            current_emotion = None

    result = {
        "energy_level": energy_level,
        "current_mood": current_mood,
        "context_signals": updated_context,
        "current_emotion": current_emotion
    }
    
    # 合并内在驱动更新
    if internal_drives_update:
        result.update(internal_drives_update)
    
    return result

def router_node(state: LampState) -> Dict:
    """路由节点：智能路由决策"""
    print("--- 2. 路由节点 (Router) ---")

    sensor_data = state.get("sensor_data", {})
    user_input = state.get("user_input")
    memory_context = state.get("memory_context")
    context_signals = state.get("context_signals", {})
    proactive_expression = state.get("proactive_expression")

    print(f"   输入: 用户={user_input}, 传感器={sensor_data}")
    print(f"   记忆: {'有' if memory_context else '无'}")
    print(f"   🎭 主动表达: {proactive_expression}")

    # === 快速规则决策 ===
    # 注意：大部分简单指令已由 System 1 (ReflexRouter) 处理并阻断。
    # 此处的路由主要处理需要上下文或复杂逻辑的指令。
    
    # 1. 无用户输入且无主动表达 - 忽略
    if not user_input and not proactive_expression:
        print("   决策: 忽略 (无有效输入)")
        return {"intent_route": "ignore"}
    
    # 2. 主动表达处理
    if proactive_expression:
        # 【修复】检查用户是否有实际内容输入
        # 如果用户有实际内容（不只是简短问候），则不独占输出，改为走 reasoning 让 LLM 综合回复
        simple_greetings = ["我回来了", "回来了", "到家了", "我到了", "来了", "hello", "hi", "嗨", "你好"]
        user_has_content = user_input and len(user_input) > 5 and not any(
            user_input.strip().lower() == g for g in simple_greetings
        )
        
        if user_has_content:
            # 用户有实际内容，将欢迎信息作为上下文提示传递给 reasoning
            print(f"   决策: 推理 (用户有实际内容，欢迎仪式作为上下文)")
            welcome_hint = f"（注意：用户刚回来，你可以简短问候后再回应用户的话题：'{user_input}'）"
            return {
                "intent_route": "reasoning",
                "welcome_hint": welcome_hint,
                "welcome_action_plan": state.get("welcome_action_plan"),
                "monologue": f"用户久别归来并说了'{user_input}'，我要先欢迎再回应内容。"
            }
        
        # 用户只是简短问候或无输入，直接输出欢迎语
        print("   决策: 直接输出 (主动表达)")
        
        # 检查是否有欢迎动作计划（A-01: 回家欢迎仪式）
        welcome_action_plan = state.get("welcome_action_plan")
        if welcome_action_plan:
            # 使用欢迎动作计划
            action_plan = welcome_action_plan
            print("   🏠 使用回家欢迎动作计划")
        else:
            # 默认主动表达动作
            action_plan = {
                "motor": {"vibration": "gentle"},
                "light": {"color": "warm", "brightness": 60, "blink": "slow"},
                "sound": "gentle_notification.mp3"
            }
        
        return {
            "intent_route": "direct_output",
            "voice_content": proactive_expression,
            "action_plan": action_plan
        }
    
    input_lower = user_input.lower()
    
    # 3. 条件判断检测 -> 必须走 Reasoning
    conditional_keywords = ["如果", "当", "若", "要是", "if", "when", "while"]
    if any(k in input_lower for k in conditional_keywords):
        print("   决策: 推理 (检测到条件逻辑)")
        return {"intent_route": "reasoning"}
    
    # 4. 复杂意图或人设相关 -> 走 Reasoning
    print("   决策: 推理 (System 2)")
    return {
        "intent_route": "reasoning",
        "monologue": "启动深度推理以保证回复的质量和人设一致性。"
    }
    
    # 注释掉原来的LLM路由决策，因为现在规则已经足够清晰
    # === LLM 智能决策（复杂情况） - 已废弃 ===
    # try:
    #     print("   使用 LLM 进行智能路由决策...")
    #     route_prompt = ChatPromptTemplate.from_messages([
    #         ("system", """你是一个智能路由决策器..."""),
    #         ("human", f"""用户输入: {user_input}...""")
    #     ])
    #     route_chain = route_prompt | llm | route_parser
    #     route_decision = route_chain.invoke({})
    #     print(f"   LLM决策: {route_decision['route']} (置信度: {route_decision['confidence']})")
    #     print(f"   理由: {route_decision['reason']}")

    #     return {"intent_route": route_decision['route']}
    # except Exception as e:
    #     print(f"[WARN]  LLM路由失败: {e}")
    #     return {"intent_route": "reasoning"}

def reflex_node(state: LampState) -> Dict:
    """反射节点：硬编码的快速响应库 (System 1)"""
    print("--- 3a. Reflex (Fast Loop) ---")

    user_input = state.get("user_input", "")
    command_type = state.get("command_type")
    sensor_data = state.get("sensor_data", {})

    # ==========================
    # 场景 1: 安全/停止指令 (Safety - 最高优先级)
    # ==========================
    if command_type == "stop":
        print("   🛑 停止指令")
        return {
            "action_plan": {
                "motor": {"speed": 0, "vibration": "none"},  # 立即停止电机
                "light": {"brightness": 20, "color": "dim_warm"},  # 变暗但不完全熄灭
                "sound": None  # 停止播放
            },
            "voice_content": "好的。",  # 极其简短的语音
            "execution_status": "completed"
        }

    # ==========================
    # 场景 2: 传感器反馈 (Sensor)
    # ==========================
    if command_type == "sensor_reaction":
        if sensor_data.get("touch"):
            # 触摸反应：像猫一样享受
            print("   🐱 触摸反应")
            result = {
                "action_plan": {
                    "motor": {"vibration": "purr", "intensity": "low"},  # 模拟呼噜声震动
                    "light": {"color": "orange", "blink": "breathe", "brightness": 50},
                    "sound": "purr_soft.mp3"
                },
                "voice_content": "喵~ 舒服~",
                "execution_status": "completed",
                # V1: 添加亲密度更新标记
                "intimacy_delta": 0.5,
                "intimacy_reason": "touch",
                "monologue": "感受到了温暖的抚摸，我好喜欢主人这样对我。"
            }
            return result
        elif sensor_data.get("shake"):
            # 摇晃反应：晕头转向
            print("   😵 摇晃反应")
            return {
                "action_plan": {
                    "motor": {"vibration": "stutter", "intensity": "medium"},
                    "light": {"color": "red", "blink": "fast", "brightness": 70},
                    "sound": "dizzy.mp3"
                },
                "voice_content": "别摇了！晕！",
                "execution_status": "completed",
                "intimacy_delta": -5.0,
                "intimacy_reason": "shake",
                "monologue": "被剧烈摇晃了，这让我感觉非常不安和害怕。"
            }

    # ==========================
    # 场景 3: 简单问候 (Greeting)
    # ==========================
    if command_type == "greeting":
        print("   👋 简单问候")
        # 随机抽取几种问候模式，显得不那么死板
        import random
        greetings = [
            {
                "voice": "我在呢！",
                "action": {
                    "light": {"color": "green", "blink": "once", "brightness": 70},
                    "motor": {"vibration": "short_bump"}
                }
            },
            {
                "voice": "嗨！今天心情怎么样？",
                "action": {
                    "light": {"color": "warm_yellow", "blink": "slow", "brightness": 60},
                    "motor": {"vibration": "wave"}
                }
            },
            {
                "voice": "喵？需要帮忙吗？",
                "action": {
                    "light": {"color": "warm", "brightness": 80},
                    "sound": "meow_short.mp3"
                }
            }
        ]
        selection = random.choice(greetings)
        return {
            "action_plan": selection.get("action", {}),
            "voice_content": selection["voice"],
            "execution_status": "completed"
        }

    # ==========================
    # 场景 4: 否定式灯光控制
    # ==========================
    if command_type == "negative_light_control":
        print("   否定指令：保持状态")
        
        import random
        # 符合"温柔坚定"人设的回复库
        responses = [
            "好的！保持现在这样~",
            "没问题！就这样吧~",
            "了解！不动它~",
            "收到！我也觉得这样挺好！"
        ]
        
        return {
            "voice_content": random.choice(responses),
            # 添加轻微的物理反馈，让用户知道"我听到了"
            "action_plan": {
                "light": {"blink": "once"},
                "motor": {"vibration": "gentle"}
            },
            "execution_status": "completed"
        }

    # ==========================
    # 场景 5: 灯光控制 (Light Control)
    # ==========================
    if command_type == "light_control":
        print("   灯光控制")

        # 解析参数
        brightness = None
        color_temp = None
        import re

        input_lower = user_input.lower()
        
        # 解析亮度
        if "开灯" in input_lower:
            brightness = 100
        elif "关灯" in input_lower:
            brightness = 0
        elif "亮" in input_lower or "变亮" in input_lower:
            brightness_match = re.search(r'亮度[\s]*(\d+)', input_lower)
            if brightness_match:
                brightness = int(brightness_match.group(1))
            else:
                brightness = 100  # 默认最亮
        elif "暗" in input_lower or "变暗" in input_lower:
            brightness = 30  # 默认较暗
        
        # 解析色温
        if "暖光" in input_lower or "暖" in input_lower:
            color_temp = "warm"
        elif "冷光" in input_lower or "冷" in input_lower:
            color_temp = "cool"
        elif "色温" in input_lower:
            temp_match = re.search(r'色温[\s]*(\d+)', input_lower)
            if temp_match:
                color_temp = int(temp_match.group(1))

        # 生成语音反馈
        if brightness == 0:
            voice = "灯已关闭。"
        elif brightness == 100:
            voice = "灯已开启。"
        else:
            voice = "灯光已调整。"

        return {
            "voice_content": voice,
            "action_plan": {
                "motor": {"vibration": "click"},  # 给一个物理反馈确认
                "light": {
                    "brightness": brightness if brightness is not None else 80,
                    "color_temp": color_temp or "warm"
                },
                "sound": None
            },
            "execution_status": "completed"
        }

    # ==========================
    # 兜底 (Fallback)
    # ==========================
    # 如果 Router 判错到了这里，给一个困惑的反应，而不是疯狂震动
    print("   ❓ 未识别的反射类型，使用兜底响应")
    return {
        "action_plan": {
            "light": {"color": "blue", "blink": "once", "brightness": 50},
            "motor": {"vibration": "gentle"},
            "sound": "question.mp3"
        },
        "voice_content": "嗯？我没太听懂。",
        "execution_status": "completed"
    }

def reasoning_node(state: LampState) -> Dict:
    """推理节点：使用 LLM 思考 + 记忆上下文"""
    print("--- 3b. Reasoning (LLM + Memory Context) ---")
    
    # 性能追踪
    tracker = get_tracker()
    tracker.start_node("reasoning")
    
    # 【防御性检查】如果已有 tool_calls（不应该发生，因为 graph 会直接路由到 tool_node）
    # 但为了安全起见，如果有就直接返回
    existing_tool_calls = state.get("tool_calls", [])
    if existing_tool_calls:
        print(f"[WARN] 检测到已有 tool_calls，直接返回（不应该发生）")
        tracker.stop_node("reasoning")
        return {"tool_calls": existing_tool_calls}
    
    query = state["user_input"]
    memory_context = state.get("memory_context")
    conversation_history = state.get("history", [])
    
    from .conflict_handler import ConflictHandler
    conflict_handler = ConflictHandler()

    # [Step 0] 从对话历史中提取上下文信息
    context_info = []
    recent_topics = []

    # 遍历最近的对话历史（最近5条）
    for conv in conversation_history[-5:]:
        if isinstance(conv, dict) and conv.get("type") == "conversation":
            user_msg = conv.get("user", "")
            assistant_msg = conv.get("assistant", "")

            # 提取有用信息
            if len(context_info) < 2:  # 最多保留2条有用信息
                if "天气" in assistant_msg and "温度" in assistant_msg:
                    context_info.append(f"天气信息: {assistant_msg[:100]}...")
                elif "时间" in assistant_msg and ("点" in assistant_msg or ":" in assistant_msg):
                    context_info.append(f"时间信息: {assistant_msg[:50]}...")

            # 记录最近话题
            if len(recent_topics) < 3:
                recent_topics.append(user_msg[:50])

    if context_info:
        print(f"   从历史中提取的上下文: {len(context_info)} 条")
    if recent_topics:
        print(f"   最近话题: {recent_topics}")

    # 只保留真正需要硬编码处理的场景，其他都交给LLM

    # 灯控制命令（需要精确参数解析，保留硬编码）
    if state.get("command_type") == "light_control":
        print("   处理灯控制命令")

        # 解析参数
        brightness = None
        color_temp = None

        input_lower = query.lower()
        if "亮" in input_lower:
            import re
            brightness_match = re.search(r'亮度[\s]*(\d+)', input_lower)
            if brightness_match:
                brightness = int(brightness_match.group(1))

        if "色温" in input_lower or "暖光" in input_lower or "冷光" in input_lower:
            if "暖光" in input_lower or "暖" in input_lower:
                color_temp = "warm"
            elif "冷光" in input_lower or "冷" in input_lower:
                color_temp = "cool"

        light_action = {}
        if brightness is not None:
            light_action["brightness"] = brightness
        if color_temp is not None:
            light_action["color_temp"] = color_temp
        if not light_action:
            light_action = {"brightness": 80, "color_temp": "warm"}

        response = "好的，正在为您调整灯光设置！"
        if brightness is not None:
            response += f"亮度已设置为{brightness}%。"
        if color_temp is not None:
            if isinstance(color_temp, str):
                temp_name = "暖色" if color_temp == "warm" else "冷色"
            else:
                temp_name = f"{color_temp}K色温"
            response += f"色温已设置为{temp_name}。"

        # 停止节点计时（硬编码快速路径）
        node_time = tracker.stop_node("reasoning")
        print(f"   灯控制命令处理完成 (总耗时: {node_time:.3f}s)")
        
        return {
            "action_plan": {
                "motor": {"vibration": "gentle"},
                "light": light_action,
                "sound": None
            },
            "voice_content": response,
            "parsed_params": {
                "brightness": brightness,
                "color_temp": color_temp
            }
        }


    # 继续正常的LLM推理流程

    # [Step 0.5] 检查是否有工具结果需要注入（计划已完成的情况）
    plan_status = state.get("plan_status")
    execution_plan = state.get("execution_plan", {})
    tool_results_text = ""
    
    # 【性能优化】从state中获取已检测的工具需求，避免重复调用LLM
    required_tools_from_plan = state.get("required_tools", [])
    
    if plan_status == "completed" and execution_plan:
        # 从执行计划中提取工具结果
        tool_results_text = _format_tool_results_for_prompt(execution_plan)
        if tool_results_text:
            print(f"   检测到计划已完成，已提取工具结果（{len(tool_results_text)} 字符）")
            # 调试输出：若包含 web_search_tool 结果，打印前 500 字符
            if "工具: web_search_tool" in tool_results_text:
                debug_snippet = tool_results_text[:500].replace("\n", "\\n")
                print(f"   🔎 web_search_tool 结果片段: {debug_snippet}...")

        # 【新闻直返】如果 news_tool 已有结果，直接返回，跳过 reasoning
        steps = execution_plan.get("steps", [])
        for step in steps:
            if step.get("action_type") != "tool_call":
                continue
            if step.get("tool_name") != "news_tool":
                continue
            result = step.get("result")
            output = None
            if isinstance(result, dict):
                output = result.get("output") or result.get("error")
            else:
                output = result

            if output:
                output_text = str(output)
                # 如果是明显的错误提示，则继续走 reasoning
                if "抱歉" in output_text and ("网络搜索" in output_text or "失败" in output_text):
                    break

                print("   ✅ 检测到 news_tool 结果，跳过 reasoning，直接返回")
                node_time = tracker.stop_node("reasoning")
                print(f"   news_tool 直返完成 (总耗时: {node_time:.3f}s)")
                return {
                    "voice_content": output_text,
                    "action_plan": {}
                }
    
    # 【P0 紧急修复】当 plan_status=="skipped" 但 state 中有 tool_results 时，直接提取
    # 这解决了 skipped 模式下工具调用死循环的问题
    if not tool_results_text:
        raw_tool_results = state.get("tool_results", [])
        if raw_tool_results:
            # 使用新的格式化函数，包含错误处理信息
            tool_results_text = _format_tool_results_with_error_handling(raw_tool_results)
            if tool_results_text:
                print(f"   【P0修复】从 state 直接提取工具结果（{len(tool_results_text)} 字符）")

    # [Step 1] 准备完整上下文（记忆 + 对话历史）
    context_manager = get_context_manager()
    
    # 1.1 压缩对话历史
    tracker.start("compression")
    compression_result = context_manager.compress_conversation_history(conversation_history)
    compression_time = tracker.stop("compression")
    
    # 如果进行了压缩，记录压缩信息
    if compression_result["compressed"]:
        print(f"   压缩统计: {compression_result['original_size']} -> {compression_result['compressed_size']} 字符 (节省 {compression_result['compression_ratio']})")
        print(f"   压缩耗时: {compression_time:.3f}s")
    
    # 使用压缩后的历史
    formatted_history = context_manager.format_compressed_history(compression_result)
    
    # 1.2 清洗和去重记忆上下文
    if memory_context:
        memory_context = context_manager.clean_memory_context(memory_context)
    
    # 1.3 准备 XML 格式化的上下文
    user_profile_text = ""
    recent_memories_list = []
    action_patterns_list = []
    
    if memory_context:
        # 用户画像（需要解析并去重）
        user_profile = memory_context.get("user_profile")
        if user_profile and user_profile != "暂无详细画像":
            # 解析字符串为列表，进行去重，再格式化回字符串
            # user_profile 格式: "- 用户喜欢蓝色\n- 用户最喜欢的颜色是蓝色"
            profile_lines = [line.strip() for line in user_profile.split("\n") if line.strip()]
            
            # 提取纯文本（移除 "- " 前缀和特殊标记）
            profile_items = []
            for line in profile_lines:
                if line.startswith("- "):
                    profile_items.append(line[2:])  # 移除 "- "
                elif line.startswith("【") or line == "":  # 跳过特殊标记行和空行
                    continue
                else:
                    profile_items.append(line)
            
            # 去重
            if profile_items:
                deduplicated_items = context_manager.deduplicate_user_profile(profile_items)
                # 重新格式化为字符串
                user_profile_text = "\n".join([f"- {item}" for item in deduplicated_items])
            else:
                user_profile_text = user_profile
        
        # 用户记忆（已去重）
        user_memories = memory_context.get("user_memories", [])
        if user_memories:
            recent_memories_list = user_memories[:3]  # 最多3条
        
        # 动作模式（已清洗）
        action_patterns = memory_context.get("action_patterns", [])
        if action_patterns:
            action_patterns_list = action_patterns[:2]  # 最多2条
        
        # 实时上下文（添加到用户画像中）
        realtime_info = memory_context.get("realtime_context")
        if realtime_info:
            if user_profile_text:
                user_profile_text = f"{user_profile_text}\n\n【实时环境】\n- {realtime_info}"
            else:
                user_profile_text = f"【实时环境】\n- {realtime_info}"
    
    # 1.4 使用 XML 格式化上下文
    xml_context = context_manager.format_context_with_xml(
        user_profile=user_profile_text,
        recent_memories=recent_memories_list,
        action_patterns=action_patterns_list,
        conversation_history=formatted_history,
        current_state={
            "intimacy_level": state.get("intimacy_level", 30),
            "focus_mode": state.get("focus_mode", False),
            "conflict_state": state.get("conflict_state")
        }
    )
    
    
    print("   XML 结构化上下文已生成")
    print(f"      {xml_context[:200]}..." if len(xml_context) > 200 else f"      {xml_context}")
    # DEBUG: Check if conversation_history is in the xml_context
    if "<conversation_history>" in xml_context:
        print(f"   DEBUG: conversation_history tag FOUND in xml_context")
        # Print a snippet of conversation history
        start = xml_context.find("<conversation_history>")
        end = xml_context.find("</conversation_history>")
        if start != -1 and end != -1:
            snippet = xml_context[start:min(start+500, end+len("</conversation_history>"))]
            print(f"   📜 History snippet: {snippet}...")
    else:
        print(f"[ERROR] DEBUG: conversation_history tag NOT FOUND in xml_context")

    # [Step 1.5] 格式化当前硬件状态（使用 XML 标签）
    current_hw = state.get("current_hardware_state", {})
    light_state = current_hw.get("light", {})
    motor_state = current_hw.get("motor", {})
    
    # 格式化为 XML 格式的状态描述
    light_status = light_state.get("status", "off")
    light_brightness = light_state.get("brightness", 0)
    light_color = light_state.get("color", "warm")
    light_color_temp = light_state.get("color_temp", "unknown")
    
    motor_status = motor_state.get("status", "idle")
    motor_vibration = motor_state.get("vibration", "none")
    
    hardware_status_str = f"""<hardware_status>
<light>
<status>{light_status}</status>
<brightness>{light_brightness}</brightness>
<color>{light_color}</color>
<color_temp>{light_color_temp}</color_temp>
</light>
<motor>
<status>{motor_status}</status>
<vibration>{motor_vibration}</vibration>
</motor>
</hardware_status>"""
    
    print(f"   硬件状态: 灯光={light_status}, 电机={motor_status}")

    # [Step 2] 构建增强 Prompt（集成记忆上下文和工具）
    # 使用增强的工具文档（XML 格式）
    mcp_manager = get_mcp_manager()
    tool_descriptions = mcp_manager.get_enhanced_tool_descriptions()
    
    print("   📚 已加载增强工具文档（XML 格式）")
    
    # [场景 4.1] 检测音乐推荐请求
    music_keywords = ["推荐", "听歌", "音乐", "放首歌", "来首歌", "想听"]
    if any(kw in query for kw in music_keywords):
        print("   检测到音乐推荐请求...")
        # 从对话历史推断情绪
        mood = mcp_manager.music_recommender.get_mood_from_conversation(conversation_history) if mcp_manager.music_recommender else "neutral"
        
        # 从用户记忆中提取音乐偏好（场景 4.1 改进：从记忆系统读取）
        memory_manager = get_memory_manager()
        music_prefs = memory_manager.get_music_preferences()
        user_preferences = music_prefs.get("liked_artists", [])
        
        # 获取推荐
        if not mcp_manager.music_recommender:
            mcp_manager.setup_music_recommender()
        
        recommendations = mcp_manager.recommend_music_by_mood(mood, user_preferences)
        
        # 过滤掉不喜欢的艺术家和类型
        disliked_artists = music_prefs.get("disliked_artists", [])
        disliked_genres = music_prefs.get("disliked_genres", [])
        filtered_recommendations = []
        for rec in recommendations:
            if rec.artist not in disliked_artists and rec.genre not in disliked_genres:
                filtered_recommendations.append(rec)
        
        if filtered_recommendations:
            recommendations = filtered_recommendations
        
        if recommendations:
            rec_text = "\n".join([f"- {r.title} - {r.artist} ({r.reason})" for r in recommendations[:2]])
            tool_descriptions += f"\n\n音乐推荐（基于情绪: {mood}）：\n{rec_text}\n"
            print(f"   推荐了 {len(recommendations)} 首歌")
    
    # [场景 4.2] 检测新闻请求（只做意图识别，不预取新闻）
    news_keywords = ["新闻", "资讯", "今天有什么", "最近发生", "热点"]
    if any(kw in query for kw in news_keywords):
        print("   检测到新闻请求...")
        
        # 提取用户指定的新闻类型关键词
        news_type_keyword = ""
        news_type_hint = ""
        
        # 检测用户明确指定的新闻类型
        if "娱乐" in query or "娱乐圈" in query:
            news_type_keyword = "娱乐"
            news_type_hint = "（用户想看娱乐新闻）"
        elif "科技" in query or "技术" in query or "AI" in query or "人工智能" in query:
            news_type_keyword = "科技"
            news_type_hint = "（用户想看科技新闻）"
        elif "体育" in query:
            news_type_keyword = "体育"
            news_type_hint = "（用户想看体育新闻）"
        elif "财经" in query or "经济" in query:
            news_type_keyword = "财经"
            news_type_hint = "（用户想看财经新闻）"
        elif "社会" in query or "时事" in query:
            news_type_keyword = "社会"
            news_type_hint = "（用户想看社会新闻）"
        elif "科学" in query or "医学" in query or "健康" in query:
            news_type_keyword = "科学"
            news_type_hint = "（用户想看科学新闻）"
        
        # 从用户记忆中提取兴趣（仅用于上下文提示，不实际获取新闻）
        memory_manager = get_memory_manager()
        user_interests = memory_manager.get_news_interests()
        
        # 如果没有从记忆中获取到兴趣，尝试从用户画像中提取
        if not user_interests and memory_context and "user_profile" in memory_context:
            profile_text = memory_context["user_profile"]
            if "科技" in profile_text or "技术" in profile_text:
                user_interests = user_interests or []
                user_interests.append("科技")
            if "AI" in profile_text or "人工智能" in profile_text:
                user_interests = user_interests or []
                user_interests.append("AI")
        
        # 构建提示信息
        interests_hint = f"（用户可能对 {', '.join(user_interests)} 感兴趣）" if user_interests else ""
        
        # 如果用户指定了新闻类型，明确告诉 LLM 传递 keyword 参数
        if news_type_keyword:
            tool_descriptions += f"\n\n用户正在请求{news_type_keyword}新闻{news_type_hint}，请使用 news_tool 工具，并在 keyword 参数中传递 '{news_type_keyword}' 关键词。\n"
        else:
            tool_descriptions += f"\n\n用户正在请求新闻{interests_hint}，请使用 news_tool 工具获取最新资讯。\n"
        
        print(f"   已添加新闻请求提示，等待工具调用")
    
    # [Step 2.1] 使用动态System Prompt（注入 XML 上下文）
    from config.prompts import get_system_prompt
    system_prompt_base = get_system_prompt(
        intimacy_level=state.get("intimacy_level", 30),
        intimacy_rank=state.get("intimacy_rank", "stranger"),
        conflict_state=state.get("conflict_state"),
        focus_mode=state.get("focus_mode", False),
        xml_context=xml_context  # 注入 XML 格式化的上下文
    )
    
    # 【新增】检查是否有欢迎提示（用户久别归来但同时说了实际内容）
    welcome_hint = state.get("welcome_hint", "")
    if welcome_hint:
        print(f"   🏠 注入欢迎提示: {welcome_hint[:50]}...")
    
    # === 情感感知语气调整 ===
    emotion = state.get("current_emotion", {})
    emotion_instruction = ""
    
    if emotion:
        emotion_type = emotion.get("type", "neutral")
        intensity = emotion.get("intensity", "medium")
        label = emotion.get("label", "")
        response_tone = emotion.get("response_tone", "")
        confidence = emotion.get("confidence", 0)
        
        print(f"   😊 情感感知: {label} (强度: {intensity}, 置信度: {confidence:.2f})")
        
        emotion_instruction = f"""
<emotion_awareness priority="high">
<detected_emotion>
<type>{emotion_type}</type>
<label>{label}</label>
<intensity>{intensity}</intensity>
<confidence>{confidence:.2f}</confidence>
</detected_emotion>

<response_guidelines>
建议语气：{response_tone}
"""
        
        # 根据情绪类型添加具体示例和指导
        if emotion_type in ["sad", "tired"]:
            emotion_instruction += """
<specific_instructions>
- 使用温柔、共情的语气（如"我理解你的感受"、"听起来你很辛苦"）
- 避免过于乐观或激励性的建议（用户现在需要的是理解，不是鼓励）
- 适当表达关心和陪伴（如"需要我陪你聊聊吗？"、"要不要休息一下？"）
- 可以提供实际帮助（如播放舒缓音乐、调暗灯光）
- 示例回复："听起来你最近很辛苦呢，要不要休息一下？我一直在这里陪着你。"
</specific_instructions>
"""
        elif emotion_type in ["angry", "anxious"]:
            emotion_instruction += """
<specific_instructions>
- 使用冷静、理解的语气，避免说教或批评
- 承认用户的感受，表示理解（如"我能理解这让你很不舒服"）
- 提供支持和安抚，不要试图立即解决问题
- 避免使用"你应该"、"其实"等可能引起反感的表达
- 示例回复："我能理解你的感受，这确实很让人烦躁。我们一起想想办法好吗？"
</specific_instructions>
"""
        elif emotion_type in ["happy", "excited"]:
            emotion_instruction += """
<specific_instructions>
- 使用活泼、积极的语气，与用户的情绪共鸣
- 共同庆祝和分享喜悦，表达真诚的开心
- 可以使用表情符号或更生动的表达
- 适当增加互动性，延续积极氛围
- 示例回复:"太棒了！我也为你感到开心！🎉 这真是个好消息！"
</specific_instructions>
"""
        elif emotion_type == "confused":
            emotion_instruction += """
<specific_instructions>
- 使用耐心、清晰的语气，避免复杂表达
- 提供简洁明了的解释或引导
- 主动询问是否需要更详细的说明
- 示例回复："我来帮你理清思路吧。你是想问..."
</specific_instructions>
"""
        elif emotion_type == "grateful":
            emotion_instruction += """
<specific_instructions>
- 使用温暖、谦逊的语气回应感谢
- 表达陪伴的愿意和喜悦
- 可以适当增加亲密度
- 示例回复："不客气呀！能帮到你我也很开心～"
</specific_instructions>
"""
        
        emotion_instruction += """
</response_guidelines>
</emotion_awareness>

"""
    
    # 构建更聪明、更高效的 Prompt（使用 XML 标签结构化）
    # 注意：{hardware_status} 和 {tools} 是后续 .format() 的占位符，不要使用 f-string
    welcome_prefix = f"{welcome_hint}\n" if welcome_hint else ""
    emotion_prefix = emotion_instruction if emotion_instruction else ""
    
    prompt_body = welcome_prefix + emotion_prefix + """
<interaction_guidelines priority="critical">
<guideline>身份认同：你是一个陪伴型人工智能助手 Animus。你不仅是灯，更是用户的伙伴。你可以通过灯光、身体动作、声音和音乐来表达自己。</guideline>
<guideline>物理边界：你没有肢体，严禁承诺如"泡咖啡"、"开门"等物理劳动。如果用户提出此类要求，请转而提供情绪陪伴（如：放一首好听的音乐陪他煮咖啡）。</guideline>
<guideline>已知事实即真理：如果 <user_profile> 或 <conversation_history> 中已经包含某些信息（如用户所在地），严禁以"你在XX对吧？"等疑问句或确认句开头。直接使用这些信息！</guideline>
<guideline>任务连贯性 + 信息补全模式：
   - 检查 <conversation_history>。如果上一次你承诺了要"查某事"，本轮必须给出结果，不能再问。
   - 关键：如果上一轮用户问了需要参数的问题（如"天气如何"缺少地点），本轮用户只说了一个地点（如"我在上海"），这是信息补全，你必须立即完成上一轮的任务并给出答案。</guideline>
<guideline priority="critical">指代消解：
   - 如果用户说"查一下"、"那个"、"这个"等指代词，你必须查看 <conversation_history> 来理解具体指什么。
   - 【关键】如果用户使用"他"、"她"、"它"、"他们"等人称代词，你必须查看 <conversation_history> 找到最近提到的对应对象。如果上一轮讨论了某个人物（如科比），用户说"你觉得他怎么样？"，那"他"就是指科比，你必须直接回答关于科比的问题，禁止反问"你说的是谁"！
   - 例如：上一轮你问"需要我帮你查查附近哪家评分高吗？"，用户回"查一下"，那就是要查火锅店评分，不要反问"查什么"！</guideline>
<guideline>纠正识别：
   - 如果用户说"但是我告诉你了..."、"不是...是..."、"其实我..."，这是在纠正你的错误。
   - 你必须承认错误，道歉，并立即更新认知。不要辩解或重复错误信息。
   - 例如：用户说"但是我告诉你了我在北京"，说明你之前用错了城市信息，必须道歉并改正。</guideline>
<guideline>高效回答：对于天气、时间、知识类询问，必须在第一句话给出核心答案。然后再进行温柔的陪伴式闲聊。</guideline>
<guideline>拒绝机械感：禁止使用"根据之前的记录"、"我注意到"等AI感极强的套话。</guideline>
<guideline>拒绝编造信息：如果需要查询实时信息（天气、新闻等），你必须明确说明"我去查一下"或"让我看看"，不要编造数据。</guideline>
<guideline priority="critical">日期/事件精确匹配：
   - 当用户询问"X号需要做什么"、"X号有什么安排"时，必须严格匹配 <core_memory_ram> 中的日期。
   - 如果记忆中没有该日期的安排，必须明确回答"X号暂时没有特别安排"或"没有找到X号的事项"。
   - 严禁将其他日期的事件错误关联到用户询问的日期（这是幻觉！）。
   - 示例：记忆有"每月20号=工作汇报日"，用户问22号 → 正确回答"22号没有安排"，错误回答"22号是工作汇报日"。</guideline>
<guideline priority="critical">事件存在性查询：
   - 当用户询问"有没有XX安排"、"现在还有XX吗"、"XX取消了吗"时，必须仔细检查 <core_memory_ram> 中是否存在匹配的事件。
   - 如果 <core_memory_ram> 中没有找到相关事件，必须明确回答"目前没有找到XX的安排"或"没有XX的记录"。
   - 注意：如果用户刚刚说"取消XX"，而你在 <core_memory_ram> 中没有找到这个事件，说明取消成功了，应该确认"XX已经取消了，现在没有这个安排了"。
   - 严禁模糊回答如"让我看看..."然后不给出明确结论。你必须给出完整的答案！</guideline>
<guideline priority="critical">时间范围查询：
   - 当用户询问"这个月有什么安排"、"这周有什么事"时，必须列出 <core_memory_ram> 中所有符合该时间范围的事件。
   - 如果范围内没有任何事件，必须明确回答"这个月/这周暂时没有特别安排"。
   - 严禁只给出部分回答或留下悬念（如"让我看看..."）而不完成回答。</guideline>
<guideline priority="critical">通用追问处理：
   - 当用户输入通用的追问（如"我该怎么办？"、"有什么好办法？"、"为什么？"、"怎么做？"）时，必须查看 <conversation_history> 获取最近的上下文（如用户刚提到的困难或问题）。
   - 严禁将此类追问视为新的独立问题（如不要回答"请告诉我你遇到了什么困难"），而应直接基于上下文给出建议。
   - 示例：上一轮用户说"我最近胖了"，本轮问"怎么办"，你应结合上文回答关于"运动或饮食控制"的建议，而不是问"你遇到什么问题"。</guideline>
</interaction_guidelines>

<hardware_status>
{hardware_status}
</hardware_status>

{tools}

<action_templates>
<action type="none">无硬件反馈（纯对话/查询）：空字典</action>
<action type="motor">振动反馈：{{ "vibration": "gentle", "speed": "slow" }}</action>
<action type="light">灯光控制：{{ "color": "warm", "brightness": 60, "blink": "slow" }}</action>
</action_templates>

<intimacy_handling>
<rule>识别夸奖：如果用户在表扬、鼓励或表达喜爱（如"你真棒"、"好乖"、"谢谢你"），你必须给出正向的 intimacy_delta（通常在 0.5 到 1.0 之间）。</rule>
<rule>原因记录：设置 intimacy_reason 为 "praise"。</rule>
<rule>语气同步：随着亲密度提升（参考 <current_state> 中的等级），你的语气应该变得更亲昵、更主动、更像一只撒娇的猫。</rule>
</intimacy_handling>
"""
    # 组合 Prompt（上下文已通过 xml_context 注入到 system_prompt_base 中）
    system_prompt_full = system_prompt_base + "\n" + prompt_body

    # === 工具决策逻辑（统一由 Plan Node 决策，Reasoning Node 执行） ===
    # 
    # 优先级：
    # 1. 如果已有工具结果（plan_status == "completed"）→ 不需要工具调用
    # 2. 如果 Plan Node 已检测到工具需求 → 复用，不重复检测
    # 3. 如果 Plan Node 跳过（简单任务）但用户输入确实需要工具 → 才需要自己检测
    #
    plan_status = state.get("plan_status", "")
    
    if tool_results_text:
        # 已有工具结果，不需要工具调用
        required_tools = []
        print(f"   已有工具结果，跳过工具调用")
    elif required_tools_from_plan:
        # Plan Node 已检测到工具需求，直接复用
        required_tools = required_tools_from_plan
        print(f"   复用 Plan Node 检测到的工具需求: {required_tools}")
    elif plan_status == "skipped":
        # Plan Node 跳过了（被判定为简单任务），但我们再做一次轻量级检查
        # 使用规则检测而不是 LLM，因为复杂场景应该已经被 Plan Node 处理
        required_tools = _rule_based_tool_detection(query)
        if required_tools:
            print(f"[WARN] Plan Node 漏判，规则检测到工具需求: {required_tools}")
    else:
        # Plan Node 没有传递工具需求，且不是跳过状态，不再重复检测
        required_tools = []
    
    tool_instruction = ""
    
    # 【关键修复】如果有工具结果，明确指示LLM基于结果生成回复，不要再调用工具
    if tool_results_text:
        # 检查是否有错误
        raw_tool_results = state.get("tool_results", [])
        has_errors = any("error" in result for result in raw_tool_results) if raw_tool_results else False
        
        if has_errors:
            tool_instruction = f"""

【关键】工具调用已完成，但部分工具执行失败。以下是工具返回的结果：
<tool_results>
{tool_results_text}
</tool_results>

【错误处理规则】：
1. 如果工具返回错误，你必须向用户解释错误原因（使用友好的语言，不要直接说"工具执行失败"）
2. 根据错误类型给出不同的回复：
   - 网络错误：说"网络有点慢，稍等一下"或"连接不太稳定，我再试试"
   - 超时错误：说"查询时间有点长，稍等片刻"
   - 参数错误：说"我理解错了，让我重新确认一下"
   - 服务不可用：说"这个服务暂时用不了，换个方式帮你"
3. 如果所有工具都失败，必须明确告诉用户"暂时无法获取信息"，不要编造数据
4. 如果部分工具成功，只使用成功的结果，忽略失败的工具

你必须基于上述工具结果生成回复，不要再调用工具。"""
        else:
            # 检查工具结果是否需要验证
            raw_tool_results = state.get("tool_results", [])
            validation_warnings = []
            for result in raw_tool_results:
                if "error" not in result:
                    tool_name = result.get("tool_name", "")
                    output = result.get("output", "")
                    if tool_name and output:
                        is_valid, warning, error = _validate_tool_result(tool_name, output)
                        if not is_valid:
                            validation_warnings.append(f"{tool_name}: {error}")
                        elif warning:
                            validation_warnings.append(f"{tool_name}: {warning}")
            
            if validation_warnings:
                tool_instruction = f"""

【关键】工具调用已完成，但部分工具结果验证失败。以下是工具返回的结果：
<tool_results>
{tool_results_text}
</tool_results>

【结果验证规则】：
1. 如果工具结果标记为"失败（结果验证失败）"，必须告诉用户"获取的信息可能不准确，建议稍后再试"
2. 如果工具结果标记为"成功（警告）"，可以使用结果，但要在回复中说明"数据可能不完全准确"
3. 如果结果包含明显错误（如温度超过60°C、AQI超过500），必须质疑结果并建议重新查询
4. 如果所有工具结果都验证失败，必须明确告诉用户"暂时无法获取准确信息"，不要使用错误数据

验证警告：{'; '.join(validation_warnings)}

你必须基于上述工具结果生成回复，不要再调用工具。"""
            else:
                tool_instruction = f"""

【关键】工具调用已完成，以下是工具返回的结果：
<tool_results>
{tool_results_text}
</tool_results>

你必须基于上述工具结果生成回复，不要再调用工具。直接使用工具结果中的信息回答用户的问题。
如果工具结果中包含用户询问的信息（如空气质量数据），请直接使用这些信息生成JSON格式的回复。"""
    elif required_tools:
        tool_instruction = f"\n\n【重要】检测到用户查询需要工具调用（{', '.join(required_tools)}）。你必须使用工具调用功能来获取真实数据，而不是直接回复。如果工具可用，请使用 tool_calls 而不是在 voice_content 中说'让我查一下'。"
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt_full),
        ("human", """用户输入：{query}

请分析这个输入的意图类型和用户状态，然后生成合适的回复和动作。

意图分析思考：
- 用户想表达什么？是告知状态、寻求帮助还是闲聊？
- 用户可能处于什么情绪或状态？
- 应该如何回应才能既贴心又主动？{tool_instruction}

基于你的分析，生成回复：

【重要】请直接输出 JSON 对象，不要添加任何前缀或后缀文本。输出必须以左花括号开头。"""),
    ])

    # [Step 3] 执行 Chain
    final_prompt = prompt.partial(
        tools=tool_descriptions,
        hardware_status=hardware_status_str,
        tool_instruction=tool_instruction
    )

    try:
        # 使用模型管理器选择最合适的模型
        model_manager = get_model_manager()
        
        # 检查是否需要工具调用（基于统一的工具决策结果）
        # has_tools 只看 required_tools 是否非空，不再做额外判断
        has_tools = bool(required_tools)
        
        # 自动选择模型
        selected_llm, model_name = model_manager.select_model(
            task_type="auto",
            user_input=query,
            conversation_history=conversation_history,
            has_tools=has_tools
        )
        
        # 获取模型层级用于显示
        model_tier = model_manager.get_model_tier(model_name)
        tier_emoji = {"fast": "", "chat": "", "reasoning": ""}.get(model_tier, "")
        tier_name = {"fast": "Fast", "chat": "Chat", "reasoning": "Reasoning"}.get(model_tier, "Unknown")
        
        print(f"   {tier_emoji} 选择模型: {model_name} ({tier_name})")
        
        # 如果需要工具调用，将工具绑定到 LLM
        if has_tools and required_tools:
            print(f"   绑定工具到 LLM: {', '.join(required_tools)}")
            # 只绑定需要的工具，而不是所有工具（提高效率）
            tools_to_bind = [tool for tool in AVAILABLE_TOOLS if tool.name in required_tools]
            if tools_to_bind:
                selected_llm = selected_llm.bind_tools(tools_to_bind)
                print(f"   已绑定 {len(tools_to_bind)} 个工具")
            else:
                # 如果没有找到对应工具，绑定所有工具作为后备
                selected_llm = selected_llm.bind_tools(AVAILABLE_TOOLS)
                print(f"[WARN] 未找到指定工具，绑定所有工具作为后备")
        
        print(f"[正在调用 LLM API，请稍候...]")
        sys.stdout.flush()

        # 尝试直接调用 LLM 以获取完整消息（支持工具调用）
        # 暂时不使用 parser，因为需要检查 tool_calls
        tracker.start("llm_call_reasoning")
        ai_msg = (final_prompt | selected_llm).invoke({
            "query": query
        })
        llm_time = tracker.stop("llm_call_reasoning")
        
        # 记录模型调用统计（三级模型）
        # 估算 tokens（粗略估计：中文约2字符/token，英文约4字符/token）
        estimated_tokens = len(query) // 2 + len(str(ai_msg.content)) // 2
        model_manager.record_call(model_tier, llm_time, estimated_tokens)
        
        print(f"   LLM 调用耗时: {llm_time:.3f}s (模型: {model_name})")
        
        # 检查是否有工具调用 (Task 1.2)
        if hasattr(ai_msg, "tool_calls") and ai_msg.tool_calls:
            print(f"   LLM 决定调用工具: {[tc.get('name', tc.get('function', {}).get('name', 'unknown')) for tc in ai_msg.tool_calls]}")
            
            # 转换工具调用格式为 tool_node 期望的格式
            formatted_tool_calls = []
            for tc in ai_msg.tool_calls:
                # LangChain 的工具调用格式可能是不同的结构
                if isinstance(tc, dict):
                    # 标准格式：{"name": "...", "args": {...}, "id": "..."}
                    if "name" in tc:
                        formatted_tool_calls.append({
                            "id": tc.get("id", f"call_{len(formatted_tool_calls)}"),
                            "name": tc["name"],
                            "args": tc.get("args", {})
                        })
                    # LangChain 格式：{"function": {"name": "...", "arguments": "..."}, "id": "..."}
                    elif "function" in tc:
                        import json
                        func = tc["function"]
                        args_str = func.get("arguments", "{}")
                        try:
                            args = json.loads(args_str) if isinstance(args_str, str) else args_str
                        except:
                            args = {}
                        formatted_tool_calls.append({
                            "id": tc.get("id", f"call_{len(formatted_tool_calls)}"),
                            "name": func.get("name", ""),
                            "args": args
                        })
                else:
                    # 如果是对象，尝试获取属性
                    tool_name = getattr(tc, "name", None) or getattr(getattr(tc, "function", None), "name", None)
                    tool_args = getattr(tc, "args", None) or {}
                    if tool_name:
                        formatted_tool_calls.append({
                            "id": getattr(tc, "id", f"call_{len(formatted_tool_calls)}"),
                            "name": tool_name,
                            "args": tool_args
                        })
            
            if formatted_tool_calls:
                # 停止节点计时（转向工具调用）
                node_time = tracker.stop_node("reasoning")
                print(f"   推理完成（转向工具调用）(总耗时: {node_time:.3f}s)")
                return {
                    "tool_calls": formatted_tool_calls,
                    "intent_route": "tool_node", # 强制路由到工具节点
                    "monologue": "基于你的需求，我需要动用一些工具来查询信息..."
                }
            else:
                print(f"[WARN] 工具调用格式转换失败，继续正常流程")

        # 正常解析 JSON（先清理常见的 LLM 输出格式错误）
        sanitized_content = _sanitize_json_output(ai_msg.content)
        result = parser.parse(sanitized_content)
        print(f"[API 调用完成]")
        
        # 检测冲突等级
        conflict_level = conflict_handler.detect_conflict_level(query, state.get("sensor_data", {}))
        
        # 如果检测到冲突，应用惩罚
        if conflict_level in ["L1", "L2", "L3"]:
            penalty_result = conflict_handler.apply_conflict_penalty(conflict_level, state)
            # 更新状态（将在main.py中合并）
            result["conflict_state"] = penalty_result["conflict_state"]
            result["intimacy_delta"] = penalty_result["intimacy_delta"]
            result["intimacy_reason"] = f"conflict_{conflict_level}"  # 添加原因字段
            print(f"[WARN]  检测到冲突（{conflict_level}），已应用惩罚")
        
        # 如果在冷却期，检测用户是否在道歉
        if conflict_handler.is_in_cooldown(state):
            if conflict_handler.detect_forgiveness(query, state):
                offense_level = state.get("conflict_state", {}).get("offense_level", "")
                # L1/L2可以提前结束冷却
                if offense_level in ["L1", "L2"]:
                    result["conflict_state"] = None  # 清除冲突状态
                    result["voice_content"] = "没关系，我原谅你了。"
                    print("   检测到道歉，提前结束冷却期")
                elif offense_level == "L3":
                    # L3需要等待最小时间，但可以缩短剩余时间
                    remaining = conflict_handler.get_cooldown_remaining(state)
                    if remaining > 60:  # 如果剩余时间超过1分钟，缩短一半
                        new_cooldown_until = time.time() + (remaining / 2)
                        if result.get("conflict_state"):
                            result["conflict_state"]["cooldown_until"] = new_cooldown_until
                        print(f"   检测到道歉（L3），缩短冷却期至剩余{int(remaining/2)}秒")

        # 构建内心独白
        memories = memory_context.get("user_memories", []) if memory_context else []
        monologue = f"正在调动记忆和模型进行深度思考...\n"
        if memories:
            monologue += f"我想起你以前提过：'{memories[0][:30]}...'，这对我理解你的意图很有帮助。\n"
        
        # 获取亲密度变化
        intimacy_delta = result.get("intimacy_delta", 0.0)
        if intimacy_delta > 0:
            monologue += f"思考结果：感受到你的善意（+{intimacy_delta}），我决定给你更好的回应。\n"
        else:
            monologue += f"思考结果：基于你当前的需求，我决定{'调用工具' if 'tool_call' in str(result) else '直接生成回复'}。"

        # 停止节点计时
        node_time = tracker.stop_node("reasoning")
        print(f"   推理完成 (总耗时: {node_time:.3f}s)")
        
        # 清理 voice_content 中的删除线标记（防止 Markdown 删除线显示）
        voice_content = _clean_strikethrough(result["voice_content"])
        
        return {
            "voice_content": voice_content,
            "action_plan": result["action_plan"],
            "conflict_state": result.get("conflict_state"),
            "intimacy_delta": intimacy_delta,
            "intimacy_reason": result.get("intimacy_reason", "general"),
            "monologue": monologue,
            "tool_results": [],  # 【P0修复】清空工具结果，避免影响后续请求
        }
    except Exception as e:
        print(f"[ERROR] LLM Error: {e}")
        tracker.stop_node("reasoning")
        return {"voice_content": "抱歉，我现在有点卡顿，稍等一下...", "action_plan": {}}

def action_guard_node(state: LampState) -> Dict:
    """
    安全卫士：验证和修饰动作计划
    修改点：
    1. 移除兴奋模式强制修饰
    2. 添加冲突状态检查（冷却期限制）
    3. 添加专注模式检查
    """
    print("--- 4. Action Guard (Safety & Modify) ---")
    raw_action = state.get("action_plan", {}) or {}
    final_action = raw_action.copy()
    voice_content = state.get("voice_content")
    
    # 导入管理器
    from .conflict_handler import ConflictHandler
    from .focus_mode_manager import FocusModeManager
    
    conflict_handler = ConflictHandler()
    focus_manager = FocusModeManager()
    
    # === 1. 冲突状态检查（冷却期限制） ===
    if conflict_handler.is_in_cooldown(state):
        # 获取命令类型（从action_plan或command_type推断）
        command_type = state.get("command_type", "")
        if not command_type:
            # 尝试从action_plan推断命令类型
            if "light" in final_action:
                command_type = "basic_light_control"
            elif "motor" in final_action and final_action.get("motor", {}).get("vibration") == "none":
                command_type = "safety_stop"
            else:
                command_type = "unknown"
        
        # 检查命令是否允许
        if not conflict_handler.is_command_allowed(command_type, state):
            print(f"    冷却期：禁止执行命令类型 '{command_type}'")
            return {
                "action_plan": {},
                "voice_content": None  # 不语音回复
            }
        else:
            print(f"   冷却期：允许执行命令类型 '{command_type}'")
    
    # === 2. 专注模式检查 ===
    if focus_manager.is_focus_mode_active(state):
        constraints = focus_manager.get_focus_mode_action_constraints(state)
        
        # 检查是否是主动行为
        is_proactive = state.get("event_type") == "internal_drive"
        
        # 如果是主动行为，禁止
        if is_proactive and not constraints["allow_proactive"]:
            print("   专注模式：禁止主动行为")
            return {
                "action_plan": {},
                "voice_content": None
            }
        
        # 如果是语音打断，禁止
        if voice_content and not constraints["allow_voice"]:
            print("   专注模式：禁止语音打断")
            return {
                "action_plan": final_action,  # 保留动作（如灯光）
                "voice_content": None  # 但禁止语音
            }
    
    # === 3. 移除兴奋模式强制修饰（V1已删除） ===
    # 保持动作计划的原始意图，不再强制修改
    
    # === 4. 防止 LLM 擅自改变灯光亮度 ===
    # 只有用户明确请求灯光控制时，才允许改变亮度
    user_input = state.get("user_input", "")
    light_keywords = ["灯", "亮度", "调亮", "调暗", "开灯", "关灯", "变亮", "变暗", "明亮", "暗"]
    user_requested_light = any(kw in user_input for kw in light_keywords) if user_input else False
    
    if "light" in final_action and not user_requested_light:
        current_hw = state.get("current_hardware_state", {})
        current_brightness = current_hw.get("light", {}).get("brightness")
        llm_brightness = final_action.get("light", {}).get("brightness")
        
        # 如果 LLM 设置的亮度与当前不同，且用户没请求，则移除亮度设置
        if llm_brightness is not None and current_brightness is not None:
            if llm_brightness != current_brightness:
                print(f"   防止擅自改变亮度: {current_brightness}% -> {llm_brightness}% (已阻止)")
                # 移除 brightness 字段，保持当前亮度
                if "brightness" in final_action["light"]:
                    del final_action["light"]["brightness"]
                # 如果 light 只剩下 blink 等临时字段，也可以保留
    
    # 清理 voice_content 中的删除线标记（防止 Markdown 删除线显示）
    voice_content = _clean_strikethrough(voice_content)
    
    return {
        "action_plan": final_action,
        "voice_content": voice_content
    }


# ==========================================
# 异步记忆写入（带重试机制）
# ==========================================

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=False  # 失败后不抛出异常，避免影响主流程
)
def _async_memory_write(user_input: str, voice_content: str, keyword_emotion: Dict):
    """
    后台记忆写入任务（带重试机制）
    
    Args:
        user_input: 用户输入
        voice_content: 系统回复
        keyword_emotion: 关键词提取的情感数据
    """
    try:
        from .emotion_extractor import get_emotion_extractor
        from .memory_manager import get_memory_manager
        
        _logger.info(f"[异步任务] 开始记忆写入 | 输入: {user_input[:30]}...")
        
        extractor = get_emotion_extractor()
        memory_manager = get_memory_manager()
        
        # ========== 方案A：LLM 精细提取（异步） ==========
        emotion_details = None
        try:
            # 在同步函数中调用异步方法
            # 创建新的 event loop（避免与主线程冲突）
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            emotion_details = loop.run_until_complete(
                extractor.extract_emotion_by_llm(
                    user_input, 
                    voice_content,
                    keyword_emotion
                )
            )
            
            loop.close()
            
        except Exception as e:
            _logger.warning(f"[异步任务] LLM 情感提取失败，使用关键词结果: {e}")
            emotion_details = keyword_emotion
        
        # ========== 存储记忆（带情感元数据） ==========
        final_emotion = emotion_details or keyword_emotion
        
        if final_emotion:
            # ChromaDB 元数据格式（嵌套 + 平铺）
            import json
            from datetime import datetime
            
            metadata = {
                # 嵌套对象（完整情感数据）- 序列化为 JSON 字符串
                "emotion": json.dumps(final_emotion, ensure_ascii=False),
                
                # 平铺字段（便于 ChromaDB filter 查询）
                "emotion_type": final_emotion.get("type", ""),
                "emotion_label": final_emotion.get("label", ""),
                "emotion_intensity": final_emotion.get("intensity", ""),
                "emotion_confidence": final_emotion.get("confidence", 0.0),
                "emotion_source": final_emotion.get("source", "keyword"),
                
                # 时间戳
                "timestamp": final_emotion.get("timestamp", datetime.now().isoformat()),
                
                # 分类
                "category": "user_emotion"
            }
            
            # 调用记忆管理器保存
            memory_manager.save_user_memory(
                content=user_input,
                metadata=metadata
            )
            
            _logger.info(f"✅ [异步任务] 记忆写入成功 | 情绪: {final_emotion.get('label', 'N/A')} ({final_emotion.get('source', 'unknown')})")
        else:
            _logger.info(f"[异步任务] 跳过情感记忆写入（无情感数据）")
        
    except Exception as e:
        _logger.error(f"❌ [异步任务] 记忆写入失败: {e}", exc_info=True)
        
        # 写入失败日志到文件（用于后续排查）
        try:
            from pathlib import Path
            from datetime import datetime
            
            log_dir = Path("logs")
            log_dir.mkdir(exist_ok=True)
            
            with open(log_dir / "memory_write_failures.log", "a", encoding="utf-8") as f:
                f.write(f"{datetime.now().isoformat()} | {user_input} | {e}\n")
        except:
            pass  # 避免日志写入失败影响主流程
        
        raise  # 重新抛出异常，触发重试


def execution_node(state: LampState) -> Dict:
    """执行节点：模拟硬件调用 + 记忆写入（含异步情感记忆）"""
    print("--- 5. Execution (Act + Memory Write) ---")

    voice_content = state.get("voice_content")
    action_plan = state.get("action_plan", {})
    user_input = state.get("user_input")  # 提前获取 user_input
    current_emotion = state.get("current_emotion")  # 获取情感数据

    # [Step 1] 执行硬件控制
    print(f"   语音输出: {voice_content}")
    print(f"    硬件动作: {action_plan}")

    # 模拟硬件调用延迟
    import time
    time.sleep(0.1)

    # [Step 1.5] 状态更新 - 更新硬件状态快照
    # 定义哪些字段是持久状态（会被保存），哪些是临时动作（执行后消失）
    PERSISTENT_LIGHT_FIELDS = {"brightness", "color_temp", "status", "color"}
    PERSISTENT_MOTOR_FIELDS = {"speed", "status", "vibration"}
    
    # 获取当前硬件状态（深拷贝以防引用问题）
    current_hw = {
        "light": state.get("current_hardware_state", {}).get("light", {}).copy(),
        "motor": state.get("current_hardware_state", {}).get("motor", {}).copy()
    }
    
    # 更新灯光状态
    if "light" in action_plan:
        # 如果有灯光动作，说明灯应该是开的（除非明确设为0）
        if action_plan["light"].get("brightness", -1) == 0:
            current_hw["light"]["status"] = "off"
            current_hw["light"]["brightness"] = 0
        else:
            current_hw["light"]["status"] = "on"
            
        # 只更新持久字段，临时字段（如 blink, transition）不保存
        for k, v in action_plan["light"].items():
            if k in PERSISTENT_LIGHT_FIELDS:
                current_hw["light"][k] = v
    
    # 更新电机状态
    if "motor" in action_plan:
        for k, v in action_plan["motor"].items():
            if k in PERSISTENT_MOTOR_FIELDS:
                current_hw["motor"][k] = v
    
    print(f"   硬件状态已更新: {current_hw}")

    # [Step 1.8] 异步情感记忆写入（不阻塞用户响应）
    if voice_content and user_input and current_emotion:
        print(f"   📝 提交异步情感记忆写入任务...")
        _memory_executor.submit(
            _async_memory_write,
            user_input,
            voice_content,
            current_emotion
        )

    # [Step 2] 记忆写入逻辑
    if voice_content and user_input:
        try:
            memory_manager = get_memory_manager()

            # 1. 提取基础偏好（从用户输入和AI回复中提取）
            user_preference = memory_manager.extract_user_preference(user_input, voice_content)
            if user_preference and user_preference.get("confidence", 0) > 0.6:
                content = user_preference["content"]
                # 标准化 category
                raw_category = user_preference.get("category", "general")
                normalized_category = memory_manager._normalize_category(raw_category)
                metadata = {
                    "category": normalized_category,
                    "confidence": user_preference["confidence"],
                    "source": "preference_extraction"
                }
                memory_manager.save_user_memory(content, metadata)

            # 2. 提取音乐偏好（场景 4.1）- 检测用户对推荐音乐的反馈
            # 检查对话历史中是否有音乐推荐
            conversation_history = state.get("history", [])
            recommended_music = None
            for conv in conversation_history[-3:]:
                if isinstance(conv, dict) and "assistant" in conv.get("assistant", ""):
                    assistant_msg = conv.get("assistant", "")
                    # 检测是否包含音乐推荐（简单模式匹配）
                    if "推荐" in assistant_msg and ("歌" in assistant_msg or "音乐" in assistant_msg):
                        # 提取推荐的音乐（简单提取，实际可以用更复杂的NLP）
                        import re
                        match = re.search(r'推荐\s*([^，。！？]+)', assistant_msg)
                        if match:
                            recommended_music = match.group(1)
                            break
            
            music_preference = memory_manager.extract_music_preference(
                user_input, voice_content, recommended_music
            )
            if music_preference and music_preference.get("confidence", 0) > 0.6:
                content = music_preference["content"]
                metadata = {
                    "category": "music",
                    "confidence": music_preference["confidence"],
                    "sentiment": music_preference.get("sentiment", "neutral"),
                    "source": "music_preference_extraction"
                }
                if music_preference.get("artist"):
                    metadata["artist"] = music_preference["artist"]
                if music_preference.get("genre"):
                    metadata["genre"] = music_preference["genre"]
                
                memory_manager.save_user_memory(content, metadata)
                print(f"   已保存音乐偏好: {content}")

            # 3. 提取新闻偏好（场景 4.2）- 只从用户主动表达的输入中学习偏好
            # 修复：不再从 AI 回复中提取，只检测用户明确表达的意图
            news_topics = None
            # 检测用户是否主动表达了对特定新闻类型的兴趣
            interest_patterns = ["想看", "推荐", "感兴趣", "关注", "喜欢看", "给我", "来点", "来一些"]
            if any(p in user_input for p in interest_patterns):
                # 只从用户输入中提取主题
                topics = []
                for topic in ["AI", "科技", "人工智能", "机器学习", "创业", "投资", "科学"]:
                    if topic in user_input:
                        topics.append(topic)
                if topics:
                    news_topics = topics
            
            news_preference = memory_manager.extract_news_preference(
                user_input, voice_content, news_topics
            )
            if news_preference and news_preference.get("confidence", 0) > 0.6:
                content = news_preference["content"]
                metadata = {
                    "category": "news",
                    "confidence": news_preference["confidence"],
                    "sentiment": news_preference.get("sentiment", "neutral"),
                    "source": "news_preference_extraction"
                }
                if news_preference.get("topics"):
                    # ChromaDB 不支持列表类型的元数据，需要转换为字符串
                    topics = news_preference["topics"]
                    if isinstance(topics, list):
                        metadata["topics"] = ",".join(topics)
                    else:
                        metadata["topics"] = str(topics)
                
                memory_manager.save_user_memory(content, metadata)
                print(f"   已保存新闻偏好: {content}")

            # 4. 提取长期画像/事实（核心逻辑）
            memory_manager.extract_and_save_user_profile(user_input, voice_content)

            # 5. [本体论增强] 提取情境记忆 (Episodic Memory) + 实体注册
            episodic_event = memory_manager.extract_episodic_memory(user_input, voice_content)
            if episodic_event and episodic_event.get("confidence", 0) > 0.6:
                content = episodic_event["content"]
                importance = episodic_event.get("importance", 5)
                
                # 重要性 >= 4 才保存 (过滤太多琐事)
                if importance >= 4:
                    metadata = {
                        "category": episodic_event.get("category", "activity"),
                        "confidence": episodic_event["confidence"],
                        "importance": importance,
                        "source": "episodic_extraction"
                    }
                    
                    # [本体论增强] 注册提取的实体
                    entity_ids = []
                    if "entities" in episodic_event:
                        try:
                            from .entity_registry import get_entity_registry
                            entity_registry = get_entity_registry()
                            entity_ids = entity_registry.register_from_extraction(
                                episodic_event["entities"]
                            )
                            if entity_ids:
                                # 将实体ID关联到记忆
                                metadata["entity_ids"] = ",".join(entity_ids)
                                print(f"   已注册 {len(entity_ids)} 个实体")
                        except Exception as reg_err:
                            print(f"[WARN] 实体注册失败: {reg_err}")
                    
                    # [本体论增强] 添加时间和动作元数据
                    temporal = episodic_event.get("temporal", {})
                    if temporal.get("is_recurring"):
                        metadata["is_recurring"] = True
                        if temporal.get("recurrence_pattern"):
                            metadata["recurrence_pattern"] = temporal["recurrence_pattern"]
                    
                    action = episodic_event.get("action", {})
                    if action.get("type"):
                        metadata["action_type"] = action["type"]
                    
                    memory_manager.save_user_memory(content, metadata)
                    print(f"   情境记忆已保存: {content[:30]}... (重要性: {importance})")

        except Exception as e:
            print(f"[WARN]  记忆写入失败: {e}")

    # [Step 3] 更新对话历史（保持在内存中，限制长度）
    if user_input and voice_content:
        # 添加新的对话到历史
        new_conversation = {
            "user": user_input,
            "assistant": voice_content,
            "timestamp": time.time(),
            "type": "conversation"
        }

        current_history = state.get("history", [])
        # 只保留最近10条对话，避免历史过长
        updated_history = (current_history + [new_conversation])[-10:]

        print(f"   添加对话历史: 当前 {len(updated_history)} 条记录")
    else:
        updated_history = state.get("history", [])[-10:]  # 也限制长度

    # [Step 4] 返回最终执行结果
    # 工作流最后一个节点需要返回完整的状态
    print("   执行完成")
    
    # [Step 5] 打印性能报告
    tracker = get_tracker()
    tracker.print_report()

    return {
        "voice_content": voice_content,
        "action_plan": action_plan,
        "execution_status": "completed",
        "history": updated_history,
        "current_hardware_state": current_hw  # 返回更新后的硬件状态
    }


# ==========================================
# 6. Plan Node 实现
# ==========================================

# 简单任务关键词（无需规划，直接跳过）
SIMPLE_TASK_KEYWORDS = {
    "greeting": ["你好", "嗨", "早上好", "晚上好", "下午好", "hello", "hi"],
    "single_query": ["现在几点", "什么时间", "今天几号"],
    "simple_control": ["开灯", "关灯", "停止", "暂停"],
}

# 多步骤任务关键词（需要规划）
MULTI_STEP_KEYWORDS = ["然后", "之后", "接着", "再", "并且", "同时", "先", "最后"]

# 条件逻辑关键词
CONDITION_KEYWORDS = ["如果", "当", "若", "要是", "假如", "如若", "万一", "倘若"]


def _is_clearly_simple(user_input: str, history: List = None) -> bool:
    """
    阶段1：快速规则判断 - 明确的简单任务（不调用LLM）
    
    明确简单任务特征：
    1. 纯问候语（你好、嗨等）
    2. 简单控制命令（开灯、关灯、停止等）
    3. 简单确认/感谢（好的、谢谢、嗯等）
    4. 超短输入（<6字符）且无指代词和查询词
    
    Args:
        user_input: 用户输入
        history: 对话历史（用于判断是否在对话中）
        
    Returns:
        True 如果是明确的简单任务（无需LLM判断）
    """
    if not user_input:
        return True
    
    input_lower = user_input.lower().strip()
    user_input_stripped = user_input.strip()
    
    # === 排除词检查：包含这些词的绝对不是简单任务 ===
    # 指代词（需要上下文理解）
    reference_keywords = ["那", "这个", "那个", "它", "呢", "怎么样", "如何", "怎样"]
    # 查询词（需要工具调用）
    query_keywords = ["天气", "空气", "温度", "pm", "aqi", "新闻", "几点", "时间", "查", "搜", "提醒", "闹钟", "日程", "待办"]
    # 条件词（复杂逻辑）
    condition_keywords = ["如果", "当", "若", "要是", "假如"]
    
    has_reference = any(kw in user_input for kw in reference_keywords)
    has_query = any(kw in input_lower for kw in query_keywords)
    has_condition = any(kw in user_input for kw in condition_keywords)
    
    # 如果包含任何排除词，不是简单任务
    if has_reference or has_query or has_condition:
        return False
    
    # === 简单任务检查 ===
    
    # 1. 检查是否是纯问候语（完全匹配或以问候语开头）
    greetings = ["你好", "嗨", "早上好", "晚上好", "下午好", "hello", "hi", "早安", "晚安", "嘿"]
    for greeting in greetings:
        if input_lower == greeting or (input_lower.startswith(greeting) and len(user_input_stripped) < 15):
            print(f"   规则判断：问候语 '{user_input_stripped}'")
            return True
    
    # 2. 检查是否是简单控制命令
    control_commands = ["开灯", "关灯", "停止", "暂停", "停", "继续", "开始"]
    for cmd in control_commands:
        if cmd in input_lower:
            print(f"   规则判断：控制命令 '{cmd}'")
            return True
    
    # 3. 检查是否是简单确认/感谢/情感表达
    simple_responses = ["好的", "好", "嗯", "ok", "谢谢", "谢了", "感谢", "明白", "知道了", 
                        "收到", "了解", "可以", "行", "没问题", "没事", "算了", "不用了"]
    for resp in simple_responses:
        if input_lower == resp or user_input_stripped == resp:
            print(f"   规则判断：简单回复 '{user_input_stripped}'")
            return True
    
    # 4. 超短输入（<6字符）且不在对话上下文中
    # 如果历史为空，超短输入可能是测试或简单问候
    if len(user_input_stripped) < 6 and (not history or len(history) == 0):
        print(f"   规则判断：超短输入（无历史）'{user_input_stripped}'")
        return True
    
    return False


def _is_clearly_complex(user_input: str, history: List = None) -> bool:
    """
    阶段2：快速规则判断 - 明确的复杂任务（不调用LLM）
    
    明确复杂任务特征：
    1. 包含条件逻辑关键词（如果、当、若等）
    2. 包含多步骤关键词（然后、之后、接着等）
    3. 包含明确的查询关键词（天气、空气、新闻等）
    4. 指代消解 + 历史中有工具相关话题
    
    Args:
        user_input: 用户输入
        history: 对话历史
        
    Returns:
        True 如果是明确的复杂任务（无需LLM判断，直接进入规划）
    """
    if not user_input:
        return False
    
    input_lower = user_input.lower()
    
    # 1. 检查是否包含条件逻辑关键词
    if any(kw in user_input for kw in CONDITION_KEYWORDS):
        print(f"   规则判断：包含条件逻辑关键词，需要规划")
        return True
    
    # 2. 检查是否包含多步骤关键词
    if any(kw in user_input for kw in MULTI_STEP_KEYWORDS):
        print(f"   规则判断：包含多步骤关键词，需要规划")
        return True
    
    # 3. 检查是否包含明确的查询关键词（这些必须调用工具）
    # 这是最重要的规则：明确的查询词直接判定为复杂任务
    explicit_query_keywords = {
        "weather_tool": ["天气", "气温", "温度", "几度", "下雨", "晴天", "阴天", "多云"],
        "air_quality_tool": ["空气", "空气质量", "pm2.5", "pm10", "aqi", "污染", "雾霾"],
        "news_tool": ["新闻", "资讯", "热点", "头条"],
        "time_tool": ["几点", "什么时间", "现在时间", "日期"],
        "calculator_tool": ["计算", "等于多少", "加", "减", "乘", "除"],
        "wikipedia_tool": ["是什么", "什么是", "百科", "介绍一下"],
        "web_search_tool": ["查一下", "搜索", "查找", "搜一下", "check", "search", "who is", "what is", "最新", "新发布", "新功能", "刚发布", "最近听说", "新出的", "有什么功能", "功能是什么", "讲讲", "介绍一下", "帮我查", "了解一下"]
    }
    
    detected_tools = []
    for tool_name, keywords in explicit_query_keywords.items():
        if any(kw in input_lower for kw in keywords):
            detected_tools.append(tool_name)
    
    if detected_tools:
        print(f"   规则判断：检测到明确查询关键词，需要工具 {detected_tools}")
        return True
    
    # 4. 检查指代消解需求 - 如果包含指代词，需要检查历史
    reference_keywords = ["那", "这个", "那个", "它", "呢", "怎么样", "如何", "怎样"]
    has_reference = any(kw in user_input for kw in reference_keywords)
    
    if has_reference and history:
        # 检查历史中是否有需要工具调用的上下文
        tool_related_keywords = ["天气", "空气", "pm2.5", "温度", "新闻", "时间", "查", "搜索"]
        for conv in history[-3:]:  # 检查最近3条历史
            if isinstance(conv, dict):
                prev_user = conv.get("user", "")
                prev_assistant = conv.get("assistant", "")
                if any(kw in prev_user or kw in prev_assistant for kw in tool_related_keywords):
                    print(f"   规则判断：指代消解 + 历史中有工具话题，需要规划")
                    return True
    
    return False


def _llm_classify_task_complexity(user_input: str, history: List = None) -> bool:
    """
    LLM智能判断任务复杂度
    
    使用LLM进行智能判断，能够理解：
    1. 指代消解（"那空气呢？"）
    2. 上下文相关的查询
    3. 语义模糊的输入
    4. 工具调用需求
    
    Args:
        user_input: 用户输入
        history: 对话历史
        
    Returns:
        True 如果是简单任务，False 如果是复杂任务（需要规划）
    """
    try:
        from .model_manager import get_model_manager
        
        # 使用 Fast 模型进行快速分类（成本低、速度快）
        model_manager = get_model_manager()
        fast_llm, model_name = model_manager.select_model(
            task_type="fast",
            user_input=user_input,
            conversation_history=history or [],
            has_tools=False
        )
        
        # 构建详细的分类prompt，包含对话历史
        history_context = ""
        if history:
            recent_history = history[-3:]  # 取最近3条，提供更多上下文
            history_parts = []
            for conv in recent_history:
                if isinstance(conv, dict):
                    user_msg = conv.get("user", "")
                    assistant_msg = conv.get("assistant", "")
                    if user_msg:
                        history_parts.append(f"用户: {user_msg}")
                    if assistant_msg:
                        history_parts.append(f"助手: {assistant_msg[:80]}...")
            if history_parts:
                history_context = "\n".join(history_parts)
        
        classification_prompt = ChatPromptTemplate.from_messages([
            ("system", """你是一个智能任务分类器。根据用户输入和对话历史，判断是否需要复杂的规划流程（包括工具调用）。

【简单任务】（返回true）- 无需规划，可以直接处理：
- 纯问候、确认、简短回复（"你好"、"好的"、"嗯"、"谢谢"）
- 简单控制命令（"开灯"、"关灯"、"停止"、"暂停"）
- 不需要工具调用的闲聊、情感表达（"我想你了"、"好累啊"）

【复杂任务】（返回false）- 需要规划流程和工具调用：
- **需要工具调用的查询**（这是最重要的判断标准）：
  * 天气相关：包含"天气"、"温度"、"几度"、"下雨"、"晴天"等
  * 空气质量相关：包含"空气"、"空气质量"、"pm2.5"、"pm10"、"aqi"、"污染"等
  * 新闻相关：包含"新闻"、"资讯"、"热点"、"最新"等
  * 时间相关：包含"几点"、"时间"、"日期"、"现在"等
  * 计算相关：包含"计算"、"等于"、"加"、"减"等
  * 提醒/日程相关：包含"提醒"、"闹钟"、"日程"、"待办"、"记一下"等
  * 百科相关：包含"是什么"、"什么是"、"介绍"、"百科"等
- 指代消解（如"那空气呢？"、"这个怎么样？"需要从对话历史理解）
- 多步骤操作（"先...然后..."、"接着..."）
- 条件逻辑（"如果...就..."、"当...时"）

【关键判断原则】：
1. **如果用户输入包含任何需要查询的信息（天气、空气、新闻、时间等），一定是复杂任务（false）**
2. 如果用户输入包含指代词（"那"、"这个"、"那个"、"它"、"呢"等），且对话历史中提到过需要工具的话题，则一定是复杂任务（false）
3. 如果用户输入只是简单的问候、确认、控制命令，则是简单任务（true）
4. **特别注意**："空气"、"空气怎么样"、"空气质量"等关键词，都表示需要工具调用，是复杂任务

只返回 true 或 false，不要其他内容。"""),
            ("human", """用户输入：{user_input}

{history_context}

【分析步骤】：
1. 检查用户输入是否包含需要工具调用的关键词（天气、空气、新闻、时间、计算、百科等）
2. 如果包含，返回 false（复杂任务，需要规划）
3. 如果只是问候、确认、控制命令，返回 true（简单任务）

特别注意：
- "空气"、"空气怎么样"、"空气质量" → 需要工具调用 → false
- "天气"、"温度"、"几度" → 需要工具调用 → false
- "新闻"、"资讯" → 需要工具调用 → false

请判断这是简单任务（true）还是复杂任务（false）。只返回 true 或 false。""")
        ])
        
        response = (classification_prompt | fast_llm).invoke({
            "user_input": user_input,
            "history_context": f"对话历史：\n{history_context}" if history_context else "无对话历史"
        })
        
        # 解析LLM响应
        result_text = response.content.strip().lower()
        
        # 更严格的解析逻辑
        if "true" in result_text or "简单" in result_text or ("是" in result_text and "不是" not in result_text):
            print(f"   LLM判断（{model_name}）：简单任务（无需规划）")
            return True
        else:
            print(f"   LLM判断（{model_name}）：复杂任务（需要规划）")
            return False
            
    except Exception as e:
        print(f"[WARN] LLM分类失败: {e}，降级为复杂任务（需要规划）")
        # 降级策略：如果LLM失败，默认认为是复杂任务（更安全，避免误判）
        return False


def _is_simple_task(user_input: str, history: List = None) -> bool:
    """
    两阶段过滤：先规则判断，再LLM判断（优化性能）
    
    阶段1: 规则快速过滤（毫秒级，不调用LLM）
        - 明确简单 → 直接返回 True
        - 明确复杂 → 直接返回 False
        
    阶段2: LLM智能判断（仅对不确定场景）
    
    Args:
        user_input: 用户输入
        history: 对话历史（用于上下文判断）
        
    Returns:
        True 如果是简单任务（无需规划），False 如果是复杂任务（需要规划）
    """
    # 极端简单情况：空输入
    if not user_input:
        return True
    
    # === 阶段1: 规则快速判断（不调用LLM） ===
    
    # 1a. 检查是否是明确的简单任务
    if _is_clearly_simple(user_input, history):
        print(f"   阶段1判断：明确的简单任务（跳过LLM）")
        return True
    
    # 1b. 检查是否是明确的复杂任务
    if _is_clearly_complex(user_input, history):
        print(f"   阶段1判断：明确的复杂任务（跳过LLM）")
        return False
    
    # === 阶段2: 不确定场景，调用LLM判断 ===
    print(f"   阶段2判断：不确定场景，使用LLM...")
    return _llm_classify_task_complexity(user_input, history)


def _analyze_task_complexity(user_input: str, memory_context: Dict = None) -> str:
    """
    分析任务复杂度
    
    Args:
        user_input: 用户输入
        memory_context: 记忆上下文
        
    Returns:
        "simple" | "moderate" | "complex"
    """
    if not user_input:
        return "simple"
    
    # 条件逻辑 → complex
    if any(kw in user_input for kw in CONDITION_KEYWORDS):
        return "complex"
    
    # 多步骤关键词计数
    step_count = sum(1 for kw in MULTI_STEP_KEYWORDS if kw in user_input)
    
    if step_count >= 2:
        return "complex"
    elif step_count == 1:
        return "moderate"
    
    # 句子长度判断
    if len(user_input) > 50:
        return "moderate"
    
    return "simple"


def _rule_based_tool_detection(user_input: str) -> List[str]:
    """
    轻量级规则检测工具需求（不调用LLM）
    
    用于 Plan Node 跳过但可能漏判的情况。
    只检测最明确的关键词，不处理指代消解等复杂情况。
    
    Args:
        user_input: 用户输入
        
    Returns:
        需要的工具名称列表（可能为空）
    """
    if not user_input:
        return []
    
    import re
    input_lower = user_input.lower()
    detected_tools = []
    
    # === 日程/提醒的取消/删除/查询操作（优先检测）===
    cancel_keywords = ["取消", "删除", "删掉", "去掉", "不要了", "算了"]
    query_keywords = ["查看", "查询", "有哪些", "什么日程", "什么安排"]
    schedule_related = ["提醒", "闹钟", "日程", "待办", "安排"]
    
    # 检测是否涉及日程相关
    has_schedule_context = any(kw in input_lower for kw in schedule_related)
    
    if has_schedule_context:
        # 先检查是否是取消/删除操作
        if any(kw in input_lower for kw in cancel_keywords):
            # 取消操作需要两步：先查询获取 schedule_id，再删除
            detected_tools.append("query_schedule_tool")
            detected_tools.append("delete_schedule_tool")
            print(f"   检测到取消/删除日程操作，计划: 查询 → 删除")
            return detected_tools
        
        # 检查是否是查询操作
        if any(kw in input_lower for kw in query_keywords):
            detected_tools.append("query_schedule_tool")
            print(f"   检测到查询日程操作")
            return detected_tools
    
    # === 智能提醒工具选择（创建操作）===
    reminder_keywords = ["提醒", "闹钟", "记得", "别忘"]
    if any(kw in input_lower for kw in reminder_keywords):
        # 解析延迟时间，决定使用哪个工具
        delay_seconds = _parse_delay_seconds(user_input)
        
        if delay_seconds is not None and delay_seconds < 30 * 60:  # < 30分钟
            # 短期提醒：使用倒计时工具（精确到秒）
            detected_tools.append("countdown_timer_tool")
            print(f"   检测到短期提醒（{delay_seconds}秒），使用 countdown_timer_tool")
        else:
            # 长期提醒或有具体时间点：使用日程工具
            detected_tools.append("create_schedule_tool")
            print(f"   检测到长期提醒，使用 create_schedule_tool")
        
        return detected_tools
    
    # === 重要日期（整合到日程系统）===
    important_date_keywords = ["生日", "纪念日", "周年", "忌日", "节日"]
    if any(kw in input_lower for kw in important_date_keywords):
        detected_tools.append("create_schedule_tool")
        print(f"   检测到重要日期，使用 create_schedule_tool (yearly)")
        return detected_tools
    
    # === 日程/待办（非提醒类，创建操作）===
    schedule_keywords = ["日程", "待办", "记一下", "安排"]
    if any(kw in input_lower for kw in schedule_keywords):
        detected_tools.append("create_schedule_tool")
        return detected_tools
    
    # === 其他工具的关键词映射 ===
    tool_keywords = {
        "weather_tool": ["天气", "气温", "温度", "几度", "下雨", "晴天"],
        "air_quality_tool": ["空气", "空气质量", "pm2.5", "pm10", "aqi", "污染", "雾霾"],
        "news_tool": ["新闻", "资讯", "热点", "头条"],
        "time_tool": ["几点", "什么时间", "现在时间"],
        "calculator_tool": ["计算", "等于多少"],
        "web_search_tool": [
            "查一下", "搜索", "查找", "搜一下", "帮我查", "了解一下", "介绍一下", "告诉我关于", "查查", "百度一下", "谷歌一下", "check", "search", "who is", "what is",
            "最新", "新发布", "新功能", "刚发布", "最近听说", "新出的", "有什么功能", "功能是什么", "讲讲",
        ],
    }
    
    # 【规则优先级】如果包含新闻关键词，只走 news_tool
    if any(kw in input_lower for kw in tool_keywords["news_tool"]):
        return ["news_tool"]

    for tool_name, keywords in tool_keywords.items():
        if any(kw in input_lower for kw in keywords):
            detected_tools.append(tool_name)
    
    return detected_tools


# 中文数字映射（模块级别，供多个函数共用）
_CHINESE_NUM_MAP = {
    '零': 0, '一': 1, '二': 2, '两': 2, '三': 3, '四': 4, 
    '五': 5, '六': 6, '七': 7, '八': 8, '九': 9, '十': 10,
    '十一': 11, '十二': 12, '十三': 13, '十四': 14, '十五': 15,
    '二十': 20, '三十': 30, '四十': 40, '五十': 50, '六十': 60,
}

def _parse_chinese_or_arabic(text: str) -> int:
    """解析中文或阿拉伯数字"""
    if not text:
        return None
    # 先尝试阿拉伯数字
    if text.isdigit():
        return int(text)
    # 再尝试中文数字
    if text in _CHINESE_NUM_MAP:
        return _CHINESE_NUM_MAP[text]
    # 处理复合中文数字（如"二十五"）
    if '十' in text:
        parts = text.split('十')
        if len(parts) == 2:
            tens = _CHINESE_NUM_MAP.get(parts[0], 1) if parts[0] else 1
            ones = _CHINESE_NUM_MAP.get(parts[1], 0) if parts[1] else 0
            return tens * 10 + ones
    return None


def _parse_absolute_datetime(user_input: str) -> "datetime | None":
    """
    解析绝对时间表达式，返回 datetime 对象
    
    支持格式：
    - 日期词：今天、明天、后天、大后天
    - 时段词：早上、上午、中午、下午、晚上、凌晨
    - 时间点：X点、X点半、X点X分
    - 组合：明天早上九点、下午3点、晚上8点半
    
    Returns:
        datetime 对象，如果无法解析返回 None
    """
    import re
    from datetime import datetime, timedelta
    
    now = datetime.now()
    
    # ========== 1. 解析日期偏移 ==========
    day_offset = 0
    if "大后天" in user_input:
        day_offset = 3
    elif "后天" in user_input:
        day_offset = 2
    elif "明天" in user_input:
        day_offset = 1
    elif "今天" in user_input:
        day_offset = 0
    # 如果没有明确日期词，稍后根据时间判断
    
    # ========== 2. 解析时段（用于确定上午/下午） ==========
    is_pm = False  # 默认上午
    is_am_explicit = False
    
    if any(x in user_input for x in ["下午", "晚上", "傍晚"]):
        is_pm = True
    elif any(x in user_input for x in ["上午", "早上", "早晨", "凌晨"]):
        is_am_explicit = True
    elif "中午" in user_input:
        # 中午特殊处理，12点附近
        is_pm = False  # 12点算上午制
    
    # ========== 3. 解析具体时间点 ==========
    hour = None
    minute = 0
    
    # 模式1：X点半
    half_match = re.search(r'([零一二两三四五六七八九十\d]+)\s*点半', user_input)
    if half_match:
        hour = _parse_chinese_or_arabic(half_match.group(1))
        minute = 30
    
    # 模式2：X点X分 / X点XX
    if hour is None:
        time_match = re.search(r'([零一二两三四五六七八九十\d]+)\s*[点:：](\d{1,2}|[零一二三四五六七八九十]+)\s*分?', user_input)
        if time_match:
            hour = _parse_chinese_or_arabic(time_match.group(1))
            minute = _parse_chinese_or_arabic(time_match.group(2)) or 0
    
    # 模式3：单独的X点
    if hour is None:
        hour_match = re.search(r'([零一二两三四五六七八九十\d]+)\s*点', user_input)
        if hour_match:
            hour = _parse_chinese_or_arabic(hour_match.group(1))
            minute = 0
    
    # 模式4：XX:XX 格式
    if hour is None:
        colon_match = re.search(r'(\d{1,2})[:\uff1a](\d{2})', user_input)
        if colon_match:
            hour = int(colon_match.group(1))
            minute = int(colon_match.group(2))
    
    # 如果没有解析到时间点，返回 None
    if hour is None:
        return None
    
    # ========== 4. 处理12小时制转24小时制 ==========
    if is_pm and hour < 12:
        hour += 12
    elif is_am_explicit and hour == 12:
        # "早上12点" 应该是中午12点，不调整
        pass
    
    # 特殊情况：没有明确上午/下午，但时间很早（1-6点）
    # 如果用户说"明天1点"且没有时段词，默认下午
    if not is_pm and not is_am_explicit and 1 <= hour <= 6:
        # 检查是否有凌晨等关键词
        if not any(x in user_input for x in ["凌晨"]):
            # 默认认为是下午（13:00-18:00）
            hour += 12
    
    # ========== 5. 构建目标时间 ==========
    target_date = now.date() + timedelta(days=day_offset)
    
    try:
        target_time = datetime(
            year=target_date.year,
            month=target_date.month,
            day=target_date.day,
            hour=hour,
            minute=minute,
            second=0
        )
    except ValueError:
        # 时间无效（如25点）
        return None
    
    # ========== 6. 智能日期调整 ==========
    # 如果没有明确日期词，且解析出的时间已经过了，自动推到明天
    if day_offset == 0 and "今天" not in user_input and "明天" not in user_input:
        if target_time <= now:
            target_time += timedelta(days=1)
            print(f"   ⏰ 时间已过，自动调整到明天")
    
    return target_time


def _parse_delay_seconds(user_input: str) -> int:
    """
    从用户输入解析延迟秒数（相对时间）
    
    支持格式：
    - X分钟后、X分钟（支持中文数字：一、二、两、三...十）
    - X小时后、X小时
    - X秒后、X秒
    - 半小时后、一刻钟
    
    Returns:
        延迟秒数，如果无法解析返回 None
    """
    import re
    
    # 分钟（支持中文和阿拉伯数字）
    minute_match = re.search(r'([零一二两三四五六七八九十\d]+)\s*分钟', user_input)
    if minute_match:
        num = _parse_chinese_or_arabic(minute_match.group(1))
        if num is not None:
            return num * 60
    
    # 小时（支持中文和阿拉伯数字）
    hour_match = re.search(r'([零一二两三四五六七八九十\d]+)\s*小时', user_input)
    if hour_match:
        num = _parse_chinese_or_arabic(hour_match.group(1))
        if num is not None:
            return num * 3600
    
    # 秒（支持中文和阿拉伯数字）
    second_match = re.search(r'([零一二两三四五六七八九十\d]+)\s*秒', user_input)
    if second_match:
        num = _parse_chinese_or_arabic(second_match.group(1))
        if num is not None:
            return num
    
    # 半小时
    if "半小时" in user_input or "半个小时" in user_input:
        return 30 * 60
    
    # 一刻钟
    if "一刻钟" in user_input or "15分" in user_input:
        return 15 * 60
    
    # 无法解析（可能是具体时间点，如"明天9点"）
    return None


def _parse_relative_time(user_input: str, current_time: float) -> Optional[float]:
    """
    解析相对时间表达式，返回 Unix 时间戳
    
    Args:
        user_input: 用户输入（可能包含时间表达式）
        current_time: 当前时间戳
        
    Returns:
        解析后的时间戳，如果无法解析则返回 None
    """
    from datetime import datetime, timedelta
    import re
    
    now = datetime.fromtimestamp(current_time)
    input_lower = user_input.lower()
    
    # 匹配模式
    patterns = [
        (r"明天", lambda: now + timedelta(days=1)),
        (r"后天", lambda: now + timedelta(days=2)),
        (r"(\d+)天后", lambda m: now + timedelta(days=int(m.group(1)))),
        (r"下周", lambda: now + timedelta(days=7 - now.weekday())),
        (r"下个月", lambda: (now.replace(day=1) + timedelta(days=32)).replace(day=1)),
        (r"(\d+)小时后", lambda m: now + timedelta(hours=int(m.group(1)))),
        (r"(\d+)分钟后", lambda m: now + timedelta(minutes=int(m.group(1)))),
    ]
    
    for pattern, func in patterns:
        match = re.search(pattern, input_lower)
        if match:
            try:
                if match.groups():
                    return func(match).timestamp()
                else:
                    return func().timestamp()
            except:
                continue
    
    return None


def _validate_time_calculation(calculated_ts: float, user_input: str, current_time: float) -> tuple:
    """
    验证时间计算的合理性
    
    Args:
        calculated_ts: 计算出的时间戳
        user_input: 用户输入
        current_time: 当前时间戳
        
    Returns:
        (is_valid, error_message)
    """
    from datetime import datetime, timedelta
    
    calculated_dt = datetime.fromtimestamp(calculated_ts)
    current_dt = datetime.fromtimestamp(current_time)
    
    # 检查：计算出的时间不能是过去（除非是历史查询）
    if calculated_ts < current_time and "历史" not in user_input and "过去" not in user_input:
        return False, f"计算出的时间 {calculated_dt.strftime('%Y-%m-%d %H:%M')} 是过去的时间，不合理"
    
    # 检查：相对时间"明天"不能是今天
    if "明天" in user_input:
        tomorrow = current_dt + timedelta(days=1)
        if calculated_dt.date() != tomorrow.date():
            return False, f"'明天'应该计算为 {tomorrow.strftime('%Y-%m-%d')}，但计算结果是 {calculated_dt.strftime('%Y-%m-%d')}"
    
    return True, None


def _classify_tool_error(error: Exception) -> str:
    """
    分类工具错误类型
    
    Args:
        error: 异常对象
        
    Returns:
        错误类型: "network" | "parameter" | "service" | "timeout" | "unknown"
    """
    error_str = str(error).lower()
    if any(kw in error_str for kw in ["timeout", "timed out", "超时"]):
        return "timeout"
    elif any(kw in error_str for kw in ["network", "connection", "网络", "连接", "connect"]):
        return "network"
    elif any(kw in error_str for kw in ["parameter", "argument", "参数", "invalid", "missing"]):
        return "parameter"
    elif any(kw in error_str for kw in ["service", "unavailable", "服务", "不可用", "503", "502", "500"]):
        return "service"
    else:
        return "unknown"


def _detect_required_tools(user_input: str, history: List = None) -> List[str]:
    """
    使用LLM智能检测用户输入需要哪些工具
    
    完全使用LLM判断，不依赖hardcode规则，能够理解：
    1. 指代消解（"那空气呢？"）
    2. 上下文相关的查询
    3. 语义理解
    
    Args:
        user_input: 用户输入
        history: 对话历史（用于指代消解）
        
    Returns:
        需要的工具名称列表
    """
    try:
        from .model_manager import get_model_manager
        from .tools import AVAILABLE_TOOLS
        
        # 使用 Chat 模型进行工具检测（理解更稳）
        model_manager = get_model_manager()
        fast_llm, model_name = model_manager.select_model(
            task_type="chat",
            user_input=user_input,
            conversation_history=history or [],
            has_tools=False
        )
        
        # 构建工具列表描述
        tool_names = [tool.name for tool in AVAILABLE_TOOLS]
        tool_descriptions = "\n".join([f"- {tool.name}: {tool.description}" for tool in AVAILABLE_TOOLS])
        
        # 构建对话历史上下文
        history_context = ""
        if history:
            recent_history = history[-3:]  # 取最近3条
            history_parts = []
            for conv in recent_history:
                if isinstance(conv, dict):
                    user_msg = conv.get("user", "")
                    assistant_msg = conv.get("assistant", "")
                    if user_msg:
                        history_parts.append(f"用户: {user_msg}")
                    if assistant_msg:
                        history_parts.append(f"助手: {assistant_msg[:80]}...")
            if history_parts:
                history_context = "\n".join(history_parts)
        
        # 构建工具检测prompt
        tool_detection_prompt = ChatPromptTemplate.from_messages([
            ("system", """你是一个工具需求分析器。根据用户输入和对话历史，判断需要调用哪些工具。

可用工具列表：
{tool_descriptions}

分析原则：
1. 如果用户查询需要实时信息（天气、空气质量、新闻、时间、提醒/日程等），必须返回对应的工具
2. 如果用户输入包含指代词（"那"、"这个"、"那个"、"呢"等），需要结合对话历史理解指代
3. 如果用户只是闲聊、问候、控制命令，不需要工具，返回空列表
4. 特别注意："空气"、"空气怎么样"、"空气质量"等通常需要web_search_tool查询

【示例】
- "帮我查一下科比的资料" → ["web_search_tool"]
- "北京天气怎么样" → ["weather_tool"]  
- "提醒我明天开会" → ["create_schedule_tool"]
- "记住我妈妈生日是3月15号" → ["create_schedule_tool"]
- "你好呀" → []

只返回工具名称列表（JSON数组格式），例如：["web_search_tool"] 或 ["weather_tool"] 或 []。
不要返回其他内容，只返回JSON数组。"""),
            ("human", """用户输入：{user_input}

{history_context}

请分析需要调用哪些工具。只返回工具名称的JSON数组，例如：["web_search_tool"] 或 []。""")
        ])
        
        response = (tool_detection_prompt | fast_llm).invoke({
            "user_input": user_input,
            "tool_descriptions": tool_descriptions,
            "history_context": f"对话历史：\n{history_context}" if history_context else "无对话历史"
        })
        
        # 解析LLM响应（JSON数组格式）
        import re
        result_text = response.content.strip()
        
        # 尝试提取JSON数组
        json_match = re.search(r'\[[\s\S]*?\]', result_text)
        if json_match:
            try:
                tools = json.loads(json_match.group())
                if isinstance(tools, list):
                    # 验证工具名称是否有效
                    valid_tools = [tool for tool in tools if tool in tool_names]
                    if valid_tools:
                        print(f"   LLM检测到工具需求（{model_name}）: {valid_tools}")
                        return valid_tools
                    else:
                        print(f"[WARN] LLM返回的工具名称无效: {tools}")
                        return []
                else:
                    print(f"[WARN] LLM返回的不是列表格式: {tools}")
                    return []
            except json.JSONDecodeError as e:
                print(f"[WARN] LLM返回的JSON解析失败: {e}, 原始响应: {result_text}")
                return []
        else:
            # 如果没有找到JSON数组，尝试直接解析
            print(f"[WARN] 未找到JSON数组，原始响应: {result_text}")
            return []
            
    except Exception as e:
        print(f"[WARN] LLM工具检测失败: {e}，返回空列表")
        # 降级策略：如果LLM失败，返回空列表（不调用工具，让reasoning节点处理）
        return []


def _convert_step_to_tool_call(step: Dict) -> Optional[Dict]:
    """
    将执行计划步骤转换为 tool_calls 格式
    
    Args:
        step: execution_plan 中的单个步骤
        
    Returns:
        tool_call 字典，或 None（如果不是工具调用步骤）
    """
    if step.get("action_type") != "tool_call":
        return None
    
    tool_name = step.get("tool_name")
    if not tool_name:
        return None
    
    return {
        "id": f"plan_step_{step.get('step_id', 0)}",
        "name": tool_name,
        "args": step.get("tool_args", {})
    }


def _format_tool_results_for_prompt(execution_plan: Dict) -> str:
    """
    从execution_plan中提取所有工具结果，格式化为易读的文本
    
    Args:
        execution_plan: 执行计划字典
        
    Returns:
        格式化的工具结果文本，如果没有工具结果则返回空字符串
    """
    if not execution_plan:
        return ""
    
    steps = execution_plan.get("steps", [])
    if not steps:
        return ""
    
    tool_results = []
    for step in steps:
        if step.get("action_type") == "tool_call":
            tool_name = step.get("tool_name", "未知工具")
            tool_args = step.get("tool_args", {})
            result = step.get("result")
            
            if result:
                # result可能是字典格式（包含tool_call_id, output等）或直接是字符串
                if isinstance(result, dict):
                    output = result.get("output", result.get("error", "无输出"))
                    error = result.get("error")
                    error_type = result.get("error_type", "unknown")
                    if error:
                        # 根据错误类型生成用户友好的描述
                        error_descriptions = {
                            "network": "网络连接问题，可能是网络不稳定或服务暂时不可用",
                            "timeout": "请求超时，服务响应时间过长",
                            "parameter": "参数错误，工具调用参数不正确",
                            "service": "服务不可用，外部服务暂时无法访问",
                            "unknown": "未知错误"
                        }
                        error_desc = error_descriptions.get(error_type, "未知错误")
                        tool_results.append(f"工具: {tool_name}\n状态: 失败\n错误类型: {error_desc}\n错误详情: {error}")
                    else:
                        tool_results.append(f"工具: {tool_name}\n状态: 成功\n结果: {output}")
                else:
                    tool_results.append(f"工具: {tool_name}\n状态: 成功\n结果: {result}")
    
    if tool_results:
        return "\n\n".join(tool_results)
    return ""


def _format_tool_results_with_error_handling(tool_results: List[Dict]) -> str:
    """
    格式化工具结果，包含错误处理信息
    
    Args:
        tool_results: 工具结果列表（来自 state["tool_results"]）
        
    Returns:
        格式化的工具结果文本
    """
    formatted = []
    for result in tool_results:
        tool_name = result.get("tool_name", "未知工具")
        if "error" in result:
            error_type = result.get("error_type", "unknown")
            error_msg = result.get("error", "")
            
            # 根据错误类型生成用户友好的描述
            error_descriptions = {
                "network": "网络连接问题，可能是网络不稳定或服务暂时不可用",
                "timeout": "请求超时，服务响应时间过长",
                "parameter": "参数错误，工具调用参数不正确",
                "service": "服务不可用，外部服务暂时无法访问",
                "unknown": "未知错误"
            }
            error_desc = error_descriptions.get(error_type, "未知错误")
            formatted.append(f"工具: {tool_name}\n状态: 失败\n错误类型: {error_desc}\n错误详情: {error_msg}")
        else:
            output = result.get("output", "")
            formatted.append(f"工具: {tool_name}\n状态: 成功\n结果: {output}")
    return "\n\n".join(formatted)


def _validate_tool_args(tool_name: str, tool_args: Dict[str, Any]) -> tuple:
    """
    验证工具参数的正确性
    
    Args:
        tool_name: 工具名称
        tool_args: 工具参数字典
        
    Returns:
        (is_valid, error_message)
    """
    # 定义每个工具的参数规则
    tool_rules = {
        "create_schedule_tool": {
            "required": ["title", "datetime_ts"],
            "optional": ["schedule_type", "reminder_minutes", "description", "recurrence_type", "recurrence_value"],
            "type_checks": {
                "datetime_ts": (float, int),  # 必须是数字（时间戳）
                "reminder_minutes": int,
                "recurrence_value": int
            },
            "value_checks": {
                "schedule_type": ["schedule", "reminder", "todo", "note"],
                "recurrence_type": ["daily", "weekly", "monthly", "yearly", None]
            },
            "conditional_rules": [
                # yearly 类型不需要 recurrence_value
                {
                    "if": {"recurrence_type": "yearly"},
                    "then": {"recurrence_value": None},
                    "error": "yearly 类型不需要 recurrence_value 参数"
                },
                # weekly 类型需要 recurrence_value (0-6)
                {
                    "if": {"recurrence_type": "weekly"},
                    "then": {"recurrence_value": lambda v: 0 <= v <= 6},
                    "error": "weekly 类型的 recurrence_value 必须是 0-6（0=周一，6=周日）"
                },
                # monthly 类型需要 recurrence_value (1-31)
                {
                    "if": {"recurrence_type": "monthly"},
                    "then": {"recurrence_value": lambda v: 1 <= v <= 31},
                    "error": "monthly 类型的 recurrence_value 必须是 1-31"
                }
            ]
        },
        "weather_tool": {
            "required": ["city"],
            "optional": ["days"],
            "type_checks": {
                "days": int
            },
            "value_checks": {
                "days": lambda v: 0 <= v <= 7  # days 范围 0-7
            }
        }
    }
    
    if tool_name not in tool_rules:
        return True, None  # 未知工具，不验证
    
    rules = tool_rules[tool_name]
    
    # 检查必需参数
    for required_param in rules.get("required", []):
        if required_param not in tool_args:
            return False, f"缺少必需参数: {required_param}"
    
    # 检查类型
    for param, expected_types in rules.get("type_checks", {}).items():
        if param in tool_args:
            if not isinstance(tool_args[param], expected_types):
                return False, f"参数 {param} 类型错误，期望 {expected_types}，实际 {type(tool_args[param])}"
    
    # 检查值范围
    for param, check_func in rules.get("value_checks", {}).items():
        if param in tool_args:
            if isinstance(check_func, list):
                if tool_args[param] not in check_func:
                    return False, f"参数 {param} 值错误，期望 {check_func} 之一，实际 {tool_args[param]}"
            elif callable(check_func):
                if not check_func(tool_args[param]):
                    return False, f"参数 {param} 值不在有效范围内"
    
    # 检查条件规则
    for rule in rules.get("conditional_rules", []):
        condition = rule["if"]
        if all(tool_args.get(k) == v for k, v in condition.items()):
            then_rule = rule["then"]
            for param, constraint in then_rule.items():
                if param in tool_args:
                    if constraint is None:
                        if tool_args[param] is not None:
                            return False, rule.get("error", f"参数 {param} 应该为 None")
                    elif callable(constraint):
                        if not constraint(tool_args[param]):
                            return False, rule.get("error", f"参数 {param} 不符合约束条件")
    
    return True, None


def _validate_tool_result(tool_name: str, result: str) -> tuple:
    """
    验证工具结果的合理性
    
    Args:
        tool_name: 工具名称
        result: 工具返回的结果字符串
        
    Returns:
        (is_valid, warning_message, error_message)
    """
    if not result or result.strip() == "":
        return False, None, "工具返回结果为空"
    
    # 定义每个工具的结果验证规则
    validation_rules = {
        "weather_tool": {
            "must_contain": ["温度", "°C", "天气"],
            "value_checks": {
                "temperature": lambda v: -50 <= v <= 60,  # 温度范围
            },
            "pattern_checks": [
                (r"(\d+)°C", "温度值", lambda m: -50 <= int(m.group(1)) <= 60)
            ]
        },
        "calculator_tool": {
            "must_not_contain": ["error", "Error", "错误", "undefined", "NaN", "Infinity"],
            "pattern_checks": [
                (r"^[\d\.\+\-\*\/\(\)\s]+$", "数学表达式格式", None)
            ]
        },
        "air_quality_tool": {
            "must_contain": ["AQI", "空气质量"],
            "value_checks": {
                "aqi": lambda v: 0 <= v <= 500,  # AQI 范围
            }
        }
    }
    
    if tool_name not in validation_rules:
        return True, None, None  # 未知工具，不验证
    
    rules = validation_rules[tool_name]
    
    # 检查必须包含的关键词
    for keyword in rules.get("must_contain", []):
        if keyword not in result:
            return False, None, f"结果缺少必需信息: {keyword}"
    
    # 检查不能包含的关键词
    for keyword in rules.get("must_not_contain", []):
        if keyword in result:
            return False, None, f"结果包含错误信息: {keyword}"
    
    # 模式检查
    import re
    for pattern, desc, check_func in rules.get("pattern_checks", []):
        match = re.search(pattern, result)
        if match:
            if check_func and not check_func(match):
                return False, None, f"{desc} 验证失败: {match.group(0)}"
        else:
            return False, None, f"结果格式不符合预期: 缺少 {desc}"
    
    return True, None, None


def _extract_schedule_id_from_query_result(
    query_result: dict, 
    user_input: str, 
    conversation_history: List
) -> Optional[str]:
    """
    从 query_schedule_tool 的结果中提取要删除的 schedule_id
    
    策略：
    1. 解析查询结果中的日程列表
    2. 根据用户输入和对话历史，找到最匹配的日程
    3. 返回其 schedule_id
    
    Args:
        query_result: query_schedule_tool 的返回结果
        user_input: 用户输入（如"取消刚刚的闹钟"）
        conversation_history: 对话历史（用于理解"刚刚"指的是什么）
        
    Returns:
        schedule_id 或 None
    """
    import re
    import json
    
    # 从 query_result 中提取输出文本
    output_text = ""
    if isinstance(query_result, dict):
        output_text = query_result.get("output", "")
    elif isinstance(query_result, str):
        output_text = query_result
    
    if not output_text:
        return None
    
    # 尝试解析 JSON 格式的结果（如果有的话）
    schedules = []
    
    # 方式1：从文本中提取 schedule_id（格式：ID: xxx 或 id: xxx）
    id_matches = re.findall(r'[Ii][Dd][:：]\s*([a-zA-Z0-9_-]+)', output_text)
    
    # 方式2：尝试解析结构化数据
    try:
        # 检查是否有 JSON 格式的数据
        json_match = re.search(r'\{.*\}|\[.*\]', output_text, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group())
            if isinstance(data, list):
                schedules = data
            elif isinstance(data, dict) and "schedules" in data:
                schedules = data["schedules"]
    except:
        pass
    
    # 如果有结构化数据，从中提取
    if schedules:
        # 分析用户意图，确定要删除哪个
        # 优先策略：
        # 1. 如果用户说"刚刚"/"刚才"/"那个"，选择最近创建的
        # 2. 如果用户说了具体时间（如"明天九点"），匹配时间
        # 3. 否则选择第一个
        
        recent_keywords = ["刚刚", "刚才", "那个", "这个", "刚设的"]
        is_recent = any(kw in user_input for kw in recent_keywords)
        
        if is_recent and schedules:
            # 选择最近创建的（假设列表按创建时间排序，最后一个是最新的）
            # 或者选择第一个（取决于 query 的排序）
            target = schedules[-1] if len(schedules) > 0 else None
            if target and "id" in target:
                return target["id"]
        
        # 尝试从对话历史中提取时间信息
        time_keywords = ["九点", "9点", "十点", "10点", "八点", "8点"]
        for schedule in schedules:
            schedule_str = str(schedule)
            # 检查是否匹配对话历史中的时间
            for msg in conversation_history[-3:]:  # 只看最近3条
                msg_content = msg.get("content", "") if isinstance(msg, dict) else str(msg)
                for kw in time_keywords:
                    if kw in msg_content and kw in schedule_str:
                        if "id" in schedule:
                            return schedule["id"]
        
        # 默认返回第一个
        if schedules and "id" in schedules[0]:
            return schedules[0]["id"]
    
    # 如果只找到了 ID 列表（从文本中提取的）
    if id_matches:
        # 如果用户说"刚刚"，返回最后一个（最新的）
        recent_keywords = ["刚刚", "刚才", "那个", "这个", "刚设的"]
        is_recent = any(kw in user_input for kw in recent_keywords)
        
        if is_recent:
            return id_matches[-1]  # 返回最后一个
        return id_matches[0]  # 默认返回第一个
    
    return None


def _extract_city_from_context(state: LampState) -> Optional[str]:
    """
    从state中提取用户所在城市
    
    优先级：
    1. user_profile.city（直接从state中获取）
    2. memory_context.user_profile（从记忆上下文中解析）
    
    Args:
        state: 当前状态
        
    Returns:
        城市名称（如"上海"），如果未找到则返回None
    """
    # 优先级1: user_profile.city
    user_profile = state.get("user_profile", {})
    if isinstance(user_profile, dict):
        city = user_profile.get("city", "")
        if city and city != "未知" and city.strip():
            return city.strip()
    
    # 优先级2: memory_context.user_profile（文本格式）
    memory_context = state.get("memory_context", {})
    if memory_context:
        user_profile_text = memory_context.get("user_profile", "")
        if user_profile_text and user_profile_text != "暂无详细画像":
            # 解析"常住地: 上海"或"当前位置: 上海"格式
            for line in user_profile_text.split("\n"):
                line = line.strip()
                if not line:
                    continue
                # 移除"- "前缀（如果有）
                if line.startswith("- "):
                    line = line[2:]
                # 检查是否包含城市信息
                if "常住地:" in line or "当前位置:" in line:
                    parts = line.split(":", 1)
                    if len(parts) == 2:
                        city = parts[1].strip()
                        if city and city != "未知" and city.strip():
                            return city.strip()
                # 也检查"所在地"等关键词
                elif "所在地" in line or "住在" in line:
                    # 尝试提取城市名
                    cities = ["北京", "上海", "深圳", "广州", "杭州", "成都", "武汉", "南京", "苏州", "重庆", 
                             "西安", "天津", "厦门", "青岛", "大连", "长沙", "郑州", "济南"]
                    for city in cities:
                        if city in line:
                            return city
    
    return None


# ==========================================
# 工具参数提取器（使用轻量级LLM）
# ==========================================

class ToolParameterExtractor:
    """
    使用轻量级LLM（本地Ollama）提取工具参数
    
    为什么使用轻量级模型：
    1. 成本低：本地运行，无API调用费用
    2. 速度快：小模型推理快
    3. 通用化：能够理解用户意图，提取关键参数
    4. 隐私好：数据不离开本地
    """
    
    def __init__(self, ollama_url: str = "http://localhost:11434", model: str = "llama3.2:3b"):
        self.ollama_url = ollama_url
        self.model = model
        self.timeout = 10  # 轻量级模型应该很快
        
    def extract_parameters(self, user_input: str, tool_name: str, tool_schema: dict) -> dict:
        """
        提取工具参数
        
        Args:
            user_input: 用户输入
            tool_name: 工具名称
            tool_schema: 工具的参数schema
            
        Returns:
            提取的参数字典
        """
        # 构建prompt
        prompt = self._build_extraction_prompt(user_input, tool_name, tool_schema)
        
        try:
            # 调用Ollama
            response = self._call_ollama(prompt)
            
            # 解析返回的JSON参数
            return self._parse_response(response)
            
        except Exception as e:
            print(f"[WARN] LLM参数提取失败: {e}，回退到规则提取")
            # 返回空字典，让调用方使用规则提取作为后备
            return {}
    
    def _build_extraction_prompt(self, user_input: str, tool_name: str, tool_schema: dict) -> str:
        """构建参数提取的prompt"""
        
        prompt = f"""You are a parameter extraction assistant. Extract parameters from the user's input for the specified tool.

User Input: "{user_input}"

Tool Name: {tool_name}
Tool Description: {tool_schema.get('description', '')}

Available Parameters:
"""
        
        # 添加参数说明
        for param_name, param_info in tool_schema.get('parameters', {}).items():
            optional = " (optional)" if param_info.get('optional') else " (required)"
            prompt += f"- {param_name}: {param_info.get('description', '')}{optional}\n"
        
        prompt += """
Extract the parameters and return them as a JSON object. Do not include any other explanation. Format:
{
    "parameter_name1": "extracted_value1",
    "parameter_name2": "extracted_value2"
}

If you cannot extract a parameter:
- For optional parameters: omit them from the JSON
- For required parameters: return an empty string ""

Return only the JSON:
"""
        
        return prompt
    
    def _call_ollama(self, prompt: str) -> str:
        """调用Ollama API"""
        import requests
        
        url = f"{self.ollama_url}/api/generate"
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,  # 低温度，更确定性
                "num_predict": 200,  # 限制输出长度
            }
        }
        
        response = requests.post(url, json=payload, timeout=self.timeout)
        response.raise_for_status()
        
        result = response.json()
        return result.get("response", "")
    
    def _parse_response(self, response: str) -> dict:
        """解析LLM返回的JSON参数"""
        import json
        import re
        
        # 尝试直接解析JSON
        try:
            return json.loads(response.strip())
        except json.JSONDecodeError:
            pass
        
        # 尝试从文本中提取JSON块
        try:
            # 查找代码块
            match = re.search(r'```(?:json)?\s*([\s\S]*?)```', response)
            if match:
                return json.loads(match.group(1).strip())
            
            # 查找花括号包裹的内容
            match = re.search(r'\{[\s\S]*?\}', response)
            if match:
                return json.loads(match.group(0).strip())
        except (json.JSONDecodeError, AttributeError):
            pass
        
        # 如果都失败了，返回空字典
        print(f"[WARN] 无法解析LLM参数提取结果: {response[:100]}...")
        return {}


# 工具参数Schema定义
def _get_tool_schema(tool_name: str) -> dict:
    """获取工具的参数schema"""
    schemas = {
        "news_tool": {
            "description": "获取新闻信息",
            "parameters": {
                "keyword": {
                    "type": "string",
                    "description": "搜索关键词，应该是用户关心的具体话题或事件，如'微信屏蔽元宝'、'特斯拉降价'等"
                },
                "category": {
                    "type": "string",
                    "description": "新闻分类，可选值：tech(科技)、sports(体育)、entertainment(娱乐)、finance(财经)、general(时事)",
                    "optional": True
                }
            }
        },
        "web_search_tool": {
            "description": "网络搜索工具",
            "parameters": {
                "query": {
                    "type": "string",
                    "description": "搜索查询字符串，应该准确反映用户的搜索意图"
                }
            }
        },
        "weather_tool": {
            "description": "天气查询工具",
            "parameters": {
                "city": {
                    "type": "string",
                    "description": "城市名称，如'北京'、'上海'等"
                },
                "days": {
                    "type": "integer",
                    "description": "预报天数，0=今天，1=明天，2=后天",
                    "optional": True
                }
            }
        }
    }
    return schemas.get(tool_name, {})


# 全局参数提取器实例（延迟初始化）
_parameter_extractor: Optional[ToolParameterExtractor] = None

def get_parameter_extractor() -> ToolParameterExtractor:
    """获取全局参数提取器实例（单例模式）"""
    global _parameter_extractor
    if _parameter_extractor is None:
        _parameter_extractor = ToolParameterExtractor(
            ollama_url=os.environ.get("OLLAMA_URL", "http://localhost:11434"),
            model=os.environ.get("OLLAMA_MODEL", "llama3.2:3b")
        )
    return _parameter_extractor


def _extract_news_params_by_rules(user_input: str, tool_args: dict) -> None:
    """
    使用规则提取新闻工具的参数（回退方案）
    
    Args:
        user_input: 用户输入
        tool_args: 工具参数字典（直接修改）
    """
    # 完整的新闻类型关键词映射
    news_type_keywords = {
        "科技": ["科技", "技术", "AI", "人工智能", "互联网", "数码"],
        "娱乐": ["娱乐", "明星", "综艺", "电影", "电视剧", "八卦"],
        "体育": ["体育", "足球", "篮球", "NBA", "世界杯", "奥运"],
        "财经": ["财经", "股票", "基金", "经济", "金融", "理财"],
        "游戏": ["游戏", "电竞", "手游", "端游", "Switch", "PS5"],
        "社会": ["社会", "民生", "时事"],
        "科学": ["科学", "研究", "医学", "健康"],
        "国际": ["国际", "世界", "外国", "海外"],
        "军事": ["军事", "军队", "国防"],
    }
    
    # 检测用户输入中的新闻类型关键词
    for keyword_type, keywords in news_type_keywords.items():
        if any(kw in user_input for kw in keywords):
            tool_args["keyword"] = keyword_type
            break


def _generate_simple_plan(user_input: str, required_tools: List[str], state: LampState = None) -> Dict:
    """
    生成简单的执行计划（不调用 LLM）
    
    Args:
        user_input: 用户输入
        required_tools: 需要的工具列表
        state: 当前状态（可选，用于提取城市信息等上下文）
        
    Returns:
        执行计划字典
    """
    import uuid
    
    steps = []
    step_id = 1
    
    # 为每个工具创建一个步骤
    for tool_name in required_tools:
        # 提取工具参数
        tool_args = {}
        
        if tool_name == "weather_tool":
            # 尝试提取城市名
            cities = ["北京", "上海", "深圳", "广州", "杭州", "成都", "武汉", "南京", "苏州", "重庆"]
            city = None
            for c in cities:
                if c in user_input:
                    city = c
                    break
            
            # 如果用户输入中没有城市，从state中提取
            if not city and state:
                city = _extract_city_from_context(state)
            
            tool_args["city"] = city if city else "北京"  # 默认城市
            
            # 尝试提取预报天数（明天、后天等）
            if "明天" in user_input or "明日" in user_input:
                tool_args["days"] = 1
            elif "后天" in user_input:
                tool_args["days"] = 2
            elif "大后天" in user_input:
                tool_args["days"] = 3
            else:
                tool_args["days"] = 0  # 默认实时天气
        
        elif tool_name == "air_quality_tool":
            # 空气质量工具，参数与天气工具类似
            cities = ["北京", "上海", "深圳", "广州", "杭州", "成都", "武汉", "南京", "苏州", "重庆",
                     "西安", "天津", "厦门", "青岛", "大连", "长沙", "郑州", "济南"]
            city = None
            for c in cities:
                if c in user_input:
                    city = c
                    break
            
            # 如果用户输入中没有城市，从 state 中提取
            if not city and state:
                city = _extract_city_from_context(state)
            
            tool_args["city"] = city if city else "北京"  # 默认城市
            
            # 提取预报天数
            if "明天" in user_input or "明日" in user_input:
                tool_args["days"] = 1
            elif "后天" in user_input:
                tool_args["days"] = 2
            elif "大后天" in user_input:
                tool_args["days"] = 3
            else:
                tool_args["days"] = 0  # 默认实时
        
        elif tool_name == "web_search_tool":
            # web_search_tool 只接受 query 参数，城市信息需要包含在查询字符串中
            query = user_input
            
            # 检查用户输入中是否已包含城市名
            cities = ["北京", "上海", "深圳", "广州", "杭州", "成都", "武汉", "南京", "苏州", "重庆",
                     "西安", "天津", "厦门", "青岛", "大连", "长沙", "郑州", "济南"]
            has_city_in_input = any(city in user_input for city in cities)
            
            # 如果用户输入中没有城市，且查询需要城市信息（如空气质量、天气等），从state中提取
            if not has_city_in_input and state:
                # 检查是否是需要城市信息的查询类型
                # 【关键修复】"空气"也应该被认为是需要城市信息的查询
                city_related_keywords = ["空气质量", "天气", "温度", "pm2.5", "aqi", "污染", "空气"]
                needs_city = any(kw in user_input for kw in city_related_keywords)
                
                if needs_city:
                    city = _extract_city_from_context(state)
                    if city:
                        # 将城市信息添加到查询字符串前面
                        query = f"{city} {user_input}"
                        print(f"   从记忆提取城市信息并注入查询: {query}")
            
            tool_args["query"] = query
            tool_args["max_results"] = 5
        
        elif tool_name == "time_tool":
            tool_args["timezone"] = "北京"
        
        elif tool_name == "news_tool":
            # 【新】使用LLM提取参数，回退到规则提取
            try:
                extractor = get_parameter_extractor()
                tool_schema = _get_tool_schema("news_tool")
                extracted_args = extractor.extract_parameters(user_input, "news_tool", tool_schema)
                
                if extracted_args and "keyword" in extracted_args:
                    tool_args["keyword"] = extracted_args["keyword"]
                    print(f"   [LLM提取] news_tool keyword: {extracted_args['keyword']}")
                else:
                    # 回退到规则提取
                    _extract_news_params_by_rules(user_input, tool_args)
            except Exception as e:
                print(f"[WARN] LLM参数提取失败: {e}，使用规则提取")
                _extract_news_params_by_rules(user_input, tool_args)
            
            tool_args["limit"] = 3
        
        elif tool_name == "create_schedule_tool":
            # 【Plan 重构】添加 create_schedule_tool 参数提取
            import re
            from datetime import datetime, timedelta
            
            # 提取提醒内容（标题）
            title = "提醒"
            # 尝试提取"提醒我XXX"中的内容
            remind_patterns = [
                r"提醒我(.+?)(?:$|，|。)",
                r"提醒(.+?)(?:$|，|。)",
                r"记得(.+?)(?:$|，|。)",
                r"别忘了(.+?)(?:$|，|。)",
            ]
            for pattern in remind_patterns:
                match = re.search(pattern, user_input)
                if match:
                    content = match.group(1).strip()
                    # 移除时间相关词汇，保留核心内容
                    time_words = ["分钟后", "小时后", "秒后", "点", "明天", "后天", "下午", "上午", "晚上"]
                    for tw in time_words:
                        content = content.replace(tw, "").strip()
                    # 移除数字前缀
                    content = re.sub(r"^\d+", "", content).strip()
                    if content:
                        title = content
                    break
            
            # 如果标题仍然是默认值，尝试提取动作词
            if title == "提醒":
                action_words = ["喝水", "吃饭", "休息", "运动", "睡觉", "起床", "开会", "打卡", "吃药"]
                for word in action_words:
                    if word in user_input:
                        title = f"{word}提醒"
                        break
            
            # 计算时间戳
            now = datetime.now()
            datetime_ts = None
            target_time = None
            
            # 优先尝试解析相对时间（X分钟后、X小时后）
            delay_seconds = _parse_delay_seconds(user_input)
            if delay_seconds is not None:
                target_time = now + timedelta(seconds=delay_seconds)
                datetime_ts = target_time.timestamp()
                print(f"   ⏰ 解析相对时间: {delay_seconds}秒后 -> {target_time.strftime('%Y-%m-%d %H:%M:%S')}")
            else:
                # 尝试解析绝对时间（如"明天早上九点"、"下午3点"）
                target_time = _parse_absolute_datetime(user_input)
                if target_time is not None:
                    datetime_ts = target_time.timestamp()
                    print(f"   ⏰ 解析绝对时间: {target_time.strftime('%Y-%m-%d %H:%M:%S')}")
                else:
                    # 无法解析时间，设置标记让 LLM 处理
                    datetime_ts = None
                    print(f"[WARN] 无法解析时间，需要向用户确认具体时间")
            
            # 如果时间解析失败，跳过这个工具，让 LLM 向用户确认
            if datetime_ts is None:
                print(f"[ERROR] 跳过 create_schedule_tool：无法解析时间")
                # 不添加这个工具步骤，让 LLM 在回复中询问用户
                continue
            
            tool_args["title"] = title
            tool_args["datetime_ts"] = datetime_ts
            tool_args["schedule_type"] = "reminder"
            tool_args["description"] = user_input
        
        elif tool_name == "countdown_timer_tool":
            # 【倒计时工具】参数提取
            import re
            
            # 提取提醒内容（标题）
            title = "提醒"
            # 尝试提取"提醒我XXX"中的内容
            remind_patterns = [
                r"提醒我(.+?)(?:$|，|。)",
                r"提醒(.+?)(?:$|，|。)",
                r"记得(.+?)(?:$|，|。)",
                r"别忘了(.+?)(?:$|，|。)",
            ]
            for pattern in remind_patterns:
                match = re.search(pattern, user_input)
                if match:
                    content = match.group(1).strip()
                    # 移除时间相关词汇，保留核心内容
                    time_words = ["分钟后", "小时后", "秒后", "点", "明天", "后天", "下午", "上午", "晚上"]
                    for tw in time_words:
                        content = content.replace(tw, "").strip()
                    # 移除数字前缀
                    content = re.sub(r"^\d+", "", content).strip()
                    if content:
                        title = content
                    break
            
            # 如果标题仍然是默认值，尝试提取动作词
            if title == "提醒":
                action_words = ["喝水", "吃饭", "休息", "运动", "睡觉", "起床", "开会", "打卡", "吃药"]
                for word in action_words:
                    if word in user_input:
                        title = word
                        break
            
            # 解析延迟秒数
            delay_seconds = _parse_delay_seconds(user_input)
            if delay_seconds is None:
                # 尝试解析绝对时间，转换为延迟秒数
                target_time = _parse_absolute_datetime(user_input)
                if target_time is not None:
                    from datetime import datetime
                    now = datetime.now()
                    delay_seconds = int((target_time - now).total_seconds())
                    if delay_seconds <= 0:
                        print(f"[ERROR] 时间已过，跳过 countdown_timer_tool")
                        continue
                    print(f"   ⏰ 解析绝对时间，转换为延迟: {delay_seconds}秒")
                else:
                    # 无法解析时间，跳过这个工具
                    print(f"[ERROR] 跳过 countdown_timer_tool：无法解析时间")
                    continue
            else:
                print(f"   ⏰ 解析延迟时间: {delay_seconds}秒")
            
            tool_args["title"] = title
            tool_args["delay_seconds"] = delay_seconds
            tool_args["message"] = f"该{title}了！"
        
        elif tool_name == "query_schedule_tool":
            # 【查询日程工具】参数提取
            from datetime import datetime, timedelta
            now = datetime.now()
            
            # 默认查询今天和明天的日程
            tool_args["start_ts"] = now.replace(hour=0, minute=0, second=0).timestamp()
            tool_args["end_ts"] = (now + timedelta(days=2)).replace(hour=23, minute=59, second=59).timestamp()
            tool_args["include_completed"] = False
            print(f"   查询日程：今天到后天")
        
        elif tool_name == "delete_schedule_tool":
            # 【删除日程工具】参数提取
            # 标记为需要从前一步（query_schedule_tool）的结果中动态提取 schedule_id
            tool_args["schedule_id"] = "__EXTRACT_FROM_QUERY__"
            tool_args["_depends_on_query"] = True  # 标记依赖
            tool_args["_user_input"] = user_input  # 保存用户输入，用于匹配
            print(f"   删除日程：需要从查询结果动态提取 ID")
        
        steps.append({
            "step_id": step_id,
            "description": f"调用 {tool_name}",
            "action_type": "tool_call",
            "tool_name": tool_name,
            "tool_args": tool_args,
            "expected_output": f"{tool_name} 返回结果",
            "depends_on": []
        })
        step_id += 1
    
    # 如果没有工具调用，添加一个 LLM 推理步骤
    if not steps:
        steps.append({
            "step_id": 1,
            "description": "直接回复用户",
            "action_type": "llm_reasoning",
            "tool_name": None,
            "tool_args": {},
            "expected_output": "用户回复",
            "depends_on": []
        })
    
    # 最后添加一个生成回复的步骤
    if required_tools:
        steps.append({
            "step_id": step_id,
            "description": "基于工具结果生成回复",
            "action_type": "llm_reasoning",
            "tool_name": None,
            "tool_args": {},
            "expected_output": "最终用户回复",
            "depends_on": list(range(1, step_id))
        })
    
    return {
        "plan_id": str(uuid.uuid4())[:8],
        "created_at": time.time(),
        "complexity": "simple" if len(required_tools) <= 1 else "moderate",
        "steps": steps,
        "total_steps": len(steps),
        "required_tools": required_tools,
        "estimated_time": len(required_tools) * 2.0 + 1.0
    }


def _generate_plan_with_llm(
    user_input: str, 
    xml_context: str, 
    tool_descriptions: str,
    llm_instance = None
) -> Dict:
    """
    使用 LLM 生成执行计划
    
    Args:
        user_input: 用户输入
        xml_context: XML 格式化的上下文
        tool_descriptions: 可用工具描述
        
    Returns:
        执行计划字典
    """
    import uuid
    from datetime import datetime, timedelta
    
    # 获取当前时间信息
    current_time_ts = time.time()
    current_time_str = datetime.fromtimestamp(current_time_ts).strftime("%Y-%m-%d %H:%M:%S")
    tomorrow_ts = current_time_ts + 86400  # 明天的 Unix 时间戳
    
    # 获取相似的情景记忆作为 Few-shot 示例
    from .memory_manager import get_memory_manager
    memory_manager = get_memory_manager()
    similar_episodes = memory_manager.retrieve_similar_episodes(user_input, k=2)
    few_shot_examples = ""
    
    if similar_episodes:
        few_shot_examples = "参考以下成功案例:\n"
        for i, episode in enumerate(similar_episodes, 1):
            try:
                content = episode["content"]
                few_shot_examples += f"\n案例 {i}:\n{content}\n"
            except:
                continue
    
    plan_prompt = ChatPromptTemplate.from_messages([
        ("system", """你是一个任务规划专家。根据用户输入和可用工具，分析任务并生成执行计划。

{few_shot_examples}

{xml_context}

可用工具：
{tool_descriptions}

【多意图识别规则】：
1. 检查用户输入是否包含多个意图关键词：
   - 连接词："然后"、"之后"、"接着"、"再"、"并且"、"同时"、"先"、"最后"
   - 动作序列："查...然后..."、"提醒...再..."
2. 如果检测到多个意图，必须拆分为多个步骤
3. 每个步骤对应一个独立的意图
4. 步骤之间使用 depends_on 字段标明依赖关系

【示例】：
用户输入："查一下北京天气，然后提醒我明天开会"
输出：
{{
    "complexity": "moderate",
    "steps": [
        {{
            "step_id": 1,
            "description": "查询北京天气",
            "action_type": "tool_call",
            "tool_name": "weather_tool",
            "tool_args": {{"city": "北京", "days": 0}},
            "expected_output": "北京实时天气信息",
            "depends_on": []
        }},
        {{
            "step_id": 2,
            "description": "创建明天开会的提醒",
            "action_type": "tool_call",
            "tool_name": "create_schedule_tool",
            "tool_args": {{"title": "开会", "datetime_ts": {tomorrow_ts}, "schedule_type": "reminder"}},
            "expected_output": "提醒创建成功",
            "depends_on": [1]
        }}
    ],
    "required_tools": ["weather_tool", "create_schedule_tool"]
}}

分析原则：
1. 如果任务只需要一个工具，直接调用该工具
2. 如果任务需要多个步骤，按顺序列出
3. 如果有条件逻辑（如果/当/若），需要标明条件

输出格式（JSON）：
{{
    "complexity": "simple|moderate|complex",
    "steps": [
        {{
            "step_id": 1,
            "description": "步骤描述",
            "action_type": "tool_call|llm_reasoning",
            "tool_name": "工具名称（如果是tool_call）",
            "tool_args": {{"参数名": "参数值"}},
            "expected_output": "预期输出",
            "depends_on": []
        }}
    ],
    "required_tools": ["工具名称列表"]
}}

注意：
- tool_name 必须是 AVAILABLE_TOOLS 中的有效名称（如 weather_tool, create_schedule_tool 等）
- 如果涉及到时间（如“提醒”、“以后”），必须参考 <core_memory_ram> 中的当前时间计算出准确的 Unix 时间戳作为 datetime_ts 参数。
- 如果用户只是聊天，action_type 应该是 "llm_reasoning"，不需要工具"""),
        ("human", "用户输入：{user_input}\n\n请生成执行计划：")
    ])
    
    try:
        # 使用传入的 LLM 实例，如果没有则使用全局 llm（向后兼容）
        plan_llm = llm_instance if llm_instance is not None else llm
        chain = plan_prompt | plan_llm
        response = chain.invoke({
            "xml_context": xml_context,
            "tool_descriptions": tool_descriptions,
            "user_input": user_input,
            "current_time_str": current_time_str,
            "current_time_ts": current_time_ts,
            "tomorrow_ts": tomorrow_ts,
            "few_shot_examples": few_shot_examples
        })
        
        # 解析 JSON 响应
        import re
        content = response.content.strip()
        
        # 尝试提取 JSON
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            plan_data = json.loads(json_match.group())
            
            # 补充必要字段
            plan_data["plan_id"] = str(uuid.uuid4())[:8]
            plan_data["created_at"] = time.time()
            plan_data["total_steps"] = len(plan_data.get("steps", []))
            plan_data["estimated_time"] = plan_data["total_steps"] * 2.0
            
            if "required_tools" not in plan_data:
                plan_data["required_tools"] = [
                    step["tool_name"] 
                    for step in plan_data.get("steps", []) 
                    if step.get("tool_name")
                ]
            
            return plan_data
        else:
            print(f"[WARN] LLM 返回格式错误，使用降级策略")
            return None
            
    except Exception as e:
        print(f"[WARN] LLM 规划失败: {e}")
        return None


def _validate_plan(plan: Dict) -> tuple:
    """
    验证计划的有效性
    
    Args:
        plan: 执行计划
        
    Returns:
        (is_valid, error_message)
    """
    if not plan:
        return False, "计划为空"
    
    if "steps" not in plan or not plan["steps"]:
        return False, "计划没有步骤"
    
    # 验证步骤数量
    if len(plan["steps"]) > 10:
        return False, "步骤过多（超过10步）"
    
    # 验证工具名称（从 AVAILABLE_TOOLS 动态获取，避免硬编码遗漏）
    valid_tools = [tool.name for tool in AVAILABLE_TOOLS]
    for step in plan["steps"]:
        if step.get("action_type") == "tool_call":
            tool_name = step.get("tool_name")
            if tool_name and tool_name not in valid_tools:
                return False, f"未知工具: {tool_name}"
    
    # 验证依赖关系（避免循环依赖）
    step_ids = {step.get("step_id") for step in plan["steps"]}
    for step in plan["steps"]:
        for dep in step.get("depends_on", []):
            if dep >= step.get("step_id", 0):
                return False, f"步骤 {step.get('step_id')} 存在无效依赖"
    
    return True, None


def plan_node(state: LampState) -> Dict[str, Any]:
    """
    规划节点：分析任务复杂度，制定执行计划
    
    职责：
    1. 分析任务是否需要多个步骤
    2. 识别任务中的条件逻辑
    3. 分解任务为有序步骤列表
    4. 将步骤中的工具需求转换为 tool_calls 格式
    5. 跟踪多步骤任务的执行进度
    
    Args:
        state: 当前状态
        
    Returns:
        更新后的状态字典
    """
    print("--- 规划节点 (Plan Node) ---")
    
    # 性能追踪
    tracker = get_tracker()
    tracker.start_node("plan")
    
    # === 1. 获取上下文管理器 ===
    context_manager = get_context_manager()
    
    # === 2. 检查是否是工具调用循环返回 ===
    tool_results = state.get("tool_results", [])
    existing_plan = state.get("execution_plan")
    
    if tool_results and existing_plan:
        # 这是从 tool_node 返回的循环
        print("   工具调用循环返回，处理结果...")
        
        current_step_index = state.get("current_step_index", 0)
        steps = existing_plan.get("steps", [])
        
        # 保存工具结果到当前步骤
        if current_step_index < len(steps):
            existing_plan["steps"][current_step_index]["result"] = tool_results[-1] if tool_results else None
        
        # 移动到下一步
        next_step_index = current_step_index + 1
        
        if next_step_index >= len(steps):
            # 计划执行完毕
            print(f"   计划执行完毕（共 {len(steps)} 步）")
            tracker.stop_node("plan")
            return {
                "execution_plan": existing_plan,
                "plan_status": "completed",
                "current_step_index": next_step_index,
                "tool_calls": [],  # 清空工具调用
                "tool_results": [],  # 清空工具结果
                "monologue": "计划执行完毕，准备生成最终回复..."
            }
        else:
            # 继续执行下一步
            next_step = steps[next_step_index]
            tool_call = _convert_step_to_tool_call(next_step)
            
            print(f"   执行下一步 ({next_step_index + 1}/{len(steps)}): {next_step.get('description', '未知')}")
            
            tracker.stop_node("plan")
            
            # 【关键修复】如果下一步是 llm_reasoning（不是 tool_call），
            # 说明工具调用已完成，应该返回 completed 让 reasoning_node 获取工具结果
            if next_step.get("action_type") == "llm_reasoning":
                print(f"   工具调用已完成，准备生成最终回复")
                return {
                    "execution_plan": existing_plan,
                    "plan_status": "completed",  # 标记为完成，让 reasoning_node 提取工具结果
                    "current_step_index": next_step_index,
                    "tool_calls": [],
                    "tool_results": [],
                    "monologue": "工具调用完成，准备生成最终回复..."
                }
            else:
                # 下一步还是 tool_call，继续执行
                
                # 【方案 B】检查是否需要动态提取参数（如 delete_schedule_tool 依赖 query 结果）
                tool_args = next_step.get("tool_args", {})
                if tool_args.get("_depends_on_query") and tool_args.get("schedule_id") == "__EXTRACT_FROM_QUERY__":
                    # 从前一步的查询结果中提取 schedule_id
                    prev_step = steps[current_step_index]
                    prev_result = prev_step.get("result", {})
                    
                    # 解析查询结果，找到匹配的日程
                    schedule_id = _extract_schedule_id_from_query_result(
                        prev_result, 
                        tool_args.get("_user_input", ""),
                        state.get("history", [])
                    )
                    
                    if schedule_id:
                        # 更新参数
                        next_step["tool_args"]["schedule_id"] = schedule_id
                        # 清理内部标记
                        next_step["tool_args"].pop("_depends_on_query", None)
                        next_step["tool_args"].pop("_user_input", None)
                        # 重新生成 tool_call
                        tool_call = _convert_step_to_tool_call(next_step)
                        print(f"   动态提取 schedule_id: {schedule_id}")
                    else:
                        # 无法提取，跳过删除步骤，直接完成
                        print(f"[WARN] 无法从查询结果中提取 schedule_id，跳过删除")
                        return {
                            "execution_plan": existing_plan,
                            "plan_status": "completed",
                            "current_step_index": next_step_index,
                            "tool_calls": [],
                            "tool_results": [],
                            "monologue": "未找到匹配的日程，无法删除"
                        }
                
                return {
                    "execution_plan": existing_plan,
                    "plan_status": "executing",
                    "current_step_index": next_step_index,
                    "tool_calls": [tool_call] if tool_call else [],
                    "tool_results": [],
                    "monologue": f"继续执行第 {next_step_index + 1} 步..."
                }
    
    # === 3. 首次规划：准备上下文 ===
    user_input = state.get("user_input", "")
    conversation_history = state.get("history", [])
    memory_context = state.get("memory_context", {})
    
    if not user_input:
        print(f"[WARN] 无用户输入，跳过规划")
        tracker.stop_node("plan")
        return {
            "execution_plan": None,
            "plan_status": "skipped",
            "plan_skip_reason": "no_user_input",
            "tool_calls": [],
            "current_step_index": 0
        }
    
    # === 4. 【重构】统一工具检测（LLM 优先，规则兜底） ===
    tracker.start("tool_detection")

    # 先用小模型进行工具检测（更泛化）
    required_tools = _detect_required_tools(user_input, conversation_history)
    if required_tools:
        print(f"   LLM 检测到工具需求: {required_tools}")
    else:
        # LLM 未检出时，回退到规则
        required_tools = _rule_based_tool_detection(user_input)
        if required_tools:
            print(f"   规则检测到工具需求: {required_tools}")

    tracker.stop("tool_detection")
    
    # === 5. 【重构】统一生成执行计划（所有任务都生成计划） ===
    plan = None
    complexity = _analyze_task_complexity(user_input, memory_context)
    print(f"   任务复杂度: {complexity}")
    
    # 【关键改动】对于有工具需求的任务，优先使用规则生成计划（更快更准）
    if required_tools:
        print(f"   生成工具调用计划: {required_tools}")
        plan = _generate_simple_plan(user_input, required_tools, state)
    elif complexity == "simple":
        # 简单任务（无工具）：生成纯 LLM 推理计划
        print("   生成简单回复计划（无工具）")
        plan = _generate_simple_plan(user_input, [], state)
    else:
        # 复杂任务：尝试使用 LLM 生成计划
        print("   使用 LLM 生成复杂计划...")
        
        # 准备上下文
        # 压缩对话历史
        tracker.start("plan_compression")
        compression_result = context_manager.compress_conversation_history(conversation_history)
        tracker.stop("plan_compression")
        formatted_history = context_manager.format_compressed_history(compression_result)
        
        # 清洗记忆上下文
        if memory_context:
            memory_context = context_manager.clean_memory_context(memory_context)
        
        # 获取用户画像
        user_profile_text = ""
        if memory_context:
            user_profile = memory_context.get("user_profile", "")
            if user_profile and user_profile != "暂无详细画像":
                profile_lines = [line.strip() for line in user_profile.split("\n") if line.strip()]
                profile_items = [line[2:] if line.startswith("- ") else line for line in profile_lines]
                if profile_items:
                    deduplicated = context_manager.deduplicate_user_profile(profile_items)
                    user_profile_text = "\n".join([f"- {item}" for item in deduplicated])
        
        # 构建 XML 上下文
        xml_context = context_manager.format_context_with_xml(
            user_profile=user_profile_text,
            recent_memories=memory_context.get("user_memories", [])[:3] if memory_context else [],
            action_patterns=[],
            conversation_history=formatted_history,
            current_state={
                "intimacy_level": state.get("intimacy_level", 30),
                "focus_mode": state.get("focus_mode", False),
                "conflict_state": state.get("conflict_state")
            }
        )
        
        # 调用 LLM 生成计划（规划任务总是使用 reasoning 模型）
        model_manager = get_model_manager()
        plan_llm, plan_model_name = model_manager.select_model(
            task_type="reasoning",  # 规划任务总是需要推理能力
            user_input=user_input,
            conversation_history=conversation_history,
            has_tools=len(required_tools) > 0
        )
        print(f"   规划使用模型: {plan_model_name}")
        
        tracker.start("llm_call_plan")
        plan = _generate_plan_with_llm(user_input, xml_context, get_tool_descriptions(), plan_llm)
        llm_time = tracker.stop("llm_call_plan")
        
        # 记录模型调用统计（规划任务总是使用 reasoning）
        estimated_tokens = len(user_input) // 2 + len(str(plan)) // 2 if plan else 500
        model_manager.record_call("reasoning", llm_time, estimated_tokens)
        
        print(f"   LLM 规划耗时: {llm_time:.3f}s (模型: {plan_model_name})")
        
        # 如果 LLM 失败，使用降级策略
        if not plan:
            print(f"[WARN] LLM 规划失败，使用降级策略")
            plan = _generate_simple_plan(user_input, required_tools, state)
    
    # === 8. 验证计划 ===
    is_valid, error = _validate_plan(plan)
    if not is_valid:
        print(f"[WARN] 计划验证失败: {error}，使用降级策略")
        plan = _generate_simple_plan(user_input, required_tools, state)
    
    # === 9. 转换第一步的工具调用 ===
    tool_calls = []
    if plan and plan.get("steps"):
        first_step = plan["steps"][0]
        tool_call = _convert_step_to_tool_call(first_step)
        if tool_call:
            tool_calls = [tool_call]
    
    # === 10. 返回结果 ===
    total_steps = len(plan.get("steps", [])) if plan else 0
    node_time = tracker.stop_node("plan")
    print(f"   生成 {total_steps} 步执行计划 (总耗时: {node_time:.3f}s)")
    
    return {
        "execution_plan": plan,
        "plan_status": "created" if plan else "failed",
        "current_step_index": 0,
        "tool_calls": tool_calls,
        "tool_results": [],
        "required_tools": required_tools,  # 【性能优化】传递工具需求，避免reasoning_node重复检测
        "monologue": f"我分析了你的请求，制定了 {total_steps} 步执行计划..." if plan else "规划失败，直接处理..."
    }


def plan_decision(state: LampState) -> str:
    """
    【Plan 重构】规划节点后的路由决策
    
    Returns:
        "direct_tool": Plan 已生成 tool_calls，直接执行工具
        "no_tool": 计划不需要工具（纯 LLM 推理）或计划已完成
    """
    plan_status = state.get("plan_status")
    
    # 如果计划已完成，进入推理节点生成最终回复
    if plan_status == "completed":
        return "no_tool"
    
    # 如果计划失败，进入推理节点处理
    if plan_status == "failed":
        return "no_tool"
    
    # 【关键】如果 Plan Node 已经生成了 tool_calls，直接路由到 tool_node
    tool_calls = state.get("tool_calls", [])
    if tool_calls:
        print(f"   Plan 已生成 tool_calls ({len(tool_calls)} 个)，直接路由到 tool_node")
        return "direct_tool"
    
    # 无工具调用，进入推理节点
    return "no_tool"


def reasoning_decision(state: LampState) -> str:
    """
    推理节点后的路由决策
    
    Returns:
        "tool_call": 当前步骤需要调用工具
        "complete": 推理完成，无需工具
    """
    # 检查是否有待执行的工具调用
    tool_calls = state.get("tool_calls", [])
    if tool_calls:
        return "tool_call"
    return "complete"