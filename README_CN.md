# RMBG-2.0 服务

基于 RMBG-2.0 模型的模块化、生产级 Python 服务，用于去除图片背景。

## 功能特性
- **RMBG-2.0 模型**：业内领先的背景去除效果。
- **FastAPI**：高性能、易于使用的 API。
- **批量处理**：支持多文件上传和 ZIP 压缩包响应。
- **Base64 支持**：易于与 Web 前端集成。
- **GPU 加速**：若有 CUDA 环境，将自动启用 GPU 加速。

## 安装指南

1.  **克隆仓库**（如果适用）或进入项目目录：
    ```bash
    cd rmbg-service
    ```

2.  **创建虚拟环境**（推荐）：
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **安装依赖**：
    ```bash
    pip install -r requirements.txt
    ```

4.  **Hugging Face 认证（必须）**：
    `briaai/RMBG-2.0` 是一个受限模型仓库。你需要：
    -   前往 [briaai/RMBG-2.0](https://huggingface.co/briaai/RMBG-2.0) 并接受许可协议。
    -   在 [Hugging Face Tokens](https://huggingface.co/settings/tokens) 创建一个访问令牌（Access Token）。
    -   在终端登录：
        ```bash
        python3 -c "from huggingface_hub import login; login()"
        # 当提示时粘贴你的 token
        ```
    -   **或者** 设置环境变量：
        ```bash
        export HF_TOKEN="你的token"
        ```

## 使用方法

1.  **启动服务器**：
    ```bash
    python3 run.py
    ```
    服务器将在 `http://0.0.0.0:8000` 启动。

2.  **API 文档**：
    在浏览器中打开 `http://localhost:8000/docs` 查看交互式 API 文档。

## API 接口

-   `GET /health`: 检查服务健康状态及模型加载情况。
-   `POST /remove-bg`: 上传图片（支持单张或多张）以去除背景。
-   `POST /remove-bg-base64`: 处理 Base64 编码的图片。

## 项目结构

-   `app/core/model.py`: 加载模型及处理图片的核心逻辑。
-   `app/api/endpoints.py`: API 路由处理程序。
-   `app/core/config.py`: 配置设置。
-   `run.py`: 启动脚本。
