
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.prompts import get_system_prompt

def verify_prompt_structure():
    print("--- Verifying Prompt Structure ---")
    
    # Mock XML context
    mock_xml_context = "<conversation_history>\nUser: Hi\nSystem: Hello\n</conversation_history>"
    
    prompt = get_system_prompt(
        intimacy_level=50,
        intimacy_rank="friend",
        conflict_state=None,
        focus_mode=False,
        xml_context=mock_xml_context,
        include_tone_examples=True
    )
    
    # Check 1: XML context is present
    if mock_xml_context not in prompt:
        print("❌ FAILED: XML context missing from prompt")
        return False
        
    # Check 2: Position check
    # We want context (mock_xml_context) to appear BEFORE tone rules (TONE_RULES)
    # The string "<tone_rules" should serve as a marker for the rules section
    
    context_pos = prompt.find(mock_xml_context)
    rules_pos = prompt.find("<tone_rules")
    
    print(f"Context position: {context_pos}")
    print(f"Rules position: {rules_pos}")
    
    if context_pos == -1:
        print("❌ FAILED: Cannot find context")
        return False
        
    if rules_pos == -1:
        print("❌ FAILED: Cannot find rules")
        return False
        
    if context_pos < rules_pos:
        print("✅ PASSED: Context appears before rules")
        
        # Additional check: Context should be before <context> tag (intimacy context)
        # Actually in my plan I put it after <system_instructions> and before <context> (intimacy) 
        # Wait, let me check the executed code.
        # I put it BEFORE <context><intimacy>...
        
        intimacy_pos = prompt.find("<intimacy")
        if context_pos < intimacy_pos:
             print("✅ PASSED: Context appears before intimacy context")
        else:
             print(f"⚠️ NOTE: Context appears after intimacy context (pos: {intimacy_pos})")

        return True
    else:
        print("❌ FAILED: Context appears AFTER rules (Lost in the Middle risk)")
        return False

if __name__ == "__main__":
    verify_prompt_structure()
