import sys
import os
import asyncio
import websockets
import json
import struct
import ssl
import tempfile
import soundfile as sf
import numpy as np

HAS_SOUNDFILE = True

FUNASR_URL = "wss://127.0.0.1:10095"
FUNASR_MODE = "2pass"  # 2pass 模式：offline + online 结合，识别更完整


def convert_to_wav(input_path: str, target_sr: int = 16000) -> str:
    """
    转换音频文件为 WAV 格式 (16kHz, mono, 16-bit PCM)
    
    Args:
        input_path: 输入音频文件路径（OGG/WAV/MP3 等）
        target_sr: 目标采样率（默认 16000）
    
    Returns:
        str: 转换后的 WAV 文件路径
    """
    # 读取音频
    audio, sr = sf.read(input_path, dtype='float32')
    
    # 转换为单声道
    if len(audio.shape) > 1:
        audio = audio.mean(axis=1)
    
    # 重采样（简单方法）
    if sr != target_sr:
        ratio = sr / target_sr
        audio = audio[::int(ratio)]
    
    # 保存为临时 WAV 文件
    wav_path = tempfile.mktemp(suffix='.wav')
    sf.write(wav_path, audio, target_sr, subtype='PCM_16')
    
    return wav_path


def extract_pcm_from_wav(wav_path: str) -> bytes:
    """
    从 WAV 文件提取 PCM 数据
    
    Args:
        wav_path: WAV 文件路径
    
    Returns:
        bytes: PCM 音频数据
    """
    with open(wav_path, "rb") as f:
        data = f.read()
    
    # 找到 "data" chunk
    idx = 12
    while idx < len(data):
        chunk_id = data[idx:idx+4]
        chunk_size = struct.unpack('<I', data[idx+4:idx+8])[0]
        if chunk_id == b'data':
            return data[idx+8:idx+8+chunk_size]
        idx += 8 + chunk_size
    
    raise ValueError("无效的 WAV 文件：找不到 data chunk")


