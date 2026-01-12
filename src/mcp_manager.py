import os
import json
import time
import asyncio
import logging
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass

# 可选导入 MCP 相关库
try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    MCP_AVAILABLE = True
except ImportError:
    ClientSession = None
    StdioServerParameters = None
    stdio_client = None
    MCP_AVAILABLE = False
    logging.warning("⚠️ MCP 库未安装，MCP 相关功能将不可用。安装命令: pip install mcp")

# 可选导入 OAuth 相关库
try:
    from authlib.integrations.requests_client import OAuth2Session
    OAUTH_AVAILABLE = True
except ImportError:
    OAuth2Session = None
    OAUTH_AVAILABLE = False
    logging.warning("⚠️ authlib 库未安装，OAuth 相关功能将不可用。安装命令: pip install authlib")

from .email_providers import create_email_provider, EmailProvider
from .content_providers import create_music_recommender, create_news_aggregator, MusicRecommender, NewsAggregator

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MCPManager")

@dataclass
class ToolInfo:
    name: str
    description: str
    parameters: Dict[str, Any]
    server_name: str

class MCPManager:
    """
    MCP 管理器 - 核心实现 (Task 1.1 & 1.3)
    管理多个 MCP Client 连接，提供工具调用路由和 OAuth 授权。
    """
    def __init__(self, token_file: str = "mcp_tokens.json"):
        self.clients = {}  # {server_name: (session, context_manager)}
        self.tool_registry = {}  # {tool_name: ToolInfo}
        self.token_file = token_file
        self.tokens = self._load_tokens()
        self.server_configs = {} # {server_name: config}
        self.email_providers = {}  # {provider_name: EmailProvider} - 支持 163、QQ、Outlook IMAP
        
        # 场景 4.1 & 4.2: 内容服务
        self.music_recommender = None  # 音乐推荐器
        self.news_aggregator = None  # 新闻聚合器

    def _load_tokens(self) -> Dict[str, Any]:
        """从文件加载 OAuth tokens"""
        if os.path.exists(self.token_file):
            try:
                with open(self.token_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"加载 token 文件失败: {e}")
        return {}

    def _save_tokens(self):
        """保存 OAuth tokens 到文件"""
        try:
            with open(self.token_file, 'w') as f:
                json.dump(self.tokens, f, indent=4)
        except Exception as e:
            logger.error(f"保存 token 文件失败: {e}")

    async def add_stdio_server(self, server_name: str, command: str, args: List[str] = None, env: Dict[str, str] = None):
        """
        添加本地 stdio MCP Server 连接 (Task 1.1)
        """
        if not MCP_AVAILABLE:
            logger.warning(f"⚠️ MCP 库未安装，无法添加 stdio server: {server_name}")
            logger.warning("   请运行: pip install mcp")
            return
        
        logger.info(f"正在连接 stdio MCP Server: {server_name}...")
        server_params = StdioServerParameters(
            command=command,
            args=args or [],
            env={**os.environ, **(env or {})}
        )
        
        # 使用 context manager 管理连接
        cm = stdio_client(server_params)
        read, write = await cm.__aenter__()
        session = ClientSession(read, write)
        await session.initialize()
        
        self.clients[server_name] = (session, cm)
        
        # 自动发现并注册工具
        tools = await session.list_tools()
        for tool in tools.tools:
            self.tool_registry[tool.name] = ToolInfo(
                name=tool.name,
                description=tool.description,
                parameters=tool.inputSchema,
                server_name=server_name
            )
            logger.info(f"  已注册工具: {tool.name} (来自 {server_name})")
        
        logger.info(f"✅ stdio MCP Server {server_name} 连接成功")

    def setup_oauth_client(self, server_name: str, client_id: str, client_secret: str, 
                          auth_url: str, token_url: str, scopes: List[str]):
        """
        配置 OAuth 2.0 客户端 (Task 1.3)
        """
        self.server_configs[server_name] = {
            "type": "oauth2",
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_url": auth_url,
            "token_url": token_url,
            "scopes": scopes
        }
        logger.info(f"已配置 OAuth 客户端: {server_name}")

    def get_authorization_url(self, server_name: str, redirect_uri: str) -> str:
        """获取 OAuth 授权 URL"""
        if not OAUTH_AVAILABLE:
            raise ImportError("OAuth 功能需要安装 authlib 库: pip install authlib")
        
        config = self.server_configs.get(server_name)
        if not config:
            raise ValueError(f"未找到服务器配置: {server_name}")
        
        client = OAuth2Session(config["client_id"], scope=' '.join(config["scopes"]), redirect_uri=redirect_uri)
        authorization_url, state = client.create_authorization_url(config["auth_url"])
        
        # 临时保存 state 以供后续验证（实际应用中应更安全地存储）
        if "states" not in self.tokens:
            self.tokens["states"] = {}
        self.tokens["states"][server_name] = state
        self._save_tokens()
        
        return authorization_url

    def handle_oauth_callback(self, server_name: str, authorization_response: str, redirect_uri: str):
        """处理 OAuth 回调，获取并保存 Token"""
        if not OAUTH_AVAILABLE:
            raise ImportError("OAuth 功能需要安装 authlib 库: pip install authlib")
        
        config = self.server_configs.get(server_name)
        if not config:
            raise ValueError(f"未找到服务器配置: {server_name}")
        
        state = self.tokens.get("states", {}).get(server_name)
        client = OAuth2Session(config["client_id"], state=state, redirect_uri=redirect_uri)
        token = client.fetch_token(config["token_url"], 
                                  authorization_response=authorization_response,
                                  client_secret=config["client_secret"])
        
        self.tokens[server_name] = token
        self._save_tokens()
        logger.info(f"✅ 已获取并保存 {server_name} 的 Token")
        return token

    def refresh_token(self, server_name: str):
        """刷新指定服务器的 Token"""
        if not OAUTH_AVAILABLE:
            logger.warning("OAuth 功能需要安装 authlib 库: pip install authlib")
            return None
        
        config = self.server_configs.get(server_name)
        token = self.tokens.get(server_name)
        if not config or not token:
            return None
        
        if "refresh_token" not in token:
            logger.warning(f"{server_name} 的 Token 不包含 refresh_token")
            return None
        
        client = OAuth2Session(config["client_id"], client_secret=config["client_secret"])
        new_token = client.refresh_token(config["token_url"], refresh_token=token["refresh_token"])
        
        self.tokens[server_name] = new_token
        self._save_tokens()
        logger.info(f"✅ 已刷新 {server_name} 的 Token")
        return new_token

    def get_token(self, server_name: str):
        """获取 Token，并在必要时刷新"""
        token = self.tokens.get(server_name)
        if not token:
            return None
        
        # 简单检查过期 (提前 1 分钟)
        expires_at = token.get("expires_at")
        if expires_at and expires_at < time.time() + 60:
            return self.refresh_token(server_name)
        
        return token

    def add_email_provider(self, provider_name: str, provider_type: str, username: str, password: str) -> bool:
        """
        添加邮箱提供商（IMAP 方式）- 支持 163、QQ、Outlook
        场景 1.3 扩展：支持国内邮箱服务
        """
        provider = create_email_provider(provider_type, username, password)
        if not provider:
            return False
        
        if provider.connect():
            self.email_providers[provider_name] = provider
            logger.info(f"✅ 已添加邮箱提供商: {provider_name} ({provider_type})")
            
            # 保存配置（不保存密码，只保存用户名）
            if "email_configs" not in self.tokens:
                self.tokens["email_configs"] = {}
            self.tokens["email_configs"][provider_name] = {
                "type": provider_type,
                "username": username
                # 不保存密码
            }
            self._save_tokens()
            return True
        else:
            logger.error(f"❌ 连接邮箱提供商失败: {provider_name}")
            return False

    def remove_email_provider(self, provider_name: str):
        """移除邮箱提供商"""
        if provider_name in self.email_providers:
            self.email_providers[provider_name].disconnect()
            del self.email_providers[provider_name]
            logger.info(f"已移除邮箱提供商: {provider_name}")

    def set_important_senders(self, provider_name: str, senders: List[str]):
        """设置重要发件人列表"""
        if "important_senders" not in self.tokens:
            self.tokens["important_senders"] = {}
        self.tokens["important_senders"][provider_name] = senders
        self._save_tokens()
        logger.info(f"已为 {provider_name} 设置 {len(senders)} 个重要发件人")
    
    def get_email_check_interval(self) -> int:
        """获取邮箱检查间隔（秒）"""
        return self.tokens.get("email_check_interval", 300)  # 默认5分钟
    
    def set_email_check_interval(self, interval: int):
        """
        设置邮箱检查间隔（秒），限制 1-60 分钟
        
        Args:
            interval: 检查间隔（秒），会被限制在 60-3600 之间
        """
        # 限制在 1-60 分钟之间
        interval = max(60, min(interval, 3600))
        self.tokens["email_check_interval"] = interval
        self._save_tokens()
        logger.info(f"已设置邮箱检查间隔: {interval}秒 ({interval//60}分钟)")

    def setup_music_recommender(self):
        """
        初始化音乐推荐器（场景 4.1）
        """
        if not self.music_recommender:
            self.music_recommender = create_music_recommender()
            logger.info("✅ 音乐推荐器已初始化")
        return self.music_recommender

    def recommend_music_by_mood(self, mood: str, user_preferences: Optional[List[str]] = None):
        """
        根据情绪推荐音乐（场景 4.1）
        """
        if not self.music_recommender:
            self.setup_music_recommender()
        
        return self.music_recommender.recommend_by_mood(mood, user_preferences)

    def setup_news_aggregator(self, user_interests: Optional[List[str]] = None):
        """
        初始化新闻聚合器（场景 4.2）
        """
        if not self.news_aggregator:
            self.news_aggregator = create_news_aggregator()
            if user_interests:
                self.news_aggregator.set_user_interests(user_interests)
            logger.info("✅ 新闻聚合器已初始化")
        return self.news_aggregator

    def add_news_feed(self, category: str, feed_url: str):
        """
        添加自定义新闻源（场景 4.2）
        """
        if not self.news_aggregator:
            self.setup_news_aggregator()
        
        self.news_aggregator.add_user_feed(category, feed_url)

    def get_news(self, category: Optional[str] = None, keyword: Optional[str] = None, max_items: int = 5):
        """
        获取新闻（场景 4.2）
        
        Args:
            category: 新闻分类 (tech, general, science)
            keyword: 搜索关键词（如果提供，且本地没有匹配分类，则使用百度搜索 via RSSHub）
            max_items: 最多返回条数
        """
        if not self.news_aggregator:
            self.setup_news_aggregator()
        
        return self.news_aggregator.fetch_news(category=category, keyword=keyword, max_items=max_items)

    async def call_tool(self, tool_name: str, args: Dict[str, Any]) -> Any:
        """
        通过名称调用工具 (Task 1.1)
        """
        if not MCP_AVAILABLE:
            raise ImportError(f"MCP 库未安装，无法调用工具: {tool_name}。请运行: pip install mcp")
        
        tool_info = self.tool_registry.get(tool_name)
        if not tool_info:
            raise ValueError(f"未找到工具: {tool_name}")
        
        server_name = tool_info.server_name
        session, _ = self.clients.get(server_name, (None, None))
        
        if not session:
            raise ValueError(f"服务器 {server_name} 未连接")
        
        logger.info(f"正在调用工具 {tool_name} (参数: {args})...")
        try:
            result = await session.call_tool(tool_name, args)
            return result
        except Exception as e:
            logger.error(f"调用工具 {tool_name} 失败: {e}")
            raise

    def get_available_tools(self) -> List[Dict[str, Any]]:
        """获取所有可用工具的描述（用于注入 Prompt）"""
        return [
            {
                "name": t.name,
                "description": t.description,
                "parameters": t.parameters
            } for t in self.tool_registry.values()
        ]
    
    def get_enhanced_tool_descriptions(self) -> str:
        """
        获取增强的工具描述（包含详细文档）
        使用 XML 格式，提升 LLM 理解准确性
        """
        from .tool_documentation import get_tool_doc_generator
        
        doc_generator = get_tool_doc_generator()
        mcp_tools = self.get_available_tools()
        
        return doc_generator.get_all_tools_xml(mcp_tools)

    async def check_proactive_events(self) -> List[Dict[str, Any]]:
        """
        检查主动提醒事件 (Task 2.1 & 2.3)
        遍历所有连接的 MCP Server，查找需要主动提醒的内容
        """
        proactive_events = []
        
        for server_name, (session, _) in self.clients.items():
            try:
                # 每个场景分类的具体逻辑
                if server_name == "google_calendar" or server_name == "outlook_calendar":
                    # 场景 1.1: 日程与任务管理 (P0)
                    events = await session.call_tool("list_upcoming_events", {"minutes": 15})
                    if events and events.get("items"):
                        for event in events["items"]:
                            proactive_events.append({
                                "type": "meeting_reminder",
                                "content": f"你 15 分钟后有个会议: {event['summary']}",
                                "server": server_name,
                                "metadata": event
                            })
                
                elif server_name in ["gmail", "outlook_email"]:
                    # 场景 1.3: 邮件重要通知 (P0) - OAuth 方式
                    emails = await session.call_tool("check_unread_emails", {"important_only": True})
                    if emails and emails.get("count", 0) > 0:
                        proactive_events.append({
                            "type": "email_notification",
                            "content": f"你有 {emails['count']} 封来自重要联系人的新邮件",
                            "server": server_name,
                            "metadata": emails
                        })
                
                # 场景 1.3: 邮件重要通知 (P0) - IMAP 方式（163、QQ、Outlook）
                elif server_name in ["email_163", "email_qq", "email_outlook"]:
                    provider = self.email_providers.get(server_name)
                    if provider:
                        # 从配置中获取重要发件人列表
                        important_senders = self.tokens.get("important_senders", {}).get(server_name, [])
                        emails = provider.get_unread_emails(important_senders=important_senders)
                        
                        important_count = sum(1 for e in emails if e.is_important)
                        total_count = len(emails)
                        
                        if important_count > 0:
                            proactive_events.append({
                                "type": "email_notification",
                                "content": f"你有 {important_count} 封来自重要联系人的新邮件（{server_name}）",
                                "server": server_name,
                                "metadata": {
                                    "important_count": important_count,
                                    "total_count": total_count,
                                    "emails": [{"sender": e.sender, "subject": e.subject} for e in emails if e.is_important]
                                }
                            })
                        elif total_count > 10:
                            proactive_events.append({
                                "type": "email_notification",
                                "content": f"你有 {total_count} 封未读邮件（{server_name}），要不要处理一下？",
                                "server": server_name,
                                "metadata": {"total_count": total_count}
                            })
                
                # 场景 7.1: 消息与通知管理 (P0)
                elif server_name == "slack" or server_name == "discord":
                    mentions = await session.call_tool("check_mentions", {})
                    if mentions and mentions.get("count", 0) > 0:
                        proactive_events.append({
                            "type": "mention_notification",
                            "content": f"有人在 {server_name} 上 @ 了你",
                            "server": server_name,
                            "metadata": mentions
                            })

            except Exception as e:
                logger.error(f"检查 {server_name} 的主动事件失败: {e}")
        
        # 场景 4.2: 新闻与资讯推送（每天推送一次）
        if self.news_aggregator:
            try:
                # 检查是否需要推送新闻（简单实现：检查上次推送时间）
                last_news_push = self.tokens.get("last_news_push_time", 0)
                current_time = time.time()
                
                # 每24小时推送一次（86400秒）
                if current_time - last_news_push > 86400:
                    news_items = self.news_aggregator.get_daily_digest(max_items=3)
                    if news_items:
                        news_summary = "\n".join([f"- {item.title}" for item in news_items[:2]])
                        proactive_events.append({
                            "type": "news_push",
                            "content": f"今天有一些你可能感兴趣的新闻：\n{news_summary}",
                            "server": "news_aggregator",
                            "metadata": {
                                "news_count": len(news_items),
                                "news": [{"title": n.title, "url": n.url} for n in news_items]
                            }
                        })
                        
                        # 更新推送时间
                        self.tokens["last_news_push_time"] = current_time
                        self._save_tokens()
            except Exception as e:
                logger.error(f"检查新闻推送失败: {e}")
        
        return proactive_events

    async def close_all(self):
        """关闭所有连接"""
        for server_name, (session, cm) in self.clients.items():
            logger.info(f"正在关闭 {server_name} 连接...")
            await cm.__aexit__(None, None, None)
        self.clients.clear()
        
        # 关闭所有邮箱连接
        for provider_name, provider in self.email_providers.items():
            provider.disconnect()
        self.email_providers.clear()
        
        logger.info("所有 MCP 连接已关闭")

# 导出单例方便使用
_mcp_manager = None

def get_mcp_manager() -> MCPManager:
    global _mcp_manager
    if _mcp_manager is None:
        _mcp_manager = MCPManager()
    return _mcp_manager

