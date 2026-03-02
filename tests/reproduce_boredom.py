
import time
import sys
import os

# Add root to path so we can import src as package
sys.path.append(os.getcwd())

from src.state_manager import StateManager
from src.state import LampState

def test_boredom_growth():
    print("Initializing StateManager...")
    sm = StateManager(state_file="./data/test_state.json")
    
    # Initialize state (mocking load to return None for clean start)
    # We can just manually construct a state or use initialize_state
    # But initialize_state tries to load real files. Let's make sure we don't mess up real data.
    # We used a test_state.json so it should be fine.
    
    state = sm.initialize_state()
    
    # Reset interaction time initially
    state = sm.reset_interaction_time(state)
    
    print(f"Initial Boredom: {state['internal_drives']['boredom']}")
    print(f"Initial Interaction Time: {state['internal_drives']['last_interaction_time']}")
    
    # Simulate loop
    print("\nSimulating 2 minutes of inactivity...")
    
    start_time = time.time()
    for i in range(12): # 12 steps of 10 seconds = 120 seconds
        # Fast forward time by mocking updates? 
        # StateManager uses time.time(). We need to patch time or just sleep?
        # Sleeping is too slow.
        # Let's verify the formula by manually changing last_interaction_time
        
        simulated_absence = (i + 1) * 10
        
        # We can't easily mock time.time() inside the class without patching.
        # So we simply modify 'last_interaction_time' backwards.
        
        state['internal_drives']['last_interaction_time'] = time.time() - simulated_absence
        
        state = sm.update_internal_state(state)
        boredom = state['internal_drives']['boredom']
        print(f"Time elapsed: {simulated_absence}s -> Boredom: {boredom}")
        
    print("\nSimulating Interaction...")
    state = sm.reset_interaction_time(state)
    print(f"After Reset -> Boredom: {state['internal_drives']['boredom']}")
    
    # Check next update
    state = sm.update_internal_state(state)
    print(f"After Next Update -> Boredom: {state['internal_drives']['boredom']}")

if __name__ == "__main__":
    test_boredom_growth()
