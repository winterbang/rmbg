# 项目架构与功能模块文档

## 1. 项目概述
本项目 (`rmbg-service`) 是一个基于深度学习模型 **RMBG-2.0** 的背景移除服务。项目已演进为支持多种部署形态：
- **Web API 服务**：基于 FastAPI 的高性能 RESTful 接口。
- **桌面应用程序**：基于 Flet (Flutter) 的现代化图形化界面工具。
- **CLI 工具**：支持命令行操作。

## 2. 系统架构图

```mermaid
graph TD
    User[用户 / 外部应用] -->|HTTP请求| API[API 服务 (FastAPI)]
    User -->|交互操作| GUI[桌面应用 (Flet)]
    
    subgraph Core[核心层 (app/core)]
        BR[BackgroundRemover (model.py)]
        Config[Settings (config.py)]
    end
    
    API --> BR
    GUI --> BR
    
    BR -->|加载/推理| Model[RMBG-2.0 模型 (HuggingFace)]
    BR -->|加速| Device[计算设备 (CUDA/MPS/CPU)]
```

## 3. 功能模块详解

### 3.1 核心层 (`app/core`)
这是项目的核心逻辑，被 API 和 GUI 共同复用。

- **`model.py` (BackgroundRemover)**
  - **职责**：负责模型的加载、预处理、推理和后处理。
  - **主要方法**：
    - `__init__`：根据配置自动选择设备 (CUDA/MPS/CPU) 并加载模型。
    - `remove_background(image)`：接收图片路径或 PIL 对象，返回去背后的 PIL 图片。
  - **特点**：单例模式设计（在 GUI 中通过线程持有），避免重复加载大模型。

- **`config.py` (Settings)**
  - **职责**：管理全局配置。
  - **关键参数**：
    - `DEVICE`：自动检测硬件加速（支持 NVIDIA CUDA 和 macOS MPS）。
    - `MODEL_ID`：指定 Hugging Face 模型 ID。

### 3.2 桌面应用层 (`flet_app.py`)
基于 Flet 构建的跨平台响应式 GUI。

- **UI 组件**
  - **Main Page**：Flet 页面容器，管理路由和主题。
  - **FilePicker**：原生文件/文件夹选择器。
  - **Preview Area**：使用 `ft.Image` 实时对比原图与处理结果。

- **并发架构**
  - **ModelLoaderThread**：后台线程加载模型，避免阻塞 UI。
  - **ProcessingThread**：批量处理逻辑运行在独立线程中，实时更新进度。
  - **ApiServerThread**：独立的 `uvicorn` 服务线程，支持一键开启/关闭 API 服务 (Port 8000)。

### 3.3 API 服务层 (`app/api`, `app/main.py`)
标准的 FastAPI 应用结构。

- **Endpoints**
  - `POST /remove-bg`：接收上传文件，返回处理后的图片。
  - `POST /remove-bg-base64`：接收 Base64 编码，适合 Web 前端调用。
  - `GET /health`：健康检查。

### 3.4 构建与部署 (`build_app.py`)
- 使用 **PyInstaller** 进行打包。
- 处理了 `transformers`, `torch`, `PIL` 等库的隐藏导入问题。
- 支持生成单文件或文件夹形式的可执行文件 (`dist/RMBG-Desktop`).

## 4. 数据流向

### 桌面端批量处理
1.  用户拖入图片列表 -> `files_to_process`。
2.  点击 "Start" -> 实例化 `ProcessingWorker`。
3.  Worker 线程 -> 调用 `BackgroundRemover.remove_background`。
4.  模型推理 (MPS/CUDA) -> 返回 PIL Image。
5.  Worker 信号 -> 更新 UI (Preview & Progress)。
6.  用户点击 "Export Results" -> 弹出文件夹选择器 -> 手动保存文件 (`no_bg_` 前缀)。

## 5. 依赖管理
项目依赖 `torch`, `torchvision`, `transformers` 等庞大的深度学习库。
- **环境隔离**：建议使用 `venv` 或 `conda`。
- **打包注意**：由于依赖包体积大，打包后的应用体积通常在 2GB 左右。

## 6. 扩展性
- **模型替换**：修改 `config.py` 中的 `MODEL_ID` 即可切换其他 Hugging Face 分割模型。
- **UI 定制**：基于 Flet/Flutter 的声明式 UI，易于修改主题和布局。
