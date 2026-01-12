import sys
import os
import time
from typing import Dict, Any, List

# 将根目录添加到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.graph import build_graph
from src.state_manager import StateManager
from src.event_manager import EventManager, Event
from src.state import LampState
from src.reflex_router import ReflexRouter

class DemoRunner:
    def __init__(self):
        self.state_manager = StateManager()
        self.event_manager = EventManager()
        from src.intimacy_manager import IntimacyManager
        self.intimacy_manager = IntimacyManager()
        self.reflex_router = ReflexRouter()
        self.app = build_graph()
        self.current_state = self.state_manager.initialize_state()
        
        # 同步 intimacy_manager 状态
        self.intimacy_manager.load_state({
            "intimacy_level": self.current_state.get("intimacy_level", 30.0),
            "intimacy_rank": self.current_state.get("intimacy_rank", "stranger"),
            "intimacy_history": self.current_state.get("intimacy_history", [])
        })
        
        self.node_trace = []
        
    def run_step(self, user_input: str = None, sensor_data: Dict = None) -> Dict[str, Any]:
        """执行一步工作流"""
        print(f"DEBUG: DemoRunner.run_step called with sensor_data={sensor_data}")

        # 1. 构造事件并进行反射检查 (System 1)
        event = None
        if user_input:
            event = Event(type="user_input", data={"text": user_input}, timestamp=time.time())
        elif sensor_data:
            # 兼容 UI 传入的简易格式
            if "shake" in sensor_data:
                event = Event(type="sensor", data={"sensor_type": "imu", "intensity": 10.0 if sensor_data["shake"] else 0}, timestamp=time.time())
            elif "touch" in sensor_data:
                event = Event(type="sensor", data={"sensor_type": "touch"}, timestamp=time.time())
            else:
                event = Event(type="sensor", data=sensor_data, timestamp=time.time())
        
        # 重置 trace
        self.node_trace = []
        
        if event:
            # 特殊处理：如果是语音输入，先模拟一个 VAD 结束事件触发 Latency Masking
            if event.type == "user_input":
                vad_event = Event(type="vad_voice_end", data={}, timestamp=time.time())
                vad_reflex = self.reflex_router.route(vad_event, self.current_state)
                if vad_reflex.triggered:
                    self.node_trace.append("Reflex (Latency Masking)")
                    if vad_reflex.action_plan:
                        self._update_hardware_from_action(vad_reflex.action_plan)

            reflex = self.reflex_router.route(event, self.current_state)
            if reflex.triggered:
                self.node_trace.append(f"Reflex ({reflex.command_type or 'unnamed'})")
                
                # 应用反射动作
                if reflex.voice_content:
                    self.current_state["voice_content"] = reflex.voice_content
                if reflex.action_plan:
                    self.current_state["action_plan"] = reflex.action_plan
                    # 更新硬件模拟状态
                    self._update_hardware_from_action(reflex.action_plan)
                
                # 更新状态增量
                if reflex.new_state_delta:
                    delta = reflex.new_state_delta
                    if "intimacy_delta" in delta:
                        intimacy_result = self.intimacy_manager.update_intimacy(
                            delta["intimacy_delta"], 
                            delta.get("intimacy_reason", "reflex")
                        )
                        self.current_state["intimacy_level"] = intimacy_result["intimacy_level"]
                        self.current_state["intimacy_rank"] = intimacy_result["intimacy_rank"]
                        self.current_state["_debug_intimacy_updated"] = f"Reflex Delta: {delta['intimacy_delta']}"
                        # 【修复】保存亲密度变化到文件
                        self.state_manager.save_state(self.current_state)
                    
                    for key, value in delta.items():
                        if key not in ["intimacy_delta", "intimacy_reason"]:
                            self.current_state[key] = value

                if reflex.block_llm:
                    return self.current_state

        # 2. 如果没被阻断，执行正常推理工作流 (System 2)
        workflow_input = {**self.current_state}
        if user_input:
            workflow_input["event_type"] = "user_input"
            workflow_input["user_input"] = user_input
        elif sensor_data:
            workflow_input["event_type"] = "sensor"
            workflow_input["sensor_data"] = sensor_data
        else:
            workflow_input["event_type"] = "timer"

        try:
            # 执行工作流
            config = {"configurable": {"thread_id": "demo"}}
            for output in self.app.stream(workflow_input, config=config, stream_mode="updates"):
                for node_name, node_output in output.items():
                    self.node_trace.append(node_name)
                    
                    # 检查是否有亲密度变化
                    if "intimacy_delta" in node_output and node_output["intimacy_delta"] != 0:
                        delta = node_output["intimacy_delta"]
                        reason = node_output.get("intimacy_reason", "unknown")
                        
                        intimacy_result = self.intimacy_manager.update_intimacy(delta, reason)
                        self.current_state["intimacy_level"] = intimacy_result["intimacy_level"]
                        self.current_state["intimacy_rank"] = intimacy_result["intimacy_rank"]
                        self.state_manager.save_state(self.current_state)
                        self.current_state["_debug_intimacy_updated"] = f"Delta: {delta}, Reason: {reason}"

                    # 更新当前状态
                    for key, value in node_output.items():
                        if key in self.current_state or key in ["intimacy_delta", "intimacy_reason", "voice_content", "action_plan", "monologue"]:
                            self.current_state[key] = value
            
            return self.current_state
            
        except Exception as e:
            print(f"Error running workflow: {e}")
            return self.current_state

    def _update_hardware_from_action(self, action_plan: Dict):
        """辅助方法：从动作计划更新硬件状态"""
        if not action_plan: return
        
        hw = self.current_state.get("current_hardware_state", {
            "light": {"status": "off", "brightness": 0},
            "motor": {"status": "off", "vibration": "none"}
        })
        
        if "light" in action_plan:
            l = action_plan["light"]
            if l.get("brightness", -1) == 0:
                hw["light"]["status"] = "off"
                hw["light"]["brightness"] = 0
            else:
                hw["light"]["status"] = "on"
                if "brightness" in l: hw["light"]["brightness"] = l["brightness"]
                if "color" in l: hw["light"]["color"] = l["color"]
                
        if "motor" in action_plan:
            m = action_plan["motor"]
            if m.get("vibration") == "none":
                hw["motor"]["status"] = "off"
            else:
                hw["motor"]["status"] = "on"
            if "vibration" in m: hw["motor"]["vibration"] = m["vibration"]
            
        self.current_state["current_hardware_state"] = hw

    def get_intimacy_info(self):
        return {
            "level": self.current_state.get("intimacy_level", 30.0),
            "rank": self.current_state.get("intimacy_rank", "stranger")
        }

    def get_hardware_state(self):
        return self.current_state.get("current_hardware_state", {
            "light": {"status": "off", "brightness": 0},
            "motor": {"status": "off", "vibration": "none"}
        })

