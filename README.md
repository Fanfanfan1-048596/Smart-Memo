# SmartMemo 智能备忘录

[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

## 项目简介

SmartMemo 是一个基于 AI 的智能备忘录应用，支持文本和语音输入，提供智能识别、定时提醒等功能。通过集成大语言模型，可以自动从自然语言中提取时间信息和待办事项。

## 主要特性

- 支持**语音输入**和文本输入（文本可能会因输入法问题导致无法输入中文）
- **智能识别时间信息和待办事项**
- **自动语音提醒功能**（提前30分钟和5分钟提醒）
- **支持单次任务和周期性任务**
- 任务数据**可导入导出**（支持 Excel 和 TXT 格式）
- 系统托盘
- 自动保存和恢复任务数据

## 环境要求

- Python 3.9 或更高版本
- 操作系统：Linux（已在 Ubuntu22.04 上测试）
- [科大讯飞 API 密钥](https://console.xfyun.cn/services)
  > [API官方文档](https://www.xfyun.cn/doc/asr/voicedictation/API.html)
- [OpenAI API 密钥](https://github.com/chatanywhere/GPT_API_free)

## 安装方法

1. 创建并激活 conda 环境：

```bash
conda env create -n smart-memo
conda activate smart-memo
```

2. 安装项目依赖：

```bash
pip install -r requirements.txt
```

3. 安装开发依赖（可选）：

```bash
pip install -e ".[dev]"
```

## 配置说明

1. 创建配置文件：

```bash
cp .env.example .env
```

2. 修改 .env 文件，填入您的 API 密钥：

```ini
# 科大讯飞配置
XF_APPID=your_app_id
XF_API_SECRET=your_api_secret
XF_API_KEY=your_api_key

# OpenAI配置
OPENAI_API_KEY=your_api_key
```

## 运行方法

直接运行主程序：

```bash
python main.py
```

或使用安装后的命令：

```bash
smart-memo
```

## 项目结构

```
smart-memo/
├── src/                   
│   ├── ai_service.py      # AI 服务实现
│   ├── audio_manager.py   # 音频管理
│   ├── config.py          # 配置管理
│   ├── data_manager.py    # 数据管理
│   ├── reminder.py        # 提醒服务
│   ├── xf_iat_service.py  # 讯飞语音识别
│   └── xf_tts_service.py  # 讯飞语音合成
├── ui/                   
│   ├── main_ui.py        # UI创建与定义（使用PyQT5）
│   └── main_window.py    # 主窗口交互功能实现
├── utils/                
│   ├── audio_utils.py    # 音频处理
│   ├── helpers.py        # 一点辅助函数
│   └── reminder_sound_utils.py  # 提醒音效
├── assets/               # 资源文件
│   ├── notification.wav  # 提醒音效（由于使用讯飞语音合成，已无用）
│   └── icon.png         # 应用图标
├── requirements.txt     # 依赖清单
├── setup.py            # 安装配置
└── README.md          # 项目说明
```

## 使用示例

1. 文本输入示例（详见ai_service.py中的prompt中的例子）：
```
明天下午3点开会
每周一上午9点晨会
每月1日检查报表
```

2. 语音输入支持同样的自然语言表达。

## 常见问题

1. 如何处理音频设备未找到的问题？
   - 确保系统已正确配置音频设备
   - 检查用户权限是否正确

2. 提醒功能无效？
   - 确保系统托盘可用
   - 检查系统通知权限

## 贡献指南

1. Fork 本项目
2. 创建特性分支
3. 提交变更
4. 发起 Pull Request

## 许可证

本项目基于 MIT 许可证开源。

## 联系方式

- 作者：Fanfanfan
- 邮箱：202230101018@mail.scut.edu.cn

## 致谢

- [PyQt5](https://www.riverbankcomputing.com/software/pyqt/)
- [科大讯飞开放平台](https://www.xfyun.cn/)
- [OpenAI](https://openai.com/)