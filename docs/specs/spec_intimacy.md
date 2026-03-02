# Spec: 亲密度系统 (Intimacy System)

---

## Meta

| 属性 | 值 |
|:---|:---|
| **PRD Reference** | @PRD: E-01, E-02, E-03, E-04 |
| **Module** | `src/intimacy_manager.py` |
| **Status** | `completed` |
| **Created** | 2025-12-16 |
| **Last Updated** | 2026-01-12 |
| **Author** | Project Animus Team |

---

## 1. Task Definition

### 1.1 目标

**核心目标**: 管理用户与 Animus 之间的亲密度数值，实现关系演化系统，使 AI 伴侣的行为和语气随着亲密度变化而自然演变。

### 1.2 触发条件

| 触发场景 | 描述 |
|:---|:---|
| 用户抚摸 | 传感器检测到触摸事件，触发亲密度增加 |
| 用户夸奖 | LLM 识别到正面反馈，触发亲密度增加 |
| 用户陪伴 | 每日陪伴超过 1 小时，触发陪伴奖励 |
| 用户冒犯 | 检测到 L1-L3 级别冒犯，触发亲密度减少 |
| 用户冷落 | 超过 24 小时无交互，触发亲密度衰减 |
| 状态恢复 | 系统启动时加载持久化的亲密度状态 |

### 1.3 非目标 (Out of Scope)

- 不负责冲突检测和冷却机制（由 `ConflictHandler` 处理）
- 不负责对话内容生成（由 `reasoning_node` 处理）
- 不负责触摸传感器的硬件交互（由硬件层处理）

---

## 2. Context

### 2.1 前置依赖

| 依赖项 | 类型 | 描述 |
|:---|:---|:---|
| `state.py` | 内部模块 | 定义 `LampState` 中的亲密度字段 |
| `StateManager` | 内部类 | 负责亲密度状态的持久化 |
| `datetime` | 标准库 | 用于每日计数器重置 |

### 2.2 调用方

| 调用方 | 场景 |
|:---|:---|
| `nodes.py: execution_node` | 检测到触摸/夸奖时调用 `update_intimacy` |
| `nodes.py: reasoning_node` | 读取当前亲密度等级，注入 System Prompt |
| `state_manager.py` | 启动时调用 `load_state` 恢复状态 |
| `demo/app.py` | 展示当前亲密度和等级 |

### 2.3 数据流

```
传感器/LLM 检测
       ↓
[IntimacyManager.update_intimacy()]
       ↓
   计算新亲密度
       ↓
   更新等级
       ↓
[StateManager.save_state()] → 持久化到 JSON
       ↓
   返回结果 → 注入 LampState
```

---

## 3. Interface

### 3.1 Input

```python
# update_intimacy 输入参数
{
    "delta": float,          # 变化量（正负均可）
    "reason": str            # 变化原因
}
```

**reason 可选值**:
| reason | 描述 | 典型 delta |
|:---|:---|:---|
| `"touch"` | 抚摸 | +0.5 |
| `"praise"` | 夸奖 | +1.0 |
| `"daily_presence"` | 每日陪伴奖励 | +2.0 |
| `"conflict_L1"` | L1 轻度冒犯 | -2.0 |
| `"conflict_L2"` | L2 中度冒犯 | -5.0 |
| `"conflict_L3"` | L3 重度冒犯 | -10.0 |
| `"neglect"` | 长期冷落 | -1.0/天 |

### 3.2 Output

```python
# update_intimacy 返回值
{
    "intimacy_level": float,    # 更新后的亲密度（0-100）
    "intimacy_rank": str,       # 当前等级
    "delta": float,             # 实际变化量（可能被上限限制）
    "reason": str,              # 原因
    "rank_changed": bool        # 等级是否发生变化
}
```

**示例**:
```python
{
    "intimacy_level": 30.5,
    "intimacy_rank": "stranger",
    "delta": 0.5,
    "reason": "touch",
    "rank_changed": False
}
```

### 3.3 Public Methods

