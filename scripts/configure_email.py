#!/usr/bin/env python3
# configure_email.py - 邮箱配置 CLI 工具

"""
邮箱配置工具
用于配置 163、QQ、Outlook 等邮箱的 IMAP 连接和重要发件人列表
"""

import sys
import os
import getpass

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.mcp_manager import get_mcp_manager

def print_header(text):
    """打印标题"""
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60 + "\n")

def configure_email_provider():
    """配置邮箱提供商"""
    mcp = get_mcp_manager()
    
    print_header("邮箱提供商配置")
    
    print("支持的邮箱类型：")
    print("  1. 163 邮箱")
    print("  2. QQ 邮箱")
    print("  3. Outlook 邮箱（IMAP）")
    print()
    
    choice = input("请选择邮箱类型 (1-3): ").strip()
    
    provider_map = {
        "1": ("163", "email_163"),
        "2": ("qq", "email_qq"),
        "3": ("outlook", "email_outlook")
    }
    
    if choice not in provider_map:
        print("❌ 无效选择")
        return False
    
    provider_type, provider_name = provider_map[choice]
    
    print(f"\n配置 {provider_type.upper()} 邮箱：")
    username = input("邮箱地址: ").strip()
    if not username:
        print("❌ 邮箱地址不能为空")
        return False
    
    print("\n提示：")
    if provider_type == "qq":
        print("  - QQ 邮箱需要使用授权码，不是 QQ 密码")
        print("  - 获取方式：QQ 邮箱 -> 设置 -> 账户 -> 开启 IMAP/SMTP -> 生成授权码")
    elif provider_type == "163":
        print("  - 163 邮箱需要使用授权码")
        print("  - 获取方式：163 邮箱 -> 设置 -> POP3/SMTP/IMAP -> 开启 IMAP -> 生成授权码")
    else:
        print("  - Outlook 邮箱使用账户密码")
    
    password = getpass.getpass("授权码/密码: ")
    if not password:
        print("❌ 授权码/密码不能为空")
        return False
    
    print(f"\n正在连接 {provider_type.upper()} 邮箱...")
    success = mcp.add_email_provider(provider_name, provider_type, username, password)
    
    if success:
        print(f"✅ {provider_type.upper()} 邮箱配置成功！")
        return True
    else:
        print(f"❌ {provider_type.upper()} 邮箱配置失败，请检查邮箱地址和授权码")
        return False

def _get_provider_selection(mcp):
    """辅助函数：选择邮箱提供商"""
    email_configs = mcp.tokens.get("email_configs", {})
    if not email_configs:
        print("❌ 请先配置邮箱提供商")
        return None
    
    print("已配置的邮箱：")
    providers = list(email_configs.keys())
    for i, provider_name in enumerate(providers, 1):
        config = email_configs[provider_name]
        print(f"  {i}. {provider_name} ({config.get('username', 'N/A')})")
    
    print()
    choice = input(f"请选择邮箱 (1-{len(providers)}): ").strip()
    
    try:
        idx = int(choice) - 1
        if idx < 0 or idx >= len(providers):
            print("❌ 无效选择")
            return None
        return providers[idx]
    except ValueError:
        print("❌ 无效输入")
        return None

def configure_important_senders():
    """配置重要发件人列表"""
    mcp = get_mcp_manager()
    
    print_header("重要发件人配置")
    
    provider_name = _get_provider_selection(mcp)
    if not provider_name:
        return False
    
    # 显示当前重要发件人
    important_senders = mcp.tokens.get("important_senders", {}).get(provider_name, [])
    if important_senders:
        print(f"\n当前重要发件人列表：")
        for sender in important_senders:
            print(f"  - {sender}")
    else:
        print(f"\n当前没有配置重要发件人")
    
    print("\n请输入重要发件人（每行一个，输入空行结束）：")
    senders = []
    while True:
        sender = input("发件人邮箱/名称: ").strip()
        if not sender:
            break
        senders.append(sender)
    
    if senders:
        mcp.set_important_senders(provider_name, senders)
        print(f"\n✅ 已为 {provider_name} 设置 {len(senders)} 个重要发件人")
        return True
    else:
        print("\n⚠️ 未添加任何发件人")
        return False

