import pyaudio
import wave
import logging
from PyQt5.QtCore import QObject, pyqtSignal, QThread
from .config import AppConfig
from utils.audio_utils import convert_audio_format
from .xf_iat_service import audio_to_text
import os

# 设置日志
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class AudioRecorder(QThread):
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, config):
        super().__init__()
        self.config = config
        self.is_recording = False
        self.frames = []
        self.stream = None
        self.audio = None

        # 初始化音频系统
        try:
            test_audio = pyaudio.PyAudio()
            default_device = test_audio.get_default_input_device_info()
            self.input_device_index = default_device["index"]
            test_audio.terminate()
            logger.debug(f"默认输入设备索引: {self.input_device_index}")
        except Exception as e:
            logger.error(f"音频系统初始化失败: {e}")
            self.input_device_index = None

    def run(self):
        if self.input_device_index is None:
            self.error.emit("未找到有效的音频输入设备")
            return

        try:
            self.audio = pyaudio.PyAudio()
            # 验证采样率
            device_info = self.audio.get_device_info_by_index(self.input_device_index)
            supported_rates = [int(device_info["defaultSampleRate"])]

            if self.config.AUDIO_RATE not in supported_rates:
                logger.warning(
                    f"采样率 {self.config.AUDIO_RATE} 可能不被支持，使用设备默认值"
                )
                self.config.AUDIO_RATE = int(device_info["defaultSampleRate"])

            self.stream = self.audio.open(
                format=self.config.AUDIO_FORMAT,
                channels=self.config.AUDIO_CHANNELS,
                rate=self.config.AUDIO_RATE,
                input=True,
                input_device_index=self.input_device_index,
                frames_per_buffer=self.config.AUDIO_CHUNK,
            )

            logger.debug("开始录音")
            self.frames = []
            self.is_recording = True

            while self.is_recording:
                try:
                    data = self.stream.read(
                        self.config.AUDIO_CHUNK, exception_on_overflow=False
                    )
                    self.frames.append(data)
                except Exception as e:
                    logger.error(f"录音过程错误: {e}")
                    break

            logger.debug("录音结束")
            self._cleanup()
            self._save_audio()
            self.finished.emit()

        except Exception as e:
            logger.error(f"录音线程错误: {e}")
            self.error.emit(str(e))
            self._cleanup()

    def stop(self):
        """停止录音"""
        logger.debug("正在停止录音")
        self.is_recording = False
        self.wait(1000)  # 等待最多1秒钟确保线程结束

    def _cleanup(self):
        """清理音频资源"""
        logger.debug("清理音频资源")
        if hasattr(self, "stream") and self.stream:
            try:
                self.stream.stop_stream()
                self.stream.close()
            except Exception as e:
                logger.error(f"关闭音频流错误: {e}")
            self.stream = None

        if hasattr(self, "audio") and self.audio:
            try:
                self.audio.terminate()
            except Exception as e:
                logger.error(f"终止音频系统错误: {e}")
            self.audio = None

    def _save_audio(self):
        """保存录音文件"""
        if not self.frames:
            logger.warning("没有录音数据可保存")
            return

        try:
            # 保存原始录音
            temp_file = str(self.config.AUDIO_FILE) + ".temp"
            with wave.open(temp_file, "wb") as wf:
                wf.setnchannels(self.config.AUDIO_CHANNELS)
                wf.setsampwidth(pyaudio.get_sample_size(self.config.AUDIO_FORMAT))
                wf.setframerate(self.config.AUDIO_RATE)
                wf.writeframes(b"".join(self.frames))

            # 转换为讯飞API所需格式
            if not convert_audio_format(temp_file, str(self.config.AUDIO_FILE)):
                raise RuntimeError("音频格式转换失败")

            # 清理临时文件
            os.remove(temp_file)

            logger.debug(f"录音文件已保存并转换: {self.config.AUDIO_FILE}")

        except Exception as e:
            logger.error(f"保存音频文件失败: {e}")
            raise

    def __del__(self):
        """析构函数，确保资源被释放"""
        self._cleanup()


class AudioManager(QObject):
    recording_status_changed = pyqtSignal(bool)
    text_converted = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.recorder = AudioRecorder(AppConfig)
        self.recorder.finished.connect(self._on_recording_finished)
        self.recorder.error.connect(self._on_error)

    def start_recording(self):
        if not self.recorder.isRunning():
            self.recorder.start()
            self.recording_status_changed.emit(True)

    def stop_recording(self):
        """确保完全停止录音并进行转换"""
        if self.recorder.isRunning():
            self.recorder.stop()
            self.recording_status_changed.emit(False)
            # 强制等待资源释放
            QThread.msleep(500)

    def _on_recording_finished(self):
        self.recording_status_changed.emit(False)
        try:
            text = audio_to_text()
            if text:
                self.text_converted.emit(text)  # 发送转换结果信号
            else:
                self.error_occurred.emit("语音转换失败：未获取到文本")
        except Exception as e:
            logger.error(f"语音转文字失败: {e}")
            self.error_occurred.emit(f"语音转换失败: {str(e)}")

    def _on_error(self, error_message):
        self.error_occurred.emit(error_message)
