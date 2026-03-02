
import sys
import os
import time
import json
import shutil

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))

from src.state_manager import StateManager
from src.state import LampState

TEST_STATE_FILE = "./data/test_lamp_state.json"

def test_persistence():
    print("🧪 Starting State Persistence Test...")
    
    # 1. Setup
    if os.path.exists(TEST_STATE_FILE):
        os.remove(TEST_STATE_FILE)
    
    sm1 = StateManager(state_file=TEST_STATE_FILE)
    
    # 2. Initialize and modify state
    print("\n--- Step 1: Initial State ---")
    state = sm1.initialize_state()
    
    # Manually set some values
    state["internal_drives"]["energy"] = 80
    state["internal_drives"]["boredom"] = 20
    state["internal_drives"]["last_interaction_time"] = time.time()
    
    print(f"Set Initial Energy: {state['internal_drives']['energy']}")
    print(f"Set Initial Boredom: {state['internal_drives']['boredom']}")
    
    # 3. Save State
    print("\n--- Step 2: Saving State ---")
    sm1.save_state(state)
    
    # 4. Simulate Time Passing (Mocking or just modifying the file timestamp/saved_at?)
    # Easier to mock by modifying the saved file's 'saved_at' to be in the past
    print("\n--- Step 3: Simulating 1 hour offline ---")
    with open(TEST_STATE_FILE, 'r') as f:
        data = json.load(f)
    
    # Rewind saved_at by 1 hour (3600 seconds)
    data["saved_at"] = time.time() - 3600 
    
    with open(TEST_STATE_FILE, 'w') as f:
        json.dump(data, f)
        
    # 5. Restore State with new Manager
    print("\n--- Step 4: Restoring State ---")
    sm2 = StateManager(state_file=TEST_STATE_FILE)
    new_state = sm2.initialize_state()
    
    new_internal = new_state["internal_drives"]
    print(f"Restored Energy: {new_internal['energy']}")
    print(f"Restored Boredom: {new_internal['boredom']}")
    
    # 6. Validation
    # Energy decay: 1 per 5 mins. 60 mins = 12 decay. 80 -> 68.
    # Boredom increase: 1 per 30 secs. 60 mins = 120 increase. 20 + 120 = 140 -> capped at 100.
    
    expected_energy = 80 - int(3600/300) # 80 - 12 = 68
    expected_boredom = min(20 + int(3600/30), 100) # 20 + 120 = 140 -> 100
    
    print(f"\nExpected Energy: ~{expected_energy}")
    print(f"Expected Boredom: {expected_boredom}")
    
    if abs(new_internal['energy'] - expected_energy) <= 1:
        print("✅ Energy persistence verification PASSED")
    else:
        print("❌ Energy persistence verification FAILED")
        
    if new_internal['boredom'] == expected_boredom:
        print("✅ Boredom persistence verification PASSED")
    else:
        print("❌ Boredom persistence verification FAILED")

    # Cleanup
    if os.path.exists(TEST_STATE_FILE):
        os.remove(TEST_STATE_FILE)

if __name__ == "__main__":
    test_persistence()
