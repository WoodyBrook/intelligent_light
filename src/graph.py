# graph.py - OODA 架构工作流（含 Plan Node）
# type: ignore
from langgraph.graph import StateGraph, END  # noqa
from .state import LampState
from .nodes import (
    evaluator_node,
    memory_loader_node,
    perception_node,
    router_node,
    reflex_node,
    reasoning_node,
    tool_node,
    action_guard_node,
    execution_node,
    plan_node,
    plan_decision,
    reasoning_decision
)


def should_proceed_decision(state: LampState):
    """决定是否继续处理"""
    return "proceed" if state.get("should_proceed", False) else "skip"


def route_decision(state: LampState):
    """路由决策"""
    return state.get("intent_route", "reflex")


def build_graph():
    """
    构建 OODA 架构工作流图（含 Plan Node）
    
    工作流结构：
    evaluator → memory_loader → perception → router → {
        "reflex": reflex → guard → execution,
        "reasoning": plan → reasoning → guard → execution,
        "direct_output": execution
    }
    
    工具调用循环：
    reasoning → tool_node (当 need_tool)
    tool_node → plan (返回规划节点执行下一步)
    """
    workflow = StateGraph(LampState)

    # === 注册所有节点 ===
    workflow.add_node("evaluator", evaluator_node)          # 全局评估器（入口）
    workflow.add_node("memory_loader", memory_loader_node)  # 记忆加载器
    workflow.add_node("perception", perception_node)        # 感知节点
    workflow.add_node("router", router_node)               # 路由节点
    workflow.add_node("reflex", reflex_node)               # 反射节点
    workflow.add_node("plan", plan_node)                   # 规划节点（新增）
    workflow.add_node("reasoning", reasoning_node)         # 推理节点
    workflow.add_node("tool_node", tool_node)              # 工具节点
    workflow.add_node("guard", action_guard_node)          # 安全卫士
    workflow.add_node("execution", execution_node)         # 执行节点

    # === 设置连接边 ===

    # 1. 入口：评估器
    workflow.set_entry_point("evaluator")

    # 2. 评估器 → 记忆加载器（条件分支）
    workflow.add_conditional_edges(
        "evaluator",
        should_proceed_decision,
        {
            "proceed": "memory_loader",  # 继续处理 → 加载记忆
            "skip": END                  # 跳过处理 → 结束
        }
    )

    # 3. 记忆加载器 → 感知节点
    workflow.add_edge("memory_loader", "perception")

    # 4. 感知节点 → 路由节点
    workflow.add_edge("perception", "router")

    # 5. 路由节点 → 三路分支（反射/规划/直接输出）
    workflow.add_conditional_edges(
        "router",
        route_decision,
        {
            "reflex": "reflex",            # 反射路径 (System 1)
            "reasoning": "plan",           # 推理路径 → 先走规划节点
            "direct_output": "execution",  # 直接输出（主动表达）
            "ignore": END                  # 忽略 → 结束
        }
    )

    # 6. 【Plan 重构】规划节点 → 条件分支
    workflow.add_conditional_edges(
        "plan",
        plan_decision,
        {
            "direct_tool": "tool_node",    # Plan 已生成 tool_calls，直接执行工具
            "no_tool": "reasoning",        # 不需要工具 或 计划已完成：进入推理
        }
    )

    # 7. 推理节点 → 条件分支（激活工具调用循环）
    workflow.add_conditional_edges(
        "reasoning",
        reasoning_decision,
        {
            "tool_call": "tool_node",      # 需要调用工具
            "complete": "guard",           # 推理完成，进入守卫
        }
    )

    # 8. 工具节点 → 规划节点（循环：返回规划节点执行下一步）
    workflow.add_edge("tool_node", "plan")

    # 9. 其他连接
    workflow.add_edge("reflex", "guard")
    workflow.add_edge("guard", "execution")
    workflow.add_edge("execution", END)

    print("🔄 OODA 工作流图构建完成（含 Plan Node）")
    return workflow.compile()
