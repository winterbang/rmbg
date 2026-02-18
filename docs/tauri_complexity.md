# Tauri + Python 方案复杂度分析

如果您决定转向 Tauri 来获得极致的 UI 效果，以下是您需要面对的 **具体复杂性** 和 **工作量**：

## 1. 架构变更 (最大的复杂点)

Tauri 本质上是一个 Rust 写的 WebView 容器。为了运行您的 Python 代码，我们需要采用 **Sidecar (边车模式)**。

### 现在的架构 (PySide6)
- **单一进程**：GUI 和模型推理都在同一个 Python 进程中。
- **通信**：直接函数调用，或者是简单的 QThread 信号槽。
- **打包**：PyInstaller 一键打包所有内容。

### Tauri 架构
- **双进程**：
    1.  **Frontend (UI)**: 运行在 WebView 中 (HTML/JS/React)。
    2.  **Core (Rust)**: Tauri 的主进程。
    3.  **Sidecar (Python)**: 您的 `rmbg-service` 作为一个独立的二进制文件运行。
- **通信链路**：
    UI (JS) `<->` Rust `<->` Python (通过 Stdin/Stdout 或 HTTP)。
- **数据传输**：
    - 图片数据不能直接传递内存对象。
    - **必须**：
        1.  前端上传图片 -> 保存到临时文件。
        2.  通过命令告诉 Python 处理该文件路径。
        3.  Python 处理完保存结果 -> 告诉前端新文件路径。
        4.  前端读取显示。

## 2. 开发环境复杂度

您需要同时维护 **3种语言** 的环境：
1.  **Frontend**: Node.js, NPM/Yarn (React/Vue/Svelte)。
2.  **Rust**: 安装 Rust 编译器 (`cargo`)，用于编译 Tauri 后端。
3.  **Python**: 现有的环境。

## 3. 打包流程复杂度 (最头疼的部分)

PyInstaller 打包只是第一步。在 Tauri 中：
1.  **Python 打包**：您必须先用 PyInstaller 把 Python 代码打包成一个**独立的二进制文件** (`rmbg-cli`)。
    - *挑战*：这个二进制文件必须完美包含所有依赖 (Torch, Transformers)，体积巨大。
2.  **Tauri 配置**：在 `tauri.conf.json` 中配置 Sidecar 路径。
3.  **Rust 编译**：Tauri 会编译 Rust 代码，并将 Python 二进制文件打包进去。
4.  **最终产物**：生成的 `.app` 或 `.exe`。

## 4. 实际工作量评估

| 工作项 | 复杂度 | 说明 |
| :--- | :--- | :--- |
| **UI 重写** | 高 | 需要用 React/Vue 重写现在 PySide6 的所有界面逻辑。 |
| **通信层开发** | 中 | 实现 JS 调用 Rust，Rust 调用 Python Sidecar 的桥接代码。 |
| **Python 改造** | 中 | 将现有的 Python 代码改造为 CLI 工具，接受参数并输出结果 (JSON)。 |
| **环境搭建** | 中 | 安装 Node.js, Rust, 配置 Sidecar。 |
| **打包调试** | **极高** | 跨平台打包 Python Sidecar 经常会遇到路径、权限、依赖缺失等问题。 |

## 总结

- **如果不缺前端开发资源**，且对 UI 极其挑剔，Tauri 是值得的，因为做出来的效果是世界级的。
- **如果是个人开发者**，目前的 PySide6 方案在开发效率上是 **碾压级** 的优势。
- **折中方案**：如果只是嫌 Qt 丑，我们可以用 **Flet**。它用 Python 写 UI，但底层是 Flutter，效果比 Qt 现代很多，且无需折腾 Sidecar 和 Rust。
