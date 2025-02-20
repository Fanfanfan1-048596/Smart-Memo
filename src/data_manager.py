import pandas as pd
from datetime import datetime, timedelta
from .config import AppConfig
import os
import json
import logging

# 设置日志
logger = logging.getLogger(__name__)


class DataManager:
    def __init__(self):
        self.excel_file = AppConfig.DATA_FILE
        os.makedirs(AppConfig.APP_DIR, exist_ok=True)
        self._init_excel()

    def _init_excel(self):
        try:
            self.df = pd.read_excel(self.excel_file, parse_dates=["datetime"])
            # 确保所有必要的列都存在
            required_columns = ["content", "datetime", "type", "cycle_info", "reminded"]
            for col in required_columns:
                if col not in self.df.columns:
                    self.df[col] = None
        except FileNotFoundError:
            self.df = pd.DataFrame(
                {
                    "content": [],
                    "datetime": [],
                    "type": [],
                    "cycle_info": [],
                    "reminded": [],
                }
            )
            self.df["datetime"] = pd.to_datetime(self.df["datetime"])
            self.save()

    def save(self):
        """保存数据到Excel文件"""
        try:
            self.df.to_excel(self.excel_file, index=False)
            # 重新读取以确保数据类型正确
            self.df = pd.read_excel(self.excel_file, parse_dates=["datetime"])
            logger.debug("数据保存成功")
        except Exception as e:
            logger.error(f"保存数据失败: {e}", exc_info=True)
            raise

    def add_task(
        self,
        content: str,
        dt: datetime,
        task_type: str = "ONCE",
        cycle_info: dict = None,
    ):
        """添加新任务"""
        try:
            logger.debug(f"添加任务: {content}, 时间: {dt}, 类型: {task_type}")
            # 确保dt是datetime类型
            if isinstance(dt, str):
                dt = pd.to_datetime(dt)

            new_task = {
                "content": content,
                "datetime": dt,
                "type": task_type,
                "cycle_info": (
                    json.dumps(cycle_info, ensure_ascii=False) if cycle_info else None
                ),
                "reminded": False,
            }
            new_df = pd.DataFrame([new_task])
            new_df["datetime"] = pd.to_datetime(new_df["datetime"])
            self.df = pd.concat([self.df, new_df], ignore_index=True)
            self.save()
        except Exception as e:
            logger.error(f"添加任务失败: {e}", exc_info=True)
            raise

    def export_to_excel(self, filepath: str):
        """导出任务列表为Excel文件"""
        try:
            logger.debug(f"导出Excel文件: {filepath}")
            # 创建用于导出的DataFrame副本
            export_df = self.df.copy()

            # 格式化datetime列
            export_df["datetime"] = export_df["datetime"].dt.strftime(
                "%Y-%m-%d %H:%M:%S"
            )

            # 如果cycle_info是JSON字符串，尝试解析它
            def format_cycle_info(info):
                if pd.isna(info):
                    return ""
                try:
                    return json.dumps(json.loads(info), ensure_ascii=False, indent=2)
                except:
                    return str(info)

            export_df["cycle_info"] = export_df["cycle_info"].apply(format_cycle_info)

            # 重命名列为中文
            export_df.columns = ["内容", "时间", "类型", "周期信息", "已提醒"]

            # 导出到Excel
            export_df.to_excel(filepath, index=False)
            logger.debug("Excel导出成功")
        except Exception as e:
            logger.error(f"导出Excel失败: {e}", exc_info=True)
            raise

    def export_to_txt(self, filepath: str):
        """导出任务列表为TXT文件"""
        try:
            logger.debug(f"导出TXT文件: {filepath}")
            with open(filepath, "w", encoding="utf-8") as f:
                for _, task in self.df.iterrows():
                    dt_str = task["datetime"].strftime("%Y年%m月%d日%H时%M分")
                    type_str = "周期任务" if task["type"] != "ONCE" else "单次任务"
                    cycle_str = ""
                    if task["cycle_info"]:
                        try:
                            cycle_info = json.loads(task["cycle_info"])
                            cycle_str = f"[周期: {cycle_info.get('type', '')}={cycle_info.get('value', '')}]"
                        except:
                            cycle_str = f"[周期: {task['cycle_info']}]"

                    f.write(f"{task['content']} - {dt_str} - {type_str}{cycle_str}\n")
            logger.debug("TXT导出成功")
        except Exception as e:
            logger.error(f"导出TXT失败: {e}", exc_info=True)
            raise

    def get_upcoming_tasks(self, include_reminded=False):
        """获取即将到来的任务"""
        now = datetime.now()
        # 获取未来30分钟内的任务（包括周期任务）
        max_check_time = now + timedelta(minutes=max(AppConfig.REMINDER_TIMES))

        upcoming = self.df[
            ((self.df["datetime"] > now) & (self.df["datetime"] <= max_check_time))
            | (self.df["type"] != "ONCE")  # 包含所有周期任务
        ].copy()

        if not include_reminded:
            upcoming = upcoming[~upcoming["reminded"]]

        return upcoming.sort_values("datetime")

    def mark_reminded(self, index):
        """标记任务为已提醒"""
        try:
            self.df.at[index, "reminded"] = True
            self.save()
            logger.debug(f"任务已标记为已提醒: {index}")
        except Exception as e:
            logger.error(f"标记任务提醒状态失败: {e}", exc_info=True)

    def _calculate_next_execution(self, task):
        """计算周期任务的下一次执行时间"""
        now = datetime.now()
        cycle_info = json.loads(task["cycle_info"]) if task["cycle_info"] else {}

        if task["type"] == "DAILY":
            time_str = cycle_info.get("time", "00:00")
            hour, minute = map(int, time_str.split(":"))
            next_time = now.replace(hour=hour, minute=minute)
            if next_time <= now:
                next_time = next_time + timedelta(days=1)

        elif task["type"] == "WEEKLY":
            weekday_map = {
                "周一": 0,
                "周二": 1,
                "周三": 2,
                "周四": 3,
                "周五": 4,
                "周六": 5,
                "周日": 6,
            }
            target_weekday = weekday_map.get(cycle_info.get("day", "周一"), 0)
            time_str = cycle_info.get("time", "00:00")
            hour, minute = map(int, time_str.split(":"))

            next_time = now
            while next_time.weekday() != target_weekday:
                next_time += timedelta(days=1)
            next_time = next_time.replace(hour=hour, minute=minute)
            if next_time <= now:
                next_time += timedelta(days=7)

        elif task["type"] == "MONTHLY":
            target_day = int(cycle_info.get("day", "1"))
            time_str = cycle_info.get("time", "00:00")
            hour, minute = map(int, time_str.split(":"))

            next_time = now.replace(day=1, hour=hour, minute=minute)
            while next_time.day != target_day:
                next_time += timedelta(days=1)
            if next_time <= now:
                if next_time.month == 12:
                    next_time = next_time.replace(year=next_time.year + 1, month=1)
                else:
                    next_time = next_time.replace(month=next_time.month + 1)

        return next_time

    def get_all_tasks(self):
        """获取所有任务"""
        return self.df.sort_values("datetime")

    def get_today_tasks(self):
        """获取今日任务"""
        self.df["datetime"] = pd.to_datetime(self.df["datetime"])
        today = datetime.now().date()
        tomorrow = today + timedelta(days=1)
        mask = (self.df["datetime"].dt.date >= today) & (
            self.df["datetime"].dt.date < tomorrow
        )
        return self.df[mask].sort_values("datetime")

    def get_recurring_tasks(self):
        """获取所有周期性任务"""
        return self.df[self.df["type"] != "ONCE"].sort_values("datetime")

    def clear_all(self):
        """清除所有任务"""
        logger.debug("清除所有任务")
        self.df = pd.DataFrame(
            {
                "content": [],
                "datetime": [],
                "type": [],
                "cycle_info": [],
                "reminded": [],
            }
        )
        self.save()

    def update_task(
        self,
        index: int,
        content: str = None,
        dt: datetime = None,
        task_type: str = None,
        cycle_info: dict = None,
    ):
        """更新任务信息"""
        try:
            logger.debug(
                f"更新任务 {index}: {content}, {dt}, {task_type}, {cycle_info}"
            )
            if content is not None:
                self.df.at[index, "content"] = content
            if dt is not None:
                self.df.at[index, "datetime"] = dt
            if task_type is not None:
                self.df.at[index, "type"] = task_type
            if cycle_info is not None:
                self.df.at[index, "cycle_info"] = json.dumps(
                    cycle_info, ensure_ascii=False
                )
            self.save()
        except Exception as e:
            logger.error(f"更新任务失败: {e}", exc_info=True)
            raise

    def delete_task(self, index: int):
        """删除指定任务"""
        try:
            logger.debug(f"删除任务: {index}")
            self.df = self.df.drop(index)
            self.df = self.df.reset_index(drop=True)
            self.save()
        except Exception as e:
            logger.error(f"删除任务失败: {e}", exc_info=True)
            raise
