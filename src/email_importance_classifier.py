# email_importance_classifier.py - 邮件重要性分类器
# 多维度判断邮件重要性

import re
import logging
from typing import List, Dict, Any, Optional
from .email_providers import EmailMessage

logger = logging.getLogger("EmailImportanceClassifier")

class EmailImportanceClassifier:
    """
    邮件重要性分类器
    支持多种判断方式：优先级标记、重要发件人、域名白名单、关键词匹配
    """
    
    def __init__(self, rules_config: Dict[str, Any] = None):
        """
        初始化分类器
        
        Args:
            rules_config: 规则配置字典，格式：
                {
                    "provider_name": {
                        "check_priority_flag": bool,
                        "important_senders": List[str],
                        "important_domains": List[str],
                        "keywords": {
                            "subject_keywords": List[str],
                            "sender_keywords": List[str]
                        },
                        "ai_classify_enabled": bool
                    }
                }
        """
        self.rules_config = rules_config or {}
    
    def is_important(self, email: EmailMessage, provider_name: str, rules: Optional[Dict[str, Any]] = None) -> bool:
        """
        多维度判断邮件重要性（带降级策略）
        任一方式返回 True 即为重要邮件
        
        Args:
            email: 邮件消息对象
            provider_name: 邮箱提供商名称
            rules: 规则配置（如果为 None，则从 self.rules_config 获取）
        
        Returns:
            bool: 是否为重要邮件
        """
        if rules is None:
            rules = self.rules_config.get(provider_name, {})
        
        # 1. 优先级标记（最高优先级）
        try:
            if rules.get("check_priority_flag", True):
                if self._check_priority_flag(email):
                    logger.debug(f"邮件 {email.uid} 通过优先级标记检测")
                    return True
        except Exception as e:
            logger.warning(f"优先级标记检测失败: {e}，跳过")
        
        # 2. 重要发件人列表
        try:
            important_senders = rules.get("important_senders", [])
            if important_senders and self._check_important_senders(email, important_senders):
                logger.debug(f"邮件 {email.uid} 通过重要发件人检测")
                return True
        except Exception as e:
            logger.warning(f"发件人检测失败: {e}，跳过")
        
        # 3. 域名白名单
        try:
            domains = rules.get("important_domains", [])
            if domains and self._check_domain_whitelist(email, domains):
                logger.debug(f"邮件 {email.uid} 通过域名白名单检测")
                return True
        except Exception as e:
            logger.warning(f"域名检测失败: {e}，跳过")
        
        # 4. 关键词匹配
        try:
            keywords = rules.get("keywords", {})
            if keywords and self._check_keywords(email, keywords):
                logger.debug(f"邮件 {email.uid} 通过关键词检测")
                return True
        except Exception as e:
            logger.warning(f"关键词检测失败: {e}，跳过")
        
        # 5. AI 分类（可选，需要显式启用）
        if rules.get("ai_classify_enabled", False):
            try:
                result = self._classify_with_ai(email)
                if result and result.get("is_important"):
                    logger.debug(f"邮件 {email.uid} 通过 AI 分类检测")
                    return True
            except Exception as e:
                logger.warning(f"AI 分类失败: {e}，跳过")
        
        return False
    
    def _check_priority_flag(self, email: EmailMessage) -> bool:
        """
        检查优先级标记
        
        Returns:
            bool: 是否标记为重要
        """
        # 检查 IMAP FLAGS
        if email.flags:
            # \Flagged 表示标记为重要
            if b'\\Flagged' in [f.encode() if isinstance(f, str) else f for f in email.flags]:
                return True
            # 也检查字符串形式
            flags_str = ' '.join([f.decode() if isinstance(f, bytes) else str(f) for f in email.flags])
            if '\\Flagged' in flags_str or 'Flagged' in flags_str:
                return True
        
        # 检查邮件头
        if email.priority_header:
            priority = str(email.priority_header).strip()
            # X-Priority: 1 = High, 2 = Normal, 3 = Low
            if priority in ["1", "High", "high"]:
                return True
            # Importance: High, Normal, Low
            if priority.lower() == "high":
                return True
        
        # 检查原始邮件对象
        if email.raw_message:
            priority = email.raw_message.get('X-Priority') or email.raw_message.get('Importance')
            if priority:
                priority_str = str(priority).strip()
                if priority_str in ["1", "High", "high"]:
                    return True
        
        return False
    
    def _check_important_senders(self, email: EmailMessage, important_senders: List[str]) -> bool:
        """
        检查重要发件人列表（增强版：支持精确匹配、模糊匹配、正则表达式）
        
        Args:
            email: 邮件消息
            important_senders: 重要发件人列表
        
        Returns:
            bool: 是否匹配
        """
        sender_lower = email.sender.lower()
        
        for important in important_senders:
            important_lower = important.lower()
            
            # 精确匹配邮箱地址
            if important_lower in sender_lower:
                return True
            
            # 提取邮箱地址部分
            email_address = self._extract_email_address(email.sender)
            if email_address and important_lower in email_address.lower():
                return True
            
            # 正则表达式匹配（如果包含特殊字符）
            if any(c in important for c in ['*', '?', '^', '$', '[', ']']):
                try:
                    pattern = re.compile(important_lower, re.IGNORECASE)
                    if pattern.search(sender_lower) or (email_address and pattern.search(email_address.lower())):
                        return True
                except re.error:
                    # 正则表达式无效，降级为普通字符串匹配
                    pass
        
        return False
    
    def _check_domain_whitelist(self, email: EmailMessage, domains: List[str]) -> bool:
        """
        检查域名白名单
        
        Args:
            email: 邮件消息
            domains: 域名列表（如 ["@company.com", "@client.com"]）
        
        Returns:
            bool: 是否匹配
        """
        sender_email = self._extract_email_address(email.sender)
        if not sender_email:
            return False
        
        # 提取域名
        if '@' not in sender_email:
            return False
        
        email_domain = "@" + sender_email.split("@")[-1].lower()
        
        # 检查是否在域名白名单中
        for domain in domains:
            domain_normalized = domain.lower().strip()
            if not domain_normalized.startswith("@"):
                domain_normalized = "@" + domain_normalized
            if email_domain == domain_normalized:
                return True
        
        return False
    
    def _check_keywords(self, email: EmailMessage, keywords_config: Dict[str, List[str]]) -> bool:
        """
        检查关键词匹配
        
        Args:
            email: 邮件消息
            keywords_config: 关键词配置
                {
                    "subject_keywords": List[str],
                    "sender_keywords": List[str]
                }
        
        Returns:
            bool: 是否匹配
        """
        subject_lower = email.subject.lower() if email.subject else ""
        sender_lower = email.sender.lower() if email.sender else ""
        
        # 检查主题关键词
        subject_keywords = keywords_config.get("subject_keywords", [])
        for keyword in subject_keywords:
            if keyword.lower() in subject_lower:
                return True
        
        # 检查发件人关键词
        sender_keywords = keywords_config.get("sender_keywords", [])
        for keyword in sender_keywords:
            if keyword.lower() in sender_lower:
                return True
        
        return False
    
    def _classify_with_ai(self, email: EmailMessage) -> Optional[Dict[str, Any]]:
        """
        使用 LLM 判断邮件重要性（预留接口，暂不实现）
        
        Args:
            email: 邮件消息
        
        Returns:
            {
                "is_important": bool,
                "confidence": float,
                "reason": str
            } 或 None（如果未启用）
        """
        # 预留接口，未来实现
        # TODO: 集成 LLM 进行智能分类
        return None
    
    def _extract_email_address(self, sender_string: str) -> Optional[str]:
        """
        从发件人字符串中提取邮箱地址
        
        Args:
            sender_string: 发件人字符串，如 "Name <email@example.com>" 或 "email@example.com"
        
        Returns:
            邮箱地址或 None
        """
        if not sender_string:
            return None
        
        # 尝试提取 <email@example.com> 格式
        match = re.search(r'<([^>]+)>', sender_string)
        if match:
            return match.group(1)
        
        # 尝试直接匹配邮箱地址
        match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', sender_string)
        if match:
            return match.group(0)
        
        return None