```python
class IntimacyManager:
    """亲密度管理器"""
    
    def __init__(self) -> None:
        """
        初始化亲密度管理器
        
        初始状态:
            - intimacy_level: 30.0
            - intimacy_rank: "stranger"
            - daily_touch_count: 0
            - daily_praise_count: 0
        """
        pass
    
    def update_intimacy(
        self, 
        delta: float, 
        reason: str
    ) -> Dict[str, Any]:
        """
        更新亲密度
        
        Args:
            delta: 变化量（可为正负）
            reason: 原因（"touch", "praise", "conflict_L1", etc.）
        
        Returns:
            包含更新后状态的字典
        
        Side Effects:
            - 更新内部状态
            - 记录历史
            - 触发每日计数器检查
        """
        pass
    
    def get_intimacy_rank(self, level: float) -> str:
        """
        根据亲密度数值返回等级
        
        Args:
            level: 亲密度数值（0-100）
        
        Returns:
            等级名称：
            - "stranger" (0-30)
            - "acquaintance" (31-50)
            - "friend" (51-75)
            - "soulmate" (76-100)
        """
        pass
    
    def reset_daily_counters(self) -> None:
        """
        重置每日计数器
        
        在日期变更时自动调用
        """
        pass
    
    def calculate_daily_bonus(
        self, 
        presence_duration_seconds: float
    ) -> float:
        """
        计算每日陪伴奖励
        
        Args:
            presence_duration_seconds: 今日陪伴时长（秒）
        
        Returns:
            奖励的亲密度增量（0 或 2.0）
        """
        pass
    
    def get_current_state(self) -> Dict[str, Any]:
        """
        获取当前状态（用于状态同步）
        
        Returns:
            包含所有状态字段的字典
        """
        pass
    
    def load_state(self, state: Dict[str, Any]) -> None:
        """
        从状态字典加载数据（用于状态恢复）
        
        Args:
            state: 包含持久化数据的字典
        """
        pass
```

### 3.4 State Fields

| 字段名 | 类型 | 描述 |
|:---|:---|:---|
| `intimacy_level` | `float` | 当前亲密度（0-100） |
| `intimacy_rank` | `str` | 当前等级名称 |
| `intimacy_delta` | `Optional[float]` | 本次变化增量 |
| `intimacy_reason` | `Optional[str]` | 变化原因 |
| `intimacy_history` | `List[Dict]` | 历史记录（调试用） |
| `daily_presence_duration` | `float` | 今日陪伴时长（秒） |

---

## 4. Business Logic

### 4.1 核心规则

1. **亲密度范围**: 0-100，初始值为 30
2. **抚摸增益**: +0.5/次，每日上限 10 次（共 +5）
3. **夸奖增益**: +1.0/次，每日上限 10 次（共 +10）
4. **陪伴奖励**: 每日陪伴 > 1 小时，+2
5. **冲突惩罚**: 
   - L1: -2
   - L2: -5
   - L3: -10
6. **冷落惩罚**: 超过 24 小时无交互，-1/天
7. **等级计算**: 
   - stranger: 0-30
   - acquaintance: 31-50
   - friend: 51-75
   - soulmate: 76-100

### 4.2 决策流程

```
update_intimacy(delta, reason)
  ↓
[检查日期是否变更]
  ├─ 是 → 重置每日计数器
  └─ 否 → 继续
  ↓
[检查是否为正向操作]
  ├─ 是 → [检查每日上限]
  │         ├─ touch 且 count >= 10 → delta = 0
  │         ├─ praise 且 count >= 10 → delta = 0
  │         └─ 未达上限 → 增加计数器
  └─ 否 → 继续（负向操作不受限制）
  ↓
[计算新亲密度]
  new_level = clamp(old_level + delta, 0, 100)
  ↓
[计算新等级]
  new_rank = get_intimacy_rank(new_level)
  ↓
[检查等级是否变化]
  rank_changed = (old_rank != new_rank)
  ↓
[记录历史]
  ↓
[返回结果]
```

### 4.3 边界情况

