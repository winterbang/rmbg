# RMBG-2.0 打包与部署指南

本文档分析了如何将 `rmbg-service` 转化为桌面应用或移动端 APP，并提供了最佳实践建议。

## 1. 桌面客户端 (Windows / macOS / Linux)

### 方案 A：独立 Python 可执行文件 (PyInstaller)
**适用场景**：快速分发，无需用户安装 Python 环境。
**原理**：将 Python 解释器、依赖库、代码和模型打包成单一的 `.exe` 或 `.app`。

*   **优点**：开发成本低，直接复用现有 Python 代码。
*   **缺点**：
    *   **包体积巨大**：PyTorch + Transformers + 模型权重至少需要 **2GB - 3GB**。
    *   **启动慢**：解压资源需要时间。

**操作步骤**：
1.  安装 PyInstaller: `pip install pyinstaller`
2.  打包命令:
    ```bash
    pyinstaller --name "RMBG2.0" --onefile --add-data "path/to/model.safetensors:." run.py
    ```

### 方案 B：现代化桌面应用 (Tauri / Electron + Python Sidecar)
**适用场景**：需要漂亮的图形界面，且对体积稍有宽容。
**原理**：前端使用 Web 技术 (React/Vue)，后端运行精简后的 Python 服务（作为 Sidecar 进程）。

*   **优点**：界面美观，交互体验好。
*   **缺点**：依然面临 Python 环境体积大的问题。

## 2. 移动端 APP (iOS / Android)

**强烈不建议**直接在该服务基础上打包 Python 环境到手机，原因如下：
*   **体积过大**：APP 包体将超过 2GB，用户难以接受。
*   **性能差**：Python 在手机上运行效率低，且且难以利用 NPU 加速。
*   **发热严重**。

### 最佳方案：使用 ONNX Runtime
RMBG-2.0 官方已经提供了 **ONNX 格式** 的模型（包括 `fp16` 和 `int8` 量化版本），体积仅 **300MB - 500MB**，且可以直接在手机上通过 ONNX Runtime 高效运行。

**核心优势**：
*   **体积小**：量化后模型仅 ~370MB。
*   **速度快**：利用手机 NPU/GPU 加速，且无需将图片数据传到服务器。

### 3. 关于量化后的画质损失

您可能会关心：“变成 INT8 后，抠图效果会不会变差？”

答案是：**会有细微损失，但肉眼通常难以察觉。**

*   **FP16 (半精度)**：几乎无损，体积减半 (约 500MB)，推荐作为首选。
*   **INT8 (8位量化)**：
    *   **边缘精度**：在极细的发丝边缘可能会有 1-2 个像素的抖动或模糊。
    *   **主体识别**：主体识别能力基本不受影响。
    *   **体积**：进一步减小到 300MB 左右。

**建议策略**：
1.  **优先尝试 FP16**：如果包体大小能接受，优先用 FP16 版 ONNX 模型。
2.  **测试 INT8**：如果对包体极其敏感 (如 Android 低端机适配)，再考虑 INT8，并重点测试毛发等复杂场景。

**操作步骤**：
1.  **下载模型**：从 Hugging Face 下载 `model_int8.onnx` 或 `model_fp16.onnx`。
2.  **集成 SDK**：
    *   **iOS**: 使用 `onnxruntime-c` 或 `onnxruntime-swift`。
    *   **Android**: 使用 `onnxruntime-android`。
    *   **Flutter/React Native**: 使用对应的 ONNX 插件。
3.  **重写逻辑**：需用 Swift/Kotlin/Dart 重写 `preprocess_image` (Resize 1024x1024) 和 `postprocess_mask` 逻辑（其实很简单，就是缩放和矩阵运算）。

## 总结建议

| 平台 | 推荐方案 | 核心技术 | 预计体积 |
| :--- | :--- | :--- | :--- |
| **桌面端** | **Electron/Tauri** | Python Sidecar | ~2.5 GB |
| **移动端** | **Native APP** | ONNX Runtime | ~400 MB |
| **服务器** | **Docker** | Python/FastAPI | ~4 GB |
