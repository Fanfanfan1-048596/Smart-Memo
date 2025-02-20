from pathlib import Path
import os
import pyaudio
import logging


class AppConfig:
    # 应用基础配置
    APP_NAME = "SmartMemo"
    APP_DIR = Path.home() / ".SmartMemo"
    BASE_DIR = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    # 文件配置
    DATA_FILE = APP_DIR / "data.xlsx"
    AUDIO_FILE = APP_DIR / "audio.wav"
    ICON_FILE = BASE_DIR / "assets" / "cover.png"

    # 音频配置
    AUDIO_CHANNELS = 1  # 录音通道数
    AUDIO_RATE = 44100  # 录音采样率
    AUDIO_CHUNK = 1024  # 缓冲区大小
    AUDIO_FORMAT = pyaudio.paInt16  # 采样格式

    # 科大讯飞配置
    XF_APPID = os.getenv('XF_APPID')
    XF_API_SECRET = os.getenv('XF_API_SECRET')
    XF_API_KEY = os.getenv('XF_API_KEY')

    # 讯飞API音频要求
    XF_AUDIO_RATE = 16000  # 采样率
    XF_AUDIO_CHANNELS = 1  # 声道数
    XF_AUDIO_WIDTH = 2  # 采样位深（字节）= 16位/8
    XF_FRAME_SIZE = 8000  # 每帧大小 = 0.5秒 * 16000Hz
    XF_INTERVAL = 0.04  # 发送间隔
    XF_TIMEOUT = 30  # 识别超时时间
    XF_RESPONSE_TIMEOUT = 5  # 首次响应超时时间

    # 提醒配置
    REMINDER_CHECK_INTERVAL = 60000  # 检查间隔（毫秒）
    REMINDER_DURATION = 5000  # 提醒显示时长（毫秒）
    REMINDER_TIMES = [30, 5]  # 提醒时间点（分钟
    NOTIFICATION_SOUND = BASE_DIR / "assets" / "notification.wav"  # 提醒音效文件路径
    NOTIFICATION_VOLUME = 1.0  # 音量大小(0.0-1.0)

    # TTS配置
    TTS_OUTPUT_FILE = APP_DIR / "temp" / "tts_output.wav"  # TTS输出文件
    TTS_VOICE = "xiaoyan"  # TTS发音人
    TTS_SPEED = 50  # 语速，取值范围：[0,100]
    TTS_VOLUME = 50  # 音量，取值范围：[0,100]
    TTS_PITCH = 50  # 音高，取值范围：[0,100]
    TTS_SAMPLE_RATE = 16000  # 采样率
    TTS_CHANNELS = 1  # 声道数
    TTS_SAMPLE_WIDTH = 2  # 采样位深（字节）= 16位/8

    # 任务类型配置
    TASK_TYPES = {
        "ONCE": "一次性",
        "DAILY": "每天",
        "WEEKLY": "每周",
        "MONTHLY": "每月",
    }

    # 日志配置
    LOG_LEVEL = logging.INFO
    LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_FILE = APP_DIR / "app.log"

    @property
    def LOG_FILE(self):
        return self.APP_DIR / "app.log"
