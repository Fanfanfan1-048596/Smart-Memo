from PyQt5.QtWidgets import (
    QWidget,
    QSystemTrayIcon,
    QMenu,
    QMessageBox,
    QListView,
    QFileDialog,
)
from PyQt5.QtCore import Qt, QCoreApplication, QStringListModel
from PyQt5.QtGui import QIcon
import pandas as pd
import json
import logging
from datetime import datetime
from .main_ui import Ui_Form_memo
from src.config import AppConfig
from src.data_manager import DataManager
from src.reminder import ReminderManager
from src.audio_manager import AudioManager
from src.ai_service import AIService

# 设置日志
logger = logging.getLogger(__name__)


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        logger.debug("初始化主窗口")
        self.ui = Ui_Form_memo()
        self.ui.setupUi(self)

        # 初始化各个管理器
        self.data_manager = DataManager()
        self.reminder = ReminderManager(self.data_manager)
        self.audio_manager = AudioManager()
        self.ai_service = AIService()

        # 启用输入法支持
        self.setAttribute(Qt.WA_InputMethodEnabled)

        self._setup_ui()
        self._setup_connections()
        self._setup_tray()

    def _setup_ui(self):
        # 设置窗口图标
        self.setWindowIcon(QIcon(str(AppConfig.ICON_FILE)))

        # 设置任务过滤器
        self.ui.comboBox_filter.currentIndexChanged.connect(self._filter_tasks)

        # 初始化任务列表
        self._refresh_task_list()

        # 设置列表样式
        self.ui.listView_list_output.setSelectionMode(QListView.SingleSelection)

    def _setup_connections(self):
        # 按钮连接
        self.ui.pushButton_extract.clicked.connect(self._handle_extract)
        self.ui.pushButton_clearall.clicked.connect(self._handle_clear)
        self.ui.pushButton_audio_input.clicked.connect(self._handle_audio)

        # 导入导出按钮连接
        self.ui.import_excel_action.triggered.connect(self._handle_import_excel)
        self.ui.import_txt_action.triggered.connect(self._handle_import_txt)
        self.ui.export_excel_action.triggered.connect(self._handle_export_excel)
        self.ui.export_txt_action.triggered.connect(self._handle_export_txt)

        # 提醒信号连接
        self.reminder.reminder_signal.connect(self._show_reminder)

        # 音频信号连接
        self.audio_manager.recording_status_changed.connect(self._update_audio_button)
        self.audio_manager.text_converted.connect(self._handle_audio_text)
        self.audio_manager.error_occurred.connect(self._handle_audio_error)

    def _setup_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon(str(AppConfig.ICON_FILE)))

        # 创建托盘菜单
        menu = QMenu()
        show_action = menu.addAction("显示")
        show_action.triggered.connect(self.showNormal)
        quit_action = menu.addAction("退出")
        quit_action.triggered.connect(QCoreApplication.instance().quit)

        self.tray_icon.setContextMenu(menu)
        self.tray_icon.show()

    def _handle_import_excel(self):
        """处理Excel导入"""
        try:
            filename, _ = QFileDialog.getOpenFileName(
                self, "导入Excel", "", "Excel Files (*.xlsx);;All Files (*)"
            )
            if filename:
                logger.debug(f"开始导入Excel文件: {filename}")
                df = pd.read_excel(filename)
                content = self._process_imported_data(df)
                self.ui.plainTextEdit_text_input.setPlainText(content)
                self._handle_extract()
        except Exception as e:
            logger.error(f"导入Excel失败: {e}", exc_info=True)
            QMessageBox.warning(self, "错误", f"导入失败: {str(e)}")

    def _handle_import_txt(self):
        """处理TXT导入"""
        try:
            filename, _ = QFileDialog.getOpenFileName(
                self, "导入TXT", "", "Text Files (*.txt);;All Files (*)"
            )
            if filename:
                logger.debug(f"开始导入TXT文件: {filename}")
                with open(filename, "r", encoding="utf-8") as f:
                    content = f.read()
                self.ui.plainTextEdit_text_input.setPlainText(content)
                self._handle_extract()
        except Exception as e:
            logger.error(f"导入TXT失败: {e}", exc_info=True)
            QMessageBox.warning(self, "错误", f"导入失败: {str(e)}")

    def _handle_export_excel(self):
        """处理Excel导出"""
        try:
            filename, _ = QFileDialog.getSaveFileName(
                self, "导出Excel", "", "Excel Files (*.xlsx);;All Files (*)"
            )
            if filename:
                if not filename.endswith(".xlsx"):
                    filename += ".xlsx"
                logger.debug(f"开始导出Excel文件: {filename}")
                self.data_manager.export_to_excel(filename)
                QMessageBox.information(self, "成功", "任务列表已成功导出为Excel文件")
        except Exception as e:
            logger.error(f"导出Excel失败: {e}", exc_info=True)
            QMessageBox.warning(self, "错误", f"导出失败: {str(e)}")

    def _handle_export_txt(self):
        """处理TXT导出"""
        try:
            filename, _ = QFileDialog.getSaveFileName(
                self, "导出TXT", "", "Text Files (*.txt);;All Files (*)"
            )
            if filename:
                if not filename.endswith(".txt"):
                    filename += ".txt"
                logger.debug(f"开始导出TXT文件: {filename}")
                self.data_manager.export_to_txt(filename)
                QMessageBox.information(self, "成功", "任务列表已成功导出为TXT文件")
        except Exception as e:
            logger.error(f"导出TXT失败: {e}", exc_info=True)
            QMessageBox.warning(self, "错误", f"导出失败: {str(e)}")

    def _process_imported_data(self, df):
        """处理导入的数据为文本格式"""
        try:
            text_lines = []
            for _, row in df.iterrows():
                line = []
                for col in df.columns:
                    if pd.notna(row[col]):  # 只添加非空值
                        line.append(str(row[col]))
                text_lines.append(" ".join(line))
            return "\n".join(text_lines)
        except Exception as e:
            logger.error(f"处理导入数据失败: {e}", exc_info=True)
            raise

    def _handle_clear(self):
        self.data_manager.clear_all()
        self._refresh_task_list()
        self.ui.plainTextEdit_text_input.clear()

    def _handle_audio(self):
        try:
            if not self.audio_manager.recorder.isRunning():
                self.audio_manager.start_recording()
            else:
                self.audio_manager.stop_recording()
        except Exception as e:
            QMessageBox.warning(self, "错误", f"录音操作失败: {str(e)}")

    def closeEvent(self, event):
        self.hide()
        event.ignore()

    def _filter_tasks(self, index):
        if index == 0:  # 全部任务
            tasks = self.data_manager.get_all_tasks()
        elif index == 1:  # 今日任务
            tasks = self.data_manager.get_today_tasks()
        else:  # 周期任务
            tasks = self.data_manager.get_recurring_tasks()

        self._update_task_list(tasks)

    def _update_task_list(self, tasks):
        """更新任务列表显示"""
        model = QStringListModel()
        formatted_tasks = []

        for _, task in tasks.iterrows():
            if task["type"] == "ONCE":
                # 一次性任务显示完整时间
                formatted_tasks.append(
                    f"{task['content']} - {task['datetime'].strftime('%Y年%m月%d日%H时%M分')}"
                )
            else:
                # 周期任务显示周期信息
                cycle_info = (
                    json.loads(task["cycle_info"]) if task["cycle_info"] else {}
                )
                if task["type"] == "DAILY":
                    formatted_tasks.append(
                        f"{task['content']} - 每天 {cycle_info.get('time', '00:00')}"
                    )
                elif task["type"] == "WEEKLY":
                    formatted_tasks.append(
                        f"{task['content']} - 每周{cycle_info.get('day', '')} {cycle_info.get('time', '00:00')}"
                    )
                elif task["type"] == "MONTHLY":
                    formatted_tasks.append(
                        f"{task['content']} - 每月{cycle_info.get('day', '')}日 {cycle_info.get('time', '00:00')}"
                    )

        model.setStringList(formatted_tasks)
        self.ui.listView_list_output.setModel(model)

    def _init_reminder_manager(self):
        """初始化提醒管理器"""
        self.reminder_manager = ReminderManager(self.data_manager)
        self.reminder_manager.reminder_signal.connect(self._show_reminder)
        logger.debug("提醒管理器初始化完成")

    def _show_reminder(self, title: str, message: str):
        """显示提醒通知"""
        try:
            # 显示系统托盘通知
            self.tray_icon.showMessage(
                title,
                message,
                QIcon(str(AppConfig.ICON_FILE)),
                AppConfig.REMINDER_DURATION,
            )
            logger.debug(f"显示提醒通知: {message}")
        except Exception as e:
            logger.error(f"显示提醒通知失败: {e}", exc_info=True)

    def _format_cycle_info(self, task_type: str, cycle_info: dict) -> str:
        """格式化周期信息显示"""
        if task_type == "DAILY":
            return f"每天 {cycle_info.get('time', '')}"
        elif task_type == "WEEKLY":
            return f"每周{cycle_info.get('day', '')} {cycle_info.get('time', '')}"
        elif task_type == "MONTHLY":
            return f"每月{cycle_info.get('day', '')}日 {cycle_info.get('time', '')}"
        return ""

    def _update_audio_button(self, is_recording):
        try:
            if is_recording:
                self.ui.pushButton_audio_input.setText("停止录音")
                self.ui.pushButton_audio_input.setStyleSheet(
                    "QPushButton {background-color: #e74c3c; color: white;}"
                )
            else:
                self.ui.pushButton_audio_input.setText("语音输入")
                self.ui.pushButton_audio_input.setStyleSheet("")
        except Exception as e:
            QMessageBox.warning(self, "错误", f"更新按钮状态失败: {str(e)}")

    def _process_ai_result(self, result):
        """处理AI返回的结果"""
        try:
            logger.debug(f"开始处理AI返回结果: {result}")
            tasks = eval(result, {"__builtins__": {}}, {})
            logger.debug(f"解析后的任务列表: {tasks}")

            for task in tasks:
                if not isinstance(task, dict):
                    raise ValueError(f"任务格式错误: {task}")

                # 从AI返回结果中提取信息
                content = task["事项"]
                time_tuple = task["时间"]
                task_type = task["类型"]
                cycle_info = task["周期"]

                # 将时间元组转换为datetime对象
                task_time = datetime(*time_tuple)

                # 添加到数据管理器
                logger.debug(
                    f"添加任务: {content} @ {task_time}, 类型: {task_type}, 周期: {cycle_info}"
                )
                self.data_manager.add_task(
                    content=content,
                    dt=task_time,
                    task_type=task_type,
                    cycle_info=cycle_info,
                )

            self._refresh_task_list()
            QMessageBox.information(self, "成功", f"成功添加 {len(tasks)} 个任务")

        except Exception as e:
            logger.error(f"处理AI结果失败: {e}", exc_info=True)
            QMessageBox.warning(self, "处理失败", f"无法处理AI返回结果: {str(e)}")

    def _handle_extract(self):
        text = self.ui.plainTextEdit_text_input.toPlainText()
        if not text:
            logger.debug("输入文本为空，跳过处理")
            return

        try:
            logger.debug(f"开始处理输入文本: {text}")
            result = self.ai_service.process_input(text)
            self._process_ai_result(result)
        except Exception as e:
            logger.error(f"文本处理失败: {e}", exc_info=True)
            QMessageBox.warning(self, "错误", f"处理失败: {str(e)}")

    def _handle_audio_text(self, text):
        """处理语音转文字的结果"""
        if text:
            logger.debug(f"接收到语音识别结果: {text}")
            self.ui.plainTextEdit_text_input.setPlainText(text)
        else:
            logger.warning("语音识别结果为空")
            QMessageBox.warning(self, "转换失败", "未能识别语音内容")

    def _refresh_task_list(self):
        """刷新任务列表显示"""
        tasks = self.data_manager.get_all_tasks()
        self._update_task_list(tasks)

    def _handle_audio_error(self, error_msg):
        """处理语音转换错误"""
        logger.error(f"语音转换错误: {error_msg}")
        QMessageBox.warning(self, "错误", f"语音转换失败：{error_msg}")

    def inputMethodEvent(self, event):
        # 处理输入法事件
        super().inputMethodEvent(event)
