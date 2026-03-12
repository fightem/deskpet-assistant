from PyQt6.QtCore import QThread, pyqtSignal
from RealtimeSTT import AudioToTextRecorder
import os

os.environ["HF_HUB_OFFLINE"] = "1"

class VoiceAssistantThread(QThread):
    # 🟢 核心魔法：PyQt的信号机制，不卡UI
    text_recognized = pyqtSignal(str)

    def __init__(self):
        # 🟢 注意：这里的 __init__ 绝对不需要传 callback 参数
        super().__init__()
        self.is_voice_mode_on = False
        self.recorder = None

    def run(self):
        """后台死循环监听"""
        print("⏳ 正在调用 4090 显卡加载满血版语音引擎 (large-v2)...")
        self.recorder = AudioToTextRecorder(
            model="large-v2",  # 4090 专属大模型，零错别字
            language="zh",
            device="cuda",  # 强制走 GPU 加速
            compute_type="float16",  # 半精度极速推理
            silero_use_onnx=True,
            enable_realtime_transcription=True,
            silero_sensitivity=0.3,
            initial_prompt="你好，露米娅。再见，露米娅。请给我读一下这篇关于计算机视觉和三维点云的论文。文献，学术，实例分割，目标检测，总结核心内容。"
        )
        print("✅ 后台语音引擎就绪，随时待命！")

        while True:
            self.recorder.text(self.process_text)

    def process_text(self, text):
        text = text.strip()
        if not text:
            return

        if self.is_voice_mode_on:
            print(f"🎙️ [耳朵听到]: {text}")
            self.text_recognized.emit(text)  # 把文字发射给主界面

    def toggle_mode(self):
        self.is_voice_mode_on = not self.is_voice_mode_on
        return self.is_voice_mode_on