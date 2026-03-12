import os
from RealtimeSTT import AudioToTextRecorder
from tts_module import speak  # 💡 直接从刚才写的模块里导入 speak 函数

os.environ["HF_HUB_OFFLINE"] = "1"


def start_voice_assistant():
    is_awake = False

    def on_recording_start():
        print("\n[🎙️ 检测到声音，正在录音...] ", end="", flush=True)

    def on_recording_stop():
        print("[⏹️ 声音停止，正在识别]")

    def process_text(text):
        nonlocal is_awake

        text = text.strip().lower()
        if not text:
            return

        name_list = ["露米", "卢米", "路米", "lumia", "路迷", "努力", "利比", "糯米"]
        has_name = any(name in text for name in name_list)

        # ------------------------------------------
        # 💤 状态 A：睡眠中
        # ------------------------------------------
        if not is_awake:
            if ("你好" in text or "妳好" in text or "您好" in text or "一毫" in text) and has_name:
                is_awake = True
                print("\n✨ [系统提示]: 🟢 已唤醒，开始持续监听")
                speak("吾在呢！有什么吩咐吗？")  # 👈 直接调用云端嘴巴
            else:
                print(f"  🔇 [睡眠中，忽略杂音]: {text}")

        # ------------------------------------------
        # 🌟 状态 B：清醒中
        # ------------------------------------------
        else:
            if ("再见" in text or "再見" in text or "拜拜" in text) and has_name:
                is_awake = False
                print("\n💤 [系统提示]: 🔴 已休眠")
                speak("那吾先休息啦，有事再叫吾。")  # 👈 直接调用云端嘴巴
            else:
                print(f"💬 [收到主人指令]: {text}")

                # 暂时使用复述功能。未来只需要把 text 丢给 LLM，再把 LLM 的回答丢给 speak() 即可
                speak(f"收到指令：{text}")

    print("⏳ 正在初始化本地耳朵 (STT)，请耐心等待...")

    recorder = AudioToTextRecorder(
        model="base",
        language="zh",
        silero_use_onnx=True,
        enable_realtime_transcription=True,
        silero_sensitivity=0.4,
        compute_type="default",
        initial_prompt="你好，露米娅。再见，露米娅。主人，有什么吩咐？",
        on_recording_start=on_recording_start,
        on_recording_stop=on_recording_stop
    )

    print("\n✅ 初始化完成！本地耳朵与云端嘴巴已完美组合。")
    print("=====================================================")
    print("👉 运行指南：说「你好，露米娅」唤醒，说「再见，露米娅」休眠")
    print("=====================================================\n")

    while True:
        recorder.text(process_text)


if __name__ == '__main__':
    # 只需要运行这个主文件即可
    start_voice_assistant()