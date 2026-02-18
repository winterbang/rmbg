# 项目目录与文件说明

本文档详细说明了 `rmbg-service` 项目中各个目录和文件的用途。

## 根目录结构

```text
rmbg-service/
├── app/                  # 核心应用逻辑代码
├── build/                # (Generated) PyInstaller 构建过程中的临时文件
├── dist/                 # (Generated) 构建完成的独立应用程序存放目录
├── docs/                 # 项目文档
├── build_app.py          # 桌面应用程序构建脚本
├── flet_app.py           # [核心] Flet 桌面应用入口代码
├── requirements.txt      # Python 依赖包列表
├── run.py                # API 服务的启动脚本
└── README.md             # 项目说明文档
```

## 详细文件说明

### 1. 核心代码 (`app/`)
- **`app/main.py`**: FastAPI 应用的入口文件，定义了 API 的路由和生命周期。
- **`app/core/`**: 核心逻辑层。
    - **`model.py`**: 包含 `BackgroundRemover` 类，负责模型的加载、图片预处理、推理（Inference）和后处理。这是去背景功能的核心。
    - **`config.py`**: 项目配置类 `Settings`，定义了模型路径、计算设备 (CUDA/MPS/CPU) 等参数。
- **`app/api/`**: API 接口定义。
    - **`endpoints.py`**: 定义了具体的 HTTP 接口，如 `/remove-bg`。

### 2. 桌面应用
- **`flet_app.py`**: 基于 Flet (Flutter) 的 GUI 应用程序。
    - 包含现代化 UI 界面、文件拖放、批量处理、图片预览等功能。
    - 集成了 API 服务启动功能。
- **`build_app.py`**: 用于将 `flet_app.py` 打包成独立可执行文件（`.app` 或 `.exe`）的脚本。

### 3. 构建产物
- **`dist/RMBG-Desktop/`**: 运行 `python build_app.py` 后生成的独立应用程序目录。包含可执行文件和所有依赖库。
- **`build/`**: 构建过程的中间文件，可随时删除。
- **`RMBG-Desktop.spec`**: PyInstaller 生成的配置文件，记录了打包参数。

### 4. 配置文件
- **`requirements.txt`**: 列出了项目运行所需的 Python 包，如 `torch`, `transformers`, `fastapi`, `flet` 等。

### 5. 文档 (`docs/`)
- **`architecture.md`**: 系统架构与功能模块说明。
- **`project_structure.md`**: (本文档) 目录结构说明。

## 关键路径说明
- **模型缓存**: 默认情况下，Hugging Face 的模型文件会下载到 `~/.cache/huggingface/` 目录。
- **图片导出**: 桌面应用默认会将处理后的图片导出到用户指定的目录，文件名前缀为 `no_bg_`。
