# test_output_quality_improvements.py
# 测试输出质量改进：幻觉防护、工具检测、指代消解、重要日期整合

import sys
import os
import re

# 直接读取文件内容进行测试，避免导入需要完整环境的模块
def read_file_content(filepath):
    """读取文件内容"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        print(f"无法读取文件 {filepath}: {e}")
        return None


def test_important_date_keywords():
    """测试重要日期关键词检测（通过检查代码）"""
    print("=" * 60)
    print("测试 1: 重要日期关键词检测")
    print("=" * 60)
    
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    nodes_file = os.path.join(base_dir, "src", "nodes.py")
    content = read_file_content(nodes_file)
    
    if not content:
        print("❌ FAIL: 无法读取 nodes.py")
        return False
    
    # 检查是否包含重要日期关键词
    important_date_keywords = ["生日", "纪念日", "周年", "忌日", "节日"]
    found_keywords = []
    
    for keyword in important_date_keywords:
        if keyword in content and "important_date_keywords" in content:
            found_keywords.append(keyword)
    
    if len(found_keywords) >= 3:  # 至少找到3个关键词
        print(f"✅ PASS: 找到重要日期关键词: {found_keywords}")
        print(f"   代码中包含: important_date_keywords = [...]")
        return True
    else:
        print(f"❌ FAIL: 未找到足够的重要日期关键词 (找到: {found_keywords})")
        return False


def test_web_search_keywords():
    """测试Web搜索关键词扩展（通过检查代码）"""
    print("\n" + "=" * 60)
    print("测试 2: Web搜索关键词扩展")
    print("=" * 60)
    
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    nodes_file = os.path.join(base_dir, "src", "nodes.py")
    content = read_file_content(nodes_file)
    
    if not content:
        print("❌ FAIL: 无法读取 nodes.py")
        return False
    
    # 检查是否包含新的关键词
    new_keywords = ["帮我查", "了解一下", "是谁", "什么是", "介绍一下", "告诉我关于", "查查"]
    found_keywords = []
    
    for keyword in new_keywords:
        if keyword in content:
            found_keywords.append(keyword)
    
    if len(found_keywords) >= 4:  # 至少找到4个新关键词
        print(f"✅ PASS: 找到新的Web搜索关键词: {found_keywords}")
        return True
    else:
        print(f"❌ FAIL: 未找到足够的新关键词 (找到: {found_keywords})")
        return False


def test_tool_descriptions():
    """测试工具描述更新（通过检查代码）"""
    print("\n" + "=" * 60)
    print("测试 3: 工具描述更新")
    print("=" * 60)
    
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    tools_file = os.path.join(base_dir, "src", "tools.py")
    content = read_file_content(tools_file)
    
    if not content:
        print("❌ FAIL: 无法读取 tools.py")
        return False
    
    # 查找 create_schedule_tool 的描述
    pattern = r'"create_schedule_tool":\s*"([^"]+)"'
    match = re.search(pattern, content)
    
    if match:
        desc = match.group(1)
        checks = [
            ("yearly" in desc, "包含 yearly 类型"),
            ("重要日期" in desc or "生日" in desc or "纪念日" in desc, "包含重要日期说明"),
        ]
        
        all_passed = True
        for check, msg in checks:
            if check:
                print(f"✅ PASS: {msg}")
            else:
                print(f"❌ FAIL: {msg}")
                all_passed = False
        
        print(f"\n工具描述: {desc[:150]}...")
        return all_passed
    else:
        print("❌ FAIL: 未找到 create_schedule_tool 的描述")
        return False


def test_anti_hallucination_prompt():
    """测试反幻觉指令是否添加到prompt中（通过检查代码）"""
    print("\n" + "=" * 60)
    print("测试 4: 反幻觉指令检查")
    print("=" * 60)
    
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    prompts_file = os.path.join(base_dir, "config", "prompts.py")
    content = read_file_content(prompts_file)
    
    if not content:
        print("❌ FAIL: 无法读取 prompts.py")
        return False
    
    # 检查是否包含反幻觉相关指令
    checks = [
        ("反幻觉" in content, "包含反幻觉验证规则"),
        ("没有相关记录" in content, "包含'没有相关记录'指令"),
        ("禁止推测" in content or "不知道" in content, "包含禁止推测的指令"),
    ]
    
    all_passed = True
    for check, msg in checks:
        if check:
            print(f"✅ PASS: {msg}")
        else:
            print(f"❌ FAIL: {msg}")
            all_passed = False
    
    # 查找 memory_usage_rules 部分
    if "<memory_usage_rules>" in content:
        rules_section = content.split("<memory_usage_rules>")[1].split("</memory_usage_rules>")[0]
        if "反幻觉" in rules_section or "没有相关记录" in rules_section:
            print("✅ PASS: 反幻觉规则在 memory_usage_rules 中")
        else:
            print("❌ FAIL: 反幻觉规则不在 memory_usage_rules 中")
            all_passed = False
    
    return all_passed


def test_few_shot_examples():
    """测试工具检测prompt中的few-shot示例"""
    print("\n" + "=" * 60)
    print("测试 5: Few-shot示例检查")
    print("=" * 60)
    
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    nodes_file = os.path.join(base_dir, "src", "nodes.py")
    content = read_file_content(nodes_file)
    
    if not content:
        print("❌ FAIL: 无法读取 nodes.py")
        return False
    
    checks = [
        ("帮我查一下科比的资料" in content, "包含科比示例"),
        ("记住我妈妈生日是3月15号" in content, "包含生日示例"),
        ("【示例】" in content, "包含示例标记"),
    ]
    
    all_passed = True
    for check, msg in checks:
        if check:
            print(f"✅ PASS: {msg}")
        else:
            print(f"❌ FAIL: {msg}")
            all_passed = False
    
    return all_passed


def test_schedule_yearly_support():
    """测试日程系统对yearly类型的支持（通过检查代码）"""
    print("\n" + "=" * 60)
    print("测试 6: 日程系统yearly支持")
    print("=" * 60)
    
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    tools_file = os.path.join(base_dir, "src", "tools.py")
    content = read_file_content(tools_file)
    
    if not content:
        print("❌ FAIL: 无法读取 tools.py")
        return False
    
    # 检查 create_schedule_tool 函数
    checks = [
        ("yearly" in content and "create_schedule_tool" in content, "函数支持yearly参数"),
        (re.search(r'每年.*月.*号循环', content), "包含yearly循环的显示逻辑"),
    ]
    
    all_passed = True
    for check, msg in checks:
        if check:
            print(f"✅ PASS: {msg}")
        else:
            print(f"❌ FAIL: {msg}")
            all_passed = False
    
    # 检查schedule_manager是否支持yearly
    schedule_file = os.path.join(base_dir, "src", "schedule_manager.py")
    schedule_content = read_file_content(schedule_file)
    
    if schedule_content and "recurrence_type == \"yearly\"" in schedule_content:
        print("✅ PASS: ScheduleManager 支持 yearly 循环")
    else:
        print("⚠️  WARN: 无法确认 ScheduleManager 的 yearly 支持（可能需要运行时测试）")
    
    return all_passed


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("输出质量改进测试套件")
    print("=" * 60)
    
    tests = [
        ("重要日期关键词检测", test_important_date_keywords),
        ("Web搜索关键词扩展", test_web_search_keywords),
        ("工具描述更新", test_tool_descriptions),
        ("反幻觉指令检查", test_anti_hallucination_prompt),
        ("Few-shot示例检查", test_few_shot_examples),
        ("日程系统yearly支持", test_schedule_yearly_support),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ 测试 '{name}' 执行失败: {e}")
            results.append((name, False))
    
    # 总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")
    
    print(f"\n总计: {passed}/{total} 通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！")
        return 0
    else:
        print(f"\n⚠️  有 {total - passed} 个测试失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())
