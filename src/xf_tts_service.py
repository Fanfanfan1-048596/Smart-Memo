import websocket
import datetime
import hashlib
import base64
import hmac
import json
from urllib.parse import urlencode
import time
import ssl
from wsgiref.handlers import format_date_time
from datetime import datetime
from time import mktime
import _thread as thread
import os
import logging
import pygame
import wave
import struct
from .config import AppConfig

logger = logging.getLogger(__name__)


class TTSService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TTSService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        try:
            # 创建临时文件目录
            os.makedirs(os.path.dirname(AppConfig.TTS_OUTPUT_FILE), exist_ok=True)
            pygame.mixer.init()
            self._initialized = True
            logger.debug("TTS服务初始化成功")
        except Exception as e:
            logger.error(f"TTS服务初始化失败: {e}", exc_info=True)
            self._initialized = False

    def text_to_speech(self, text):
        """将文本转换为语音并播放"""
        try:
            if not self._initialized:
                logger.error("TTS服务未正确初始化")
                return False

            # 创建WebSocket参数
            ws_param = WsParam(
                AppConfig.XF_APPID, AppConfig.XF_API_KEY, AppConfig.XF_API_SECRET, text
            )

            # 建立WebSocket连接
            websocket.enableTrace(False)
            ws_url = ws_param.create_url()
            ws = websocket.WebSocketApp(
                ws_url,
                on_message=self._on_message,
                on_error=self._on_error,
                on_close=self._on_close,
            )
            ws.on_open = lambda ws: self._on_open(ws, ws_param)

            # 运行WebSocket连接
            ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})

            # 播放生成的音频
            return self._play_audio()

        except Exception as e:
            logger.error(f"TTS转换失败: {e}", exc_info=True)
            return False

    def _on_message(self, ws, message, *args):
        """处理WebSocket消息回调"""
        try:
            message = json.loads(message)
            code = message["code"]
            if code != 0:
                logger.error(f"TTS API返回错误: {message['message']}, code: {code}")
                return

            audio = base64.b64decode(message["data"]["audio"])
            status = message["data"]["status"]

            # 写入临时PCM文件
            temp_pcm = AppConfig.APP_DIR / "temp" / "temp.pcm"
            with open(temp_pcm, "ab") as f:
                f.write(audio)

            # 如果是最后一帧，转换为WAV格式
            if status == 2:
                self._convert_to_wav(temp_pcm, AppConfig.TTS_OUTPUT_FILE)
                ws.close()

        except Exception as e:
            logger.error(f"处理TTS消息失败: {e}", exc_info=True)

    def _on_error(self, ws, error, *args):
        """处理WebSocket错误回调"""
        logger.error(f"TTS WebSocket错误: {error}")

    def _on_close(self, ws, close_status_code, close_msg, *args):
        """处理WebSocket关闭回调"""
        logger.debug("TTS WebSocket连接关闭")

    def _on_open(self, ws, ws_param):
        """处理WebSocket连接建立回调"""

        def run(*args):
            try:
                # 清除之前的音频文件
                if os.path.exists(AppConfig.TTS_OUTPUT_FILE):
                    os.remove(AppConfig.TTS_OUTPUT_FILE)

                data = {
                    "common": ws_param.CommonArgs,
                    "business": ws_param.BusinessArgs,
                    "data": ws_param.Data,
                }
                ws.send(json.dumps(data))
            except Exception as e:
                logger.error(f"发送TTS请求失败: {e}", exc_info=True)
                ws.close()

        thread.start_new_thread(run, ())

    def _convert_to_wav(self, pcm_file, wav_file):
        """将PCM文件转换为WAV格式"""
        try:
            with open(pcm_file, "rb") as pcmf:
                pcm_data = pcmf.read()

            with wave.open(str(wav_file), "wb") as wavf:
                wavf.setnchannels(AppConfig.TTS_CHANNELS)
                wavf.setsampwidth(AppConfig.TTS_SAMPLE_WIDTH)
                wavf.setframerate(AppConfig.TTS_SAMPLE_RATE)
                wavf.writeframes(pcm_data)

            # 删除临时PCM文件
            os.remove(pcm_file)

        except Exception as e:
            logger.error(f"PCM转WAV失败: {e}", exc_info=True)

    def _play_audio(self):
        """播放音频文件"""
        try:
            if not os.path.exists(AppConfig.TTS_OUTPUT_FILE):
                logger.error("音频文件不存在")
                return False

            try:
                # 初始化pygame音频
                pygame.mixer.quit()
                pygame.mixer.init(
                    frequency=AppConfig.TTS_SAMPLE_RATE,
                    channels=AppConfig.TTS_CHANNELS,
                    size=-16,
                )
                pygame.mixer.music.load(str(AppConfig.TTS_OUTPUT_FILE))
                pygame.mixer.music.play()

                # 等待播放完成
                while pygame.mixer.music.get_busy():
                    pygame.time.Clock().tick(10)

                return True

            except pygame.error as pe:
                logger.error(f"PyGame错误: {pe}")
                # 使用系统命令播放
                os.system(f"aplay {AppConfig.TTS_OUTPUT_FILE}")
                return True

        except Exception as e:
            logger.error(f"播放音频失败: {e}", exc_info=True)
            return False


class WsParam:
    """WebSocket参数类"""

    def __init__(self, APPID, APIKey, APISecret, Text):
        self.APPID = APPID
        self.APIKey = APIKey
        self.APISecret = APISecret
        self.Text = Text

        self.CommonArgs = {"app_id": self.APPID}
        self.BusinessArgs = {
            "aue": "raw",
            "auf": "audio/L16;rate=16000",
            "vcn": AppConfig.TTS_VOICE,
            "tte": "utf8",
            "speed": AppConfig.TTS_SPEED,
            "volume": AppConfig.TTS_VOLUME,
            "pitch": AppConfig.TTS_PITCH,
        }
        self.Data = {
            "status": 2,
            "text": str(base64.b64encode(self.Text.encode("utf-8")), "UTF8"),
        }

    def create_url(self):
        """生成WebSocket URL"""
        url = "wss://tts-api.xfyun.cn/v2/tts"
        now = datetime.now()
        date = format_date_time(mktime(now.timetuple()))

        signature_origin = "host: ws-api.xfyun.cn\n"
        signature_origin += "date: " + date + "\n"
        signature_origin += "GET /v2/tts HTTP/1.1"

        signature_sha = hmac.new(
            self.APISecret.encode("utf-8"),
            signature_origin.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).digest()
        signature_sha = base64.b64encode(signature_sha).decode(encoding="utf-8")

        authorization_origin = f'api_key="{self.APIKey}", algorithm="hmac-sha256", headers="host date request-line", signature="{signature_sha}"'
        authorization = base64.b64encode(authorization_origin.encode("utf-8")).decode(
            encoding="utf-8"
        )

        v = {"authorization": authorization, "date": date, "host": "ws-api.xfyun.cn"}
        return url + "?" + urlencode(v)
