# 🤖 智能语音助手 (AI Voice Assistant)

一个集成了DeepSeek大语言模型、Edge TTS语音合成、实时语音识别和多种扩展功能的智能对话系统。支持文本对话、语音交互、天气查询、IP地理位置查询、RAG知识库等功能。

[![Python](https://img.shields.io/badge/Python-3.7+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey.svg)](https://www.microsoft.com/windows)

## 📋 目录

- [功能特点](#功能特点)
- [系统要求](#系统要求)
- [安装指南](#安装指南)
- [快速开始](#快速开始)
- [功能说明](#功能说明)
- [配置指南](#配置指南)
- [API集成](#api集成)
- [常见问题](#常见问题)
- [贡献指南](#贡献指南)

## ✨ 功能特点

### 🎯 核心功能
- **智能对话**: 集成DeepSeek大语言模型，支持自然语言对话
- **语音交互**: 实时语音识别 + 智能语音合成
- **双引擎TTS**: Edge TTS + Windows TTS双引擎支持
- **流式对话**: 支持实时流式对话模式
- **对话管理**: 完整的对话历史记录和管理
- **多语言支持**: 中文、英文等多语言识别和合成

### 🌟 扩展功能
- **天气查询**: 支持全球城市实时天气和预报查询
- **IP地理位置**: IP地址查询和地理位置信息
- **RAG知识库**: 文档检索增强生成，支持本地知识库
- **文件管理**: 智能文件上传、管理和检索
- **模型管理**: 多AI模型配置和切换
- **剪贴板集成**: 智能剪贴板内容处理

### 🎤 语音功能
- **实时语音识别**: 支持连续语音输入
- **语音活动检测**: 智能检测语音开始和结束
- **智能语音选择**: 根据文本语言自动选择合适语音
- **语音参数控制**: 语速、音调、音量精确调节
- **多引擎支持**: Edge TTS、Windows TTS无缝切换

### 🎨 用户界面
- **现代化GUI**: 直观美观的图形用户界面
- **响应式设计**: 自适应窗口大小和分辨率
- **主题支持**: 多种界面主题可选
- **实时状态**: 实时显示系统状态和处理进度

## 🔧 系统要求

### 基础要求
- **操作系统**: Windows 10/11 (推荐)
- **Python**: 3.7+ (推荐 3.9+)
- **内存**: 最少4GB RAM (推荐8GB+)
- **存储**: 500MB可用空间
- **网络**: 稳定的互联网连接 (用于AI API调用)

### 必需依赖
```bash
# AI对话功能
openai>=1.0.0
httpx>=0.24.0
tenacity>=8.0.0

# 语音功能
edge-tts>=6.1.0
pywin32>=306
pygame>=2.5.0

# 语音识别
SpeechRecognition>=3.10.0
pyaudio>=0.2.11
webrtcvad>=2.0.10

# 数据处理
requests>=2.28.0
numpy>=1.21.0
Pillow>=10.0.0
```

## 📦 安装指南

### 方法1: 自动安装（推荐）
```bash
# 1. 克隆项目
git clone https://github.com/YOUR_USERNAME/ai-voice-assistant.git
cd ai-voice-assistant

# 2. 运行自动安装脚本
python setup_virtual_env.py

# 3. 激活虚拟环境
activate_env.bat
```

### 方法2: 手动安装
```bash
# 1. 创建虚拟环境
python -m venv venv
venv\Scripts\activate

# 2. 安装依赖
pip install -r requirements_ai.txt

# 3. 配置API密钥
copy config.example.json config.json
# 编辑 config.json 文件，填入您的 DeepSeek API 密钥
```

### 方法3: Docker安装（开发中）
```bash
# 使用Docker运行（即将支持）
docker run -it ai-voice-assistant
```

## 🚀 快速开始

### 1. 配置API密钥
```bash
# 复制配置模板
copy config.example.json config.json

# 编辑配置文件，填入您的DeepSeek API密钥
notepad config.json
```

在 `config.json` 中设置您的API密钥：
```json
{
  "api": {
    "deepseek_api_key": "YOUR_DEEPSEEK_API_KEY_HERE"
  }
}
```

### 2. 启动应用
```bash
# 方法1: 使用启动脚本
start_assistant.bat

# 方法2: 直接运行
python ai_voice_assistant.py
```

### 3. 基础使用
1. **文本对话**: 在输入框中输入问题，点击发送
2. **语音对话**: 点击"🎤 语音"按钮启用语音模式
3. **天气查询**: 输入"北京今天天气怎么样？"
4. **IP查询**: 输入"我的IP地址是什么？"
5. **知识库**: 上传文档到知识库，然后提问相关内容

### 4. 功能演示
```python
# 天气查询示例
from weather_query_handler import handle_weather_query

result = handle_weather_query("北京今天天气怎么样？")
print(result["response"])

# IP查询示例
from ip_query_handler import handle_ip_query

result = handle_ip_query("我的IP地址是什么？")
print(result["response"])
```

## 📖 功能说明

### 🎯 主要功能模块

#### 智能对话
- **AI对话**: 与DeepSeek大语言模型进行自然语言对话
- **流式响应**: 支持实时流式对话，提升交互体验
- **上下文记忆**: 自动维护对话上下文和历史记录
- **多轮对话**: 支持复杂的多轮对话场景

#### 语音交互
- **语音识别**: 实时语音转文字，支持连续语音输入
- **语音合成**: 智能文字转语音，支持多种语音和语言
- **语音模式**: 一键切换语音对话模式
- **语音参数**: 可调节语速、音调、音量等参数

#### 天气查询
- **实时天气**: 查询全球主要城市当前天气
- **天气预报**: 获取未来5天天气预报
- **智能识别**: 自动识别天气查询意图
- **多语言支持**: 支持中英文天气查询

#### IP地理位置
- **IP查询**: 查询IP地址的地理位置信息
- **位置服务**: 获取详细的地理位置数据
- **网络信息**: 显示网络运营商和连接信息

#### 知识库系统
- **文档上传**: 支持多种格式文档上传
- **智能检索**: RAG技术增强的文档检索
- **知识问答**: 基于上传文档的智能问答
- **文档管理**: 完整的文档管理和组织功能

### 🎨 界面操作

#### 主界面
1. **对话区域**: 显示对话历史和AI回复
2. **输入框**: 输入文字消息或问题
3. **功能按钮**: 发送、语音、设置等快捷按钮
4. **状态栏**: 显示当前状态和处理进度

#### 设置界面
1. **API配置**: 配置DeepSeek API密钥和参数
2. **语音设置**: 选择TTS引擎和语音参数
3. **界面设置**: 调整主题、字体等界面选项
4. **功能开关**: 启用或禁用特定功能模块

## ⚙️ 配置指南

### API配置

#### DeepSeek API
1. 访问 [DeepSeek官网](https://www.deepseek.com/) 注册账号
2. 获取API密钥
3. 在 `config.json` 中配置：
```json
{
  "api": {
    "deepseek_api_key": "YOUR_API_KEY",
    "base_url": "https://api.deepseek.com",
    "model": "deepseek-chat",
    "max_tokens": 2000,
    "temperature": 0.7
  }
}
```

#### 天气API
项目已内置天气API密钥，无需额外配置。支持的API：
- **WeatherStack**: 实时天气和历史天气
- **OpenWeatherMap**: 天气预报
- **ipapi.co**: IP地理位置

### 语音配置

#### TTS引擎选择
```json
{
  "tts": {
    "engine": "edge",  // "edge" 或 "windows"
    "voice": "zh-CN-XiaoxiaoNeural",
    "rate": "+0%",
    "volume": "+0%",
    "auto_play": true
  }
}
```

#### 语音识别设置
```json
{
  "voice": {
    "recognition_engine": "whisper",
    "language": "zh-CN",
    "energy_threshold": 300,
    "pause_threshold": 0.8
  }
}
```

## 🔌 API集成

### 天气查询API
```python
from weather_query_handler import handle_weather_query

# 查询天气
result = handle_weather_query("北京今天天气怎么样？")
if result["success"]:
    print(result["response"])
    weather_data = result["weather_data"]
```

### IP查询API
```python
from ip_query_handler import handle_ip_query

# 查询IP信息
result = handle_ip_query("我的IP地址是什么？")
if result["success"]:
    print(result["response"])
    ip_data = result["ip_data"]
```

### 知识库API
```python
from rag_system import get_rag_system

# 初始化RAG系统
rag = get_rag_system()

# 添加文档
rag.add_document("document.pdf")

# 查询知识库
response = rag.query("相关问题")
```

### 语音合成API
```python
from smart_tts_manager import get_smart_tts_manager

# 初始化TTS管理器
tts = get_smart_tts_manager()

# 语音合成
await tts.speak_text("你好，这是语音合成测试")
```

## ❓ 常见问题

### Q1: 如何获取DeepSeek API密钥？
**A**:
1. 访问 [DeepSeek官网](https://www.deepseek.com/)
2. 注册账号并登录
3. 在控制台中创建API密钥
4. 将密钥配置到 `config.json` 文件中

### Q2: 程序启动失败怎么办？
**A**: 检查以下几点：
1. 确认Python版本为3.7+
2. 运行 `pip install -r requirements_ai.txt` 安装依赖
3. 检查 `config.json` 文件是否正确配置
4. 查看 `ai_voice_assistant.log` 日志文件

### Q3: 语音识别不工作怎么办？
**A**: 可能的解决方案：
1. 检查麦克风权限和设备
2. 安装 `pyaudio`: `pip install pyaudio`
3. 调整语音识别阈值参数
4. 确认系统音频设备正常

### Q4: 天气查询失败怎么办？
**A**: 天气查询失败可能原因：
1. 网络连接问题
2. API调用频率限制
3. 城市名称识别错误
4. 稍后重试或使用其他城市名称

### Q5: 如何添加自定义知识库？
**A**: 添加知识库的步骤：
1. 在界面中点击"知识库管理"
2. 上传PDF、TXT、DOCX等格式文档
3. 等待文档处理完成
4. 在对话中提问相关内容

## � 项目特色

### 🎯 技术亮点
- **模块化设计**: 清晰的模块分离，易于维护和扩展
- **异步处理**: 高性能的异步对话和语音合成
- **智能识别**: 自动识别用户意图，调用相应服务
- **多API集成**: 集成多个第三方API服务
- **实时交互**: 支持实时语音对话和流式响应

### 🔧 架构设计
```
智能语音助手
├── 核心程序层
│   ├── AI对话引擎 (DeepSeek)
│   ├── 语音合成引擎 (Edge TTS)
│   └── 语音识别引擎 (Whisper)
├── 扩展功能层
│   ├── 天气查询服务
│   ├── IP地理位置服务
│   └── RAG知识库系统
└── 用户界面层
    ├── GUI界面
    ├── 语音交互
    └── 配置管理
```

## 🤝 贡献指南

### 如何贡献
1. Fork 本项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

### 开发规范
- 遵循PEP 8代码规范
- 添加适当的注释和文档
- 编写单元测试
- 更新相关文档

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🙏 致谢

- [DeepSeek](https://www.deepseek.com/) - 提供强大的AI对话能力
- [Edge TTS](https://github.com/rany2/edge-tts) - 高质量的语音合成
- [WeatherStack](https://weatherstack.com/) - 天气数据服务
- [OpenWeatherMap](https://openweathermap.org/) - 天气预报服务
- [ipapi.co](https://ipapi.co/) - IP地理位置服务

## 📞 联系方式

如有问题或建议，请：
1. 查看 [使用指南](AI语音助手使用指南.md)
2. 查看 [常见问题](#常见问题) 部分
3. 提交 [Issue](https://github.com/YOUR_USERNAME/ai-voice-assistant/issues)
4. 发起 [Discussion](https://github.com/YOUR_USERNAME/ai-voice-assistant/discussions)

---

⭐ 如果这个项目对您有帮助，请给它一个星标！

**享受智能语音助手带来的便利！** 🎉