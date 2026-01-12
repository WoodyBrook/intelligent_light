# schedule_manager.py - 本地日程管理器
# 负责日程、提醒、待办事项和注意事项的 CRUD 及持久化

import os
import json
import time
import uuid
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

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
        logger.info(f"📅 ScheduleManager 初始化完成，加载了 {len(self.schedules)} 条日程")

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
            logger.error(f"❌ 加载日程数据失败: {e}")
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
            # logger.info(f"💾 日程数据已保存到 {self.data_file}")
        except Exception as e:
            logger.error(f"❌ 保存日程数据失败: {e}")

    def add_schedule(self, 
                     title: str, 
                     datetime_ts: Optional[float], 
                     schedule_type: str = "reminder", 
                     reminder_minutes: int = 0,
                     description: str = "") -> Dict[str, Any]:
        """
        添加日程
        
        Args:
            title: 标题
            datetime_ts: 时间戳（Unix timestamp）
            schedule_type: 类型 "schedule" | "reminder" | "todo" | "note"
            reminder_minutes: 提前提醒分钟数
            description: 描述
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
        
        self.schedules.append(new_item)
        self._save_data()
        logger.info(f"➕ 添加日程: [{schedule_type}] {title}")
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
            logger.info(f"🗑️ 删除日程: {schedule_id}")
            return True
        return False

    def complete_todo(self, schedule_id: str) -> bool:
        """标记待办事项为完成"""
        for s in self.schedules:
            if s["id"] == schedule_id:
                s["completed"] = True
                self._save_data()
                logger.info(f"✅ 完成待办: {s['title']}")
                return True
        return False

    def check_upcoming(self, window_minutes: int = 5) -> List[Dict[str, Any]]:
        """
        检查即将到来的日程
        """
        current_time = time.time()
        upcoming = []
        
        for schedule in self.schedules:
            # 跳过 note 类型、已完成的 todo 和已提醒的
            if schedule["type"] == "note" or schedule["reminded"]:
                continue
            if schedule["type"] == "todo" and schedule["completed"]:
                continue
            
            if schedule["datetime"] is None:
                continue
            
            # 计算提醒时间点
            # schedule 类型提前 reminder_minutes 提醒
            # reminder/todo 类型到点提醒 (reminder_minutes = 0)
            reminder_time = schedule["datetime"] - schedule["reminder_minutes"] * 60
            
            # 检查是否在提醒窗口内（当前时间已过提醒点，且在窗口内）
            # 我们允许一点延迟，只要在 window_minutes 分钟内
            if reminder_time <= current_time < reminder_time + window_minutes * 60:
                upcoming.append(schedule)
        
        return upcoming

    def mark_reminded(self, schedule_id: str):
        """标记为已提醒"""
        for s in self.schedules:
            if s["id"] == schedule_id:
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
