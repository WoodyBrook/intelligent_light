# 代码梳理报告 - V1 MVP 代码复用分析

## 分析目标
对照 `Prd1_0.md` 中的 V1 MVP 需求，梳理现有代码库，明确：
- ✅ **可直接复用**：代码完整，符合V1需求
- 🔧 **需要修改**：代码存在但需要调整以符合V1需求
- ❌ **需要删除**：V1不需要的功能
- ➕ **需要新增**：V1需要但当前缺失的功能

---

## 一、核心架构文件

### 1. `state.py` - 状态定义

**当前状态**：✅ 基本完整，但需要补充V1新需求字段

**可复用部分**：
- ✅ `LampState` TypedDict 基础结构
- ✅ 所有V2.0已有字段（user_profile, internal_drives, memory_context等）

**需要修改**：
- 🔧 **添加亲密度相关字段**：
  ```python
  intimacy_level: int  # 0-100
  intimacy_rank: str  # "stranger|acquaintance|friend|soulmate"
  intimacy_history: List[Dict]  # 历史记录（可选）
  ```
- 🔧 **添加专注模式字段**：
  ```python
  focus_mode: bool
  focus_mode_start_time: Optional[float]
  focus_mode_duration: int  # 默认7200秒（2小时）
  ```
- 🔧 **添加冲突状态字段**（用于冲突分级与修复）：
  ```python
  conflict_state: Optional[Dict]  # 包含 level, cooldown_end_time, repair_attempts 等
  ```

**需要删除**：
- ❌ 无（所有字段V1都可能用到）

---

### 2. `graph.py` - 工作流图

**当前状态**：✅ 完全可复用

**可复用部分**：
- ✅ OODA架构完整（evaluator → memory_loader → perception → router → reflex/reasoning → guard → execution）
- ✅ 所有节点连接关系
- ✅ 条件分支逻辑

**需要修改**：
- 🔧 无（架构完全符合V1需求）

**需要删除**：
- ❌ 无

---

### 3. `main.py` - 主程序

**当前状态**：✅ 基本可复用，需要小调整

**可复用部分**：
- ✅ OODA事件循环完整
- ✅ 事件管理器集成
- ✅ 状态管理器集成
- ✅ 优雅退出机制

**需要修改**：
- 🔧 **专注模式检查**：在触发主动行为前，检查 `focus_mode` 状态
- 🔧 **勿扰时间唤醒行为**：在勿扰时间内，如果用户主动交互，触发"被吵醒"状态

**需要删除**：
- ❌ 无

---

## 二、节点实现文件

### 4. `nodes.py` - 节点实现

**当前状态**：🔧 大部分可复用，但需要大量修改以符合V1需求

#### 4.1 `evaluator_node` - 评估器

**可复用部分**：
- ✅ 事件类型判断逻辑
- ✅ 内部驱动触发逻辑（无聊度检查）

**需要修改**：
- 🔧 **专注模式检查**：在主动行为触发前，检查 `focus_mode`，如果开启则禁止主动行为
- 🔧 **勿扰时间唤醒**：在勿扰时间内，如果用户主动交互，设置"被吵醒"状态

#### 4.2 `memory_loader_node` - 记忆加载器

**可复用部分**：
- ✅ 完全可复用（RAG检索逻辑）

**需要修改**：
- 🔧 无

#### 4.3 `perception_node` - 感知节点

**可复用部分**：
- ✅ 内部状态读取
- ✅ 上下文信号更新

**需要修改**：
- 🔧 **专注模式状态**：从 `context_signals` 中读取 `focus_mode`（当前代码有简单推断，需要改为从state读取）

#### 4.4 `router_node` - 路由节点

**可复用部分**：
- ✅ 规则路由逻辑（反射/推理判断）
- ✅ 关键词匹配

**需要修改**：
- 🔧 **专注模式命令识别**：添加"开启专注模式"、"我要工作了"等命令识别
- 🔧 **专注模式下的路由**：专注模式下，只允许直接交互，禁止主动行为

#### 4.5 `reflex_node` - 反射节点

**可复用部分**：
- ✅ 传感器反馈逻辑
- ✅ 灯光控制逻辑
- ✅ 简单问候逻辑

**需要修改**：
- 🔧 **专注模式下的触摸反馈**：专注模式下，抚摸应给予静默反馈（轻微震动/眯眼），不触发语音
- 🔧 **冲突分级处理**：添加L1-L3冲突检测与响应（当前只有简单的"恐惧"状态）

#### 4.6 `reasoning_node` - 推理节点

**可复用部分**：
- ✅ LLM调用逻辑
- ✅ 上下文构建逻辑
- ✅ 记忆注入逻辑

**需要修改**：
- 🔧 **System Prompt重写**：改为"温柔坚定猫"的A基调，添加Few-shot示例
- 🔧 **思考状态反馈**：在LLM调用前，设置"思考中"状态（用于UI显示）
- 🔧 **冲突分级检测**：在LLM回复中检测L1-L3级别的冒犯，触发相应处理
- 🔧 **Forgiveness Detector**：在冷却期间，检测用户是否在道歉
- 🔧 **亲密度影响Prompt**：根据亲密度等级调整Prompt的tone

