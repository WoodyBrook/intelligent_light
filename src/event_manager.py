# event_manager.py - 事件管理器
# 管理各种事件源：用户输入、定时器、传感器、内部驱动

from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass
from datetime import datetime
import threading
import queue
import time
import sys
import select

# 延迟导入，避免循环依赖
_email_checker = None

def _get_email_checker():
    """延迟获取邮箱检查器（动态读取配置）"""
    global _email_checker
    if _email_checker is None:
        try:
            from .email_checker import get_email_checker
            from .mcp_manager import get_mcp_manager
            mcp = get_mcp_manager()
            interval = mcp.get_email_check_interval()
            _email_checker = get_email_checker(check_interval=interval)
        except ImportError:
            # 如果导入失败，返回 None（邮箱功能不可用）
            return None
    return _email_checker


@dataclass
class Event:
    """事件数据结构"""
    type: str  # "user_input", "timer", "sensor", "internal_drive"
    data: Dict[str, Any]
    timestamp: float


class EventManager:
    """
    事件管理器 - 管理多种事件源
    支持非阻塞的事件获取，用于 OODA 循环
    """

    def __init__(self):
        self.event_queue = queue.Queue()
        self.timers = []  # 定时器列表
        self.sensors = {}  # 传感器回调字典
        self.user_input_available = False
        self.last_timer_check = time.time()
        self.last_email_check = time.time()  # 上次邮箱检查时间
        self.last_schedule_check = time.time()  # 上次日程检查时间
        self.input_buffer = ""  # 输入缓冲区
        self.last_input_check = time.time()
        self.internal_event_queue = []  # 用于存储拆分后的子事件

        print("🔄 EventManager 初始化完成")

    def get_event(self) -> Optional[Event]:
        """
        非阻塞获取事件
        检查各种事件源并返回第一个可用的事件
        """
        # 0. 优先处理内部缓冲的事件
        if self.internal_event_queue:
            return self.internal_event_queue.pop(0)

        # 1. 检查用户输入（非阻塞）
        user_event = self._check_user_input()
        if user_event:
            # Latency Masking: 如果是语音输入，先发送一个 VAD 结束信号触发思考动画
            if user_event.type == "user_input":
                vad_event = Event(
                    type="vad_voice_end",
                    data={},
                    timestamp=time.time()
                )
                self.internal_event_queue.append(user_event)
                return vad_event
            return user_event

        # 2. 检查定时器事件
        timer_event = self._check_timers()
        if timer_event:
            return timer_event

        # 3. 检查邮箱事件（在定时器检查后）
        email_event = self._check_email_events()
        if email_event:
            return email_event

        # 4. 检查日程事件
        schedule_event = self._check_schedule_events()
        if schedule_event:
            return schedule_event

        # 5. 检查传感器事件
        sensor_event = self._check_sensors()
        if sensor_event:
            return sensor_event

        # 5. 如果没有其他事件，返回 None（由调用者决定是否触发内部驱动）
        return None

    def _check_user_input(self) -> Optional[Event]:
        """检查用户输入（非阻塞，友好模式）"""
        # 使用 select 检查 stdin 是否有数据
        if sys.platform != 'win32':
            # Unix-like 系统
            import select
            try:
                # 检查是否有输入（非阻塞）
                if select.select([sys.stdin], [], [], 0)[0]:
                    try:
                        # 直接读取输入，不需要额外延时
                        user_input = input().strip()
                        if user_input:
                            print(f"🎤 用户输入: {user_input}")
                            return Event(
                                type="user_input",
                                data={"text": user_input},
                                timestamp=time.time()
                            )
                    except EOFError:
                        pass
            except (OSError, ValueError):
                # select 在某些情况下可能失败，使用备用方案
                pass
        else:
            # Windows 系统（简化处理）
            if self.user_input_available:
                try:
                    user_input = input().strip()
                    self.user_input_available = False
                    if user_input:
                        print(f"🎤 用户输入: {user_input}")
                        return Event(
                            type="user_input",
                            data={"text": user_input},
                            timestamp=time.time()
                        )
                except EOFError:
                    pass

        return None

    def _check_timers(self) -> Optional[Event]:
        """检查定时器事件"""
        current_time = time.time()

        # 每分钟触发一次定时器事件
        if current_time - self.last_timer_check >= 60:  # 60秒 = 1分钟
            self.last_timer_check = current_time
            return Event(
                type="timer",
                data={"interval": "minute", "reason": "periodic_check"},
                timestamp=current_time
            )

        # 每5分钟触发一次状态检查
        if current_time - self.last_timer_check >= 300:  # 300秒 = 5分钟
            return Event(
                type="timer",
                data={"interval": "5_minutes", "reason": "state_check"},
                timestamp=current_time
            )

        return None

    def _check_email_events(self) -> Optional[Event]:
        """
        检查邮箱事件（非阻塞）
        动态读取配置的检查间隔，避免过于频繁
        """
        email_checker = _get_email_checker()
        if not email_checker:
            return None
        
        # 动态获取配置的检查间隔
        try:
            from .mcp_manager import get_mcp_manager
            mcp = get_mcp_manager()
            check_interval = mcp.get_email_check_interval()
            # 最小间隔为配置的 1/5，避免过于频繁
            min_interval = max(60, check_interval // 5)
        except:
            min_interval = 60  # 降级：至少间隔1分钟
        
        current_time = time.time()
        if current_time - self.last_email_check < min_interval:
            return None
        
        try:
            # 检查所有邮箱提供商
            reminders = email_checker.check_all_providers()
            
            if reminders:
                # 只返回第一个提醒（避免一次返回太多事件）
                reminder = reminders[0]
                self.last_email_check = current_time
                
                return Event(
                    type="email_notification",
                    data={
                        "provider_name": reminder.provider_name,
                        "reminder_type": reminder.reminder_type,
                        "message": reminder.message,
                        "emails": [
                            {
                                "uid": e.uid,
                                "sender": e.sender,
                                "subject": e.subject,
                                "date": e.date,
                                "is_important": e.is_important
                            }
                            for e in reminder.emails
                        ]
                    },
                    timestamp=current_time
                )
            else:
                self.last_email_check = current_time
                return None
                
        except Exception as e:
            # 邮箱检查失败不影响其他功能
            print(f"⚠️ 邮箱检查失败: {e}")
            self.last_email_check = current_time
            return None

    def _check_schedule_events(self) -> Optional[Event]:
        """
        检查日程提醒事件（非阻塞）
        每1分钟检查一次窗口
        注意：日程提醒优先级高于专注模式，始终触发
        """
        current_time = time.time()
        
        # 每1分钟检查一次（为了及时提醒，缩小间隔到1分钟）
        if current_time - self.last_schedule_check < 60:
            return None
        
        try:
            from .schedule_manager import get_schedule_manager
            manager = get_schedule_manager()
            
            # 检查即将到来的日程（5分钟窗口）
            upcoming = manager.check_upcoming(window_minutes=5)
            
            if not upcoming:
                self.last_schedule_check = current_time
                return None
            
            # 获取第一个需要提醒的日程
            schedule = upcoming[0]
            
            # 标记已提醒
            manager.mark_reminded(schedule["id"])
            self.last_schedule_check = current_time
            
            print(f"⏰ 触发日程提醒: {schedule['title']} ({schedule['type']})")
            
            return Event(
                type="schedule_reminder",
                data={
                    "schedule": schedule,
                    "reminder_type": "upcoming"
                },
                timestamp=current_time
            )
            
        except Exception as e:
            print(f"⚠️ 日程检查失败: {e}")
            self.last_schedule_check = current_time
            return None

    def _check_sensors(self) -> Optional[Event]:
        """检查传感器事件（模拟实现）"""
        # 这里可以集成真实的传感器
        # 目前返回模拟的触摸传感器事件

        # 模拟：偶尔触发触摸事件（用于测试）
        if time.time() % 100 < 1:  # 大约每100秒有1秒触发
            return Event(
                type="sensor",
                data={"sensor_type": "touch", "value": True},
                timestamp=time.time()
            )

        return None

    def register_timer(self, callback: Callable, interval: int):
        """
        注册定时器（暂时未使用，保留接口）
        """
        self.timers.append({
            "callback": callback,
            "interval": interval,
            "last_trigger": time.time()
        })

    def register_sensor(self, sensor_type: str, callback: Callable):
        """
        注册传感器（暂时未使用，保留接口）
        """
        self.sensors[sensor_type] = callback

    def signal_user_input_available(self):
        """
        信号指示用户输入可用（用于 Windows 系统）
        """
        self.user_input_available = True

    def get_event_summary(self) -> Dict[str, Any]:
        """
        获取事件管理器状态摘要
        """
        return {
            "timers_count": len(self.timers),
            "sensors_count": len(self.sensors),
            "queue_size": self.event_queue.qsize(),
            "last_timer_check": self.last_timer_check,
            "last_email_check": self.last_email_check,
            "last_schedule_check": self.last_schedule_check
        }
