#!/usr/bin/env python3
"""
FunASR 语音识别命令行工具
供所有 agent 通过 exec 工具调用

用法:
    python3 funasr_recognizer.py <音频文件> [超时秒数]

返回:
    识别文本（纯文本，无额外输出）

示例:
    python3 funasr_recognizer.py /path/to/voice.ogg
    python3 funasr_recognizer.py /path/to/voice.ogg 60
"""

import sys
import os

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from funasr_recognizer import recognize_voice


def main():
    if len(sys.argv) < 2:
        print("用法: python3 funasr_recognizer.py <音频文件> [超时秒数]", file=sys.stderr)
        print("示例: python3 funasr_recognizer.py voice.ogg 60", file=sys.stderr)
        sys.exit(1)
    
    audio_file = sys.argv[1]
    timeout = int(sys.argv[2]) if len(sys.argv) > 2 else 120
    
    # 检查文件是否存在
    if not os.path.exists(audio_file):
        print(f"错误: 文件不存在: {audio_file}", file=sys.stderr)
        sys.exit(1)
    
    try:
        # 识别音频
        result = recognize_voice(audio_file, timeout)
        
        # 只输出识别结果（纯文本）
        print(result)
        
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
