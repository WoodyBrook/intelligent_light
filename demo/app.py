import streamlit as st
import time
import os
import sys
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

from typing import Dict, List

# 路径设置
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from demo.utils import DemoRunner
from demo.scenarios import DEMO_SCENARIOS, get_scenario_instructions

# 页面配置
st.set_page_config(
    page_title="Animus V1 Demo - 智能宠物演示",
    page_icon="🐱",
    layout="wide"
)

# 自定义 CSS
st.markdown("""
<style>
    .stChatMessage {
        border-radius: 15px;
        padding: 10px;
        margin-bottom: 10px;
    }
    .main-header {
        font-size: 2.5rem;
        color: #ff4b4b;
        text-align: center;
        margin-bottom: 1rem;
    }
    .scenario-box {
        background-color: #e8f4f8;
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid #2980b9;
        margin-bottom: 20px;
    }
    .monologue-box {
        background-color: #fff4f4;
        padding: 15px;
        border-radius: 10px;
        font-style: italic;
        color: #555;
        border: 1px dashed #ff4b4b;
    }
</style>
""", unsafe_allow_html=True)

# 初始化 DemoRunner
if 'runner' not in st.session_state or st.sidebar.button("🔄 强制重置系统"):
    st.session_state.runner = DemoRunner()
    st.toast("系统已重置/初始化")

# 调试面板
if st.sidebar.checkbox("🛠️ 显示底层调试信息"):
    st.sidebar.write(f"当前亲密度实例值: {st.session_state.runner.current_state.get('intimacy_level')}")
    st.sidebar.write(f"最后一次 Node Trace: {st.session_state.trace}")
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'last_monologue' not in st.session_state:
    st.session_state.last_monologue = ""
if 'trace' not in st.session_state:
    st.session_state.trace = []

