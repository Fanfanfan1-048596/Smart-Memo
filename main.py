import sys
import os
import logging
from pathlib import Path
from PyQt5.QtWidgets import QApplication, QMessageBox, QSystemTrayIcon
from PyQt5.QtGui import QIcon
from ui.main_window import MainWindow
from src.config import AppConfig
from utils.audio_utils import check_audio_system


def ensure_app_directories():
    """确保应用程序所需的目录都存在"""
    try:
        os.makedirs(AppConfig.APP_DIR, exist_ok=True)
        os.makedirs(os.path.dirname(AppConfig.AUDIO_FILE), exist_ok=True)
        os.makedirs(os.path.dirname(AppConfig.TTS_OUTPUT_FILE), exist_ok=True)
        return True
    except Exception as e:
        print(f"创建应用目录失败: {e}")
        return False


def setup_logging():
    """初始化日志系统"""
    try:
        log_file = AppConfig.APP_DIR / "app.log"
        log_dir = os.path.dirname(log_file)
        os.makedirs(log_dir, exist_ok=True)  # 确保日志目录存在

        # 修改为 DEBUG 级别以获取更详细的日志
        logging.basicConfig(
            level=logging.DEBUG,  # 将日志级别改为 DEBUG
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[logging.FileHandler(str(log_file)), logging.StreamHandler()],
        )

        # 设置更详细的WebSocket日志
        websocket_logger = logging.getLogger("websocket")
        websocket_logger.setLevel(logging.DEBUG)
        websocket_logger.addHandler(logging.StreamHandler())

        # 设置请求相关的日志
        requests_log = logging.getLogger("urllib3")
        requests_log.setLevel(logging.DEBUG)
        requests_log.addHandler(logging.StreamHandler())

        logger = logging.getLogger("SmartMemo")
        logger.debug("日志系统初始化完成")
        return logger

    except Exception as e:
        print(f"初始化日志系统失败: {e}")
        # 如果日志系统初始化失败，创建一个只输出到控制台的logger
        console_logger = logging.getLogger("SmartMemo")
        console_logger.addHandler(logging.StreamHandler())
        console_logger.setLevel(logging.DEBUG)  # 同样设置为 DEBUG 级别
        return console_logger


def check_system_tray():
    """检查系统托盘是否可用"""
    if not QSystemTrayIcon.isSystemTrayAvailable():
        QMessageBox.critical(None, "错误", "系统托盘不可用，提醒功能可能受限。")
        return False
    return True


def main():
    logger = None
    try:
        # 首先确保目录存在
        if not ensure_app_directories():
            QMessageBox.critical(None, "错误", "无法创建应用程序目录，程序将退出。")
            return 1

        # 初始化日志
        logger = setup_logging()
        logger.info("应用程序启动")

        # 检查音频系统
        if not check_audio_system():
            logger.warning("音频系统可能不可用，某些功能可能受限")
            QMessageBox.warning(
                None,
                "音频系统警告",
                "未检测到可用的音频输入设备，语音功能可能无法使用。",
            )

        # 创建应用
        app = QApplication(sys.argv)
        app.setApplicationName(AppConfig.APP_NAME)
        logger.info("Qt应用程序创建成功")

        # 检查系统托盘
        if not check_system_tray():
            logger.warning("系统托盘不可用，提醒功能可能受限")

        # 设置应用程序不会在最后一个窗口关闭时退出
        app.setQuitOnLastWindowClosed(False)

        # 创建并显示主窗口
        window = MainWindow()
        window.show()
        logger.info("主窗口显示成功")

        # 设置系统托盘图标
        tray_icon = QSystemTrayIcon(QIcon(str(AppConfig.ICON_FILE)), app)
        tray_icon.show()
        logger.info("系统托盘图标创建成功")

        return app.exec_()

    except Exception as e:
        error_msg = f"程序启动错误: {str(e)}"
        if logger:
            logger.error(error_msg, exc_info=True)
        else:
            print(error_msg)
        QMessageBox.critical(
            None, "启动错误", f"{error_msg}\n请检查日志文件获取详细信息。"
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
