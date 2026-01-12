# 邮箱服务配置指南

## 概述

场景 1.3（邮件重要通知）支持多种邮箱服务，包括：
- **OAuth 方式**：Gmail、Outlook（企业版）
- **IMAP 方式**：163 邮箱、QQ 邮箱、Outlook（个人版）

## 配置方式

### 方式 1：OAuth 方式（推荐，适用于 Gmail、Outlook 企业版）

#### Gmail 配置步骤

1. **创建 Google Cloud 项目**
   - 访问 [Google Cloud Console](https://console.cloud.google.com/)
   - 创建新项目或选择现有项目
   - 启用 Gmail API

2. **创建 OAuth 2.0 凭据**
   - 进入"API 和服务" > "凭据"
   - 创建 OAuth 2.0 客户端 ID
   - 设置授权重定向 URI（如：`http://localhost:8000/callback`）

3. **在代码中配置**
   ```python
   from mcp_manager import get_mcp_manager
   
   mcp = get_mcp_manager()
   mcp.setup_oauth_client(
       server_name="gmail",
       client_id="YOUR_GOOGLE_CLIENT_ID",
       client_secret="YOUR_GOOGLE_CLIENT_SECRET",
       auth_url="https://accounts.google.com/o/oauth2/v2/auth",
       token_url="https://oauth2.googleapis.com/token",
       scopes=["https://www.googleapis.com/auth/gmail.readonly"]
   )
   
   # 获取授权 URL
   auth_url = mcp.get_authorization_url("gmail", "http://localhost:8000/callback")
   print(f"请在浏览器中打开: {auth_url}")
   
   # 用户授权后，处理回调
   # mcp.handle_oauth_callback("gmail", authorization_response, redirect_uri)
   ```

#### Outlook 企业版配置步骤

1. **注册 Azure 应用**
   - 访问 [Azure Portal](https://portal.azure.com/)
   - 进入"Azure Active Directory" > "应用注册"
   - 创建新注册
   - 添加重定向 URI

2. **获取 Client ID 和 Secret**
   - 在应用注册页面获取"应用程序(客户端) ID"
   - 创建客户端密码（Secret）

3. **在代码中配置**
   ```python
   mcp.setup_oauth_client(
       server_name="outlook",
       client_id="YOUR_AZURE_CLIENT_ID",
       client_secret="YOUR_AZURE_CLIENT_SECRET",
       auth_url="https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
       token_url="https://login.microsoftonline.com/common/oauth2/v2.0/token",
       scopes=["https://graph.microsoft.com/Mail.Read"]
   )
   ```

---

### 方式 2：IMAP 方式（适用于 163、QQ、Outlook 个人版）

#### 163 邮箱配置

1. **开启 IMAP 服务**
   - 登录 163 邮箱网页版
   - 进入"设置" > "POP3/SMTP/IMAP"
   - 开启 IMAP/SMTP 服务
   - 生成授权码（不是邮箱密码）

2. **在代码中配置**
   ```python
   from mcp_manager import get_mcp_manager
   
   mcp = get_mcp_manager()
   success = mcp.add_email_provider(
       provider_name="email_163",
       provider_type="163",
       username="your_email@163.com",
       password="your_authorization_code"  # 使用授权码，不是邮箱密码
   )
   
   if success:
       # 设置重要发件人（可选）
       mcp.set_important_senders("email_163", [
           "boss@company.com",
           "important@client.com"
       ])
   ```

#### QQ 邮箱配置

1. **开启 IMAP 服务**
   - 登录 QQ 邮箱网页版
   - 进入"设置" > "账户"
   - 找到"POP3/IMAP/SMTP/Exchange/CardDAV/CalDAV服务"
   - 开启"IMAP/SMTP服务"
   - 生成授权码（不是QQ密码）

2. **在代码中配置**
   ```python
   success = mcp.add_email_provider(
       provider_name="email_qq",
       provider_type="qq",
       username="your_email@qq.com",
       password="your_authorization_code"  # 使用授权码，不是QQ密码
   )
   
   if success:
       mcp.set_important_senders("email_qq", [
           "friend@qq.com",
           "family@qq.com"
       ])
   ```

#### Outlook 个人版配置（IMAP 方式）

1. **开启 IMAP 服务**
   - 登录 Outlook.com
   - 进入"设置" > "邮件" > "同步电子邮件"
   - 确保 IMAP 已启用

2. **在代码中配置**
   ```python
   success = mcp.add_email_provider(
       provider_name="email_outlook",
       provider_type="outlook",
       username="your_email@outlook.com",
       password="your_password"  # Outlook 个人版使用密码
   )
   ```

---

## 重要发件人配置

为每个邮箱服务配置重要发件人列表，系统会优先提醒这些发件人的邮件：

```python
# 163 邮箱
mcp.set_important_senders("email_163", [
    "boss@company.com",
    "hr@company.com",
    "important@client.com"
])

# QQ 邮箱
mcp.set_important_senders("email_qq", [
    "friend@qq.com",
    "family@qq.com"
])

# Gmail（OAuth 方式）
mcp.set_important_senders("gmail", [
    "boss@gmail.com",
    "important@gmail.com"
])
```

---

## 安全注意事项

1. **授权码 vs 密码**
   - 163 和 QQ 邮箱必须使用授权码，不是邮箱密码
   - 授权码在邮箱设置中生成，可以随时重置

2. **Token 存储**
   - OAuth Token 存储在 `mcp_tokens.json` 文件中
   - 建议将此文件添加到 `.gitignore`
   - 生产环境应使用加密存储

3. **密码存储**
   - IMAP 方式的密码不会保存到文件（仅内存中）
   - 每次启动需要重新输入或从安全配置读取

4. **权限最小化**
   - OAuth 方式只请求只读权限（`readonly`）
   - 不会发送邮件或修改邮箱设置

---

## 测试连接

```python
from mcp_manager import get_mcp_manager
import asyncio

async def test_email_connection():
    mcp = get_mcp_manager()
    
    # 测试 IMAP 连接
    if mcp.add_email_provider("test_163", "163", "test@163.com", "auth_code"):
        provider = mcp.email_providers["test_163"]
        emails = provider.get_unread_emails()
        print(f"找到 {len(emails)} 封未读邮件")
        for email in emails[:5]:
            print(f"  - {email.sender}: {email.subject}")

asyncio.run(test_email_connection())
```

---

## 故障排查

### 163/QQ 邮箱连接失败

1. **检查授权码**
   - 确认使用的是授权码，不是邮箱密码
   - 授权码可能已过期，重新生成

2. **检查 IMAP 服务**
   - 确认已在邮箱设置中开启 IMAP 服务
   - 某些邮箱需要手机验证才能开启

3. **检查网络**
   - 确认能够访问 IMAP 服务器
   - 163: `imap.163.com:993`
   - QQ: `imap.qq.com:993`

### Outlook 连接失败

1. **OAuth 方式**
   - 检查 Client ID/Secret 是否正确
   - 检查重定向 URI 是否匹配
   - 检查 Token 是否过期

2. **IMAP 方式**
   - 确认密码正确
   - 某些企业版 Outlook 可能禁用了 IMAP

---

## 下一步

配置完成后，系统会在定时检查（每2.5分钟）时自动检测新邮件，并在发现重要邮件时主动提醒用户。

提醒语气示例：
- "你有一封来自老板的邮件，要不要看看？"
- "你有 3 封来自重要联系人的新邮件（163邮箱）"
- "你有 10 封未读邮件（QQ邮箱），要不要处理一下？"