# --- 侧边栏 (Sidebar) ---
with st.sidebar:
    st.header("🎮 传感器模拟")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("👋 摸摸头", use_container_width=True):
            with st.spinner("Animus 感受中..."):
                state = st.session_state.runner.run_step(sensor_data={"touch": True})
                if state.get("_debug_intimacy_updated"):
                    st.toast(f"📈 亲密度更新: {state['_debug_intimacy_updated']}")
                st.session_state.last_monologue = state.get("monologue", "")
                st.session_state.trace = st.session_state.runner.node_trace
                if state.get("voice_content"):
                    st.session_state.messages.append({"role": "assistant", "content": state["voice_content"]})
                st.rerun()
    
    with col2:
        if st.button("🫨 摇晃它", use_container_width=True):
            with st.spinner("Animus 晕乎乎..."):
                state = st.session_state.runner.run_step(sensor_data={"shake": True})
                st.session_state.last_monologue = state.get("monologue", "")
                st.session_state.trace = st.session_state.runner.node_trace
                if state.get("voice_content"):
                    st.session_state.messages.append({"role": "assistant", "content": state["voice_content"]})
                st.rerun()

    st.divider()
    
    # 邮箱配置部分
    st.header("📧 邮箱配置")
    with st.expander("配置邮箱提醒", expanded=False):
        try:
            from src.mcp_manager import get_mcp_manager
            mcp = get_mcp_manager()
            
            # 显示已配置的邮箱
            email_configs = mcp.tokens.get("email_configs", {})
            if email_configs:
                st.success(f"已配置 {len(email_configs)} 个邮箱")
                for provider_name, config in email_configs.items():
                    with st.container():
                        st.write(f"**{provider_name}** ({config.get('type', 'N/A')})")
                        st.caption(f"用户: {config.get('username', 'N/A')}")
                        
                        # 显示重要发件人
                        important_senders = mcp.tokens.get("important_senders", {}).get(provider_name, [])
                        if important_senders:
                            st.caption(f"重要发件人: {', '.join(important_senders[:3])}{'...' if len(important_senders) > 3 else ''}")
            else:
                st.info("尚未配置邮箱")
                st.caption("使用 CLI 工具配置: python scripts/configure_email.py")
            
            # 检查间隔配置
            st.subheader("检查间隔")
            current_interval = mcp.get_email_check_interval()
            st.caption(f"当前: {current_interval}秒 ({current_interval//60}分钟)")
            
            interval_minutes = st.selectbox(
                "检查间隔",
                [5, 10, 15, 30],
                index=[5, 10, 15, 30].index(current_interval//60) if current_interval//60 in [5, 10, 15, 30] else 0,
                key="check_interval"
            )
            
            if st.button("更新间隔", use_container_width=True):
                mcp.set_email_check_interval(interval_minutes * 60)
                st.success(f"✅ 已设置检查间隔为 {interval_minutes} 分钟")
                st.info("⚠️ 需要重启系统才能生效")
                st.rerun()
            
            st.divider()
            
            # 快速配置入口
            st.subheader("快速配置")
            provider_type = st.selectbox("邮箱类型", ["163", "qq", "outlook"], key="email_type")
            username = st.text_input("邮箱地址", key="email_username")
            password = st.text_input("授权码/密码", type="password", key="email_password")
            
            if st.button("添加邮箱", use_container_width=True):
                if username and password:
                    with st.spinner("正在连接邮箱..."):
                        success = mcp.add_email_provider(
                            f"email_{provider_type}",
                            provider_type,
                            username,
                            password
                        )
                    if success:
                        st.success("✅ 邮箱配置成功！")
                        st.rerun()
                    else:
                        st.error("❌ 配置失败，请检查邮箱地址和授权码")
                else:
                    st.warning("请填写完整信息")
            
            # 重要性规则配置（如果有已配置的邮箱）
            if email_configs:
                st.divider()
                st.subheader("重要性判断规则")
                st.caption("高级配置，建议使用 CLI 工具: python scripts/configure_email.py")
                
                selected_provider = st.selectbox("选择邮箱", list(email_configs.keys()), key="rule_provider")
                if selected_provider:
                    importance_rules = mcp.tokens.get("email_importance_rules", {}).get(selected_provider, {})
                    
                    st.write("**当前规则：**")
                    st.write(f"- 优先级标记检测: {'✅' if importance_rules.get('check_priority_flag', True) else '❌'}")
                    st.write(f"- 域名白名单: {len(importance_rules.get('important_domains', []))} 个")
                    keywords = importance_rules.get('keywords', {})
                    st.write(f"- 主题关键词: {len(keywords.get('subject_keywords', []))} 个")
                    st.write(f"- 发件人关键词: {len(keywords.get('sender_keywords', []))} 个")
        except Exception as e:
            st.error(f"邮箱配置功能暂不可用: {e}")
            st.caption("请使用 CLI 工具: python scripts/configure_email.py")
    
    st.divider()
    
    st.header("💡 硬件模拟状态")
    hw_state = st.session_state.runner.get_hardware_state()
    light = hw_state.get("light", {})
    motor = hw_state.get("motor", {})
    
    # 灯光展示
    light_status = "🟢 开启" if light.get("status") == "on" else "⚪ 关闭"
    st.subheader(f"灯光: {light_status}")
    if light.get("status") == "on":
        brightness = light.get("brightness", 0)
        st.progress(brightness / 100.0, text=f"亮度: {brightness}%")
        color = light.get("color", "warm")
        st.caption(f"颜色模式: {color}")
    
    # 电机展示
    motor_status = "🟢 运行中" if motor.get("status") == "on" or motor.get("vibration") != "none" else "⚪ 停止"
    st.subheader(f"电机: {motor_status}")
    if motor.get("vibration") != "none":
        st.info(f"振动模式: {motor.get('vibration')}")

# --- 主界面 (Main UI) ---
st.markdown("<h1 class='main-header'>Animus V1 智能宠物控制台</h1>", unsafe_allow_html=True)

# 场景选择器
selected_scenario = st.selectbox("🎬 选择演示场景", list(DEMO_SCENARIOS.keys()))
if selected_scenario:
    st.markdown(f"<div class='scenario-box'>💡 <b>场景建议:</b> {get_scenario_instructions(selected_scenario)}</div>", unsafe_allow_html=True)
    with st.expander("📝 查看该场景预设指令"):
        for cmd in DEMO_SCENARIOS[selected_scenario]:
            st.code(cmd)

# 顶部状态条 (Intimacy)
intimacy = st.session_state.runner.get_intimacy_info()
col_a, col_b = st.columns([3, 1])
with col_a:
    rank_icons = {"stranger": "👤", "acquaintance": "👋", "friend": "🤝", "soulmate": "❤️"}
    st.subheader(f"{rank_icons.get(intimacy['rank'], '❓')} 关系等级: {intimacy['rank'].capitalize()}")
    st.progress(intimacy['level'] / 100.0, text=f"亲密度: {intimacy['level']:.1f}/100")

# 对话与技术追踪分栏
chat_col, tech_col = st.columns([2, 1])

with chat_col:
    st.subheader("💬 对话交互")
    
    # 显示历史消息
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # 聊天输入
    if prompt := st.chat_input("和 Animus 说点什么..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("思考中..."):
                state = st.session_state.runner.run_step(user_input=prompt)
                st.session_state.last_monologue = state.get("monologue", "")
                st.session_state.trace = st.session_state.runner.node_trace
                
                response = state.get("voice_content", "...")
                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})
        st.rerun()

with tech_col:
    st.subheader("🔍 技术追踪 (System Trace)")
    
    # 思考链 (Monologue)
    st.markdown("#### 💭 内部独白 (Monologue)")
    if st.session_state.last_monologue:
        st.markdown(f"<div class='monologue-box'>{st.session_state.last_monologue}</div>", unsafe_allow_html=True)
    else:
        st.caption("暂无思考内容")
    
    st.divider()
    
    # 节点追踪 (Graph Trace)
    st.markdown("#### 🛤️ 工作流路径")
    if st.session_state.trace:
        for node in st.session_state.trace:
            st.success(f"✔️ Node: **{node}**")
    else:
        st.caption("等待工作流触发...")
    
    st.divider()
    
    # 记忆检索 (Memory Context)
    st.markdown("#### 🧠 记忆检索")
    memory_context = st.session_state.runner.current_state.get("memory_context")
    if memory_context:
        memories = memory_context.get("user_memories", [])
        if memories:
            for m in memories:
                st.warning(f"📌 {m}")
        else:
            st.caption("未找到相关记忆")
    else:
        st.caption("无检索上下文")

