
import os
import sys
import shutil
import time
import json
import logging
import unittest
from datetime import datetime, timedelta
from typing import Dict, Any, List

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src")))

from schedule_manager import ScheduleManager
from memory_manager import MemoryManager
from pattern_scanner import PatternScanner

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TestScenarios")

class TestFunctionalScenarios(unittest.TestCase):
    def setUp(self):
        # Setup paths with unique ID to avoid locks
        import uuid
        self.run_id = str(uuid.uuid4())
        self.test_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), f"../../data/test_functional_{self.run_id}"))
        
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
        os.makedirs(self.test_dir, exist_ok=True)
        
        self.schedule_file = os.path.join(self.test_dir, "schedules.json")
        self.db_path = os.path.join(self.test_dir, "chroma_db")
        
        logger.info(f"Test Directory: {self.test_dir}")
        
        # Initialize Managers with test paths
        self.schedule_manager = ScheduleManager(data_file=self.schedule_file)
        self.schedule_manager.schedules = [] # Reset explicitly
        
        # For MemoryManager, we need to handle embeddings.
        try:
            # Check permissions
            test_file = os.path.join(self.test_dir, "test_write.txt")
            with open(test_file, "w") as f:
                f.write("test")
            logger.info("Write permission verified")
            
            self.memory_manager = MemoryManager(db_path=self.db_path)
            # Override profile path
            self.memory_manager.profile_path = os.path.join(self.test_dir, "user_profile.json")
        except Exception as e:
            logger.error(f"Failed to init MemoryManager: {e}")
            self.skipTest("MemoryManager failed to initialize")

        self.pattern_scanner = PatternScanner(self.memory_manager)

    def tearDown(self):
        # Cleanup
        try:
            # Force close chroma if possible? 
            # Chroma client handling is tricky, often holds locks.
            # We will try to delete.
             if os.path.exists(self.test_dir):
                 # Wait a bit
                 time.sleep(1)
                 # On Mac/Linux usually fine, but let's see.
                 # shutil.rmtree(self.test_dir) # Disable cleanup for debugging if needed
                 pass 
        except Exception as e:
            logger.warning(f"Cleanup failed: {e}")

    def test_scenario_1_weekly_schedule(self):
        logger.info("=== Testing Scenario 1: Weekly Schedule ===")
        
        # 1. Add Schedule
        # Next Monday 15:00
        now = datetime.now()
        days_ahead = 0 - now.weekday() if now.weekday() < 0 else 7 - now.weekday() # This finds next monday?
        # Actually proper calculation:
        today = datetime.now()
        days_until_monday = (7 - today.weekday()) % 7
        if days_until_monday == 0:
            days_until_monday = 7 # Next monday
        
        next_monday = today + timedelta(days=days_until_monday)
        target_time = next_monday.replace(hour=15, minute=0, second=0, microsecond=0)
        target_ts = target_time.timestamp()
        
        recurrence = {
            "type": "weekly",
            "days_of_week": [0], # Monday
            "interval": 1
        }
        
        logger.info(f"Adding schedule for {target_time}, recurrence: {recurrence}")
        item = self.schedule_manager.add_schedule(
            title="Weekly Meeting",
            datetime_ts=target_ts,
            schedule_type="schedule",
            recurrence=recurrence
        )
        
        # Verify Added
        schedules = self.schedule_manager.get_schedules()
        self.assertEqual(len(schedules), 1)
        self.assertEqual(schedules[0]["title"], "Weekly Meeting")
        self.assertEqual(schedules[0]["recurrence"]["type"], "weekly")
        
        # 2. Update Schedule (via Delete + Add) -> Change to 16:00
        logger.info("Updating schedule to 16:00")
        schedule_id = item["id"]
        
        # Delete
        deleted = self.schedule_manager.delete_schedule(schedule_id)
        self.assertTrue(deleted)
        self.assertEqual(len(self.schedule_manager.get_schedules()), 0)
        
        # Add New
        new_target_time = target_time.replace(hour=16)
        new_target_ts = new_target_time.timestamp()
        
        new_item = self.schedule_manager.add_schedule(
            title="Weekly Meeting",
            datetime_ts=new_target_ts, # 16:00
            schedule_type="schedule",
            recurrence=recurrence
        )
        
        # Verify Update
        schedules = self.schedule_manager.get_schedules()
        self.assertEqual(len(schedules), 1)
        self.assertEqual(schedules[0]["datetime"], new_target_ts)
        self.assertEqual(schedules[0]["recurrence"]["type"], "weekly")
        
        # 3. Delete Schedule
        logger.info("Deleting schedule")
        self.schedule_manager.delete_schedule(new_item["id"])
        self.assertEqual(len(self.schedule_manager.get_schedules()), 0)
        logger.info("Scenario 1 Passed")

    def test_scenario_2_pattern_extraction(self):
        logger.info("=== Testing Scenario 2: Pattern Extraction ===")
        
        # 1. Form Memory (Jan 10)
        date_1 = datetime(2025, 1, 10, 10, 0, 0)
        ts_1 = date_1.timestamp()
        
        # We need to manually inject day_of_month because save_user_memory doesn't seem to calculate it from timestamp automatically
        # based on my reading. PatternScanner relies on metadata 'day_of_month'.
        
        meta_1 = {
            "timestamp": ts_1,
            "creation_time": ts_1,
            "date": date_1.strftime("%Y-%m-%d %H:%M:%S"),
            "day_of_month": 10, # Crucial for scanner
            "month": 1,
            "weekday": 4 # Friday
        }
        
        logger.info("Saving memory for Jan 10: Payroll received")
        self.memory_manager.save_user_memory("今天发工资了", metadata=meta_1)
        
        # 2. Reinforce Memory (Feb 10)
        date_2 = datetime(2025, 2, 10, 10, 0, 0)
        ts_2 = date_2.timestamp()
        
        meta_2 = {
            "timestamp": ts_2,
            "creation_time": ts_2,
            "date": date_2.strftime("%Y-%m-%d %H:%M:%S"),
            "day_of_month": 10,
            "month": 2,
            "weekday": 0 # Monday
        }
        
        logger.info("Saving memory for Feb 10: Payroll received")
        self.memory_manager.save_user_memory("今天发工资了", metadata=meta_2)
        
        # 3. Pattern Extraction
        logger.info("Scanning for patterns...")
        patterns = self.pattern_scanner.scan_all_patterns()
        
        found = False
        for p in patterns:
            logger.info(f"Found pattern: {p}")
            if p["type"] == "monthly" and p["day_of_month"] == 10:
                found = True
                self.assertIn("工资", str(p))
                
        self.assertTrue(found, "Should have found monthly payroll pattern")
        
        # 4. Consolidate to Profile (Mocking profile)
        # Verify scanner can consolidate
        class MockProfile:
            def __init__(self):
                self.important_dates = []
            def dict(self):
                return {"important_dates": self.important_dates}
                
        # Mocking load_profile and save_profile on memory_manager
        original_load = getattr(self.memory_manager, "load_profile", None)
        original_save = getattr(self.memory_manager, "save_profile", None)
        
        mock_profile_obj = MockProfile()
        
        self.memory_manager.load_profile = lambda: mock_profile_obj
        self.memory_manager.save_profile = lambda p: None # Do nothing on save
        
        added_count = self.pattern_scanner.consolidate_to_profile(patterns)
        
        self.assertGreaterEqual(added_count, 1)
        self.assertEqual(len(mock_profile_obj.important_dates), 1)
        self.assertEqual(mock_profile_obj.important_dates[0]["date"], "*-10")
        self.assertIn("工资", mock_profile_obj.important_dates[0]["name"])
        
        logger.info("Pattern consolidated to profile successfully")
        logger.info("Scenario 2 Passed")

    def test_scenario_3_monthly_report(self):
        logger.info("=== Testing Scenario 3: Monthly Report Pattern ===")
        
        # 1. Form Memory (March 20)
        date_1 = datetime(2025, 3, 20, 19, 0, 0) # Evening
        ts_1 = date_1.timestamp()
        
        meta_1 = {
            "timestamp": ts_1,
            "creation_time": ts_1,
            "date": date_1.strftime("%Y-%m-%d %H:%M:%S"),
            "day_of_month": 20,
            "month": 3,
            "weekday": 3 # Thursday
        }
        
        content = "好烦，要做汇报了"
        logger.info(f"Saving memory for Mar 20: {content}")
        self.memory_manager.save_user_memory(content, metadata=meta_1)
        
        # 2. Reinforce Memory (April 20)
        date_2 = datetime(2025, 4, 20, 19, 0, 0)
        ts_2 = date_2.timestamp()
        
        meta_2 = {
            "timestamp": ts_2,
            "creation_time": ts_2,
            "date": date_2.strftime("%Y-%m-%d %H:%M:%S"),
            "day_of_month": 20,
            "month": 4,
            "weekday": 6 # Sunday
        }
        
        logger.info(f"Saving memory for Apr 20: {content}")
        self.memory_manager.save_user_memory(content, metadata=meta_2)
        
        # 3. Pattern Extraction
        logger.info("Scanning for patterns...")
        patterns = self.pattern_scanner.scan_all_patterns()
        
        found = False
        found_pattern = None
        for p in patterns:
            logger.info(f"Found pattern: {p}")
            if p["type"] == "monthly" and p["day_of_month"] == 20:
                found = True
                found_pattern = p
                
        self.assertTrue(found, "Should have found monthly report pattern on 20th")
        # Verify content clustering picked up the text
        # Since it falls into 'else' block of clustering, it uses content[:20]
        self.assertIn("好烦，要做汇报了", found_pattern["sample_content"])
        
        logger.info("Scenario 3 Passed")


    def test_scenario_4_single_shot_pattern(self):
        logger.info("=== Testing Scenario 4: Single Shot Pattern (Semantic) ===")
        
        # 1. Form Memory (May 20) only once
        date_1 = datetime(2025, 5, 20, 10, 0, 0)
        ts_1 = date_1.timestamp()
        
        meta_1 = {
            "timestamp": ts_1,
            "creation_time": ts_1,
            "date": date_1.strftime("%Y-%m-%d %H:%M:%S"),
            "day_of_month": 20,
            "month": 5,
            "weekday": 1 # Tuesday
        }
        
        # User explicitly says "every month"
        content = "好烦，老板说以后每月20号要和他汇报"
        logger.info(f"Saving memory: {content}")
        self.memory_manager.save_user_memory(content, metadata=meta_1)
        
        # 2. Pattern Extraction
        logger.info("Scanning for patterns...")
        patterns = self.pattern_scanner.scan_all_patterns()
        
        found = False
        for p in patterns:
            # We are looking for the 'report' pattern derived from this single event
            if p["type"] == "monthly" and p["day_of_month"] == 20:
                # Check if this pattern corresponds to the new content
                if "汇报" in str(p.get("sample_content", "")):
                    found = True
                    break
        
        # Current expectation: Should FAIL (return False) because count < 2
        # But for the purpose of the test script passing, we might assert False.
        # However, the user asked "Can it identify?", so we want to see the result.
        # I will assert False to confirm it CANNOT yet.
        
        if not found:
            logger.info("Pattern NOT found as expected (requires min 2 occurrences)")
        else:
            logger.info("Unexpectedly FOUND pattern!")
            
        self.assertFalse(found, "System currently should NOT be able to identify single-shot patterns without semantic improvements")
        logger.info("Scenario 4 Passed (Confirmed Limitation)")

