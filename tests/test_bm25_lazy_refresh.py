"""
测试 BM25 延迟刷新机制
验证：
1. 保存记忆时不会立即刷新 BM25（累积到阈值才刷新）
2. 强制刷新能正确处理剩余更新
3. 性能提升验证
"""
import sys
import os
import time

# 添加项目根目录
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()


def test_lazy_refresh_mechanism():
    """测试延迟刷新机制"""
    print("=" * 60)
    print("测试 BM25 延迟刷新机制")
    print("=" * 60)
    
    from src.memory_manager import MemoryManager
    
    # 使用临时目录避免污染正式数据
    test_db_path = "./data/test_bm25_lazy"
    mm = MemoryManager(db_path=test_db_path)
    
    # 验证初始状态
    print("\n[1] 验证初始配置")
    assert hasattr(mm, '_pending_bm25_updates'), "缺少 _pending_bm25_updates 属性"
    assert hasattr(mm, '_bm25_refresh_threshold'), "缺少 _bm25_refresh_threshold 属性"
    assert mm._pending_bm25_updates == 0, f"初始计数器应为0，实际为 {mm._pending_bm25_updates}"
    assert mm._bm25_refresh_threshold == 10, f"默认阈值应为10，实际为 {mm._bm25_refresh_threshold}"
    print(f"   ✅ 初始计数器: {mm._pending_bm25_updates}")
    print(f"   ✅ 刷新阈值: {mm._bm25_refresh_threshold}")
    
    # 测试保存记忆时的累积行为
    print("\n[2] 测试保存记忆时的累积行为")
    
    # 降低阈值以便测试
    mm._bm25_refresh_threshold = 5
    print(f"   测试阈值设为: {mm._bm25_refresh_threshold}")
    
    refresh_count = 0
    original_refresh = mm._refresh_bm25
    
    def mock_refresh():
        nonlocal refresh_count
        refresh_count += 1
        print(f"   🔄 BM25 刷新被调用 (第 {refresh_count} 次)")
        original_refresh()
    
    mm._refresh_bm25 = mock_refresh
    
    # 保存 4 条记忆（不应触发刷新）
    print("\n   保存 4 条记忆（阈值=5，不应触发刷新）...")
    for i in range(4):
        mm.save_user_memory(
            f"测试记忆 {i+1}: 用户喜欢测试数据",
            metadata={"category": "preference", "test": True}
        )
    
    assert mm._pending_bm25_updates == 4, f"应有4条待刷新，实际 {mm._pending_bm25_updates}"
    assert refresh_count == 0, f"不应触发刷新，实际触发了 {refresh_count} 次"
    print(f"   ✅ 待刷新计数: {mm._pending_bm25_updates}")
    print(f"   ✅ 刷新次数: {refresh_count}")
    
    # 保存第 5 条记忆（应触发刷新）
    print("\n   保存第 5 条记忆（应触发刷新）...")
    mm.save_user_memory(
        "测试记忆 5: 触发刷新的记忆",
        metadata={"category": "preference", "test": True}
    )
    
    assert mm._pending_bm25_updates == 0, f"刷新后计数器应为0，实际 {mm._pending_bm25_updates}"
    assert refresh_count == 1, f"应触发1次刷新，实际 {refresh_count} 次"
    print(f"   ✅ 待刷新计数: {mm._pending_bm25_updates}")
    print(f"   ✅ 刷新次数: {refresh_count}")
    
    # 测试强制刷新
    print("\n[3] 测试强制刷新")
    
    # 保存 3 条记忆（不触发自动刷新）
    for i in range(3):
        mm.save_user_memory(
            f"测试记忆 {6+i}: 强制刷新前的数据",
            metadata={"category": "preference", "test": True}
        )
    
    assert mm._pending_bm25_updates == 3, f"应有3条待刷新，实际 {mm._pending_bm25_updates}"
    print(f"   待刷新计数: {mm._pending_bm25_updates}")
    
    # 调用强制刷新
    print("   调用 force_refresh_bm25()...")
    mm.force_refresh_bm25()
    
    assert mm._pending_bm25_updates == 0, f"强制刷新后计数器应为0，实际 {mm._pending_bm25_updates}"
    assert refresh_count == 2, f"应触发2次刷新，实际 {refresh_count} 次"
    print(f"   ✅ 待刷新计数: {mm._pending_bm25_updates}")
    print(f"   ✅ 总刷新次数: {refresh_count}")
    
    # 测试无待刷新时的强制刷新
    print("\n[4] 测试无待刷新时的强制刷新")
    mm.force_refresh_bm25()
    assert refresh_count == 2, f"无待刷新时不应触发刷新，实际 {refresh_count} 次"
    print(f"   ✅ 无待刷新时不触发刷新")
    
    print("\n" + "=" * 60)
    print("✅ 所有测试通过！")
    print("=" * 60)
    
    # 清理测试数据
    import shutil
    if os.path.exists(test_db_path):
        shutil.rmtree(test_db_path)
        print(f"   已清理测试目录: {test_db_path}")


def test_performance_comparison():
    """性能对比测试（可选）"""
    print("\n" + "=" * 60)
    print("性能对比测试")
    print("=" * 60)
    
    from src.memory_manager import MemoryManager
    
    test_db_path = "./data/test_bm25_perf"
    mm = MemoryManager(db_path=test_db_path)
    
    # 模拟 15 轮对话
    num_memories = 15
    mm._bm25_refresh_threshold = 10
    
    refresh_count = 0
    original_refresh = mm._refresh_bm25
    
    def mock_refresh():
        nonlocal refresh_count
        refresh_count += 1
        original_refresh()
    
    mm._refresh_bm25 = mock_refresh
    
    print(f"\n保存 {num_memories} 条记忆（阈值={mm._bm25_refresh_threshold}）...")
    start_time = time.time()
    
    for i in range(num_memories):
        mm.save_user_memory(
            f"性能测试记忆 {i+1}: 用户偏好数据",
            metadata={"category": "preference", "test": True}
        )
    
    # 模拟程序退出时的强制刷新
    mm.force_refresh_bm25()
    
    elapsed = time.time() - start_time
    
    print(f"\n结果:")
    print(f"   - 保存记忆数: {num_memories}")
    print(f"   - BM25 刷新次数: {refresh_count}")
    print(f"   - 总耗时: {elapsed:.2f}s")
    print(f"   - 预期旧方案刷新次数: {num_memories}")
    print(f"   - 性能提升: {(1 - refresh_count/num_memories) * 100:.0f}%")
    
    # 清理
    import shutil
    if os.path.exists(test_db_path):
        shutil.rmtree(test_db_path)
        print(f"   已清理测试目录: {test_db_path}")


if __name__ == "__main__":
    test_lazy_refresh_mechanism()
    test_performance_comparison()