def configure_importance_rules():
    """配置邮件重要性判断规则"""
    mcp = get_mcp_manager()
    
    print_header("邮件重要性判断规则配置")
    
    provider_name = _get_provider_selection(mcp)
    if not provider_name:
        return False
    
    # 获取当前规则
    importance_rules = mcp.tokens.get("email_importance_rules", {})
    provider_rules = importance_rules.get(provider_name, {})
    
    print(f"\n当前规则配置：")
    print(f"  检查优先级标记: {provider_rules.get('check_priority_flag', True)}")
    print(f"  重要发件人: {len(provider_rules.get('important_senders', []))} 个")
    print(f"  域名白名单: {len(provider_rules.get('important_domains', []))} 个")
    print(f"  主题关键词: {len(provider_rules.get('keywords', {}).get('subject_keywords', []))} 个")
    print(f"  发件人关键词: {len(provider_rules.get('keywords', {}).get('sender_keywords', []))} 个")
    print(f"  AI 分类: {'启用' if provider_rules.get('ai_classify_enabled', False) else '禁用'}")
    
    print("\n配置选项：")
    print("  1. 配置域名白名单")
    print("  2. 配置关键词（主题+发件人）")
    print("  3. 切换优先级标记检测")
    print("  4. 返回")
    
    choice = input("请选择 (1-4): ").strip()
    
    if choice == "1":
        # 配置域名白名单
        print("\n请输入重要域名（每行一个，如 @company.com，输入空行结束）：")
        domains = []
        while True:
            domain = input("域名: ").strip()
            if not domain:
                break
            if not domain.startswith("@"):
                domain = "@" + domain
            domains.append(domain)
        
        if not provider_rules:
            provider_rules = {}
        provider_rules["important_domains"] = domains
        importance_rules[provider_name] = provider_rules
        mcp.tokens["email_importance_rules"] = importance_rules
        mcp._save_tokens()
        print(f"\n✅ 已设置 {len(domains)} 个域名")
        return True
    
    elif choice == "2":
        # 配置关键词
        keywords = provider_rules.get("keywords", {})
        
        print("\n主题关键词（每行一个，输入空行结束）：")
        subject_keywords = []
        while True:
            keyword = input("关键词: ").strip()
            if not keyword:
                break
            subject_keywords.append(keyword)
        
        print("\n发件人关键词（每行一个，输入空行结束）：")
        sender_keywords = []
        while True:
            keyword = input("关键词: ").strip()
            if not keyword:
                break
            sender_keywords.append(keyword)
        
        if not provider_rules:
            provider_rules = {}
        provider_rules["keywords"] = {
            "subject_keywords": subject_keywords,
            "sender_keywords": sender_keywords
        }
        importance_rules[provider_name] = provider_rules
        mcp.tokens["email_importance_rules"] = importance_rules
        mcp._save_tokens()
        print(f"\n✅ 已设置 {len(subject_keywords)} 个主题关键词，{len(sender_keywords)} 个发件人关键词")
        return True
    
    elif choice == "3":
        # 切换优先级标记检测
        current = provider_rules.get("check_priority_flag", True)
        new_value = not current
        if not provider_rules:
            provider_rules = {}
        provider_rules["check_priority_flag"] = new_value
        importance_rules[provider_name] = provider_rules
        mcp.tokens["email_importance_rules"] = importance_rules
        mcp._save_tokens()
        print(f"\n✅ 优先级标记检测已{'启用' if new_value else '禁用'}")
        return True
    
    return False

def list_configured_providers():
    """列出已配置的邮箱提供商"""
    mcp = get_mcp_manager()
    
    print_header("已配置的邮箱")
    
    email_configs = mcp.tokens.get("email_configs", {})
    if not email_configs:
        print("❌ 尚未配置任何邮箱")
        return
    
    for provider_name, config in email_configs.items():
        print(f"\n📧 {provider_name}:")
        print(f"  类型: {config.get('type', 'N/A')}")
        print(f"  用户名: {config.get('username', 'N/A')}")
        
        # 显示重要发件人
        important_senders = mcp.tokens.get("important_senders", {}).get(provider_name, [])
        if important_senders:
            print(f"  重要发件人 ({len(important_senders)} 个):")
            for sender in important_senders:
                print(f"    - {sender}")
        else:
            print("  重要发件人: 未配置")

def configure_check_interval():
    """配置邮箱检查间隔"""
    mcp = get_mcp_manager()
    
    print_header("邮箱检查间隔配置")
    
    current_interval = mcp.get_email_check_interval()
    print(f"当前检查间隔: {current_interval}秒 ({current_interval//60}分钟)")
    print()
    
    print("预设选项：")
    print("  1. 5分钟（默认，适合及时响应）")
    print("  2. 10分钟（平衡模式）")
    print("  3. 15分钟（省电模式）")
    print("  4. 30分钟（极省电模式）")
    print("  5. 自定义（输入秒数，限制 1-60 分钟）")
    print()
    
    choice = input("请选择 (1-5): ").strip()
    
    if choice == "1":
        interval = 300  # 5分钟
    elif choice == "2":
        interval = 600  # 10分钟
    elif choice == "3":
        interval = 900  # 15分钟
    elif choice == "4":
        interval = 1800  # 30分钟
    elif choice == "5":
        try:
            minutes = int(input("请输入检查间隔（分钟，1-60）: ").strip())
            if minutes < 1 or minutes > 60:
                print("❌ 间隔必须在 1-60 分钟之间")
                return False
            interval = minutes * 60
        except ValueError:
            print("❌ 无效输入")
            return False
    else:
        print("❌ 无效选择")
        return False
    
    mcp.set_email_check_interval(interval)
    print(f"\n✅ 已设置检查间隔为 {interval}秒 ({interval//60}分钟)")
    print("   注意：需要重启系统才能生效")
    return True

def main():
    """主菜单"""
    while True:
        print_header("邮箱配置工具")
        print("1. 配置邮箱提供商（163/QQ/Outlook）")
        print("2. 配置重要发件人列表")
        print("3. 配置检查间隔")
        print("4. 配置重要性判断规则（域名、关键词等）")
        print("5. 查看已配置的邮箱")
        print("6. 退出")
        print()
        
        choice = input("请选择操作 (1-6): ").strip()
        
        if choice == "1":
            configure_email_provider()
        elif choice == "2":
            configure_important_senders()
        elif choice == "3":
            configure_check_interval()
        elif choice == "4":
            configure_importance_rules()
        elif choice == "5":
            list_configured_providers()
        elif choice == "6":
            print("\n👋 再见！")
            break
        else:
            print("❌ 无效选择，请重试")
        
        input("\n按 Enter 继续...")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 已取消，再见！")
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()