#### 4.7 `action_guard_node` - 安全卫士

**可复用部分**：
- ✅ 动作计划验证逻辑

**需要修改**：
- 🔧 **移除"兴奋模式强制修饰"**：V1使用"温柔坚定猫"，不是"兴奋模式"
- 🔧 **添加专注模式检查**：确保专注模式下不输出语音/主动动作
- 🔧 **添加冲突状态检查**：冷却期间，禁止非白名单指令

#### 4.8 `execution_node` - 执行节点

**可复用部分**：
- ✅ 硬件状态更新逻辑
- ✅ 记忆写入逻辑
- ✅ 对话历史更新逻辑

**需要修改**：
- 🔧 **亲密度更新逻辑**：添加亲密度计算（根据交互类型增减）
- 🔧 **冲突分级处理**：检测用户行为，触发L1-L3分级
- 🔧 **修复仪式处理**：检测用户道歉，结束冷却
- 🔧 **专注模式超时检查**：检查专注模式是否超时，自动关闭

#### 4.9 `tool_node` - 工具节点

**当前状态**：⚠️ 占位实现

**需要修改**：
- 🔧 V1暂时不需要工具调用，可以保留但简化

---

## 三、管理器文件

### 5. `state_manager.py` - 状态管理器

**当前状态**：✅ 基本可复用，需要补充

**可复用部分**：
- ✅ 状态初始化逻辑
- ✅ 内部状态更新逻辑（无聊度、能量值）
- ✅ 状态持久化逻辑

**需要修改**：
- 🔧 **亲密度初始化**：在 `initialize_state()` 中添加 `intimacy_level: 30`
- 🔧 **专注模式初始化**：添加 `focus_mode: False` 等字段
- 🔧 **冲突状态初始化**：添加 `conflict_state: None`
- 🔧 **添加亲密度更新方法**：`update_intimacy(interaction_type, state) -> LampState`
- 🔧 **添加专注模式管理方法**：`toggle_focus_mode(state, enable) -> LampState`

**需要删除**：
- ❌ 无

---

### 6. `event_manager.py` - 事件管理器

**当前状态**：✅ 完全可复用

**可复用部分**：
- ✅ 所有事件检测逻辑
- ✅ 非阻塞事件获取

**需要修改**：
- 🔧 无（V1需求完全满足）

**需要删除**：
- ❌ 无

---

### 7. `memory_manager.py` - 记忆管理器

**当前状态**：✅ 完全可复用

**可复用部分**：
- ✅ 双路RAG系统（用户记忆 + 动作库）
- ✅ Query Rewrite逻辑
- ✅ 记忆保存/检索逻辑

**需要修改**：
- 🔧 无（V1的M-01、M-02需求完全满足）

**需要删除**：
- ❌ 无

---

### 8. `tools.py` - 工具定义

**当前状态**：✅ 可复用，但V1不是必需

**可复用部分**：
- ✅ 所有工具函数（天气、时间、计算等）

**需要修改**：
- 🔧 V1阶段工具调用不是P0需求，可以保留但不强制使用

**需要删除**：
- ❌ 无（保留以备V2使用）

---

## 四、配置文件

### 9. `requirements.txt` - 依赖版本

**当前状态**：✅ 基本可复用，需要补充

**可复用部分**：
- ✅ 所有现有依赖

**需要修改**：
- 🔧 **补充缺失依赖**（如果V1需要）：
  ```
  # 可能需要添加（根据实际需求）：
  # python-dotenv>=1.0.0  # .env文件支持
  # ollama>=0.1.0  # 如果直接调用Ollama（当前通过langchain）
  ```

**需要删除**：
- ❌ 无

---

## 五、测试文件

### 10. `test_interactive.py` / `test_simple.py`

**当前状态**：⚠️ 需要评估

**建议**：
- 🔧 保留但需要更新测试用例以符合V1需求
- 🔧 添加V1新功能的测试（亲密度、专注模式、冲突分级）

---

## 六、需要新增的文件

### 11. `intimacy_manager.py` - 亲密度管理器（新增）

**功能**：
- 计算亲密度变化
- 更新亲密度等级
- 根据等级生成Prompt调整

**接口定义**（伪代码）：
```python
class IntimacyManager:
    def calculate_intimacy_change(
        self, 
        interaction_type: str,  # "touch", "praise", "hit", "neglect"
        current_intimacy: int
    ) -> Dict[str, Any]:
        """
        计算亲密度变化
        返回: {"change": int, "new_level": int, "new_rank": str}
        """
        pass
    
    def get_intimacy_rank(self, level: int) -> str:
        """根据数值返回等级：stranger|acquaintance|friend|soulmate"""
        pass
    
    def get_prompt_tone(self, rank: str) -> str:
        """根据等级返回Prompt tone调整"""
        pass
```

