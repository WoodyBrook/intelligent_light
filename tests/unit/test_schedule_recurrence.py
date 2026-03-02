# test_schedule_recurrence.py
# 测试 ScheduleManager 的循环事件功能

import pytest
import time
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
import json
import os
import tempfile


class TestScheduleRecurrence:
    """测试循环事件功能"""
    
    @pytest.fixture
    def manager(self):
        """创建临时的 ScheduleManager 实例"""
        # 使用临时文件避免影响真实数据
        from src.schedule_manager import ScheduleManager
        
        # 重置单例
        ScheduleManager._instance = None
        
        # 创建临时目录
        temp_dir = tempfile.mkdtemp()
        temp_file = os.path.join(temp_dir, "test_schedules.json")
        
        manager = ScheduleManager(data_file=temp_file)
        yield manager
        
        # 清理
        if os.path.exists(temp_file):
            os.remove(temp_file)
        if os.path.exists(temp_dir):
            os.rmdir(temp_dir)
        
        # 重置单例
        ScheduleManager._instance = None
    
    # === Test: Add weekly recurrence ===
    def test_add_weekly_recurrence(self, manager):
        """测试创建周循环事件"""
        # 创建一个每周一10:00的会议
        base_time = datetime(2026, 1, 19, 10, 0, 0).timestamp()  # 2026-01-19 是周一
        
        recurrence = {
            "type": "weekly",
            "interval": 1,
            "days_of_week": [0]  # 周一
        }
        
        item = manager.add_schedule(
            title="Weekly Meeting",
            datetime_ts=base_time,
            schedule_type="schedule",
            reminder_minutes=15,
            recurrence=recurrence
        )
        
        assert item["title"] == "Weekly Meeting"
        assert item["recurrence"] == recurrence
        assert item["last_reminded_at"] is None
        assert "id" in item
    
    # === Test: Weekly check_upcoming ===
    def test_check_upcoming_weekly(self, manager):
        """测试周循环事件的提醒触发"""
        # 创建一个每周一 10:00 的会议
        base_time = datetime(2026, 1, 19, 10, 0, 0).timestamp()  # 周一
        
        recurrence = {
            "type": "weekly",
            "interval": 1,
            "days_of_week": [0]
        }
        
        manager.add_schedule(
            title="Weekly Meeting",
            datetime_ts=base_time,
            schedule_type="schedule",
            reminder_minutes=15,
            recurrence=recurrence
        )
        
        # Mock 时间到周一 09:47（提醒时间点09:45之后，在提醒窗口内）
        mock_time = datetime(2026, 1, 19, 9, 47, 0).timestamp()
        
        with patch('src.schedule_manager.time.time', return_value=mock_time):
            upcoming = manager.check_upcoming(window_minutes=5)
        
        assert len(upcoming) == 1
        assert upcoming[0]["title"] == "Weekly Meeting"
        assert "_next_occurrence" in upcoming[0]
    
    # === Test: Monthly recurrence ===
    def test_check_upcoming_monthly(self, manager):
        """测试月循环事件的提醒触发"""
        # 创建一个每月15号 09:00 的提醒
        base_time = datetime(2026, 1, 15, 9, 0, 0).timestamp()
        
        recurrence = {
            "type": "monthly",
            "interval": 1,
            "day_of_month": 15
        }
        
        manager.add_schedule(
            title="Monthly Rent",
            datetime_ts=base_time,
            schedule_type="reminder",
            reminder_minutes=0,
            recurrence=recurrence
        )
        
        # Mock 时间到 2月15日 09:00
        mock_time = datetime(2026, 2, 15, 9, 0, 0).timestamp()
        
        with patch('src.schedule_manager.time.time', return_value=mock_time):
            upcoming = manager.check_upcoming(window_minutes=5)
        
        assert len(upcoming) == 1
        assert upcoming[0]["title"] == "Monthly Rent"
    
    # === Test: Monthly day overflow (31st in Feb) ===
    def test_monthly_day_overflow(self, manager):
        """测试每月31号在2月的处理（应回退到28/29号）"""
        # 创建一个每月31号的提醒
        base_time = datetime(2026, 1, 31, 10, 0, 0).timestamp()
        
        recurrence = {
            "type": "monthly",
            "interval": 1,
            "day_of_month": 31
        }
        
        manager.add_schedule(
            title="End of Month Review",
            datetime_ts=base_time,
            schedule_type="schedule",
            reminder_minutes=0,
            recurrence=recurrence
        )
        
        # Mock 时间到 2026年2月28日（非闰年，2月只有28天）
        mock_time = datetime(2026, 2, 28, 10, 0, 0).timestamp()
        
        with patch('src.schedule_manager.time.time', return_value=mock_time):
            upcoming = manager.check_upcoming(window_minutes=5)
        
        assert len(upcoming) == 1
        assert upcoming[0]["title"] == "End of Month Review"
    
    # === Test: Deduplication via last_reminded_at ===
    def test_deduplication(self, manager):
        """测试 last_reminded_at 防止重复提醒"""
        base_time = datetime(2026, 1, 19, 10, 0, 0).timestamp()
        
        recurrence = {
            "type": "weekly",
            "interval": 1,
            "days_of_week": [0]
        }
        
        item = manager.add_schedule(
            title="Weekly Meeting",
            datetime_ts=base_time,
            schedule_type="schedule",
            reminder_minutes=15,
            recurrence=recurrence
        )
        
        # 第一次检查 - 应该触发
        mock_time = datetime(2026, 1, 19, 9, 50, 0).timestamp()
        with patch('src.schedule_manager.time.time', return_value=mock_time):
            upcoming = manager.check_upcoming(window_minutes=10)
        assert len(upcoming) == 1
        
        # 标记为已提醒
        occurrence_ts = upcoming[0]["_next_occurrence"]
        manager.mark_reminded(item["id"], occurrence_ts)
        
        # 第二次检查同一时间 - 不应该再触发
        with patch('src.schedule_manager.time.time', return_value=mock_time):
            upcoming = manager.check_upcoming(window_minutes=10)
        assert len(upcoming) == 0
        
        # 下周一应该再次触发
        next_week_mock_time = datetime(2026, 1, 26, 9, 50, 0).timestamp()
        with patch('src.schedule_manager.time.time', return_value=next_week_mock_time):
            upcoming = manager.check_upcoming(window_minutes=10)
        assert len(upcoming) == 1
    
    # === Test: Backward compatibility ===
    def test_backward_compatibility(self, manager):
        """测试旧的非循环日程仍然正常工作"""
        # 创建一个普通的一次性事件（无 recurrence）
        event_time = time.time() + 300  # 5分钟后
        
        item = manager.add_schedule(
            title="One-time Meeting",
            datetime_ts=event_time,
            schedule_type="schedule",
            reminder_minutes=10
            # 不传 recurrence
        )
        
        assert "recurrence" not in item
        assert item["reminded"] is False
        
        # 检查提醒窗口
        mock_time = event_time - 600 + 1  # 提醒点后1秒
        with patch('src.schedule_manager.time.time', return_value=mock_time):
            upcoming = manager.check_upcoming(window_minutes=5)
        
        assert len(upcoming) == 1
        
        # 标记已提醒
        manager.mark_reminded(item["id"])
        
        # 再次检查 - 不应触发
        with patch('src.schedule_manager.time.time', return_value=mock_time):
            upcoming = manager.check_upcoming(window_minutes=5)
        assert len(upcoming) == 0
    
    # === Test: Daily recurrence ===
    def test_daily_recurrence(self, manager):
        """测试每日循环事件"""
        base_time = datetime(2026, 1, 20, 8, 0, 0).timestamp()
        
        recurrence = {
            "type": "daily",
            "interval": 1
        }
        
        manager.add_schedule(
            title="Morning Standup",
            datetime_ts=base_time,
            schedule_type="reminder",
            reminder_minutes=0,
            recurrence=recurrence
        )
        
        # 第二天同一时间应该触发
        mock_time = datetime(2026, 1, 21, 8, 0, 0).timestamp()
        with patch('src.schedule_manager.time.time', return_value=mock_time):
            upcoming = manager.check_upcoming(window_minutes=5)
        
        assert len(upcoming) == 1
        assert upcoming[0]["title"] == "Morning Standup"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
