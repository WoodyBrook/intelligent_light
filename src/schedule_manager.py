# schedule_manager.py - 本地日程管理器
# 负责日程、提醒、待办事项和注意事项的 CRUD 及持久化

import os
import json
import time
import uuid
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import calendar

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ScheduleManager")

class ScheduleManager:
    """
    日程管理器 - 管理本地日程和提醒
    """
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(ScheduleManager, cls).__new__(cls)
        return cls._instance

    def __init__(self, data_file: str = "./data/schedules.json"):
        # 确保只初始化一次
        if hasattr(self, 'initialized'):
            return
        
        self.data_file = data_file
        self.schedules: List[Dict[str, Any]] = []
        self.last_check_time = time.time()
        self.initialized = True
        
        # 加载数据
        self._load_data()
        logger.info(f"ScheduleManager 初始化完成，加载了 {len(self.schedules)} 条日程")

    def _load_data(self):
        """从 JSON 文件加载数据"""
        if not os.path.exists(self.data_file):
            self.schedules = []
            return

        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.schedules = data.get("schedules", [])
                self.last_check_time = data.get("last_check_time", time.time())
        except Exception as e:
            logger.error(f"[ERROR] 加载日程数据失败: {e}")
            self.schedules = []

    def _save_data(self):
        """保存数据到 JSON 文件"""
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
            
            data = {
                "schedules": self.schedules,
                "last_check_time": self.last_check_time,
                "updated_at": time.time()
            }
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            # logger.info(f"日程数据已保存到 {self.data_file}")
        except Exception as e:
            logger.error(f"[ERROR] 保存日程数据失败: {e}")

    def _calculate_next_occurrence(self, schedule: Dict[str, Any], after_ts: float) -> Optional[float]:
        """
        计算循环事件在指定时间之后的下一次发生时间
        
        Args:
            schedule: 日程项（必须有 recurrence 字段）
            after_ts: 在此时间戳之后查找下一次发生
            
        Returns:
            下一次发生的时间戳，如果无法计算则返回 None
        """
        recurrence = schedule.get("recurrence")
        if not recurrence:
            return None
            
        base_ts = schedule.get("datetime")
        if base_ts is None:
            return None
            
        recurrence_type = recurrence.get("type")
        interval = recurrence.get("interval", 1)
        base_dt = datetime.fromtimestamp(base_ts)
        after_dt = datetime.fromtimestamp(after_ts)
        
        if recurrence_type == "daily":
            # 每 N 天重复
            days_since_base = (after_dt.date() - base_dt.date()).days
            if days_since_base < 0:
                next_dt = base_dt
            else:
                periods_passed = days_since_base // interval
                next_dt = base_dt + timedelta(days=periods_passed * interval)
                # 如果 next_dt 已经过了 after_ts，取下一个周期
                if next_dt.timestamp() <= after_ts:
                    next_dt = base_dt + timedelta(days=(periods_passed + 1) * interval)
            return next_dt.timestamp()
            
        elif recurrence_type == "weekly":
            # 每周特定日重复
            days_of_week = recurrence.get("days_of_week", [base_dt.weekday()])
            if not days_of_week:
                days_of_week = [base_dt.weekday()]
            
            # 从 max(after_dt, base_dt 的前一天) 开始往后找
            # 这样确保如果 after_ts 是 0（首次），我们从 base_dt 开始找
            start_dt = after_dt if after_ts >= base_ts else base_dt - timedelta(days=1)
            check_dt = start_dt.replace(hour=base_dt.hour, minute=base_dt.minute, 
                                        second=base_dt.second, microsecond=0)
            for day_offset in range(8):  # 最多查7天
                candidate = check_dt + timedelta(days=day_offset)
                if candidate.weekday() in days_of_week and candidate.timestamp() > after_ts:
                    return candidate.timestamp()
            return None
            
        elif recurrence_type == "monthly":
            # 每月特定日重复
            day_of_month = recurrence.get("day_of_month", base_dt.day)
            
            # 从 max(after_dt, base_dt) 的月份开始检查
            start_dt = after_dt if after_ts >= base_ts else base_dt
            year, month = start_dt.year, start_dt.month
            for _ in range(13):  # 最多检查13个月
                # 处理月末溢出（如31号在2月变成28/29号）
                max_day = calendar.monthrange(year, month)[1]
                actual_day = min(day_of_month, max_day)
                
                try:
                    candidate = datetime(year, month, actual_day, 
                                         base_dt.hour, base_dt.minute, base_dt.second)
                    if candidate.timestamp() > after_ts:
                        return candidate.timestamp()
                except ValueError:
                    pass  # 无效日期，跳过
                
                # 下个月
                month += 1
                if month > 12:
                    month = 1
                    year += 1
            return None
            
        elif recurrence_type == "yearly":
            # 每年特定日期重复
            start_dt = after_dt if after_ts >= base_ts else base_dt
            year = start_dt.year
            for _ in range(5):  # 最多检查5年
                try:
                    candidate = datetime(year, base_dt.month, base_dt.day,
                                         base_dt.hour, base_dt.minute, base_dt.second)
                    if candidate.timestamp() > after_ts:
                        return candidate.timestamp()
                except ValueError:
                    pass  # 2月29日等特殊情况
                year += 1
            return None
            
        return None

    def add_schedule(self, 
                     title: str, 
                     datetime_ts: Optional[float], 
                     schedule_type: str = "reminder", 
                     reminder_minutes: int = 0,
                     description: str = "",
                     recurrence: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        添加日程
        
        Args:
            title: 标题
            datetime_ts: 时间戳（Unix timestamp），对于循环事件为首次发生时间
            schedule_type: 类型 "schedule" | "reminder" | "todo" | "note"
            reminder_minutes: 提前提醒分钟数
            description: 描述
            recurrence: 循环规则（可选）
                - type: "daily" | "weekly" | "monthly" | "yearly"
                - interval: 间隔数量（默认1）
                - days_of_week: [0-6] 周几（仅 weekly）
                - day_of_month: 1-31 每月几号（仅 monthly）
        """
        new_item = {
            "id": str(uuid.uuid4()),
            "title": title,
            "type": schedule_type,
            "datetime": datetime_ts,
            "reminder_minutes": reminder_minutes,
            "description": description,
            "completed": False,
            "created_at": time.time(),
            "reminded": False
        }
        
        # 添加循环规则（如果有）
        if recurrence:
            new_item["recurrence"] = recurrence
            new_item["last_reminded_at"] = None  # 用于循环事件的去重
        
        self.schedules.append(new_item)
        self._save_data()
        recurrence_label = " (循环)" if recurrence else ""
        logger.info(f"➕ 添加日程: [{schedule_type}] {title}{recurrence_label}")
        return new_item

    def get_schedules(self, 
                      start_ts: Optional[float] = None, 
                      end_ts: Optional[float] = None, 
                      schedule_type: Optional[str] = None,
                      include_completed: bool = False) -> List[Dict[str, Any]]:
        """
        查询日程
        """
        results = self.schedules
        
        # 按类型过滤
        if schedule_type:
            results = [s for s in results if s["type"] == schedule_type]
            
        # 按完成状态过滤（仅针对 todo）
        if not include_completed:
            results = [s for s in results if not (s["type"] == "todo" and s["completed"])]
            
        # 按时间范围过滤
        if start_ts is not None:
            results = [s for s in results if s["datetime"] is None or s["datetime"] >= start_ts]
        if end_ts is not None:
            results = [s for s in results if s["datetime"] is None or s["datetime"] <= end_ts]
            
        # 按时间排序
        results.sort(key=lambda x: x["datetime"] if x["datetime"] is not None else float('inf'))
        
        return results

    def delete_schedule(self, schedule_id: str) -> bool:
        """删除日程"""
        initial_count = len(self.schedules)
        self.schedules = [s for s in self.schedules if s["id"] != schedule_id]
        
        if len(self.schedules) < initial_count:
            self._save_data()
            logger.info(f"删除日程: {schedule_id}")
            return True
        return False

    def complete_todo(self, schedule_id: str) -> bool:
        """标记待办事项为完成"""
        for s in self.schedules:
            if s["id"] == schedule_id:
                s["completed"] = True
                self._save_data()
                logger.info(f"完成待办: {s['title']}")
                return True
        return False

    def check_upcoming(self, window_minutes: int = 5) -> List[Dict[str, Any]]:
        """
        检查即将到来的日程（支持循环事件）
        """
        current_time = time.time()
        upcoming = []
        
        for schedule in self.schedules:
            # 跳过 note 类型和已完成的 todo
            if schedule["type"] == "note":
                continue
            if schedule["type"] == "todo" and schedule["completed"]:
                continue
            
            if schedule["datetime"] is None:
                continue
            
            recurrence = schedule.get("recurrence")
            
            if recurrence:
                # === 循环事件逻辑 ===
                last_reminded = schedule.get("last_reminded_at") or 0
                
                # 计算搜索起点：从上次提醒时间或(当前时间-提醒窗口-提前量)开始
                # 这确保我们能找到当前窗口内的事件，即使 last_reminded 很久以前
                reminder_minutes = schedule["reminder_minutes"]
                search_start = max(last_reminded, current_time - window_minutes * 60 - reminder_minutes * 60 - 1)
                
                # 计算下一次发生时间
                next_occurrence = self._calculate_next_occurrence(schedule, search_start)
                if next_occurrence is None:
                    continue
                
                # 计算这次发生的提醒时间点
                reminder_time = next_occurrence - reminder_minutes * 60
                
                # 检查是否在提醒窗口内，且尚未提醒过这次
                if (reminder_time <= current_time < reminder_time + window_minutes * 60 
                    and next_occurrence > last_reminded):
                    # 返回一个带有 next_occurrence 信息的副本
                    schedule_copy = schedule.copy()
                    schedule_copy["_next_occurrence"] = next_occurrence
                    upcoming.append(schedule_copy)
            else:
                # === 非循环事件逻辑（保持原有行为）===
                if schedule["reminded"]:
                    continue
                    
                reminder_time = schedule["datetime"] - schedule["reminder_minutes"] * 60
                
                if reminder_time <= current_time < reminder_time + window_minutes * 60:
                    upcoming.append(schedule)
        
        return upcoming

    def mark_reminded(self, schedule_id: str, occurrence_ts: Optional[float] = None):
        """
        标记为已提醒
        
        Args:
            schedule_id: 日程ID
            occurrence_ts: 对于循环事件，记录本次提醒的发生时间
        """
        for s in self.schedules:
            if s["id"] == schedule_id:
                if s.get("recurrence"):
                    # 循环事件：更新 last_reminded_at 而不是 reminded
                    s["last_reminded_at"] = occurrence_ts or time.time()
                else:
                    # 非循环事件：标记为已提醒
                    s["reminded"] = True
                self._save_data()
                break

def get_schedule_manager() -> ScheduleManager:
    """获取单例实例"""
    return ScheduleManager()

if __name__ == "__main__":
    # 简单测试
    manager = get_schedule_manager()
    now = time.time()
    
    # 添加测试数据
    manager.add_schedule("测试会议", now + 60, "schedule", 5) # 1分钟后开会，5分钟前提醒 -> 立即提醒
    manager.add_schedule("喝水提醒", now + 10, "reminder")   # 10秒后提醒
    
    # 模拟等待一点时间
    time.sleep(1)
    
    # 查询
    print(f"当前日程数: {len(manager.get_schedules())}")
    
    # 检查提醒
    upcoming = manager.check_upcoming(5)
    print(f"即将到来的提醒: {len(upcoming)}")
    for s in upcoming:
        print(f" - {s['title']} ({s['type']})")
