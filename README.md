# 桌面宠物露米娅（Rumia Pet）

> 一款面向中国大学生和研究生的桌面宠物应用，集成生活和学习功能，为校园生活增添便利与乐趣

## 项目简介

桌面宠物露米娅是一款基于PyQt5开发的桌面宠物应用，专为中国大学生和研究生设计。它不仅具有萌趣的外观和动作，还集成了生活和学习两个方向的多种实用功能，让你的电脑桌面更加生动有趣，同时为校园生活提供便利。

## 项目特色

- **萌趣可爱的宠物形象**：露米娅拥有多种表情和动作，会根据不同场景做出相应的反应
- **生活功能集成**：内置音乐播放、天气查询、股票搜索、校园集市、热点分析等实用工具
- **学习功能集成**：学校通知、日程管理、论文阅读与对话等学术辅助功能
- **个性化设置**：支持调整宠物大小、位置等，模仿经典桌面宠物的交互体验
- **互动性强**：可以通过点击、拖拽等方式与宠物互动

## 安装指南

### 环境要求

- Python 3.10.6 或更高版本
- CUDA 12.8
- 6GB 以上显存（推荐）

### 依赖安装

1. 克隆或下载项目到本地

2. 使用conda创建并激活环境
   ```sh
   conda create -n rumia-pet python=3.10.6
   conda activate rumia-pet
   ```

3. 安装CUDA 12.8对应的PyTorch
   ```sh
   pip install torch==2.7.1 torchvision==0.22.1 torchaudio==2.7.1 --index-url https://download.pytorch.org/whl/cu128
   ```

4. 安装核心依赖包
   ```sh
   pip install sentence-transformers==5.2.3 modelscope==1.34.0 faiss-cpu==1.13.2 scikit-learn==1.7.2 langchain==1.2.10 langchain-community==0.4.1 langchain-huggingface==1.2.1 PyQt6==6.10.2 PyQt6-WebEngine==6.10.0 markdown==3.10.2 pymdown-extensions==10.21 zhconv==1.4.3 openai==2.26.0 pypdf==6.7.5 pdf2image==1.17.0 pytesseract==0.3.13 pillow==12.1.1 langdetect==1.0.9 python-dotenv==1.2.2 tiktoken==0.12.0 magic-pdf==1.3.12 opencv-python==4.13.0.92 ultralytics==8.4.21 doclayout-yolo==0.0.4 rapid-table<2.0 transformers<4.52 safetensors<0.6 tokenizers<0.22 ftfy==6.3.1 dill==0.4.1 shapely==2.1.2 pyclipper==1.4.0 build==1.4.0
   ```

5. 安装语音与音频处理依赖
   ```sh
   pip install faster-whisper==1.1.1 SpeechRecognition==3.15.1 PyAudio==0.2.14 soundfile==0.13.1 realtimestt==0.3.104 openwakeword==0.6.0 pvporcupine==1.9.5
   ```

6. 安装数据处理与科学计算依赖
   ```sh
   pip install pandas==2.3.3 numpy==2.2.6 matplotlib==3.10.8 seaborn==0.13.2 polars==1.38.1
   ```

7. 安装网络请求与数据获取依赖
   ```sh
   pip install requests==2.32.5 beautifulsoup4==4.14.3 akshare==1.18.35
   ```

8. 安装自动化与打包工具
   ```sh
   pip install PyAutoGUI==0.9.54 pyinstaller==6.19.0 auto-py-to-exe==2.50.0
   ```

9. 安装其他依赖
   ```sh
   pip install langgraph==1.0.10 eel==0.18.2 pygame==2.6.1 albumentations==2.0.8 onnxruntime==1.23.2
   ```

10. 或者直接使用项目提供的requirements.txt文件安装
    ```sh
    pip install -r requirements.txt
    ```

### 字体安装

请双击 `./data/font/Lolita.ttf` 安装"萝莉体"字体，以确保界面显示正常。

### 启动方法

#### 运行源码

```sh
python rumia.py
```

