from datetime import datetime, timedelta
import re
from typing import Optional, Tuple, Dict


def parse_datetime_str(text: str) -> Optional[datetime]:
    """解析各种格式的日期时间字符串"""
    patterns = [
        (
            r"(\d{4})年(\d{1,2})月(\d{1,2})日(\d{1,2})时(\d{1,2})分",
            lambda m: datetime(
                int(m.group(1)),
                int(m.group(2)),
                int(m.group(3)),
                int(m.group(4)),
                int(m.group(5)),
            ),
        ),
        (
            r"明天(.+?)(\d{1,2})[点时](\d{1,2})?分?",
            lambda m: datetime.now().replace(
                hour=int(m.group(2)), minute=int(m.group(3) or 0)
            )
            + timedelta(days=1),
        ),
        (
            r"后天(.+?)(\d{1,2})[点时](\d{1,2})?分?",
            lambda m: datetime.now().replace(
                hour=int(m.group(2)), minute=int(m.group(3) or 0)
            )
            + timedelta(days=2),
        ),
    ]

    for pattern, handler in patterns:
        match = re.search(pattern, text)
        if match:
            try:
                return handler(match)
            except ValueError:
                continue
    return None


def format_task(content: str, dt: datetime, task_type: str = "ONCE") -> str:
    """格式化任务显示文本"""
    type_marks = {"ONCE": "🔵", "DAILY": "🔄", "WEEKLY": "📅", "MONTHLY": "📆"}
    return f"{type_marks.get(task_type, '❓')} {content} - {dt.strftime('%Y年%m月%d日%H时%M分')}"


def validate_cycle_info(cycle_info: Dict) -> bool:
    """验证周期任务信息的有效性"""
    required_fields = {
        "DAILY": ["time"],
        "WEEKLY": ["time", "weekday"],
        "MONTHLY": ["time", "day"],
    }

    if "type" not in cycle_info:
        return False

    task_type = cycle_info["type"]
    if task_type not in required_fields:
        return False

    return all(field in cycle_info for field in required_fields[task_type])
