#!/bin/bash
# 语音消息自动识别脚本
# 
# 用法：voice-message-handler.sh <音频文件路径>
# 
# 功能：
# 1. 自动识别语音消息
# 2. 输出识别文本
# 3. 如果失败，输出错误信息

set -e

AUDIO_PATH="$1"

if [ -z "$AUDIO_PATH" ]; then
    echo "❌ 错误：缺少音频文件路径"
    exit 1
fi

if [ ! -f "$AUDIO_PATH" ]; then
    echo "❌ 错误：文件不存在: $AUDIO_PATH"
    exit 1
fi

# 激活 conda 环境并识别
source ~/anaconda3/etc/profile.d/conda.sh
conda activate faenv

# 调用识别脚本
python3 ~/.openclaw/middleware/speech-to-text/funasr_recognizer_cli.py "$AUDIO_PATH" 2>/dev/null

# 检查退出码
if [ $? -eq 0 ]; then
    exit 0
else
    echo "❌ 语音识别失败"
    exit 1
fi
