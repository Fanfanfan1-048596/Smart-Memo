import pyaudio
import wave
import numpy as np
from scipy import signal
import logging
import os
from typing import Tuple, List, Dict
from src.config import AppConfig

logger = logging.getLogger(__name__)


def check_audio_system() -> bool:
    """检查系统音频配置"""
    try:
        audio = pyaudio.PyAudio()

        # 获取所有可用设备信息
        info = []
        for i in range(audio.get_device_count()):
            device_info = audio.get_device_info_by_index(i)
            if device_info["maxInputChannels"] > 0:  # 只获取输入设备
                info.append(
                    {
                        "index": i,
                        "name": device_info["name"],
                        "rate": int(device_info["defaultSampleRate"]),
                        "channels": int(device_info["maxInputChannels"]),
                    }
                )

        if not info:
            logger.error("未找到音频输入设备")
            return False

        # 检查默认设备
        try:
            default_device = audio.get_default_input_device_info()
            logger.info(f"默认输入设备: {default_device['name']}")
            logger.info(f"默认采样率: {int(default_device['defaultSampleRate'])}")
        except Exception as e:
            logger.error(f"获取默认设备失败: {e}")
            return False

        return True

    except Exception as e:
        logger.error(f"音频系统检查失败: {e}")
        return False
    finally:
        if "audio" in locals():
            audio.terminate()


def get_audio_info(file_path: str) -> Tuple[int, int, int]:
    """获取音频文件信息

    Returns:
        Tuple[channels, sample_width, framerate]
    """
    with wave.open(file_path, "rb") as wf:
        return (wf.getnchannels(), wf.getsampwidth(), wf.getframerate())


def validate_audio(file_path: str, print_info: bool = True) -> bool:
    """验证音频文件是否符合讯飞API要求"""
    try:
        with wave.open(file_path, "rb") as wf:
            channels = wf.getnchannels()
            sample_width = wf.getsampwidth()  # 返回字节数（2字节=16位）
            framerate = wf.getframerate()

            if print_info:
                logger.debug(
                    f"音频信息: 通道数={channels}, "
                    f"采样位数={sample_width*8}位, "
                    f"采样率={framerate}Hz"
                )

            # 验证格式是否符合要求
            if channels != 1:
                logger.warning("只支持单声道音频")
                return False

            if sample_width != 2:  # 2字节 = 16位
                logger.warning("只支持16位音频")
                return False

            if framerate != 16000:
                logger.warning("只支持16kHz采样率")
                return False

            return True

    except Exception as e:
        logger.error(f"音频验证失败: {e}")
        return False


def convert_audio_format(
    input_file: str, output_file: str, target_rate: int = 16000
) -> bool:
    """转换音频格式为符合讯飞API要求的格式"""
    try:
        logger.debug(f"开始转换音频文件: {input_file}")
        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_file), exist_ok=True)

        with wave.open(input_file, "rb") as wf:
            # 获取原始音频参数
            n_channels = wf.getnchannels()
            sampwidth = wf.getsampwidth()
            framerate = wf.getframerate()

            # 读取音频数据
            frames = wf.readframes(wf.getnframes())
            audio_data = np.frombuffer(frames, dtype=np.int16)

            # 如果是立体声，转换为单声道
            if n_channels == 2:
                logger.debug("转换立体声为单声道")
                audio_data = audio_data.reshape(-1, 2).mean(axis=1).astype(np.int16)

            # 重采样到目标采样率
            if framerate != target_rate:
                logger.debug(f"重采样: {framerate}Hz -> {target_rate}Hz")
                samples = len(audio_data)
                ratio = target_rate / framerate
                new_samples = int(samples * ratio)
                audio_data = signal.resample(audio_data, new_samples).astype(np.int16)

            # 保存为新格式
            with wave.open(output_file, "wb") as wf_out:
                wf_out.setnchannels(1)
                wf_out.setsampwidth(2)
                wf_out.setframerate(target_rate)
                wf_out.writeframes(audio_data.tobytes())

            logger.info(f"音频格式转换成功: {output_file}")
            return True

    except Exception as e:
        logger.error(f"音频格式转换失败: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    # 测试代码
    import sys

    logging.basicConfig(level=logging.DEBUG)

    if len(sys.argv) > 1:
        input_file = sys.argv[1]
        print(f"系统音频检查: {check_audio_system()}")
        print(f"音频文件信息: {get_audio_info(input_file)}")
        print(f"音频格式验证: {validate_audio(input_file)}")