| 情况 | 条件 | 处理方式 |
|:---|:---|:---|
| 亲密度下溢 | `level + delta < 0` | 设为 0 |
| 亲密度上溢 | `level + delta > 100` | 设为 100 |
| 每日触摸上限 | `daily_touch_count >= 10` | delta 设为 0，不增加 |
| 每日夸奖上限 | `daily_praise_count >= 10` | delta 设为 0，不增加 |
| 跨日期操作 | 日期变更 | 自动重置每日计数器 |
| 历史记录过长 | `len(history) > 100` | 只保留最近 100 条 |

### 4.4 等级转换

```
stranger (0-30) ─[level > 30]→ acquaintance (31-50)
                                     ↓
acquaintance (31-50) ─[level > 50]→ friend (51-75)
                                     ↓
friend (51-75) ─[level > 75]→ soulmate (76-100)

（反向同理，level 降低会降级）
```

### 4.5 等级对行为的影响

| 等级 | 亲密度 | 行为特征 |
|:---|:---|:---|
| `stranger` | 0-30 | 只回答问题，语气机械，不主动搭话 |
| `acquaintance` | 31-50 | 略有主动性，语气正式，偶尔问候 |
| `friend` | 51-75 | 主动关心，语气亲切，使用昵称 |
| `soulmate` | 76-100 | 主动撒娇，语气活泼，高度依赖 |

---

## 5. Error Handling

### 5.1 错误分类

| 错误类型 | 严重性 | 处理策略 | 降级方案 |
|:---|:---|:---|:---|
| 输入 delta 非数字 | WARNING | 类型转换 | 使用 0 |
| 输入 reason 为空 | WARNING | 记录日志 | 使用 "unknown" |
| 状态加载失败 | ERROR | 记录错误 | 使用初始值 |
| 历史记录损坏 | WARNING | 清空历史 | 重新开始记录 |

### 5.2 日志规范

```python
# INFO: 正常操作
print(f"   💝 亲密度更新: {old_level} → {new_level} ({delta:+.1f}, {reason})")

# WARNING: 每日上限
print(f"   ⚠️  今日抚摸次数已达上限（10次）")

# INFO: 等级变化
print(f"   🎉 亲密度等级变化: {old_rank} → {new_rank}")

# INFO: 每日重置
print(f"   📅 每日计数器已重置（日期: {date}）")
```

### 5.3 降级策略

```python
def load_state(self, state: Dict[str, Any]) -> None:
    """从状态加载数据，带降级保护"""
    try:
        if "intimacy_level" in state:
            self.intimacy_level = float(state["intimacy_level"])
        if "intimacy_rank" in state:
            self.intimacy_rank = state["intimacy_rank"]
        # ... 其他字段
    except (TypeError, ValueError) as e:
        print(f"   ⚠️  状态加载部分失败: {e}，使用默认值")
        # 保持已成功加载的值，失败的使用默认值
```

---

## 6. Test Cases

### 6.1 单元测试

- [x] **test_initial_state**: 验证初始状态为 level=30, rank="stranger"
- [x] **test_update_intimacy_touch**: 测试抚摸增加亲密度 +0.5
- [x] **test_update_intimacy_praise**: 测试夸奖增加亲密度 +1.0
- [x] **test_update_intimacy_conflict_l1**: 测试 L1 冲突减少亲密度 -2
- [x] **test_update_intimacy_conflict_l2**: 测试 L2 冲突减少亲密度 -5
- [x] **test_update_intimacy_conflict_l3**: 测试 L3 冲突减少亲密度 -10
- [x] **test_intimacy_bounds**: 测试边界值（0-100）
- [x] **test_get_intimacy_rank_stranger**: 测试 0-30 等级判断
- [x] **test_get_intimacy_rank_acquaintance**: 测试 31-50 等级判断
- [x] **test_get_intimacy_rank_friend**: 测试 51-75 等级判断
- [x] **test_get_intimacy_rank_soulmate**: 测试 76-100 等级判断
- [x] **test_rank_change_detection**: 测试等级变化检测
- [x] **test_daily_touch_limit**: 测试每日抚摸上限（10次）
- [x] **test_daily_praise_limit**: 测试每日夸奖上限（10次）
- [x] **test_daily_bonus_calculation**: 测试每日陪伴奖励计算
- [x] **test_reset_daily_counters**: 测试每日计数器重置
- [x] **test_check_and_reset_daily_counters**: 测试自动日期检查
- [x] **test_intimacy_history_recording**: 测试历史记录
- [x] **test_get_current_state**: 测试获取当前状态
- [x] **test_load_state**: 测试加载状态

