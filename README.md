([简体中文](./README_zh.md)|English)
# openclaw-feishu-voice-skill
Add relevant Skills and processing scripts to OpenClaw so that it can automatically handle audio files sent via Lark by transcribing them into text and executing actions based on the transcribed text.

## Objective
During the process of using OpenClaw, I aim to send messages via voice by directly sending audio files, enabling OpenClaw to recognize them, and then convert them into text.

## Start Background FunASR for Speech Recognition
Use the previously built FunASR service to let OpenClaw call the FunASR service to convert audio to text. References: [Deploy Tongyi FunASR Service Locally for Speech Recognition](https://blog.csdn.net/tinygone/article/details/158586128?spm=1011.2415.3001.5331), [Deploy Tongyi FunASR Service Locally (Part 2)](https://blog.csdn.net/tinygone/article/details/158624294?spm=1011.2415.3001.5331)
Since I use a WebSocket service and have modified some server-side code, I have uploaded the latest code here: https://github.com/tinygone/FunASR.
Modifications:
- FunASR\runtime\python\websocket\funasr_wss_server.py: Mainly added logs for easier debugging; some code adjusted slightly.
- FunASR\runtime\python\websocket\funasr_wss_client.py: Mainly for debugging; not needed in production.

**Startup Preparation:**
```
conda create -n faenv python=3.12.9
conda activate faenv
git clone https://github.com/tinygone/FunASR.git
cd FunASR
conda activate faenv
pip3 install -e ./
# Install necessary components; ignore if already installed
# Install modelscope, which automatically downloads models
pip install modelscope
# Set environment variable: MODELSCOPE_CACHE="target_path"
# Install pytorch, specifically including torchaudio
pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu130
# Update transformers
pip install -U transformers

pip install tiktoken

pip install websockets
pip install pyaudio
# Install ffmpeg; it cannot be installed in one command, refer to previous materials for details
```

**Start the server:** To get the server running:
```
# You can replace host with your server's IP, but using 0.0.0.0 is recommended for use in Tailscale environments
python .\funasr_wss_server.py   --host 0.0.0.0 --port 10095
```

## Building the Recognition Workflow
When Feishu sends audio files, they are in OGG format. If sent directly to FunASR for recognition, it will not work. So first convert them to WAV format.
Add relevant Skills and processing scripts to OpenClaw. File address at: https://github.com/tinygone/openclaw-feishu-voice-skill
Includes 2 parts:
- voice-handle skill, needs to be placed in the `~/.openclaw/skills/` directory
- speech-to-text processing script, needs to be placed in the `~/.openclaw/middleware/` directory

Ensure the Agent can identify the Skill, and ensure the environment where OpenClaw is running has started.

If the Skill is not configured correctly, at this time you can send a voice message to OpenClaw's Agent via Feishu. You will receive a similar message like below, which shows receiving a 16-second audio file.
```
[media attached: /home/band/.openclaw/media/inbound/xxx.ogg (audio/ogg; codecs=opus) | /home/band/.openclaw/media/inbound/7c570ea2-4b9a-4105-a8c9-26d8e7047a24.ogg]  
To send an image back, prefer the message tool (media/path/filePath). If you must inline, use MEDIA:[https://example.com/image.jpg](https://example.com/image.jpg) (spaces ok, quote if needed) or a safe relative path like MEDIA:./image.jpg. Avoid absolute paths (MEDIA:/...) and ~ paths — they are blocked for security. Keep caption in the text body.

ou_xxx: {"file_key":"file_xxx","duration":16000}
```

If the Skill is already configured correctly, and both the client (computer where OpenClaw is running) and FunASR server are running correctly, you will receive similar messages like below.


Based on actual testing, GLM-5 model and Ollama locally running qwen3.5:9b both run normally.
