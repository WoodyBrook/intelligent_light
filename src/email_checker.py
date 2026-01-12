# email_checker.py - 邮箱检查服务
# 定时检查未读邮件，生成提醒事件

import time
import logging
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass
from .email_providers import EmailProvider, EmailMessage
from .mcp_manager import get_mcp_manager
from .email_importance_classifier import EmailImportanceClassifier

logger = logging.getLogger("EmailChecker")

@dataclass
class EmailReminder:
    """邮件提醒数据"""
    provider_name: str
    emails: List[EmailMessage]
    reminder_type: str  # "important" | "batch"
    message: str  # 提醒话术

class EmailChecker:
    """
    邮箱检查服务
    负责定时检查未读邮件，生成提醒事件
    """
    
    def __init__(self, check_interval: int = None):
        """
        初始化邮箱检查器
        
        Args:
            check_interval: 检查间隔（秒），如果为 None 则从配置读取
        """
        self.mcp_manager = get_mcp_manager()
        if check_interval is None:
            check_interval = self.mcp_manager.get_email_check_interval()
        self.check_interval = check_interval
        self.last_check_time = {}  # {provider_name: timestamp}
        self.notified_email_uids: Dict[str, Set[str]] = {}  # {provider_name: set(uid)}
        
        # 初始化重要性分类器
        importance_rules = self.mcp_manager.tokens.get("email_importance_rules", {})
        self.classifier = EmailImportanceClassifier(importance_rules)
        
        logger.info(f"📧 EmailChecker 初始化完成，检查间隔: {check_interval}秒 ({check_interval//60}分钟)")
    
    def should_check(self, provider_name: str) -> bool:
        """判断是否应该检查该邮箱"""
        last_time = self.last_check_time.get(provider_name, 0)
        current_time = time.time()
        return (current_time - last_time) >= self.check_interval
    
    def check_provider(self, provider_name: str) -> Optional[EmailReminder]:
        """
        检查指定邮箱提供商的未读邮件
        
        Args:
            provider_name: 邮箱提供商名称（如 "email_163", "email_qq"）
        
        Returns:
            EmailReminder 或 None（如果没有需要提醒的邮件）
        """
        if not self.should_check(provider_name):
            return None
        
        # 从 MCP Manager 获取邮箱提供商
        provider = self.mcp_manager.email_providers.get(provider_name)
        if not provider:
            logger.warning(f"未找到邮箱提供商: {provider_name}")
            return None
        
        try:
            # 获取未读邮件（不传 important_senders，由分类器统一处理）
            unread_emails = provider.get_unread_emails(important_senders=None)
            
            if not unread_emails:
                self.last_check_time[provider_name] = time.time()
                return None
            
            # 过滤已提醒的邮件
            notified_uids = self.notified_email_uids.get(provider_name, set())
            new_emails = [e for e in unread_emails if e.uid not in notified_uids]
            
            if not new_emails:
                self.last_check_time[provider_name] = time.time()
                return None
            
            # 使用分类器判断重要性
            importance_rules = self.mcp_manager.tokens.get("email_importance_rules", {})
            provider_rules = importance_rules.get(provider_name, {})
            
            # 如果没有配置新规则，使用原有的重要发件人列表（向后兼容）
            if not provider_rules:
                important_senders = self.mcp_manager.tokens.get("important_senders", {}).get(provider_name, [])
                if important_senders:
                    provider_rules = {"important_senders": important_senders}
            
            # 为每封邮件判断重要性
            for email in new_emails:
                email.is_important = self.classifier.is_important(email, provider_name, provider_rules)
            
            # 分类邮件
            important_emails = [e for e in new_emails if e.is_important]
            other_emails = [e for e in new_emails if not e.is_important]
            
            # 生成提醒
            reminder = None
            
            # 优先提醒重要邮件
            if important_emails:
                # 只提醒第一封重要邮件（避免过于频繁）
                email = important_emails[0]
                message = self._generate_important_email_message(email)
                reminder = EmailReminder(
                    provider_name=provider_name,
                    emails=[email],
                    reminder_type="important",
                    message=message
                )
                # 记录已提醒
                if provider_name not in self.notified_email_uids:
                    self.notified_email_uids[provider_name] = set()
                self.notified_email_uids[provider_name].add(email.uid)
            
            # 如果未读邮件总数超过阈值，提醒批量处理
            elif len(unread_emails) >= 10:
                message = self._generate_batch_reminder_message(len(unread_emails))
                reminder = EmailReminder(
                    provider_name=provider_name,
                    emails=new_emails[:5],  # 只返回前5封作为示例
                    reminder_type="batch",
                    message=message
                )
                # 记录已提醒的邮件
                if provider_name not in self.notified_email_uids:
                    self.notified_email_uids[provider_name] = set()
                for email in new_emails[:5]:
                    self.notified_email_uids[provider_name].add(email.uid)
            
            self.last_check_time[provider_name] = time.time()
            return reminder
            
        except Exception as e:
            logger.error(f"检查邮箱 {provider_name} 失败: {e}")
            return None
    
    def check_all_providers(self) -> List[EmailReminder]:
        """
        检查所有已配置的邮箱提供商
        
        Returns:
            需要提醒的邮件列表
        """
        reminders = []
        
        for provider_name in self.mcp_manager.email_providers.keys():
            reminder = self.check_provider(provider_name)
            if reminder:
                reminders.append(reminder)
        
        return reminders
    
    def _generate_important_email_message(self, email: EmailMessage) -> str:
        """
        生成重要邮件提醒话术（符合"温柔坚定猫"性格）
        """
        # 提取发件人名称（去掉邮箱地址）
        sender_name = email.sender.split('<')[0].strip() if '<' in email.sender else email.sender
        sender_name = sender_name.strip('"').strip("'")
        
        # 截断过长的主题
        subject = email.subject[:30] + "..." if len(email.subject) > 30 else email.subject
        
        messages = [
            f"有封重要邮件哦，来自 {sender_name}，标题是「{subject}」。要现在看看吗？",
            f"收到一封重要邮件，{sender_name} 发来的，关于「{subject}」。要不要看看？",
            f"有封邮件需要你注意一下，{sender_name} 的「{subject}」。"
        ]
        
        import random
        return random.choice(messages)
    
    def _generate_batch_reminder_message(self, count: int) -> str:
        """
        生成批量邮件提醒话术
        """
        messages = [
            f"你有 {count} 封未读邮件了，要不要抽空处理一下？",
            f"邮箱里积了 {count} 封未读邮件，需要我帮你看看吗？",
            f"未读邮件有 {count} 封了，记得处理一下哦。"
        ]
        
        import random
        return random.choice(messages)
    
    def clear_notified_history(self, provider_name: Optional[str] = None):
        """
        清除已提醒记录（用于测试或重置）
        
        Args:
            provider_name: 如果指定，只清除该提供商的记录；否则清除所有
        """
        if provider_name:
            self.notified_email_uids.pop(provider_name, None)
        else:
            self.notified_email_uids.clear()
        logger.info(f"已清除提醒记录: {provider_name or '全部'}")

# 全局单例
_email_checker = None

def get_email_checker(check_interval: int = None) -> EmailChecker:
    """
    获取邮箱检查器单例
    
    Args:
        check_interval: 检查间隔（秒），如果为 None 则从配置读取
    """
    global _email_checker
    if _email_checker is None:
        _email_checker = EmailChecker(check_interval=check_interval)
    return _email_checker
