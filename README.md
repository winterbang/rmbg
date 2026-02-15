# RMBG-2.0 Service

[中文文档](README_CN.md)

A modular, production-ready Python service for removing image backgrounds using the RMBG-2.0 model.

## Features
- **RMBG-2.0 Model**: State-of-the-art background removal.
- **FastAPI**: High-performance, easy-to-use API.
- **Batch Processing**: Support for multiple file uploads and ZIP responses.
- **Base64 Support**: Easy integration with web frontends.
- **GPU Acceleration**: Automatically uses CUDA if available.

## Installation

1.  **Clone the repository** (if applicable) or navigate to the project directory:
    ```bash
    cd rmbg-service
    ```

2.  **Create a virtual environment** (recommended):
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Hugging Face Authentication (Required)**:
    The `briaai/RMBG-2.0` model is a gated repository. You need to:
    -   Go to [briaai/RMBG-2.0](https://huggingface.co/briaai/RMBG-2.0) and accept the license terms.
    -   Create an access token at [Hugging Face Tokens](https://huggingface.co/settings/tokens).
    -   Login in your terminal:
        ```bash
        python3 -c "from huggingface_hub import login; login()"
        # Paste your token when prompted
        ```
    -   **OR** set the environment variable:
        ```bash
        export HF_TOKEN="your_token_here"
        ```

## Usage

1.  **Start the server**:
    ```bash
    python3 run.py
    ```
    The server will start at `http://0.0.0.0:8000`.

2.  **API Documentation**:
    Open `http://localhost:8000/docs` in your browser to see the interactive API documentation.

## API Endpoints

-   `GET /health`: Check service health and model status.
-   `POST /remove-bg`: Upload image(s) to remove background.
-   `POST /remove-bg-base64`: Process base64 encoded images.

## Project Structure

-   `app/core/model.py`: Core logic for loading the model and processing images.
-   `app/api/endpoints.py`: API route handlers.
-   `app/core/config.py`: Configuration settings.
-   `run.py`: Entry point script.
