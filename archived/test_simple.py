"""
简单测试脚本 - 用于诊断输入问题
"""
print("测试脚本启动...")
import sys
sys.stdout.flush()

print("测试 1: 基本输入")
sys.stdout.flush()

try:
    user_input = input("请输入一些文字: ")
    print(f"你输入了: {user_input}")
except Exception as e:
    print(f"输入错误: {e}")
    import traceback
    traceback.print_exc()

print("\n测试 2: 导入模块")
sys.stdout.flush()

try:
    print("  正在导入 graph...")
    sys.stdout.flush()
    from graph import build_graph
    print("  导入成功")
    sys.stdout.flush()
    
    print("  正在构建工作流...")
    sys.stdout.flush()
    app = build_graph()
    print("  构建成功")
    sys.stdout.flush()
    
except Exception as e:
    print(f"  错误: {e}")
    import traceback
    traceback.print_exc()

print("\n测试 3: 再次输入")
sys.stdout.flush()

try:
    user_input2 = input("请再次输入: ")
    print(f"你输入了: {user_input2}")
except Exception as e:
    print(f"输入错误: {e}")
    import traceback
    traceback.print_exc()

print("\n测试完成")

