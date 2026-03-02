import sys
import os
import logging

# Add root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.evaluation.test_runner import EvaluationRunner
from tests.evaluation.run_evaluation import create_real_agent

def verify_fix():
    print("🚀 Initializing Real Agent for Verification...")
    agent = create_real_agent()
    runner = EvaluationRunner(agent=agent)
    
    # Manually load context cases
    context_data = runner.load_cases("context")
    context_cases = context_data.get("cases", [])
    
    # Filter for A4-11 and A4-12
    target_ids = ["A4-11", "A4-12"]
    cases_to_run = [c for c in context_cases if c["id"] in target_ids]
    
    if not cases_to_run:
        print("[ERROR] Could not find target cases!")
        return

    print(f"✅ Found {len(cases_to_run)} cases. Running verification...")
    
    for case in cases_to_run:
        print(f"\n▶️ Running {case['id']}: {case.get('name')}")
        result = runner.run_single_case(case)
        status = "✅ PASS" if result["passed"] else "❌ FAIL"
        scores = result.get("scores", {})
        print(f"   Result: {status} (Score: {result['total_score']})")
        print(f"   Response: {result['response']}")
        print(f"   Expected Keywords: {result['expected_keywords']}")

if __name__ == "__main__":
    verify_fix()