async def _recognize_async(audio_path: str, timeout: int = 120) -> str:
    """
    异步识别音频文件
    
    Args:
        audio_path: 音频文件路径
        timeout: 超时时间（秒）
    
    Returns:
        str: 识别结果文本
    """
    # 1. 转换音频格式
    wav_path = convert_to_wav(audio_path)
    
    try:
        # 2. 提取 PCM 数据
        pcm_data = extract_pcm_from_wav(wav_path)
        
        # 3. SSL 上下文（禁用证书验证）
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        # 4. 连接到 FunASR
        async with websockets.connect(
            FUNASR_URL,
            subprotocols=["binary"],
            ping_interval=None,
            ssl=ssl_context,
            close_timeout=10
        ) as ws:
            # 5. 发送配置（对标官方客户端）
            config = {
                "mode": FUNASR_MODE,
                "chunk_size": [5, 10, 5],
                "encoder_chunk_look_back": 4,
                "decoder_chunk_look_back": 0,
                "chunk_interval": 10,
                "audio_fs": 16000,
                "wav_name": os.path.basename(audio_path),
                "wav_format": "pcm",
                "is_speaking": True,
                "hotwords": "",
                "itn": True
            }
            await ws.send(json.dumps(config))
            
            # 6. 分块发送音频（对标官方客户端）
            # 官方 stride 计算: stride = int(60 * chunk_size[1] / chunk_interval / 1000 * sample_rate * 2)
            # = 60 * 10 / 10 / 1000 * 16000 * 2 = 1920 bytes (60ms)
            sample_rate = 16000
            chunk_size_middle = 10  # chunk_size[1] from [5, 10, 5]
            chunk_interval = 10
            stride = int(60 * chunk_size_middle / chunk_interval / 1000 * sample_rate * 2)
            chunk_num = (len(pcm_data) + stride - 1) // stride
            
            print(f"[DEBUG] 音频信息: {len(pcm_data)} bytes, stride={stride}, {chunk_num} chunks, {len(pcm_data)/32000:.2f}s")
            
            for i in range(chunk_num):
                beg = i * stride
                chunk = pcm_data[beg:beg+stride]
                await ws.send(chunk)
                
                # 2pass 模式：按实时节奏发送（对标官方）
                # sleep_duration = 60 * chunk_size[1] / chunk_interval / 1000
                # = 60 * 10 / 10 / 1000 = 0.06秒
                await asyncio.sleep(0.06)
            
            # 7. 发送结束信号
            print(f"[DEBUG] 发送 is_speaking: False")
            await ws.send(json.dumps({"is_speaking": False}))
            
            # 8. 接收结果（2pass 模式）
            # 2pass 模式正确逻辑（对标官方）：
            # - online 持续累加（正在识别的临时部分）
            # - offline 累加时清空 online（因为被替换了）
            # - 后续的 online 会继续累加（新的临时部分）
            # - 不要收到 is_final 就立即退出，等待足够时间
            # - 最终结果 = offline + online
            online_text = ""
            offline_text = ""
            last_offline_time = None
            
            # 增加等待时间，确保收到完整结果
            start_time = asyncio.get_event_loop().time()
            while (asyncio.get_event_loop().time() - start_time) < timeout:
                try:
                    result = await asyncio.wait_for(ws.recv(), timeout=5.0)
                    data = json.loads(result)
                    
                    mode = data.get("mode", "")
                    text = data.get("text", "")
                    is_final = data.get("is_final", False)
                    
                    if text:
                        print(f"[DEBUG] mode={mode}, text={text}")
                    
                    # 累加 online 结果（正在识别的临时部分）
                    if mode in ["online", "2pass-online"] and text:
                        online_text += text
                    
                    # 累加 offline 结果（已经识别完成的部分）
                    # offline 结果会替换对应的 online 结果
                    if mode in ["offline", "2pass-offline"] and text:
                        offline_text += text
                        print(f"[DEBUG] offline 累加后: {offline_text}")
                        # 清空 online 结果，因为已经被 offline 替换
                        online_text = ""
                        last_offline_time = asyncio.get_event_loop().time()
                    
                    # 检查是否完成（不要立即退出，等待足够时间）
                    if is_final:
                        print(f"[DEBUG] 收到 is_final=True，继续等待后续消息...")
                        # 不要立即退出，继续等待后续的 online 消息
                        # 等待 3 秒没有新消息才退出
                        await asyncio.sleep(3)
                        
                except asyncio.TimeoutError:
                    # 超时后如果有结果就返回
                    if offline_text or online_text:
                        print(f"[DEBUG] 超时，返回已有结果")
                        break
                    continue
            
            # 最终结果 = offline + online
            result = offline_text + online_text
            print(f"[DEBUG] 最终结果: offline='{offline_text}' + online='{online_text}'")
            return result
            
    finally:
        # 清理临时文件
        if os.path.exists(wav_path):
            os.unlink(wav_path)


def recognize_voice(audio_path: str, timeout: int = 120) -> str:
    """
    识别语音文件
    
    Args:
        audio_path: 音频文件路径（支持 OGG/WAV/MP3 等）
        timeout: 超时时间（秒）
    
    Returns:
        str: 识别结果文本
    
    Example:
        >>> text = recognize_voice("/path/to/voice.ogg")
        >>> print(text)
        "你好，这是一段测试语音"
    """
    # 检查文件是否存在
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"音频文件不存在: {audio_path}")
    
    # 检查 soundfile
    if not HAS_SOUNDFILE:
        raise RuntimeError("soundfile 未安装，请运行: pip install soundfile")
    
    # 运行异步识别
    return asyncio.run(_recognize_async(audio_path, timeout))


# 测试入口
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("用法: python funasr_recognizer.py <音频文件>")
        print("示例: python funasr_recognizer.py voice.ogg")
        sys.exit(1)
    
    audio_file = sys.argv[1]
    
    print(f"正在识别: {audio_file}")
    print("-" * 60)
    
    try:
        result = recognize_voice(audio_file)
        print(f"\n✅ 识别结果:\n{result}")
    except Exception as e:
        print(f"❌ 识别失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