---

### 12. `conflict_handler.py` - 冲突处理器（新增）

**功能**：
- 检测用户行为的冲突等级（L0-L3）
- 管理冷却状态
- 处理修复仪式

**接口定义**（伪代码）：
```python
class ConflictHandler:
    def detect_conflict_level(
        self, 
        user_input: str,
        sensor_data: Dict,
        current_state: LampState
    ) -> Dict[str, Any]:
        """
        检测冲突等级
        返回: {"level": "L0|L1|L2|L3", "reason": str, "intimacy_penalty": int}
        """
        pass
    
    def enter_cooldown(
        self, 
        level: str, 
        state: LampState
    ) -> LampState:
        """进入冷却状态"""
        pass
    
    def check_forgiveness(
        self, 
        user_input: str,
        current_cooldown: Dict
    ) -> bool:
        """检测用户是否在道歉（Forgiveness Detector）"""
        pass
```

---

### 13. `focus_mode_manager.py` - 专注模式管理器（新增，可选）

**功能**：
- 管理专注模式的开启/关闭
- 检查专注模式超时
- 专注模式下的行为限制

**接口定义**（伪代码）：
```python
class FocusModeManager:
    def enable_focus_mode(
        self, 
        state: LampState,
        duration: int = 7200
    ) -> LampState:
        """开启专注模式"""
        pass
    
    def check_timeout(self, state: LampState) -> bool:
        """检查专注模式是否超时"""
        pass
    
    def should_allow_proactive(self, state: LampState) -> bool:
        """检查是否允许主动行为"""
        pass
```

**注意**：如果逻辑简单，可以合并到 `state_manager.py` 中，不需要单独文件。

---

## 七、需要删除/废弃的代码

### 14. 废弃的功能

**需要删除/注释**：
- ❌ **action_guard_node 中的"兴奋模式强制修饰"**：V1使用"温柔坚定猫"，不是"兴奋模式"
  ```python
  # 删除这段：
  if state["current_mood"] == "excited":
      if "motor" in final_action:
          final_action["motor"]["speed"] = "super_fast"
      if "light" in final_action:
          final_action["light"]["brightness"] = 100
  ```

---

## 八、总结

### 代码复用率：**~85%**

| 文件 | 状态 | 复用率 | 主要修改点 |
|:---|:---|:---|:---|
| `state.py` | 🔧 需修改 | 90% | 添加亲密度、专注模式、冲突状态字段 |
| `graph.py` | ✅ 可复用 | 100% | 无 |
| `main.py` | 🔧 需修改 | 95% | 专注模式检查、勿扰时间唤醒 |
| `nodes.py` | 🔧 需修改 | 70% | System Prompt、冲突分级、亲密度、专注模式 |
| `state_manager.py` | 🔧 需修改 | 85% | 添加亲密度、专注模式管理方法 |
| `event_manager.py` | ✅ 可复用 | 100% | 无 |
| `memory_manager.py` | ✅ 可复用 | 100% | 无 |
| `tools.py` | ✅ 可复用 | 100% | 无（V1非必需） |

### 需要新增的文件

1. **`intimacy_manager.py`** - 亲密度管理器（必须）
2. **`conflict_handler.py`** - 冲突处理器（必须）
3. **`focus_mode_manager.py`** - 专注模式管理器（可选，可合并到state_manager）

### 优先级修改清单

**P0（必须修改，否则V1无法工作）**：
1. `state.py` - 添加亲密度、专注模式、冲突状态字段
2. `nodes.py` - System Prompt改为"温柔坚定猫"
3. `nodes.py` - 添加冲突分级检测（L0-L3）
4. `nodes.py` - 添加亲密度更新逻辑
5. `nodes.py` - 添加专注模式命令识别与处理
6. `state_manager.py` - 添加亲密度初始化与管理方法
7. 新增 `intimacy_manager.py`
8. 新增 `conflict_handler.py`

**P1（重要，影响体验）**：
1. `nodes.py` - 思考状态反馈
2. `nodes.py` - Forgiveness Detector
3. `main.py` - 专注模式检查
4. `main.py` - 勿扰时间唤醒行为
5. `action_guard_node` - 移除"兴奋模式"强制修饰

**P2（可选，V1.1再做）**：
1. 新增 `focus_mode_manager.py`（如果逻辑复杂）
2. 工具调用优化（V1非必需）

---

## 九、下一步建议

1. **先修改 `state.py`**：添加所有V1需要的字段
2. **创建 `intimacy_manager.py` 和 `conflict_handler.py`**：实现核心业务逻辑
3. **修改 `nodes.py`**：按优先级逐步修改各节点
4. **修改 `state_manager.py`**：添加管理方法
5. **修改 `main.py`**：添加专注模式检查

**建议顺序**：state.py → 新增管理器 → nodes.py → state_manager.py → main.py

