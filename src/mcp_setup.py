import asyncio
from .mcp_manager import get_mcp_manager

async def setup_mcp_priority_scenarios():
    """
    配置 MCP 优先场景 (Task 1.1, 1.3, 7.1)
    """
    mcp = get_mcp_manager()
    
    print("正在配置 MCP 优先场景...")

    # 1. 配置 OAuth 客户端 (需要用户填入自己的 ID/Secret)
    # 场景 1.1 & 1.3: Google 服务
    print("\n--- 配置 Google OAuth (场景 1.1 & 1.3) ---")
    mcp.setup_oauth_client(
        server_name="google",
        client_id="YOUR_GOOGLE_CLIENT_ID",
        client_secret="YOUR_GOOGLE_CLIENT_SECRET",
        auth_url="https://accounts.google.com/o/oauth2/v2/auth",
        token_url="https://oauth2.googleapis.com/token",
        scopes=[
            "https://www.googleapis.com/auth/calendar.readonly",
            "https://www.googleapis.com/auth/gmail.readonly"
        ]
    )
    
    # 场景 7.1: Slack
    print("\n--- 配置 Slack OAuth (场景 7.1) ---")
    mcp.setup_oauth_client(
        server_name="slack",
        client_id="YOUR_SLACK_CLIENT_ID",
        client_secret="YOUR_SLACK_CLIENT_SECRET",
        auth_url="https://slack.com/oauth/v2/authorize",
        token_url="https://slack.com/api/oauth.v2.access",
        scopes=["channels:read", "chat:read", "users:read"]
    )

    # 2. 获取授权 URL 的示例
    # redirect_uri = "http://localhost:8000/callback"
    # auth_url = mcp.get_authorization_url("google", redirect_uri)
    # print(f"\n请在浏览器中打开此 URL 进行 Google 授权:\n{auth_url}")

    # 3. 本地 stdio server 示例 (如文件系统)
    # await mcp.add_stdio_server(
    #     "filesystem",
    #     "npx",
    #     ["-y", "@modelcontextprotocol/server-filesystem", "/Users/JiajunFei/Documents"]
    # )

    # 4. 邮箱提供商配置示例（IMAP 方式 - 163、QQ、Outlook）
    print("\n--- 配置邮箱提供商 (场景 1.3 扩展: 163、QQ、Outlook) ---")
    print("提示：以下为示例配置，请根据实际情况修改")
    
    # 163 邮箱示例
    # mcp.add_email_provider("email_163", "163", "your_email@163.com", "your_authorization_code")
    
    # QQ 邮箱示例（需要使用授权码，不是QQ密码）
    # mcp.add_email_provider("email_qq", "qq", "your_email@qq.com", "your_authorization_code")
    
    # Outlook 邮箱示例（IMAP 方式）
    # mcp.add_email_provider("email_outlook", "outlook", "your_email@outlook.com", "your_password")
    
    # 设置重要发件人列表（可选）
    # mcp.set_important_senders("email_163", ["boss@company.com", "important@client.com"])
    # mcp.set_important_senders("email_qq", ["friend@qq.com"])
    
    # 5. 内容服务配置（场景 4.1 & 4.2）
    print("\n--- 配置内容服务 (场景 4.1 & 4.2: 音乐推荐 & 新闻推送) ---")
    
    # 场景 4.1: 音乐推荐
    print("\n初始化音乐推荐器...")
    mcp.setup_music_recommender()
    
    # 场景 4.2: 新闻聚合
    print("\n初始化新闻聚合器...")
    user_interests = ["AI", "科技", "人工智能"]  # 示例兴趣
    mcp.setup_news_aggregator(user_interests)
    
    # 添加自定义新闻源（可选）
    # mcp.add_news_feed("tech", "https://www.36kr.com/feed")
    # mcp.add_news_feed("science", "https://www.guokr.com/rss/")
    
    print("\nMCP 配置完成。")
    print("   - OAuth 服务：请在 mcp_tokens.json 中填入有效的 Token 或运行授权流程")
    print("   - IMAP 邮箱：使用 add_email_provider() 方法添加 163、QQ、Outlook 邮箱")
    print("   - 音乐推荐：已初始化，可通过对话触发（如：'推荐一首歌'）")
    print("   - 新闻推送：已初始化，每24小时自动推送一次")

if __name__ == "__main__":
    asyncio.run(setup_mcp_priority_scenarios())

