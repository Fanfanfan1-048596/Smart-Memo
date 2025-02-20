import logging
from datetime import datetime
import json
from openai import OpenAI
import os
from dotenv import load_dotenv

# 设置日志
logger = logging.getLogger(__name__)

# 加载环境变量
load_dotenv()


class AIService:
    def __init__(self):
        self.client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY"), base_url=os.getenv("OPENAI_API_BASE")
        )
        self._init_prompt()

    def _init_prompt(self):
        self.prompt = """
        你是一个智能备忘录助手，可以从用户的自然语言输入中提取备忘事项、时间以及周期信息。

        输出格式要求：
        [{'事项': '具体内容', '时间': (年,月,日,时,分), '类型': '任务类型', '周期': 周期信息}]

        说明：
        1. 事项必须是字符串，提取用户真正需要做的事
        2. 时间必须是5个整数的元组，用圆括号()包围
        3. 类型可以是：
        - 'ONCE': 单次任务
        - 'DAILY': 每日任务
        - 'WEEKLY': 每周任务
        - 'MONTHLY': 每月任务
        4. 周期信息根据类型不同而不同：
        - ONCE: null
        - DAILY: {'type': 'daily', 'time': 'HH:MM'}
        - WEEKLY: {'type': 'weekly', 'day': '周几', 'time': 'HH:MM'}
        - MONTHLY: {'type': 'monthly', 'day': '几号', 'time': 'HH:MM'}

        示例1（复杂日程安排）：
        用户输入: "下周一和周三下午3点要开项目会议，这周五下午4点先开个预备会议，然后从下个月开始每个月1号和15号早上9点要开产品例会。"

        思维过程：
        1. 识别出多个事项：预备会议（单次）、项目会议（多次）、产品例会（定期）
        2. 分析时间：
        - 预备会议：本周五下午4点（单次）
        - 项目会议：下周一和周三下午3点（单次）
        - 产品例会：每月1号和15号早上9点（周期）
        3. 确定当前时间：2025年2月19日
        4. 计算具体日期：
        - 本周五是2月21日
        - 下周一是2月24日
        - 下周三是2月26日
        - 下月起的每月1号和15号

        输出: [
            {'事项': '预备会议', '时间': (2025,2,21,16,0), '类型': 'ONCE', '周期': null},
            {'事项': '项目会议', '时间': (2025,2,24,15,0), '类型': 'ONCE', '周期': null},
            {'事项': '项目会议', '时间': (2025,2,26,15,0), '类型': 'ONCE', '周期': null},
            {'事项': '产品例会', '时间': (2025,3,1,9,0), '类型': 'MONTHLY', '周期': {'type': 'monthly', 'day': '1', 'time': '09:00'}},
            {'事项': '产品例会', '时间': (2025,3,15,9,0), '类型': 'MONTHLY', '周期': {'type': 'monthly', 'day': '15', 'time': '09:00'}}
        ]

        示例2（混合日常和工作安排）：
        用户输入: "我要制定一个新计划：每天早上7点晨跑，工作日上午9点到公司打卡，每周二和周四下午6点参加瑜伽课，这周六下午3点和朋友聚会。对了，下周一上午10点要去医院复查。"

        思维过程：
        1. 识别多个事项类型：
        - 晨跑（每日固定）
        - 打卡（每个工作日）
        - 瑜伽课（每周固定）
        - 聚会（单次）
        - 复查（单次）
        2. 分析时间规律：
        - 晨跑：每天早上7点
        - 打卡：工作日9点
        - 瑜伽课：每周二四6点
        - 聚会：本周六下午3点
        - 复查：下周一上午10点
        3. 根据当前日期（2025年2月19日）计算具体时间

        输出: [
            {'事项': '晨跑', '时间': (2025,2,20,7,0), '类型': 'DAILY', '周期': {'type': 'daily', 'time': '07:00'}},
            {'事项': '打卡', '时间': (2025,2,20,9,0), '类型': 'DAILY', '周期': {'type': 'daily', 'time': '09:00'}},
            {'事项': '瑜伽课', '时间': (2025,2,20,18,0), '类型': 'WEEKLY', '周期': {'type': 'weekly', 'day': '周二', 'time': '18:00'}},
            {'事项': '瑜伽课', '时间': (2025,2,20,18,0), '类型': 'WEEKLY', '周期': {'type': 'weekly', 'day': '周四', 'time': '18:00'}},
            {'事项': '聚会', '时间': (2025,2,22,15,0), '类型': 'ONCE', '周期': null},
            {'事项': '复查', '时间': (2025,2,24,10,0), '类型': 'ONCE', '周期': null}
        ]

        注意：
        1. 时间解析规则：
        - "今天/明天/后天" -> 基于当前日期计算
        - "下周/下月" -> 基于当前日期推算
        - "每天/每周/每月" -> 设置为周期任务
        2. 如遇到模糊时间：
        - "早上" 默认为7:00
        - "上午" 默认为9:00
        - "中午" 默认为12:00
        - "下午" 默认为14:00
        - "傍晚" 默认为18:00
        - "晚上" 默认为20:00
        - "半夜" 默认为0:00
        - "凌晨" 默认为2:00
        注意，这些时间仅作为默认值，具体时间仍需根据上下文确定。一个容易出错的是“今晚12点叫我睡觉”，一般指的是第二天0点，而不是当天0点。
        3. 多任务处理：
        - 分别提取每个独立事项
        - 正确识别是否为周期任务
        - 设置合适的起始时间
        4. 输出要求：
        - 不要包含任何额外解释
        - 严格遵守格式要求
        - 时间必须是5个整数的元组
        """

    def get_current_time(self) -> str:
        """获取当前时间字符串"""
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def process_input(self, user_input: str) -> str:
        try:
            logger.debug(f"开始处理用户输入: {user_input}")
            messages = [
                {
                    "content": f"{self.get_current_time()}。{self.prompt}",
                    "role": "system",
                },
                {"content": user_input, "role": "user"},
            ]

            response = self.client.chat.completions.create(
                model="gpt-4o-mini-2024-07-18", messages=messages, temperature=0.5
            )

            result = response.choices[0].message.content.strip()
            logger.debug(f"API返回原始结果: {result}")

            # 验证结果格式
            if not result.startswith("[") or not result.endswith("]"):
                raise ValueError("返回结果格式错误，必须是列表格式")

            # 替换 'null' 为 'None'
            result = result.replace("null", "None")

            # 使用 eval 安全地评估字符串
            try:
                parsed_result = eval(result, {"__builtins__": {}}, {})
                logger.debug(f"解析结果: {parsed_result}")

                # 验证每个任务的格式
                for item in parsed_result:
                    if not isinstance(item, dict):
                        raise ValueError(f"任务格式错误: {item}")
                    # 验证必要字段
                    required_fields = {"事项", "时间", "类型", "周期"}
                    if not all(field in item for field in required_fields):
                        raise ValueError(f"任务缺少必要字段: {item}")
                return result

            except Exception as e:
                logger.error(f"结果解析失败: {e}")
                raise ValueError(f"无法解析返回结果: {e}")

        except Exception as e:
            logger.error(f"处理失败: {e}", exc_info=True)
            raise RuntimeError(f"AI服务处理失败: {str(e)}")