#### 运行release版本

1. 将压缩包解压到任意文件夹下
2. 双击 `./data/font/Lolita.ttf` 安装"萝莉体"字体
3. 双击 `rumia.exe` 运行
4. 开始享受与露米娅的时光！

## 使用说明

### 基本操作

- **点击宠物**：与宠物互动，触发不同的表情和动作
- **拖拽宠物**：按住鼠标左键拖动宠物到任意位置
- **右键菜单**：点击右键打开功能菜单

### 功能模块

#### 生活功能

- **音乐播放器**：播放本地音乐文件，提供音乐控制功能
- **天气查询**：显示当前天气状况和未来天气预报
- **股票搜索**：搜索当前热门的十大股票内容，筛选涨幅情况并进行推荐，支持用户根据股票代码增加内容
- **校园集市吃瓜**：爬取校园集市的所有消息，筛选买卖相关内容供用户选择，当出现买卖相关内容时，后台第一时间提示用户
- **热点分析**：实时筛选B站、知乎、微博前30条热门信息供用户翻阅

#### 学习功能

- **学校通知模块**：爬取学校本科生院和研究生院的通知，支持关键词筛选
- **日程管理**：添加和管理个人日程，在时间快要截止时通知学生进度
- **论文阅读功能**：基于本地知识库，提供翻译论文和论文对话助手，采用TTS、STT、LLM和RAG知识增强技术，支持双栏阅读论文，用户可对话论文细节，享受动漫人声回应

### 个性化设置

- **自定义调节**：支持调整宠物大小、方位等
- **界面设置**：提供多种界面风格选择
- **通知设置**：自定义各类通知的提醒方式

## 项目结构

```
RumiaPet-main/
├── data/                 # 数据目录
│   ├── academic/         # 学术相关数据
│   ├── campus/           # 校园相关数据
│   ├── font/             # 字体文件
│   ├── icon/             # 图标文件
│   ├── rumia/            # 宠物形象和动作资源
│   ├── schedule/         # 日程数据
│   ├── web/              # 网络相关数据
│   └── crawler_config.json # 爬虫配置文件
│
├── ui/                   # 用户界面模块
│   ├── data/             # UI相关数据
│   ├── FetcherNews.py    # 新闻获取模块
│   ├── MusicPlayer.py    # 音乐播放器模块
│   ├── SchoolNotice.py   # 校园通知模块
│   ├── Spider_zano.py    # 爬虫模块
│   ├── WeatherUI.py      # 天气UI模块
│   ├── gupiao.py         # 股票模块
│   ├── petSettingUI.py   # 宠物设置UI模块
│   ├── scheduleUI.py     # 日程UI模块
│   └── webSettingUI.py   # 网络设置UI模块
│
├── utils/                # 工具模块
│   ├── config/           # 配置相关
│   ├── style/            # 样式相关
│   ├── fetcher_news.py   # 新闻获取工具
│   ├── pet.py            # 宠物核心逻辑
│   ├── realtimesst.log   # 实时语音识别日志
│   ├── spider_jishi.py   # 即时爬虫
│   ├── stt_module.py     # 语音转文本模块
│   ├── tts_module.py     # 文本转语音模块
│   └── weather_api.py    # 天气API调用
│
├── .gitignore            # Git忽略文件
├── README.md             # 项目说明文档
├── config.ini            # 配置文件
├── config2.ini           # 辅助配置文件
├── favicon.ico           # 应用图标
├── pack.bat              # 打包脚本
├── requirements.txt      # 依赖列表
└── rumia.py              # 主程序入口
```

## 已知问题

1. 在某些系统环境下，宠物可能会出现卡顿现象
2. 部分功能可能需要网络连接才能正常使用
3. 字体安装失败可能导致界面显示异常

## 许可证

本项目采用 MIT 许可证 - 详情见 LICENSE 文件

## 致谢

感谢所有为项目做出贡献的开发者和用户，希望露米娅能为你的电脑使用体验增添一份乐趣！
