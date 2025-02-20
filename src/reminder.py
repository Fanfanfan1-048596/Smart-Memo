from PyQt5.QtCore import QObject, pyqtSignal, QTimer
from datetime import datetime, timedelta
from .config import AppConfig
from utils.reminder_sound_utils import SoundPlayer
from .xf_tts_service import TTSService
import logging

# 设置日志
logger = logging.getLogger(__name__)


class ReminderManager(QObject):
    reminder_signal = pyqtSignal(str, str)

    def __init__(self, data_manager):
        super().__init__()
        self.data_manager = data_manager
        self.timer = QTimer()
        self.timer.timeout.connect(self.check_reminders)
        self.timer.start(AppConfig.REMINDER_CHECK_INTERVAL)
        self.reminder_times = [30, 5]
        self.reminded_tasks = {}
        # self.sound_player = SoundPlayer()
        self.tts_service = TTSService()

    def check_reminders(self):
        try:
            now = datetime.now()
            upcoming = self.data_manager.get_upcoming_tasks()

            for idx, task in upcoming.iterrows():
                task_id = f"{task['content']}-{task['datetime']}"

                # 初始化提醒记录
                if task_id not in self.reminded_tasks:
                    self.reminded_tasks[task_id] = []

                # 检查每个提醒时间点
                for minutes in self.reminder_times:
                    reminder_time = task["datetime"] - timedelta(minutes=minutes)

                    # 如果到达提醒时间且未提醒过
                    if (
                        reminder_time <= now
                        and minutes not in self.reminded_tasks[task_id]
                        and not task["reminded"]
                    ):

                        # 生成提醒消息
                        message = self._generate_reminder_message(
                            task["content"], minutes, task["datetime"]
                        )

                        # 发送提醒
                        self.reminder_signal.emit("备忘提醒", message)
                        # self.sound_player.play_notification()
                        self.tts_service.text_to_speech(message)
                        logger.debug(f"发送提醒: {message}")

                        # 记录已提醒
                        self.reminded_tasks[task_id].append(minutes)

                        # 如果是最后一次提醒，标记任务为已提醒
                        if minutes == min(self.reminder_times):
                            self.data_manager.mark_reminded(idx)
                            self._handle_recurring_task(idx, task)

                # 清理过期的提醒记录
                if task["datetime"] < now:
                    self.reminded_tasks.pop(task_id, None)

        except Exception as e:
            logger.error(f"检查提醒时出错: {e}", exc_info=True)

    def _generate_reminder_message(
        self, content: str, minutes: int, task_time: datetime
    ) -> str:
        """生成提醒消息"""
        time_str = task_time.strftime("%H:%M")
        if minutes > 0:
            return f"现在是{time_str}，{minutes}分钟后记得{content}"
        else:
            return f"现在是{time_str}，该{content}了）"

    def _handle_recurring_task(self, idx, task):
        """处理周期性任务"""
        try:
            if task["type"] != "ONCE":
                next_time = self._calculate_next_time(task)
                if next_time:
                    logger.debug(f"创建下一个周期任务: {task['content']} @ {next_time}")
                    self.data_manager.add_task(
                        task["content"],
                        next_time,
                        task["type"],
                        eval(task["cycle_info"]) if task["cycle_info"] else None,
                    )
        except Exception as e:
            logger.error(f"处理周期任务时出错: {e}", exc_info=True)

    def _calculate_next_time(self, task):
        """计算下一次任务时间"""
        try:
            current_time = task["datetime"]
            task_type = task["type"]
            cycle_info = eval(task["cycle_info"]) if task["cycle_info"] else None

            if task_type == "DAILY":
                return current_time + timedelta(days=1)
            elif task_type == "WEEKLY":
                return current_time + timedelta(weeks=1)
            elif task_type == "MONTHLY":
                # 处理月末问题
                next_month = current_time + timedelta(days=32)
                return next_month.replace(day=current_time.day)
            return None
        except Exception as e:
            logger.error(f"计算下一次任务时间出错: {e}", exc_info=True)
            return None
