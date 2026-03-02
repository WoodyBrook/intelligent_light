# email_providers.py - 邮箱服务提供商支持
# 支持 163、QQ、Outlook 等邮箱的 IMAP 连接

import imaplib
import email
from email.header import decode_header
from typing import List, Dict, Any, Optional, Any as AnyType
from dataclasses import dataclass, field
import logging

logger = logging.getLogger("EmailProviders")

@dataclass
class EmailConfig:
    """邮箱配置"""
    provider: str  # "163", "qq", "outlook", "gmail"
    imap_server: str
    imap_port: int
    smtp_server: str
    smtp_port: int
    username: str
    password: str  # 或授权码
    use_ssl: bool = True

@dataclass
class EmailMessage:
    """邮件消息"""
    uid: str
    sender: str
    subject: str
    date: str
    is_read: bool
    is_important: bool = False
    flags: Optional[List[str]] = None  # IMAP FLAGS（如 ['\\Flagged', '\\Seen']）
    priority_header: Optional[str] = None  # X-Priority 或 Importance 头
    raw_message: Optional[AnyType] = None  # 原始邮件对象（用于后续解析）

class EmailProvider:
    """邮箱服务提供商基类"""
    
    def __init__(self, config: EmailConfig):
        self.config = config
        self.connection = None
    
    def connect(self) -> bool:
        """连接到邮箱服务器"""
        try:
            if self.config.use_ssl:
                self.connection = imaplib.IMAP4_SSL(self.config.imap_server, self.config.imap_port)
            else:
                self.connection = imaplib.IMAP4(self.config.imap_server, self.config.imap_port)
            
            self.connection.login(self.config.username, self.config.password)
            self.connection.select('INBOX')
            logger.info(f"成功连接到 {self.config.provider} 邮箱")
            return True
        except Exception as e:
            logger.error(f"[ERROR] 连接 {self.config.provider} 邮箱失败: {e}")
            return False
    
    def disconnect(self):
        """断开连接"""
        if self.connection:
            try:
                self.connection.close()
                self.connection.logout()
            except:
                pass
            self.connection = None
    
    def get_unread_emails(self, important_senders: Optional[List[str]] = None) -> List[EmailMessage]:
        """获取未读邮件"""
        if not self.connection:
            if not self.connect():
                return []
        
        try:
            # 搜索未读邮件
            status, messages = self.connection.search(None, 'UNSEEN')
            if status != 'OK':
                return []
            
            email_ids = messages[0].split()
            emails = []
            
            for email_id in email_ids[-10:]:  # 只取最近10封
                # 获取邮件内容和 FLAGS
                status, msg_data = self.connection.fetch(email_id, '(RFC822 FLAGS)')
                if status != 'OK':
                    continue
                
                # 解析 FLAGS（如果存在）
                flags = []
                priority_header = None
                
                # 尝试解析 FLAGS
                try:
                    # msg_data 格式: [(b'1 (FLAGS (\\Seen \\Flagged) RFC822 {...})', b'...')]
                    if len(msg_data) > 0 and len(msg_data[0]) > 0:
                        flags_str = msg_data[0][0].decode('utf-8', errors='ignore')
                        # 提取 FLAGS 部分
                        if 'FLAGS' in flags_str:
                            import re
                            flags_match = re.search(r'FLAGS\s+\(([^)]+)\)', flags_str)
                            if flags_match:
                                flags = [f.strip() for f in flags_match.group(1).split()]
                except Exception as e:
                    logger.debug(f"解析 FLAGS 失败: {e}")
                
                # 获取邮件体（在第二个元素）
                email_body = msg_data[0][1] if len(msg_data[0]) > 1 else None
                if not email_body:
                    continue
                
                msg = email.message_from_bytes(email_body)
                
                # 解析发件人
                sender = self._decode_header(msg['From'])
                subject = self._decode_header(msg['Subject'])
                date = msg['Date']
                
                # 获取优先级头
                priority_header = msg.get('X-Priority') or msg.get('Importance') or msg.get('Priority')
                
                # 检查是否是重要发件人（保留原有逻辑，后续由分类器统一处理）
                is_important = False
                if important_senders:
                    for important in important_senders:
                        if important.lower() in sender.lower():
                            is_important = True
                            break
                
                emails.append(EmailMessage(
                    uid=email_id.decode(),
                    sender=sender,
                    subject=subject,
                    date=date,
                    is_read=False,
                    is_important=is_important,
                    flags=flags,
                    priority_header=priority_header,
                    raw_message=msg
                ))
            
            return emails
        except Exception as e:
            logger.error(f"获取未读邮件失败: {e}")
            return []
    
    def _decode_header(self, header: Optional[str]) -> str:
        """解码邮件头"""
        if not header:
            return ""
        try:
            decoded_parts = decode_header(header)
            decoded_str = ""
            for part, encoding in decoded_parts:
                if isinstance(part, bytes):
                    decoded_str += part.decode(encoding or 'utf-8')
                else:
                    decoded_str += part
            return decoded_str
        except:
            return str(header) if header else ""

class EmailProvider163(EmailProvider):
    """163 邮箱"""
    
    def __init__(self, username: str, password: str):
        config = EmailConfig(
            provider="163",
            imap_server="imap.163.com",
            imap_port=993,
            smtp_server="smtp.163.com",
            smtp_port=465,
            username=username,
            password=password,
            use_ssl=True
        )
        super().__init__(config)

class EmailProviderQQ(EmailProvider):
    """QQ 邮箱"""
    
    def __init__(self, username: str, password: str):
        config = EmailConfig(
            provider="qq",
            imap_server="imap.qq.com",
            imap_port=993,
            smtp_server="smtp.qq.com",
            smtp_port=465,
            username=username,
            password=password,  # 需要使用授权码，不是QQ密码
            use_ssl=True
        )
        super().__init__(config)

class EmailProviderOutlook(EmailProvider):
    """Outlook 邮箱（IMAP 方式）"""
    
    def __init__(self, username: str, password: str):
        config = EmailConfig(
            provider="outlook",
            imap_server="outlook.office365.com",
            imap_port=993,
            smtp_server="smtp.office365.com",
            smtp_port=587,
            username=username,
            password=password,
            use_ssl=True
        )
        super().__init__(config)

def create_email_provider(provider: str, username: str, password: str) -> Optional[EmailProvider]:
    """工厂方法：创建邮箱提供商实例"""
    providers = {
        "163": EmailProvider163,
        "qq": EmailProviderQQ,
        "outlook": EmailProviderOutlook,
    }
    
    provider_class = providers.get(provider.lower())
    if not provider_class:
        logger.error(f"不支持的邮箱提供商: {provider}")
        return None
    
    return provider_class(username, password)

