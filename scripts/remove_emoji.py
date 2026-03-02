#!/usr/bin/env python3
"""
批量移除 Python 文件中 print 语句里的 emoji
"""

import os
import re

# 项目根目录
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src_dir = os.path.join(project_root, "src")

# emoji 到文本的替换映射
emoji_replacements = {
    "✅ ": "",
    "❌ ": "[ERROR] ",
    "🔧 ": "",
    "📅 ": "",
    "🏷️ ": "",
    "✨ ": "",
    "📝 ": "",
    "🔍 ": "",
    "📊 ": "",
    "📦 ": "",
    "🔄 ": "",
    "💾 ": "",
    "⚠️ ": "[WARN] ",
    "⚠️  ": "[WARN] ",
    "🎵 ": "",
    "📰 ": "",
    "🗑️ ": "",
    "🗑️  ": "",
    "💡 ": "",
    "🎤 ": "",
    "⚙️ ": "",
    "⚙️  ": "",
    "🛡️ ": "",
    "🛡️  ": "",
    "🔇 ": "",
    "💚 ": "",
    "🤖 ": "",
    "⚡ ": "",
    "🔬 ": "",
    "📥 ": "",
    "📄 ": "",
    "⭐ ": "",
    "📂 ": "",
    "🎬 ": "",
    "🔗 ": "",
    "📋 ": "",
    "🧠 ": "",
    "⏱️ ": "",
    "🧪 ": "",
    "🔊 ": "",
    "📍 ": "",
    "🎯 ": "",
    "💤 ": "",
    "🔌 ": "",
    "📡 ": "",
    "🌐 ": "",
    "🚀 ": "",
    "💬 ": "",
    "📑 ": "",
    "🌤️ ": "",
    "🌬️ ": "",
    "👤 ": "",
    # 带空格的变体
    " ✅": "",
    " ❌": "",
    # 无空格版本
    "✅": "",
    "❌": "[ERROR]",
    "🔧": "",
    "📅": "",
    "🏷️": "",
    "🏷": "",
    "✨": "",
    "📝": "",
    "🔍": "",
    "📊": "",
    "📦": "",
    "🔄": "",
    "💾": "",
    "⚠️": "[WARN]",
    "⚠": "[WARN]",
    "🎵": "",
    "📰": "",
    "🗑️": "",
    "🗑": "",
    "💡": "",
    "🎤": "",
    "⚙️": "",
    "⚙": "",
    "🛡️": "",
    "🛡": "",
    "🔇": "",
    "💚": "",
    "🤖": "",
    "⚡": "",
    "🔬": "",
    "📥": "",
    "📄": "",
    "⭐": "",
    "📂": "",
    "🎬": "",
    "🔗": "",
    "📋": "",
    "🧠": "",
    "⏱️": "",
    "⏱": "",
    "🧪": "",
    "🔊": "",
    "📍": "",
    "🎯": "",
    "💤": "",
    "🔌": "",
    "📡": "",
    "🌐": "",
    "🚀": "",
    "💬": "",
    "📑": "",
    "🌤️": "",
    "🌤": "",
    "🌬️": "",
    "🌬": "",
    "👤": "",
}

# 要处理的文件
files_to_process = [
    "memory_manager.py",
    "nodes.py",
    "pattern_scanner.py",
    "schedule_manager.py",
    "tools.py",
    "main.py",
    "mcp_manager.py",
    "model_manager.py",
    "mcp_setup.py",
    "email_providers.py",
    "state_manager.py",
    "intimacy_manager.py",
    # entity_registry.py 已手动处理
]


def remove_emoji_from_file(filepath):
    """从单个文件中移除 emoji"""
    if not os.path.exists(filepath):
        return 0
    
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    
    original_content = content
    
    # 应用替换
    for emoji, replacement in emoji_replacements.items():
        content = content.replace(emoji, replacement)
    
    # 清理多余空格（替换后可能产生的双空格）
    content = re.sub(r'print\(f?"   \[', 'print(f"[', content)
    content = re.sub(r'print\(f?"  \[', 'print(f"[', content)
    
    if content != original_content:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        # 计算修改的行数
        orig_lines = original_content.split("\n")
        new_lines = content.split("\n")
        changed = sum(1 for a, b in zip(orig_lines, new_lines) if a != b)
        return changed
    
    return 0


def main():
    print("=" * 60)
    print("批量移除 Python 文件中的 emoji")
    print("=" * 60)
    
    total_changes = 0
    
    for filename in files_to_process:
        filepath = os.path.join(src_dir, filename)
        changes = remove_emoji_from_file(filepath)
        if changes > 0:
            print(f"  {filename}: 修改了 {changes} 行")
            total_changes += changes
        else:
            if os.path.exists(filepath):
                print(f"  {filename}: 无变化")
            else:
                print(f"  {filename}: 文件不存在")
    
    print("=" * 60)
    print(f"总计修改 {total_changes} 行")
    print("=" * 60)


if __name__ == "__main__":
    main()
