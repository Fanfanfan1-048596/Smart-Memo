import websocket
import datetime
import hashlib
import base64
import hmac
import json
import os
from urllib.parse import urlencode
import time
import ssl
from wsgiref.handlers import format_date_time
from datetime import datetime
from time import mktime
import _thread as thread
from .config import AppConfig
import logging
from utils.audio_utils import validate_audio

STATUS_FIRST_FRAME = 0  # 第一帧的标识
STATUS_CONTINUE_FRAME = 1  # 中间帧标识
STATUS_LAST_FRAME = 2  # 最后一帧的标识

# 全局变量，用于存储转换结果
result_text = None

# 设置日志
logger = logging.getLogger(__name__)


class WsParam(object):
    def __init__(self, APPID, APIKey, APISecret, AudioFile):
        self.APPID = APPID
        self.APIKey = APIKey
        self.APISecret = APISecret
        self.AudioFile = AudioFile

        # 公共参数(common)
        self.CommonArgs = {"app_id": self.APPID}

        # 业务参数(business)，更多个性化参数可在官网查看
        self.BusinessArgs = {
            "domain": "iat",
            "language": "zh_cn",
            "accent": "mandarin",
            "vinfo": 1,
            "vad_eos": 10000,
        }

    def create_url(self):
        url = "wss://ws-api.xfyun.cn/v2/iat"
        # 生成RFC1123格式的时间戳
        now = datetime.now()
        date = format_date_time(mktime(now.timetuple()))

        # 拼接字符串
        signature_origin = "host: " + "ws-api.xfyun.cn" + "\n"
        signature_origin += "date: " + date + "\n"
        signature_origin += "GET " + "/v2/iat " + "HTTP/1.1"
        # 进行hmac-sha256进行加密
        signature_sha = hmac.new(
            self.APISecret.encode("utf-8"),
            signature_origin.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).digest()
        signature_sha = base64.b64encode(signature_sha).decode(encoding="utf-8")

        authorization_origin = (
            'api_key="%s", algorithm="%s", headers="%s", signature="%s"'
            % (self.APIKey, "hmac-sha256", "host date request-line", signature_sha)
        )
        authorization = base64.b64encode(authorization_origin.encode("utf-8")).decode(
            encoding="utf-8"
        )
        # 将请求的鉴权参数组合为字典
        v = {"authorization": authorization, "date": date, "host": "ws-api.xfyun.cn"}
        # 拼接鉴权参数，生成url
        url = url + "?" + urlencode(v)
        return url


wsParam = WsParam(
    APPID=AppConfig.XF_APPID,
    APISecret=AppConfig.XF_API_SECRET,
    APIKey=AppConfig.XF_API_KEY,
    AudioFile=str(AppConfig.AUDIO_FILE),
)


