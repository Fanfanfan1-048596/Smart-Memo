import pygame
import logging
from src.config import AppConfig

logger = logging.getLogger(__name__)


class SoundPlayer:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SoundPlayer, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        try:
            pygame.mixer.init()
            pygame.mixer.music.set_volume(AppConfig.NOTIFICATION_VOLUME)
            self._initialized = True
            logger.debug("音频播放器初始化成功")
        except Exception as e:
            logger.error(f"音频播放器初始化失败: {e}", exc_info=True)
            self._initialized = False

    def play_notification(self):
        """播放提醒音效"""
        try:
            if not self._initialized:
                return

            if not AppConfig.NOTIFICATION_SOUND.exists():
                logger.error(f"提醒音效文件不存在: {AppConfig.NOTIFICATION_SOUND}")
                return

            pygame.mixer.music.load(str(AppConfig.NOTIFICATION_SOUND))
            pygame.mixer.music.play()
            logger.debug("播放提醒音效")
        except Exception as e:
            logger.error(f"播放提醒音效失败: {e}", exc_info=True)
