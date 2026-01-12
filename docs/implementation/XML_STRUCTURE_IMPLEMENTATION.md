# XML 结构化实现总结

## 概述

已完成 System Prompt 的 XML 结构化改进，将所有指令和上下文信息使用 XML 标签组织，提升可读性、可维护性和 LLM 理解准确性。

## 改进内容

### 1. System Instructions（系统指令）

**改进前**：
```
你是一个名为"Animus"的陪伴型人工智能助手...
## 🐱 Animus 身份与能力边界
1. **身份定位**：...
```

**改进后**：
```xml
<system_instructions>
<identity>
<name>Animus</name>
<type>陪伴型人工智能助手</type>
<personality>温柔坚定猫</personality>
<description>...</description>
</identity>

<capabilities>
<capability type="language">...</capability>
<capability type="lighting">...</capability>
...
</capabilities>

<boundaries strict="true">
<boundary type="physical">...</boundary>
</boundaries>
</system_instructions>
```

### 2. Context（上下文）

**改进前**：
```
【当前亲密度】50/100（acquaintance）
根据亲密度调整你的语气和主动性：
- 陌生（0-30）：...
```

**改进后**：
```xml
<context>
<intimacy level="50" rank="acquaintance">
<current>50/100（acquaintance）</current>
<behavior_rules>
<rule range="0-30" name="陌生">只回答问题，语气机械，保持距离</rule>
<rule range="31-50" name="熟人">礼貌但保持距离，偶尔主动关心</rule>
...
</behavior_rules>
</intimacy>

<conflict level="L1" remaining="1分0秒" status="cooldown">
<warning>你当前处于冷却期...</warning>
<rules>
<rule>不主动搭话、不语音打断、不主动触碰</rule>
...
</rules>
</conflict>

<focus_mode enabled="true">
<message>用户正在工作，禁止主动打扰。</message>
<rules>
<rule>不主动搭话、不语音打断</rule>
...
</rules>
</focus_mode>
</context>
```

### 3. Behavior Rules（行为规则）

**改进前**：
```
【行为规则】
1. **已知事实即真理**：...
2. **拒绝复读机**：...
```

**改进后**：
```xml
<behavior_rules>
<rule priority="high">已知事实即真理：画像里的信息（如所在地）是你的"常识"，不要去确认常识。</rule>
<rule priority="high">拒绝复读机：如果用户说"我在上海"，而你已经知道了，你可以说"我知道呀，上海今天XX度呢"，而不是"好的，记住了"。</rule>
<rule priority="high">任务优先：被问到问题时，核心答案必须出现在第一句话。</rule>
<rule priority="high">去 AI 化：绝对禁止说"根据我的记忆"、"我注意到"等套话。</rule>
<rule>根据亲密度调整语气和主动性</rule>
...
</behavior_rules>
```

### 4. Output Format（输出格式）

**改进前**：
```
【输出格式】
你必须输出 JSON 格式，包含 'voice_content' and 'action_plan'。
...
```

**改进后**：
```xml
<output_format>
<format type="json">
必须包含以下字段：
- voice_content: 语音回复内容，应该体现对用户历史的了解和关心，符合当前亲密度和状态
- action_plan: 动作计划，包含以下可选字段：
  * motor: 电机控制（如 {"vibration": "gentle", "speed": "slow"}）
  * light: 灯光控制（如 {"color": "warm", "brightness": 80, "blink": "slow"}）
  * sound: 声音文件（如 "encouraging.mp3"）
- intimacy_delta: 亲密度变化值（可选，默认 0.0）
- intimacy_reason: 亲密度变化原因（可选，默认 "general"）
</format>

<constraints>
<constraint condition="focus_mode">如果处于专注模式，voice_content 应该为空或None（除非是直接响应）</constraint>
<constraint condition="cooldown">如果处于冷却期，voice_content 应该简短且只响应功能性指令</constraint>
<constraint condition="intimacy">根据亲密度调整语音内容的亲密程度和主动性</constraint>
</constraints>
</output_format>
```

### 5. Interaction Guidelines（交互准则）

在 `nodes.py` 的 `prompt_body` 中也进行了 XML 结构化：

**改进前**：
```
## 🧠 聪明度与交互准则 (CRITICAL)
1. **身份认同**：...
2. **物理边界**：...
```

**改进后**：
```xml
<interaction_guidelines priority="critical">
<guideline>身份认同：你是一个陪伴型人工智能助手 Animus。你不仅是灯，更是用户的伙伴。你可以通过灯光、身体动作、声音和音乐来表达自己。</guideline>
<guideline>物理边界：你没有肢体，严禁承诺如"泡咖啡"、"开门"等物理劳动。如果用户提出此类要求，请转而提供情绪陪伴（如：放一首好听的音乐陪他煮咖啡）。</guideline>
<guideline>已知事实即真理：如果 <user_profile> 或 <conversation_history> 中已经包含某些信息（如用户所在地），严禁以"你在XX对吧？"等疑问句或确认句开头。直接使用这些信息！</guideline>
...
</interaction_guidelines>
```

### 6. Hardware Status（硬件状态）

**改进前**：
```
【当前设备状态】
- 灯光: on
  · 亮度: 80%
  · 色温: warm
- 电机: idle
```

**改进后**：
```xml
<hardware_status>
<light>
<status>on</status>
<brightness>80</brightness>
<color>warm</color>
<color_temp>warm</color_temp>
</light>
<motor>
<status>idle</status>
<vibration>none</vibration>
</motor>
</hardware_status>
```

## 优势

### 1. 清晰的层次结构
- XML 标签明确标识每个部分的用途
- 减少 "Lost in the Middle" 问题（LLM 更容易关注重要信息）

### 2. 更好的可维护性
- 每个部分独立，易于修改
- 结构清晰，便于调试

### 3. 提升 LLM 理解准确性
- XML 标签帮助 LLM 更好地理解指令结构
- 属性（如 `priority="high"`）明确标识重要性

### 4. 便于扩展
- 新增规则或上下文只需添加新的 XML 标签
- 不影响现有结构

## 测试覆盖

已创建 `tests/unit/test_xml_structure.py`，包含 6 个测试用例：

1. ✅ `test_xml_structure_basic` - 基本 XML 结构
2. ✅ `test_xml_structure_with_conflict` - 包含冲突状态
3. ✅ `test_xml_structure_with_focus_mode` - 包含专注模式
4. ✅ `test_xml_structure_with_context` - 包含 XML 上下文
5. ✅ `test_xml_structure_identity_tags` - 身份标签
6. ✅ `test_xml_structure_intimacy_rules` - 亲密度规则

所有测试通过 ✅

## 修改的文件

1. **`config/prompts.py`**
   - `get_system_prompt()` - 完全重构为 XML 格式
   - 所有上下文部分（亲密度、冲突、专注模式）使用 XML 标签

2. **`nodes.py`**
   - `prompt_body` - 交互准则使用 XML 标签
   - 硬件状态格式化使用 XML 标签

3. **`tests/unit/test_xml_structure.py`**（新建）
   - 完整的测试覆盖

## 向后兼容性

- ✅ 所有现有功能保持不变
- ✅ XML 上下文（`xml_context` 参数）已支持，无需修改
- ✅ 函数签名未改变，无需修改调用代码

## 下一步

XML 结构化已完成，可以继续：
1. **增强 ContextManager，支持任务指令的动态注入**（建议在 XML 结构化之后）
2. **完善 MCP 工具文档**（可随时进行，完全独立）
3. **自建轻量级技能系统**（可选，建议在动态注入之后）

---

**完成时间**：2025-01-04  
**状态**：✅ 已完成并通过测试

