---
name: voice-handler
version: 1.0.3
description: "MUST USE when receiving .ogg audio files, audio/ogg MIME type, or [media attached]. Uses FunASR for speech recognition. DO NOT try to install Whisper."
---

# Voice Handler Skill

自动处理飞书语音消息。

## 触发条件

当消息中包含以下任一项时自动激活：
- `<media:audio>`
- `[Audio]`
- `.ogg` 文件路径
- `audio/ogg` MIME 类型
- `[media attached: .../inbound/*.ogg]`

## 处理流程

### 步骤 1：提取音频文件路径

从消息中找到音频文件路径，格式通常为：
```
~/.openclaw/media/inbound/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx.ogg
```

### 步骤 2：调用语音识别

使用以下命令识别语音：

```bash
source ~/anaconda3/etc/profile.d/conda.sh && conda activate faenv && \
python3 ~/.openclaw/middleware/speech-to-text/funasr_recognizer_cli.py \
<音频文件路径>
```

**或者使用更简单的脚本：**

```bash
~/.openclaw/middleware/speech-to-text/voice-message-handler.sh \
<音频文件路径>
```

### 步骤 3：处理识别结果

- **识别成功**：将识别文本作为用户的实际输入内容，继续处理用户的请求
- **识别失败**：回复用户"语音识别失败，请重试或发送文字消息"

## 重要规则

### ✅ 必须遵守

1. **自动执行**：收到语音消息时立即识别，不要询问用户是否需要识别
2. **静默处理**：不要说"我识别到你说..."，直接按照识别内容回复
3. **失败处理**：识别失败时友好提示，不要报错堆栈信息

### ❌ 禁止行为

1. 不要问"需要我识别这条语音吗？"
2. 不要说"我收到了一条语音消息"
3. 不要输出调试信息或错误堆栈

## 示例

### 示例 1：简单的语音消息

**收到的消息：**
```
[media attached: ~/.openclaw/media/inbound/abc123.ogg (audio/ogg; codecs=opus)]
```

**处理流程：**
1. 提取路径：`~/.openclaw/media/inbound/abc123.ogg`
2. 执行识别：
   ```bash
   source ~/anaconda3/etc/profile.d/conda.sh && conda activate faenv && \
   python3 ~/.openclaw/middleware/speech-to-text/funasr_recognizer_cli.py \
   ~/.openclaw/media/inbound/abc123.ogg
   ```
3. 识别结果：`"今天天气怎么样"`
4. 回复：按照用户问"今天天气怎么样"来回答

### 示例 2：包含文字的语音消息

**收到的消息：**
```
请帮我处理一下
[Audio]
~/.openclaw/media/inbound/def456.ogg
```

**处理流程：**
1. 提取路径：`~/.openclaw/media/inbound/def456.ogg`
2. 执行识别
3. 识别结果：`"创建一个新项目"`
4. 回复：按照"请帮我处理一下，创建一个新项目"来回答

## 技术细节

### FunASR 配置

- **服务地址**：`wss://127.0.0.1:10095`
- **识别模式**：2pass（在线 + 离线）
- **音频格式**：OGG (Opus) → WAV (16kHz, mono, 16-bit)
- **超时时间**：120 秒

### Python 环境

- **Conda 环境**：`faenv`
- **依赖库**：websockets, soundfile

### 故障排除

**问题：识别失败**
- 检查 FunASR 服务是否运行：`nc -zv 127.0.0.1 10095`
- 检查音频文件是否存在
- 检查 conda 环境是否正确

**问题：识别不完整**
- 增加超时时间
- 检查网络连接
- 检查音频质量

---

**创建时间**: 2026-03-14
**版本**: 1.0.0
