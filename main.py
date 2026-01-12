"""
智能台灯系统主程序 - OODA架构
运行方式：python main.py
按 Ctrl+C 退出程序
"""
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 导入并运行主程序
from src.main import main

if __name__ == "__main__":
    main()

