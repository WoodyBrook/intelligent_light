
import os
import sys
import shutil
import time
import uuid
import logging
from datetime import datetime, timedelta

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from schedule_manager import ScheduleManager
from memory_manager import MemoryManager
from pattern_scanner import PatternScanner

# Setup Logging: Silence internal logs
logging.getLogger().setLevel(logging.WARNING)

# Colors for prettifying output
class Colors:
    HEADER = ''
    BLUE = ''
    CYAN = ''
    GREEN = ''
    WARNING = ''
    FAIL = ''
    ENDC = ''
    BOLD = ''
    UNDERLINE = ''

# Emoji stripper
import re
def remove_emojis(text):
    # Remove common emojis used in the codebase
    return re.sub(r'[📅➕🗑✅🔧🔄💾📊💡⚙️👤🤖]', '', text).strip()

# Patch print to clean internal outputs
_original_print = print
def clean_print(*args, **kwargs):
    # Only clean if it looks like a system message (args[0] is str)
    if args and isinstance(args[0], str):
        cleaned_args = tuple(remove_emojis(str(arg)) for arg in args)
        # If cleaning resulted in empty string (e.g. just an emoji), skip? 
        # No, just print cleaned.
        # Also remove "INFO:..." if any slip through, though logging level should handle that.
        _original_print(*cleaned_args, **kwargs)
    else:
        _original_print(*args, **kwargs)

import builtins
builtins.print = clean_print

def print_box(text, color=Colors.BLUE):
    print(f"{color}{text}{Colors.ENDC}")

def print_user(text):
    print(f"{Colors.GREEN}用户: {text}{Colors.ENDC}")

def print_ai(text):
    print(f"{Colors.CYAN}AI: {text}{Colors.ENDC}")

def print_system(text):
    print(f"{Colors.WARNING}系统: {text}{Colors.ENDC}")

def run_demo():
    # Setup Temporary Environment
    run_id = str(uuid.uuid4())[:8]
    test_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), f"../data/demo_{run_id}"))
    os.makedirs(test_dir, exist_ok=True)
    
    print_box(f"Neko-Light 功能演示 (环境: {run_id})", Colors.HEADER)
    print("正在初始化核心系统...\n")
    
    try:
        schedule_file = os.path.join(test_dir, "schedules.json")
        db_path = os.path.join(test_dir, "chroma_db")
        
        # Init Managers
        schedule_manager = ScheduleManager(data_file=schedule_file)
        # Mock Memory Manager's persistent store effectively for the demo
        memory_manager = MemoryManager(db_path=db_path)
        memory_manager.profile_path = os.path.join(test_dir, "user_profile.json")
        pattern_scanner = PatternScanner(memory_manager)
        
        # === SCENARIO 1: SCHEDULE MANAGEMENT ===
        print_box("场景一：智能日程管理")
        
        # Step 1: User request
        print_user("帮我定一个每周一下午3点的团队周会。")
        
        # Action
        now = datetime.now()
        days_until_monday = (7 - now.weekday()) % 7
        if days_until_monday == 0: days_until_monday = 7
        next_monday = now + timedelta(days=days_until_monday)
        target_ts = next_monday.replace(hour=15, minute=0, second=0).timestamp()
        
        item = schedule_manager.add_schedule(
            title="团队周会",
            datetime_ts=target_ts,
            schedule_type="schedule",
            recurrence={"type": "weekly", "days_of_week": [0]}
        )
        
        print_ai(f"好的！正在核对日程...")
        display_time = datetime.fromtimestamp(target_ts).strftime('%A %H:%M')
        # Simple translation for display weekday
        weekday_map = {"Monday": "周一", "Tuesday": "周二", "Wednesday": "周三", "Thursday": "周四", "Friday": "周五", "Saturday": "周六", "Sunday": "周日"}
        for en, cn in weekday_map.items():
            display_time = display_time.replace(en, cn)
            
        print_system(f"已添加日程: [每周] {item['title']} @ {display_time}")
        
        # Step 2: Change time
        print("\n" + "-"*30 + "\n")
        print_user("还是改成下午4点吧。")
        
        print_ai("这就为您更新...")
        schedule_manager.delete_schedule(item["id"])
        new_ts = next_monday.replace(hour=16, minute=0).timestamp()
        schedule_manager.add_schedule(
            title="团队周会",
            datetime_ts=new_ts,
            schedule_type="schedule",
            recurrence={"type": "weekly", "days_of_week": [0]}
        )
        
        new_display_time = datetime.fromtimestamp(new_ts).strftime('%H:%M')
        print_system(f"日程已更新: {item['title']} 时间调整为 {new_display_time}")
        
        
        # === SCENARIO 2: PATTERN RECOGNITION ===
        print("\n")
        print_box("场景二：智能规律发现")
        
        # Step 1: Month 1
        print_system("时间穿越: 2025-01-10 (周五)")
        print_user("耶！今天发工资啦！")
        
        date_1 = datetime(2025, 1, 10, 10, 0)
        memory_manager.save_user_memory("今天发工资了", metadata={
            "timestamp": date_1.timestamp(),
            "date": "2025-01-10",
            "day_of_month": 10,
            "weekday": 4
        })
        print_ai("已记录。")
        
        # Step 2: Month 2
        print("\n" + "-"*30 + "\n")
        print_system("时间穿越: 2025-02-10 (周一)")
        print_user("收到工资了！该还信用卡了。")
        
        date_2 = datetime(2025, 2, 10, 10, 0)
        memory_manager.save_user_memory("今天发工资了", metadata={
            "timestamp": date_2.timestamp(),
            "date": "2025-02-10",
            "day_of_month": 10,
            "weekday": 0
        })
        print_ai("收到。")
        
        # Step 3: Insight
        print("\n" + "-"*30 + "\n")
        print_system("夜间处理: 正在扫描行为规律...")
        
        patterns = pattern_scanner.scan_all_patterns()
        
        if patterns:
            for p in patterns:
                print_ai(f"我发现了一个规律：")
                # Ensure width handling for Chinese characters in box is tricky, keeping it simple
                content = f"检测到规律: {p['frequency']} - {p['sample_content']} (置信度: {p['confidence']})"
                print(f"{Colors.GREEN}{content}{Colors.ENDC}")
        else:
            print_system("暂未发现规律。")

        # Cleanup
        # shutil.rmtree(test_dir)
        print("\n")
        print_box("演示成功完成", Colors.HEADER)
        print(f"测试数据保留在: {test_dir} (用于检查)")

    except Exception as e:
        print_box(f"演示失败: {e}", Colors.FAIL)
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_demo()