### 6.2 测试文件路径

```
tests/
└── test_intimacy_manager.py
```

### 6.3 Mock 需求

| Mock 对象 | 原因 |
|:---|:---|
| `datetime.date.today()` | 控制日期以测试跨日重置 |

### 6.4 示例测试代码

```python
import unittest
from datetime import date, timedelta
from src.intimacy_manager import IntimacyManager

class TestIntimacyManager(unittest.TestCase):
    
    def setUp(self):
        """每个测试前初始化"""
        self.manager = IntimacyManager()
        self.manager.intimacy_level = 30.0
        self.manager.intimacy_rank = "stranger"
        self.manager.daily_touch_count = 0
        self.manager.daily_praise_count = 0
        self.manager.last_reset_date = date.today().isoformat()
    
    def test_update_intimacy_touch(self):
        """测试抚摸增加亲密度"""
        result = self.manager.update_intimacy(0.5, "touch")
        self.assertEqual(result["intimacy_level"], 30.5)
        self.assertEqual(result["delta"], 0.5)
        self.assertEqual(result["reason"], "touch")
        self.assertEqual(self.manager.daily_touch_count, 1)
    
    def test_daily_touch_limit(self):
        """测试每日抚摸次数上限（10次）"""
        # 抚摸10次
        for i in range(10):
            self.manager.update_intimacy(0.5, "touch")
        
        # 第11次应该不再增加
        initial_level = self.manager.intimacy_level
        result = self.manager.update_intimacy(0.5, "touch")
        self.assertEqual(result["intimacy_level"], initial_level)
        self.assertEqual(result["delta"], 0.0)
    
    def test_rank_change_detection(self):
        """测试等级变化检测"""
        self.manager.intimacy_level = 30.0
        result = self.manager.update_intimacy(0.1, "praise")
        self.assertTrue(result["rank_changed"])
        self.assertEqual(result["intimacy_rank"], "acquaintance")
```

---

## 7. Implementation Notes

### 7.1 开发注意事项

- ⚠️ **必须使用 IntimacyManager**: 禁止在 nodes.py 中直接修改 `state["intimacy_level"]`
- ⚠️ **必须持久化**: 亲密度变更后必须调用 `StateManager.save_state()`
- ⚠️ **浮点精度**: 使用 `round(value, 2)` 避免浮点精度问题
- ⚠️ **历史记录**: 限制为最近 100 条，防止内存膨胀

### 7.2 技术债务

| 问题 | 优先级 | 描述 |
|:---|:---|:---|
| 日志迁移 | P3 | 当前使用 `print()`，需迁移到 `logging` |
| 冷落检测 | P2 | 当前未实现自动冷落检测（-1/天） |

### 7.3 未来优化

- [ ] **优化 1**: 实现自动冷落检测机制
- [ ] **优化 2**: 添加亲密度变化事件系统（观察者模式）
- [ ] **优化 3**: 支持亲密度衰减曲线配置

### 7.4 相关文档

- **PRD**: `docs/prd/Prd1_5.md` - 第 2.2 节"情感与亲密度系统"
- **架构设计**: `docs/architecture/architecture_design.md` - 亲密度系统流程
- **冲突处理**: 参见 `ConflictHandler` 的 Spec（待编写）

---

## 版本历史

| 版本 | 日期 | 变更说明 |
|:---|:---|:---|
| v1.0 | 2025-12-16 | 初始版本，实现核心亲密度逻辑 |
| v1.1 | 2026-01-12 | 按新 Spec 模板重写，补充完整接口和测试用例 |

---

**文档状态**: `completed`  
**最后更新**: 2026-01-12
