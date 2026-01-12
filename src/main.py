"""
智能台灯系统主程序 - OODA架构
运行方式：python main.py
按 Ctrl+C 退出程序
"""
import time
import signal
import sys
from dotenv import load_dotenv

load_dotenv()  # 自动加载 .env 文件中的变量

from .graph import build_graph
from .event_manager import EventManager
from .state_manager import StateManager
from .state import LampState
from .performance_tracker import get_tracker

# 全局变量用于优雅退出
running = True

def signal_handler(signum, frame):
    """信号处理器 - 优雅退出"""
    global running
    print("\n🛑 收到退出信号，正在关闭...")
    running = False

def main():
    """主函数：运行 OODA 事件循环"""
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    print("=" * 60)
    print("🤖 智能台灯系统 (Neko-Light V1) 启动")
    print("🚀 进入 OODA 事件循环模式")
    print("=" * 60)

    # 初始化组件
    print("🔧 初始化组件...")
    event_manager = EventManager()
    state_manager = StateManager()
    app = build_graph()
    
    # 初始化V1新增管理器
    from .intimacy_manager import IntimacyManager
    from .conflict_handler import ConflictHandler
    from .focus_mode_manager import FocusModeManager
    from .reflex_router import ReflexRouter
    
    intimacy_manager = IntimacyManager()
    conflict_handler = ConflictHandler()
    focus_mode_manager = FocusModeManager()
    reflex_router = ReflexRouter()
    
    # 从状态中恢复管理器状态
    current_state = state_manager.initialize_state()
    if "intimacy_level" in current_state:
        intimacy_manager.load_state({
            "intimacy_level": current_state.get("intimacy_level", 30.0),
            "intimacy_rank": current_state.get("intimacy_rank", "stranger"),
            "daily_touch_count": 0,  # 每日计数器不持久化
            "daily_praise_count": 0,
            "last_reset_date": "",
            "intimacy_history": current_state.get("intimacy_history", [])
        })
    
    # 检查每日陪伴奖励
    daily_duration = current_state.get("daily_presence_duration", 0.0)
    bonus = intimacy_manager.calculate_daily_bonus(daily_duration)
    if bonus > 0:
        print(f"   🎁 获得每日陪伴奖励: +{bonus}")
        bonus_result = intimacy_manager.update_intimacy(bonus, "daily_presence_bonus")
        current_state["intimacy_level"] = bonus_result["intimacy_level"]
        current_state["intimacy_rank"] = bonus_result["intimacy_rank"]
        # 奖励发放后，如果需要可以在这里重置时长，或者由intimacy_manager的每日重置逻辑处理
        # PRD要求 >1小时奖励，通常是每天一次。
    
    print("✅ 所有管理器初始化完成")

    # 初始化状态
    current_state = state_manager.initialize_state()

    # 显示初始状态摘要
    summary = state_manager.get_state_summary(current_state)
    print("📊 初始状态:")
    print(f"   - 用户: {summary['user_name']}")
    print(f"   - 情绪: {summary['current_mood']} | 能量: {summary['energy_level']}")
    print(f"   - 无聊度: {summary['boredom']} | 活动状态: {summary['activity_level']}")
    print(".1f")
    print("\n🎤 请输入您的指令，然后按 Enter 键确认：")
    print("   💡 示例：'你好'、'今天天气怎么样'、'我饿了'")
    print("   ⏳ 请完整输入后按 Enter，或等待系统主动发起对话")

    # OODA 事件循环
    loop_count = 0
    last_loop_time = time.time()
    while running:
        loop_count += 1
        current_time = time.time()
        loop_duration = current_time - last_loop_time
        last_loop_time = current_time

        try:
            # === OODA 循环开始 ===
            
            # 0. 累计在场时长（简单假设只要循环在跑，用户就在场，或者根据activity_level判断）
            # V1简化：只要程序运行且activity_level不是away，就累加时长
            if current_state.get("context_signals", {}).get("activity_level") != "away":
                current_state["daily_presence_duration"] = current_state.get("daily_presence_duration", 0.0) + loop_duration

            # 1. 观察 (Observe) - 获取事件
            event = event_manager.get_event()

            # 1.5 反射路由 (System 1) - 极速响应
            if event:
                reflex = reflex_router.route(event, current_state)
                if reflex.triggered:
                    print(f"   ⚡ 反射触发: {reflex.command_type or 'unnamed'}")
                    
                    # 执行反射动作
                    if reflex.voice_content:
                        print(f"   🗣️  反射语音: {reflex.voice_content}")
                    if reflex.action_plan:
                        print(f"   🎭 反射动作: {reflex.action_plan}")
                        # 这里可以调用真正的硬件控制接口
                    
                    # 更新状态增量
                    if reflex.new_state_delta:
                        delta = reflex.new_state_delta
                        # 处理亲密度
                        if "intimacy_delta" in delta:
                            intimacy_result = intimacy_manager.update_intimacy(
                                delta["intimacy_delta"],
                                delta.get("intimacy_reason", "reflex_trigger")
                            )
                            current_state["intimacy_level"] = intimacy_result["intimacy_level"]
                            current_state["intimacy_rank"] = intimacy_result["intimacy_rank"]
                        
                        # 处理冲突状态
                        if "conflict_state" in delta:
                            current_state["conflict_state"] = delta["conflict_state"]
                        
                        # 处理专注模式
                        if "focus_mode" in delta:
                            current_state["focus_mode"] = delta["focus_mode"]
                            if "focus_mode_reason" in delta:
                                current_state["focus_mode_reason"] = delta["focus_mode_reason"]
                    
                    # 决定是否阻断 System 2 (推理层)
                    if reflex.block_llm:
                        print("   🛑 反射阻断推理层")
                        # 如果是用户输入被阻断，仍需重置交互时间
                        if event.type == "user_input":
                            current_state = state_manager.reset_interaction_time(current_state)
                        continue

            # 2. 调整 (Orient) - 更新内部状态
            current_state = state_manager.update_internal_state(current_state)
            
            # 2.5. 专注模式检查 - 处理用户输入中的专注模式切换
            if event and event.type == "user_input":
                user_input_text = event.data.get("text", "")
                if user_input_text:
                    # 检查是否应该进入/退出专注模式
                    if focus_mode_manager.should_enter_focus_mode(user_input_text, current_state):
                        focus_updates = focus_mode_manager.enter_focus_mode(
                            current_state, 
                            reason="user_expression",
                            auto=False
                        )
                        current_state.update(focus_updates)
                        print(f"   🔇 用户开启专注模式")
                    
                    elif focus_mode_manager.should_exit_focus_mode(user_input_text, current_state):
                        focus_updates = focus_mode_manager.exit_focus_mode(current_state)
                        current_state.update(focus_updates)
                        print(f"   🔊 用户关闭专注模式")

            # 3. 决策 (Decide) - 判断是否需要触发工作流
            should_trigger = False
            trigger_reason = "none"

            if event:
                # 有外部事件，立即触发
                should_trigger = True
                trigger_reason = f"event_{event.type}"

                # 更新事件相关状态
                if event.type == "user_input":
                    current_state["user_input"] = event.data.get("text")
                    current_state["event_type"] = "user_input"
                    # 重置交互时间
                    current_state = state_manager.reset_interaction_time(current_state)
                elif event.type == "sensor":
                    current_state["sensor_data"] = event.data
                    current_state["event_type"] = "sensor"
                elif event.type == "timer":
                    current_state["event_type"] = "timer"
                elif event.type == "email_notification":
                    # 邮箱通知事件：将数据放到 sensor_data 中（复用字段）
                    current_state["sensor_data"] = event.data
                    current_state["event_type"] = "email_notification"
                else:
                    current_state["event_type"] = event.type
                    # 对于其他事件类型，如果有数据也放到 sensor_data
                    if event.data:
                        current_state["sensor_data"] = event.data

                print(f"🎪 事件触发: {event.type} - {event.data}")

            else:
                # 检查内部驱动是否需要触发
                internal = current_state.get("internal_drives", {})
                boredom = internal.get("boredom", 0)
                user_prefs = current_state.get("user_preferences", {})

                # 条件1：无聊度超过阈值且主动行为启用
                if (boredom > 60 and  # 从80降低到60，提高触发频率
                    user_prefs.get("enabled", True) and
                    user_prefs.get("level", 0) > 0):
                    should_trigger = True
                    trigger_reason = f"boredom_{boredom}"
                    current_state["event_type"] = "internal_drive"
                    print(f"😴 内部驱动触发: 无聊度 {boredom} > 60")

                # 条件2：定时状态检查（每2.5分钟）
                elif loop_count % 150 == 0:  # 每150次循环（约2.5分钟）- 提高频率
                    should_trigger = True
                    trigger_reason = "periodic_check"
                    current_state["event_type"] = "timer"
                    print("⏰ 定时状态检查")

            # 4. 行动 (Act) - 执行工作流
            if should_trigger:
                print(f"⚡ 触发工作流 (原因: {trigger_reason})")

                # 重置性能追踪器，开始新一轮追踪
                perf_tracker = get_tracker()
                perf_tracker.start_session()

                # 准备输入状态
                workflow_input = {**current_state}

                try:
                    # 执行工作流
                    print("   🔄 执行中...")
                    result = app.invoke(workflow_input)

                    # 提取本次执行的输出（只在本次使用）
                    voice = result.get("voice_content")
                    action = result.get("action_plan", {})
                    execution_status = result.get("execution_status")

                    # 只在工作流真正执行时显示输出
                    if execution_status == "completed":
                        if voice:
                            print(f"   🗣️  语音: {voice}")
                        if action:
                            print(f"   🎭 动作: {action}")

                    # 选择性更新状态：只保留持久化字段，不保留临时输出
                    persistent_fields = [
                        "history", "user_profile", "internal_drives", 
                        "user_preferences", "context_signals",
                        # V1新增字段
                        "intimacy_level", "intimacy_rank", "intimacy_history",
                        "daily_presence_duration",
                        "focus_mode", "focus_mode_start_time", "focus_mode_duration",
                        "focus_mode_auto", "focus_mode_reason",
                        "conflict_state"
                    ]
                    
                    for field in persistent_fields:
                        if field in result:
                            current_state[field] = result[field]
                    
                    # 处理亲密度变化
                    if "intimacy_delta" in result and result["intimacy_delta"] != 0:
                        intimacy_result = intimacy_manager.update_intimacy(
                            result["intimacy_delta"],
                            result.get("intimacy_reason", "unknown")
                        )
                        current_state["intimacy_level"] = intimacy_result["intimacy_level"]
                        current_state["intimacy_rank"] = intimacy_result["intimacy_rank"]
                        if intimacy_result.get("rank_changed"):
                            print(f"   🎉 亲密度等级变化: {intimacy_result['intimacy_rank']}")
                    
                    # 处理冲突状态变化
                    if "conflict_state" in result:
                        current_state["conflict_state"] = result["conflict_state"]
                        if result["conflict_state"] is None:
                            print("   ✨ 冲突状态已清除")

                    # 确保历史记录被正确保存
                    if "history" in current_state:
                        print(f"   📝 当前对话历史: {len(current_state['history'])} 条记录")

                    # 清空临时字段，避免污染
                    current_state["voice_content"] = None
                    current_state["action_plan"] = {}
                    current_state["execution_status"] = None

                    # 如果有用户交互，重置相关状态
                    if event and event.type == "user_input":
                        current_state = state_manager.reset_interaction_time(current_state)
                        # 清空用户输入，避免重复处理
                        current_state["user_input"] = ""
                        current_state["event_type"] = None
                        current_state["sensor_data"] = {}

                except Exception as e:
                    print(f"   ❌ 工作流执行失败: {e}")
                    # 继续循环，不中断程序

                print(f"   ✅ 工作流执行完成 (循环 #{loop_count})")

            # === OODA 循环结束 ===

            # 显示定期状态摘要（每10次循环）
            if loop_count % 10 == 0:
                summary = state_manager.get_state_summary(current_state)
                print(f"📊 状态摘要 (循环 #{loop_count}):")
                print(f"   - 无聊度: {summary['boredom']} | 能量: {summary['energy']}")
                print(f"   - 活动: {summary['activity_level']} | 离开时长: {summary['absence_duration_minutes']}分钟")

            # 休眠 - 防止 CPU 占用过高，并给用户输入时间
            if not event:
                # 没有事件时，频繁检查用户输入（每0.3秒）
                time.sleep(0.3)  # 从0.5秒改为0.3秒 - 更敏捷
            else:
                # 有事件处理后，快速响应
                time.sleep(0.1)  # 100ms

        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"❌ 循环中发生错误: {e}")
            time.sleep(1)  # 错误时稍微多休眠

    # 程序退出
    print("\n" + "=" * 60)
    print("👋 Neko-Light V1 已关闭")

    # 保存最终状态
    state_manager.save_state(current_state)

    summary = state_manager.get_state_summary(current_state)
    print("📊 最终状态:")
    print(f"   - 运行循环数: {loop_count}")
    print(f"   - 无聊度: {summary['boredom']}")
    print(f"   - 能量值: {summary['energy']}")
    print(".1f")
    print("=" * 60)

if __name__ == "__main__":
    main()

