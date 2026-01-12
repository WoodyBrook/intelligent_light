"""
交互式测试脚本
运行方式：python test_interactive.py
"""
import json
import sys

# 确保输出立即刷新
sys.stdout.reconfigure(line_buffering=True) if hasattr(sys.stdout, 'reconfigure') else None

from graph import build_graph
from state import LampState

def format_action_plan(action_plan):
    """美化动作计划的输出"""
    if not action_plan:
        return "无动作"
    
    result = []
    if "motor" in action_plan:
        motor = action_plan["motor"]
        result.append(f"⚙️  电机: {json.dumps(motor, ensure_ascii=False, indent=2)}")
    if "light" in action_plan:
        light = action_plan["light"]
        result.append(f"💡 灯光: {json.dumps(light, ensure_ascii=False, indent=2)}")
    if "sound" in action_plan:
        result.append(f"🔊 声音: {action_plan['sound']}")
    
    return "\n".join(result) if result else "无动作"

def test_text_input(app, user_input):
    """测试文本输入（触发推理路径）"""
    print("\n" + "=" * 60)
    print(f"📝 测试输入: {user_input}")
    print("=" * 60)
    print("⏳ 正在处理，请稍候...")
    import sys
    sys.stdout.flush()  # 确保输出立即显示
    
    initial_state: LampState = {
        "user_input": user_input,
        "sensor_data": {},
        "energy_level": 0,
        "current_mood": "",
        "intent_route": "",
        "action_plan": {},
        "voice_content": None,
        "history": []
    }
    
    result = app.invoke(initial_state)
    
    print("\n" + "-" * 60)
    print("📊 最终结果:")
    print("-" * 60)
    
    voice = result.get('voice_content')
    action = result.get('action_plan')
    
    if voice:
        print(f"\n💬 台灯说:\n   {voice}")
    else:
        print("\n💬 台灯说:\n   *台灯用温暖的光芒和动作表达情感*")
    
    print(f"\n🎬 动作计划:")
    print(format_action_plan(action))
    print("=" * 60)

def test_sensor_trigger(app):
    """测试传感器触发（触发反射路径）"""
    print("\n" + "=" * 60)
    print("👆 测试传感器触发（触摸）")
    print("=" * 60)
    print("⏳ 正在处理...")
    import sys
    sys.stdout.flush()  # 确保输出立即显示
    
    initial_state: LampState = {
        "user_input": None,
        "sensor_data": {"touch": True},
        "energy_level": 0,
        "current_mood": "",
        "intent_route": "",
        "action_plan": {},
        "voice_content": None,
        "history": []
    }
    
    result = app.invoke(initial_state)
    
    print("\n" + "-" * 60)
    print("📊 最终结果:")
    print("-" * 60)
    
    voice = result.get('voice_content')
    action = result.get('action_plan')
    
    if voice:
        print(f"\n💬 台灯说:\n   {voice}")
    else:
        print("\n💬 台灯说:\n   *台灯用温暖的光芒和动作表达情感*")
    
    print(f"\n🎬 动作计划:")
    print(format_action_plan(action))
    print("=" * 60)

def main():
    """交互式主函数"""
    print("=" * 60)
    print(" 智能台灯 - 交互式测试")
    print("=" * 60)
    print("\n使用说明:")
    print("  - 直接输入文本进行测试（触发推理路径）")
    print("  - 输入 'touch' 或 'sensor' 测试传感器触发（反射路径）")
    print("  - 输入 'quit' 或 'exit' 退出")
    print("  - 输入 'help' 查看帮助")
    print("=" * 60)
    
    # 添加初始化提示
    print("\n[正在初始化工作流...]")
    import sys
    sys.stdout.flush()
    
    try:
        app = build_graph()
        print("[工作流初始化完成]")
        sys.stdout.flush()
    except Exception as e:
        print(f"\n❌ 初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return
    
    while True:
        try:
            # 确保输出缓冲区刷新
            sys.stdout.flush()
            sys.stderr.flush()
            
            # 尝试使用更明确的提示
            print()  # 先换行
            sys.stdout.flush()
            user_input = input(">>> 请输入测试内容: ").strip()
            
            if not user_input:
                continue
            
            # 处理特殊命令
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("\n👋 再见！")
                break
            elif user_input.lower() in ['help', 'h']:
                print("\n📖 帮助信息:")
                print("  - 输入任意文本：测试 LLM 推理功能")
                print("  - 'touch' 或 'sensor'：测试反射路径（快速响应）")
                print("  - 'quit' 或 'exit'：退出程序")
                continue
            elif user_input.lower() in ['touch', 'sensor']:
                test_sensor_trigger(app)
            else:
                # 普通文本输入测试
                test_text_input(app, user_input)
                
        except KeyboardInterrupt:
            print("\n\n👋 再见！")
            break
        except Exception as e:
            print(f"\n❌ 错误: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    main()

