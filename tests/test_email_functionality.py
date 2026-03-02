#!/usr/bin/env python3
"""
邮件功能测试脚本
测试邮件模块的各个组件是否正常工作
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
from unittest.mock import Mock, patch, MagicMock
from dataclasses import dataclass


class TestEmailProviders(unittest.TestCase):
    """测试邮件提供商模块"""
    
    def test_email_config_dataclass(self):
        """测试 EmailConfig 数据类"""
        from src.email_providers import EmailConfig
        
        config = EmailConfig(
            provider="test",
            imap_server="imap.test.com",
            imap_port=993,
            smtp_server="smtp.test.com",
            smtp_port=465,
            username="test@test.com",
            password="password123",
            use_ssl=True
        )
        
        self.assertEqual(config.provider, "test")
        self.assertEqual(config.imap_server, "imap.test.com")
        self.assertEqual(config.imap_port, 993)
        self.assertTrue(config.use_ssl)
    
    def test_email_message_dataclass(self):
        """测试 EmailMessage 数据类"""
        from src.email_providers import EmailMessage
        
        msg = EmailMessage(
            uid="123",
            sender="test@example.com",
            subject="Test Subject",
            date="2024-01-01",
            is_read=False,
            is_important=True,
            flags=["\\Flagged"],
            priority_header="1"
        )
        
        self.assertEqual(msg.uid, "123")
        self.assertEqual(msg.sender, "test@example.com")
        self.assertTrue(msg.is_important)
        self.assertIn("\\Flagged", msg.flags)
    
    def test_create_email_provider_163(self):
        """测试创建 163 邮箱提供商"""
        from src.email_providers import create_email_provider, EmailProvider163
        
        provider = create_email_provider("163", "user@163.com", "password")
        
        self.assertIsInstance(provider, EmailProvider163)
        self.assertEqual(provider.config.imap_server, "imap.163.com")
        self.assertEqual(provider.config.imap_port, 993)
    
    def test_create_email_provider_qq(self):
        """测试创建 QQ 邮箱提供商"""
        from src.email_providers import create_email_provider, EmailProviderQQ
        
        provider = create_email_provider("qq", "123456@qq.com", "authcode")
        
        self.assertIsInstance(provider, EmailProviderQQ)
        self.assertEqual(provider.config.imap_server, "imap.qq.com")
    
    def test_create_email_provider_outlook(self):
        """测试创建 Outlook 邮箱提供商"""
        from src.email_providers import create_email_provider, EmailProviderOutlook
        
        provider = create_email_provider("outlook", "user@outlook.com", "password")
        
        self.assertIsInstance(provider, EmailProviderOutlook)
        self.assertEqual(provider.config.imap_server, "outlook.office365.com")
    
    def test_create_email_provider_invalid(self):
        """测试创建无效邮箱提供商"""
        from src.email_providers import create_email_provider
        
        provider = create_email_provider("invalid_provider", "user", "pass")
        
        self.assertIsNone(provider)
    
    def test_decode_header(self):
        """测试邮件头解码"""
        from src.email_providers import EmailProvider, EmailConfig
        
        config = EmailConfig(
            provider="test",
            imap_server="test.com",
            imap_port=993,
            smtp_server="test.com",
            smtp_port=465,
            username="test",
            password="test"
        )
        provider = EmailProvider(config)
        
        # 测试普通文本
        result = provider._decode_header("Simple Header")
        self.assertEqual(result, "Simple Header")
        
        # 测试空值
        result = provider._decode_header(None)
        self.assertEqual(result, "")


class TestEmailImportanceClassifier(unittest.TestCase):
    """测试邮件重要性分类器"""
    
    def setUp(self):
        """设置测试环境"""
        from src.email_providers import EmailMessage
        
        self.test_email = EmailMessage(
            uid="1",
            sender="boss@company.com",
            subject="Urgent: Meeting Tomorrow",
            date="2024-01-01",
            is_read=False,
            flags=["\\Flagged"],
            priority_header="1"
        )
    
    def test_classifier_initialization(self):
        """测试分类器初始化"""
        from src.email_importance_classifier import EmailImportanceClassifier
        
        classifier = EmailImportanceClassifier()
        self.assertIsNotNone(classifier)
    
    def test_check_priority_flag_flagged(self):
        """测试优先级标记检测 - 已标记"""
        from src.email_importance_classifier import EmailImportanceClassifier
        
        classifier = EmailImportanceClassifier()
        result = classifier._check_priority_flag(self.test_email)
        
        self.assertTrue(result)
    
    def test_check_priority_flag_high_priority(self):
        """测试优先级标记检测 - 高优先级头"""
        from src.email_importance_classifier import EmailImportanceClassifier
        from src.email_providers import EmailMessage
        
        email = EmailMessage(
            uid="2",
            sender="test@test.com",
            subject="Test",
            date="2024-01-01",
            is_read=False,
            flags=[],
            priority_header="1"  # 高优先级
        )
        
        classifier = EmailImportanceClassifier()
        result = classifier._check_priority_flag(email)
        
        self.assertTrue(result)
    
    def test_check_important_senders(self):
        """测试重要发件人检测"""
        from src.email_importance_classifier import EmailImportanceClassifier
        
        classifier = EmailImportanceClassifier()
        
        # 测试精确匹配
        result = classifier._check_important_senders(
            self.test_email,
            ["boss@company.com"]
        )
        self.assertTrue(result)
        
        # 测试模糊匹配
        result = classifier._check_important_senders(
            self.test_email,
            ["boss"]
        )
        self.assertTrue(result)
        
        # 测试不匹配
        result = classifier._check_important_senders(
            self.test_email,
            ["other@example.com"]
        )
        self.assertFalse(result)
    
    def test_check_domain_whitelist(self):
        """测试域名白名单检测"""
        from src.email_importance_classifier import EmailImportanceClassifier
        
        classifier = EmailImportanceClassifier()
        
        # 测试匹配
        result = classifier._check_domain_whitelist(
            self.test_email,
            ["@company.com"]
        )
        self.assertTrue(result)
        
        # 测试不匹配
        result = classifier._check_domain_whitelist(
            self.test_email,
            ["@other.com"]
        )
        self.assertFalse(result)
    
    def test_check_keywords(self):
        """测试关键词匹配"""
        from src.email_importance_classifier import EmailImportanceClassifier
        
        classifier = EmailImportanceClassifier()
        
        # 测试主题关键词匹配
        result = classifier._check_keywords(
            self.test_email,
            {"subject_keywords": ["Urgent", "Important"], "sender_keywords": []}
        )
        self.assertTrue(result)
        
        # 测试发件人关键词匹配
        result = classifier._check_keywords(
            self.test_email,
            {"subject_keywords": [], "sender_keywords": ["boss"]}
        )
        self.assertTrue(result)
        
        # 测试不匹配
        result = classifier._check_keywords(
            self.test_email,
            {"subject_keywords": ["Newsletter"], "sender_keywords": ["marketing"]}
        )
        self.assertFalse(result)
    
    def test_is_important_combined(self):
        """测试综合重要性判断"""
        from src.email_importance_classifier import EmailImportanceClassifier
        
        rules = {
            "check_priority_flag": True,
            "important_senders": ["boss@company.com"],
            "important_domains": ["@company.com"],
            "keywords": {
                "subject_keywords": ["Urgent"],
                "sender_keywords": []
            }
        }
        
        classifier = EmailImportanceClassifier({"test_provider": rules})
        result = classifier.is_important(self.test_email, "test_provider")
        
        self.assertTrue(result)


class TestEmailChecker(unittest.TestCase):
    """测试邮箱检查服务"""
    
    @patch('src.email_checker.get_mcp_manager')
    def test_email_checker_initialization(self, mock_get_mcp):
        """测试邮箱检查器初始化"""
        mock_mcp = Mock()
        mock_mcp.get_email_check_interval.return_value = 300
        mock_mcp.tokens = {}
        mock_get_mcp.return_value = mock_mcp
        
        from src.email_checker import EmailChecker
        
        checker = EmailChecker(check_interval=600)
        
        self.assertEqual(checker.check_interval, 600)
        self.assertIsNotNone(checker.classifier)
    
    @patch('src.email_checker.get_mcp_manager')
    def test_should_check(self, mock_get_mcp):
        """测试是否应该检查"""
        mock_mcp = Mock()
        mock_mcp.get_email_check_interval.return_value = 300
        mock_mcp.tokens = {}
        mock_get_mcp.return_value = mock_mcp
        
        from src.email_checker import EmailChecker
        import time
        
        checker = EmailChecker(check_interval=300)
        
        # 首次检查应该返回 True
        self.assertTrue(checker.should_check("test_provider"))
        
        # 设置刚刚检查过
        checker.last_check_time["test_provider"] = time.time()
        self.assertFalse(checker.should_check("test_provider"))
        
        # 设置很久以前检查过
        checker.last_check_time["test_provider"] = time.time() - 400
        self.assertTrue(checker.should_check("test_provider"))
    
    @patch('src.email_checker.get_mcp_manager')
    def test_generate_important_email_message(self, mock_get_mcp):
        """测试生成重要邮件提醒消息"""
        mock_mcp = Mock()
        mock_mcp.get_email_check_interval.return_value = 300
        mock_mcp.tokens = {}
        mock_get_mcp.return_value = mock_mcp
        
        from src.email_checker import EmailChecker
        from src.email_providers import EmailMessage
        
        checker = EmailChecker(check_interval=300)
        
        email = EmailMessage(
            uid="1",
            sender="Test User <test@example.com>",
            subject="Test Subject",
            date="2024-01-01",
            is_read=False
        )
        
        message = checker._generate_important_email_message(email)
        
        self.assertIn("Test User", message)
        self.assertIn("Test Subject", message)
    
    @patch('src.email_checker.get_mcp_manager')
    def test_generate_batch_reminder_message(self, mock_get_mcp):
        """测试生成批量邮件提醒消息"""
        mock_mcp = Mock()
        mock_mcp.get_email_check_interval.return_value = 300
        mock_mcp.tokens = {}
        mock_get_mcp.return_value = mock_mcp
        
        from src.email_checker import EmailChecker
        
        checker = EmailChecker(check_interval=300)
        message = checker._generate_batch_reminder_message(15)
        
        self.assertIn("15", message)
    
    @patch('src.email_checker.get_mcp_manager')
    def test_clear_notified_history(self, mock_get_mcp):
        """测试清除已提醒记录"""
        mock_mcp = Mock()
        mock_mcp.get_email_check_interval.return_value = 300
        mock_mcp.tokens = {}
        mock_get_mcp.return_value = mock_mcp
        
        from src.email_checker import EmailChecker
        
        checker = EmailChecker(check_interval=300)
        checker.notified_email_uids = {
            "provider1": {"uid1", "uid2"},
            "provider2": {"uid3"}
        }
        
        # 清除特定提供商
        checker.clear_notified_history("provider1")
        self.assertNotIn("provider1", checker.notified_email_uids)
        self.assertIn("provider2", checker.notified_email_uids)
        
        # 清除所有
        checker.clear_notified_history()
        self.assertEqual(len(checker.notified_email_uids), 0)


class TestEmailIntegration(unittest.TestCase):
    """集成测试 - 测试模块间的协作"""
    
    def test_full_importance_classification_flow(self):
        """测试完整的重要性分类流程"""
        from src.email_providers import EmailMessage
        from src.email_importance_classifier import EmailImportanceClassifier
        
        # 创建测试邮件
        emails = [
            EmailMessage(
                uid="1",
                sender="vip@important.com",
                subject="Meeting Request",
                date="2024-01-01",
                is_read=False,
                flags=["\\Flagged"]
            ),
            EmailMessage(
                uid="2",
                sender="newsletter@spam.com",
                subject="Weekly Newsletter",
                date="2024-01-01",
                is_read=False,
                flags=[]
            ),
            EmailMessage(
                uid="3",
                sender="boss@company.com",
                subject="URGENT: Project Deadline",
                date="2024-01-01",
                is_read=False,
                priority_header="1"
            )
        ]
        
        # 配置规则
        rules = {
            "check_priority_flag": True,
            "important_senders": ["vip@important.com", "boss@company.com"],
            "important_domains": ["@company.com"],
            "keywords": {
                "subject_keywords": ["URGENT", "Meeting"],
                "sender_keywords": []
            }
        }
        
        classifier = EmailImportanceClassifier({"test": rules})
        
        # 分类结果
        results = []
        for email in emails:
            is_important = classifier.is_important(email, "test")
            results.append((email.uid, is_important))
        
        # 验证结果
        self.assertTrue(results[0][1])  # 第一封应该是重要的（有标记 + 重要发件人）
        self.assertFalse(results[1][1])  # 第二封不重要
        self.assertTrue(results[2][1])  # 第三封重要（高优先级 + 重要发件人 + 关键词）


def run_tests():
    """运行所有测试"""
    print("=" * 60)
    print("邮件功能测试")
    print("=" * 60)
    
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加测试类
    suite.addTests(loader.loadTestsFromTestCase(TestEmailProviders))
    suite.addTests(loader.loadTestsFromTestCase(TestEmailImportanceClassifier))
    suite.addTests(loader.loadTestsFromTestCase(TestEmailChecker))
    suite.addTests(loader.loadTestsFromTestCase(TestEmailIntegration))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 输出总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    print(f"运行测试: {result.testsRun}")
    print(f"成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失败: {len(result.failures)}")
    print(f"错误: {len(result.errors)}")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