class WebsocketConnection:
    def __init__(self):
        self.ws = None
        self.result = None
        self.error = None
        self.closed = False
        self.received_message = False
        self.final_result = []
        self.all_data_sent = False  # 新增：标记是否已发送所有数据
        logger.debug("初始化WebSocket连接")

    def on_message(self, ws, message):
        try:
            logger.debug(f"\n{'='*50}")
            logger.debug(f"接收到新消息: {message}")
            self.received_message = True
            msg = json.loads(message)

            # 检查错误码
            if msg.get("code") != 0:
                self.error = msg.get("message", "未知错误")
                logger.error(f"识别错误: {self.error} (code: {msg.get('code')})")
                self.close()
                return

            # 处理数据
            if "data" not in msg:
                logger.debug("消息中无data字段")
                return

            data = msg["data"]
            logger.debug(
                f"解析得到的数据: {json.dumps(data, ensure_ascii=False, indent=2)}"
            )

            # 提取识别结果
            if "result" in data:
                result = data["result"]
                if "ws" in result:
                    text = ""
                    for item in result["ws"]:
                        for w in item["cw"]:
                            text += w["w"]

                    if text.strip():
                        logger.debug(f"识别出文本: {text}")
                        self.final_result.append(text)
                        self.result = "".join(self.final_result)
                        logger.debug(f"当前累积结果: {self.result}")

            # 检查是否是最后一帧响应
            if self.all_data_sent and data.get("status") == 2:
                logger.info(f"收到最终识别结果: {self.result}")
                self.close()

            logger.debug(f"{'='*50}\n")

        except Exception as e:
            logger.error(f"处理消息时出错: {str(e)}", exc_info=True)
            self.error = str(e)
            self.close()

    def on_error(self, ws, error):
        logger.error(f"WebSocket错误: {error}")
        self.error = str(error)
        self.close()

    def on_close(self, ws, *args):
        logger.debug("WebSocket连接关闭")
        self.closed = True
        if self.ws:
            self.ws.close()
        self.ws = None

    def on_open(self, ws):
        def run(*args):
            try:
                frameSize = AppConfig.XF_FRAME_SIZE
                interval = AppConfig.XF_INTERVAL
                status = STATUS_FIRST_FRAME

                logger.debug(
                    f"准备发送音频数据: frameSize={frameSize}, interval={interval}"
                )

                with open(wsParam.AudioFile, "rb") as fp:
                    while True and not self.closed:
                        buf = fp.read(frameSize)

                        # 处理文件结束
                        if not buf:
                            if status == STATUS_FIRST_FRAME:
                                logger.warning("音频文件为空")
                                break
                            logger.debug("到达文件末尾，发送最后一帧")
                            status = STATUS_LAST_FRAME

                        # 根据不同状态发送数据
                        try:
                            if status == STATUS_FIRST_FRAME:
                                d = {
                                    "common": wsParam.CommonArgs,
                                    "business": wsParam.BusinessArgs,
                                    "data": {
                                        "status": 0,
                                        "format": "audio/L16;rate=16000",
                                        "audio": str(base64.b64encode(buf), "utf-8"),
                                        "encoding": "raw",
                                    },
                                }
                                ws.send(json.dumps(d))
                                status = STATUS_CONTINUE_FRAME
                                logger.debug("已发送第一帧数据")
                            elif status == STATUS_CONTINUE_FRAME and buf:
                                d = {
                                    "data": {
                                        "status": 1,
                                        "format": "audio/L16;rate=16000",
                                        "audio": str(base64.b64encode(buf), "utf-8"),
                                        "encoding": "raw",
                                    }
                                }
                                ws.send(json.dumps(d))
                                logger.debug("已发送中间帧数据")
                            elif status == STATUS_LAST_FRAME:
                                d = {
                                    "data": {
                                        "status": 2,
                                        "format": "audio/L16;rate=16000",
                                        "audio": str(base64.b64encode(buf), "utf-8"),
                                        "encoding": "raw",
                                    }
                                }
                                ws.send(json.dumps(d))
                                logger.debug("已发送最后一帧数据")
                                self.all_data_sent = True  # 标记所有数据已发送
                                break
                        except Exception as e:
                            logger.error(f"发送数据失败: {e}")
                            raise

                        time.sleep(interval)

                # 等待最终结果
                wait_time = 0
                while not self.closed and wait_time < 10:  # 最多等待10秒
                    time.sleep(0.1)
                    wait_time += 0.1

            except Exception as e:
                logger.error(f"音频发送过程出错: {e}", exc_info=True)
                self.error = str(e)
            finally:
                if not self.closed:
                    self.close()

        thread.start_new_thread(run, ())

    def connect(self):
        websocket.enableTrace(False)
        self.ws = websocket.WebSocketApp(
            wsParam.create_url(),
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close,
        )
        self.ws.on_open = self.on_open
        self.ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})

    def close(self):
        self.closed = True
        if self.ws:
            self.ws.close()


def audio_to_text() -> str:
    """将音频文件转换为文本"""
    try:
        logger.debug("开始语音转文字")
        # 修正音频文件路径
        if not os.path.exists(AppConfig.AUDIO_FILE):
            raise FileNotFoundError(f"音频文件不存在: {AppConfig.AUDIO_FILE}")

        # 添加音频格式验证
        if not validate_audio(str(AppConfig.AUDIO_FILE)):
            raise ValueError(
                "音频格式不符合要求：\n"
                "- 采样率：16kHz\n"
                "- 采样位数：16位\n"
                "- 声道数：单声道"
            )

        conn = WebsocketConnection()

        def run_websocket():
            try:
                conn.connect()
            except Exception as e:
                logger.error(f"WebSocket连接错误: {e}")
                conn.error = str(e)
                conn.closed = True

        # 在新线程中运行WebSocket连接
        thread.start_new_thread(run_websocket, ())

        # 等待结果
        timeout = 30  # 30秒超时
        start_time = time.time()

        while not conn.closed:
            if time.time() - start_time > timeout:
                conn.close()
                raise TimeoutError("语音转换超时")

            # 检查是否收到任何消息
            if not conn.received_message and time.time() - start_time > 5:
                conn.close()
                raise TimeoutError("未收到服务器响应")

            time.sleep(0.1)

        if conn.error:
            raise RuntimeError(f"语音转换失败: {conn.error}")

        if not conn.result:
            raise RuntimeError("未能获取识别结果")

        logger.debug(f"语音转文字完成，结果: {conn.result}")
        return conn.result

    except Exception as e:
        logger.error(f"语音转换过程错误: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    res = audio_to_text()
    res = res.strip('"')
    print(res)
