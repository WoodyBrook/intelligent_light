import pytest
from config.prompts import get_system_prompt

def test_xml_structure_basic():
    """测试 XML 结构化基本功能"""
    prompt = get_system_prompt(
        intimacy_level=50,
        intimacy_rank="acquaintance",
        conflict_state=None,
        focus_mode=False,
        xml_context=None
    )
    
    # 检查是否包含 XML 标签
    assert "<system_instructions>" in prompt
    assert "</system_instructions>" in prompt
    assert "<context>" in prompt
    assert "</context>" in prompt
    assert "<intimacy>" in prompt
    assert "</intimacy>" in prompt
    assert "<behavior_rules>" in prompt
    assert "</behavior_rules>" in prompt

def test_xml_structure_with_conflict():
    """测试包含冲突状态的 XML 结构"""
    import time
    conflict_state = {
        "offense_level": "L1",
        "cooldown_until": time.time() + 60  # 未来60秒（确保是未来时间）
    }
    
    prompt = get_system_prompt(
        intimacy_level=30,
        intimacy_rank="stranger",
        conflict_state=conflict_state,
        focus_mode=False,
        xml_context=None
    )
    
    assert "<conflict" in prompt
    assert "L1" in prompt or "冷却期" in prompt  # 检查是否包含冲突等级或相关文本
    assert "<rules>" in prompt or "<warning>" in prompt

def test_xml_structure_with_focus_mode():
    """测试包含专注模式的 XML 结构"""
    prompt = get_system_prompt(
        intimacy_level=75,
        intimacy_rank="friend",
        conflict_state=None,
        focus_mode=True,
        xml_context=None
    )
    
    assert "<focus_mode" in prompt
    assert 'enabled="true"' in prompt
    assert "<rules>" in prompt

def test_xml_structure_with_context():
    """测试包含 XML 上下文的完整结构"""
    xml_context = """<context>
<user_profile>用户在北京</user_profile>
<recent_memories>
- 用户喜欢咖啡
</recent_memories>
</context>"""
    
    prompt = get_system_prompt(
        intimacy_level=60,
        intimacy_rank="friend",
        conflict_state=None,
        focus_mode=False,
        xml_context=xml_context
    )
    
    assert "<user_profile>" in prompt
    assert "用户在北京" in prompt

def test_xml_structure_identity_tags():
    """测试身份标签是否正确"""
    prompt = get_system_prompt(
        intimacy_level=50,
        intimacy_rank="acquaintance",
        conflict_state=None,
        focus_mode=False,
        xml_context=None
    )
    
    assert "<identity>" in prompt
    assert "<name>Animus</name>" in prompt
    assert "<personality>温柔坚定猫</personality>" in prompt
    assert "<capabilities>" in prompt
    assert "<boundaries" in prompt

def test_xml_structure_intimacy_rules():
    """测试亲密度规则是否正确"""
    prompt = get_system_prompt(
        intimacy_level=80,
        intimacy_rank="soulmate",
        conflict_state=None,
        focus_mode=False,
        xml_context=None
    )
    
    assert 'level="80"' in prompt
    assert 'rank="soulmate"' in prompt
    assert "<behavior_rules>" in prompt
    assert "灵魂伴侣" in prompt

