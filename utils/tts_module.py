import requests
import pyaudio

# ================= ⚠️ 必填配置区 ⚠️ =================
API_URL = "http://117.50.81.89:9880/tts"
REF_AUDIO_PATH = "/workspace/GPT-SoVITS/cankao/原神语音神里绫华没什么-External9_290_1_爱给网_aigei_com.mp3.reformatted_vocals.mp3_0000191680_0000344320 (1).wav"
PROMPT_TEXT = "九条沙罗小姐刚才说这场比赛让她受教良多。"
PROMPT_LANG = "zh"
# =====================================================

# 🟢 [新增] 全局打断标志位
_stop_flag = False


def stop_speaking():
    """🟢 [新增] 触发打断，让嘴巴立刻闭上"""
    global _stop_flag
    _stop_flag = True


def speak(text_to_speak):
    global _stop_flag
    _stop_flag = False  # 🟢 每次开口前，重置打断标志

    print(f"✨ [云端嘴巴开始流式推理]: {text_to_speak[:20]}...")

    payload = {
        "text": text_to_speak,
        "text_lang": "zh",
        "ref_audio_path": REF_AUDIO_PATH,
        "prompt_text": PROMPT_TEXT,
        "prompt_lang": PROMPT_LANG,
        "media_type": "raw",
        "streaming_mode": True
    }

    try:
        response = requests.post(API_URL, json=payload, stream=True)

        if response.status_code == 200:
            p = pyaudio.PyAudio()
            stream = p.open(format=pyaudio.paInt16,
                            channels=1,
                            rate=32000,
                            output=True)

            # 🟢 [新增核心逻辑]：像水管一样接水，一旦发现刹车被按下，立刻关水龙头
            for chunk in response.iter_content(chunk_size=4096):
                if _stop_flag:
                    print("🛑 [系统提示]: 主人发话了，立刻停止播报！")
                    break  # 跳出循环，强行切断声音

                if chunk:
                    stream.write(chunk)

            stream.stop_stream()
            stream.close()
            p.terminate()
        else:
            print(f"❌ 云端合成失败: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ 无法连接到云端 API: {e}")