#!/usr/bin/env python3
"""
Memory Reflection Job - 后台记忆整合任务
定期汇总碎片记忆，生成高级 Insight 写入 core_preferences

用法:
    python scripts/reflection_job.py [--force]

触发条件（满足以下全部条件才会运行）:
    1. 距离上次 Reflection 超过 24 小时
    2. 新增记忆数超过 10 条
    3. 或使用 --force 强制触发

建议的定时任务配置:
    # cron (Linux)
    0 3 * * * cd /path/to/Neko_light && python scripts/reflection_job.py >> /var/log/neko_reflection.log 2>&1
    
    # launchd (macOS) - 创建 ~/Library/LaunchAgents/com.neko.reflection.plist
"""

import os
import sys
import time
import argparse
from datetime import datetime

# 添加 src 到 path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from src.memory_manager import MemoryManager
from src.state import UserProfile


def should_run_reflection(profile: UserProfile, memory_manager: MemoryManager, force: bool) -> bool:
    """判断是否应该运行 Reflection"""
    if force:
        print("🔧 强制模式，跳过条件检查")
        return True
    
    now = time.time()
    hours_since_last = (now - profile.last_synthesized) / 3600
    
    # 条件 1: 超过 24 小时
    if hours_since_last < 24:
        print(f"⏰ 距上次 Reflection 仅 {hours_since_last:.1f} 小时（需要 >= 24h），跳过")
        return False
    
    # 条件 2: 新增记忆数超过阈值
    new_memory_count = memory_manager._count_memories_since(profile.last_synthesized)
    if new_memory_count < 10:
        print(f"📝 新增记忆仅 {new_memory_count} 条（需要 >= 10），跳过")
        return False
    
    print(f"✅ 满足触发条件: 距上次 {hours_since_last:.1f}h, 新增记忆 {new_memory_count} 条")
    return True


def run_reflection(memory_manager: MemoryManager) -> bool:
    """
    执行 Reflection
    
    Returns:
        bool: 是否成功生成了 Insight
    """
    profile = memory_manager.load_profile()
    
    # 1. 获取最近 N 条记忆
    print("\n📚 Step 1: 获取最近记忆...")
    recent_memories = memory_manager.get_recent_memories(limit=50)
    
    if not recent_memories:
        print("   没有记忆可供 Reflection")
        return False
    
    print(f"   获取到 {len(recent_memories)} 条记忆")
    
    # 2. 格式化记忆
    print("\n📝 Step 2: 格式化记忆...")
    memory_lines = []
    for m in recent_memories:
        date_str = m.get("date", "")[:10] if m.get("date") else "未知日期"
        category = m.get("category", "未分类")
        content = m.get("content", "")[:100]  # 截断过长内容
        memory_lines.append(f"- [{date_str}] [{category}] {content}")
    
    memory_text = "\n".join(memory_lines)
    print(f"   格式化完成，共 {len(memory_text)} 字符")
    
    # 3. 调用 LLM 生成 Insight
    print("\n🧠 Step 3: 调用 LLM 生成 Insight...")
    
    try:
        from langchain_openai import ChatOpenAI
        from langchain_core.prompts import ChatPromptTemplate
        from langchain_core.output_parsers import JsonOutputParser
        
        llm = ChatOpenAI(
            model="deepseek-v3-1-terminus",
            temperature=0.7,
            api_key=os.environ.get("VOLCENGINE_API_KEY"),
            base_url="https://ark.cn-beijing.volces.com/api/v3",
            timeout=60
        )
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """你是一个记忆分析师。根据以下用户记忆片段，总结出 3-5 条关于用户的高级画像洞察。

要求:
1. 每条洞察是一个简短的陈述句（10-20字）
2. 侧重于稳定的个性/偏好，而非一次性事件
3. 使用第三人称 "用户..."
4. 如果发现矛盾（如 "喜欢辣" 和 "不喜欢辣"），以时间更近的为准
5. 避免过于泛化的洞察（如 "用户是个好人"）

输出格式：JSON 数组，不要包含其他内容
["用户喜欢在周末散步", "用户对科技新闻感兴趣", ...]"""),
            ("human", f"用户记忆片段:\n{memory_text}")
        ])
        
        chain = prompt | llm | JsonOutputParser()
        
        insights = chain.invoke({})
        
        if not isinstance(insights, list):
            print(f"   ❌ LLM 返回格式错误: {type(insights)}")
            return False
        
        print(f"   ✅ 生成 {len(insights)} 条 Insight:")
        for i, insight in enumerate(insights, 1):
            print(f"      {i}. {insight}")
        
    except Exception as e:
        print(f"   ❌ LLM 调用失败: {e}")
        return False
    
    # 4. 更新 Profile
    print("\n💾 Step 4: 更新 Profile...")
    
    # 合并而非覆盖（去重）
    existing = set(profile.core_preferences)
    added_count = 0
    for insight in insights:
        if isinstance(insight, str) and insight not in existing:
            profile.core_preferences.append(insight)
            added_count += 1
    
    # 限制最多 10 条 core_preferences（保留最新的）
    if len(profile.core_preferences) > 10:
        removed_count = len(profile.core_preferences) - 10
        profile.core_preferences = profile.core_preferences[-10:]
        print(f"   移除了 {removed_count} 条旧 Insight（超出限制）")
    
    profile.last_synthesized = time.time()
    memory_manager.save_profile(profile)
    
    print(f"   ✅ 新增 {added_count} 条 Insight，Profile 已更新")
    print(f"   当前 core_preferences: {profile.core_preferences}")
    
    return True


def main():
    parser = argparse.ArgumentParser(description="Memory Reflection Job")
    parser.add_argument("--force", action="store_true", help="强制运行，忽略触发条件")
    parser.add_argument("--dry-run", action="store_true", help="试运行，不实际更新 Profile")
    args = parser.parse_args()
    
    print("=" * 50)
    print(f"🧠 Memory Reflection Job")
    print(f"⏰ 启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    try:
        memory_manager = MemoryManager()
        profile = memory_manager.load_profile()
        
        print(f"\n📋 当前状态:")
        print(f"   上次 Reflection: {datetime.fromtimestamp(profile.last_synthesized).strftime('%Y-%m-%d %H:%M:%S') if profile.last_synthesized else '从未'}")
        print(f"   当前 core_preferences 数量: {len(profile.core_preferences)}")
        
        if should_run_reflection(profile, memory_manager, args.force):
            if args.dry_run:
                print("\n🔧 试运行模式，不实际更新 Profile")
                recent = memory_manager.get_recent_memories(limit=10)
                print(f"   最近 10 条记忆预览:")
                for m in recent[:5]:
                    print(f"     - {m.get('content', '')[:50]}...")
            else:
                print("\n🚀 开始执行 Reflection...")
                success = run_reflection(memory_manager)
                if success:
                    print("\n✅ Reflection 完成")
                else:
                    print("\n⚠️ Reflection 未生成有效结果")
        else:
            print("\n⏭️ 跳过 Reflection")
            
    except Exception as e:
        print(f"\n❌ 执行失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    print("\n" + "=" * 50)


if __name__ == "__main__":
    main()
