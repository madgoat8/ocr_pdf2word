@echo off
echo === Starting PaddleOCR-VL-1.6 Inference Server ===

if not exist "models\PaddleOCR-VL-1.6-GGUF.gguf" (
    echo [ERROR] Model file not found! Please run: python scripts\download_model.py
    pause
    exit /b 1
)

if not exist "llama-b9158-bin-win-cuda-12.4-x64\llama-server.exe" (
    echo [ERROR] llama-server.exe not found!
    pause
    exit /b 1
)

if not exist "models\PaddleOCR-VL-1.6-GGUF-mmproj.gguf" (
    echo [ERROR] mmproj file not found!
    pause
    exit /b 1
)

REM Optimized for 4GB VRAM
set CUDA_VISIBLE_DEVICES=0
set GGML_CUDA_FORCE_MMQ=1

llama-b9158-bin-win-cuda-12.4-x64\llama-server.exe ^
    --model models\PaddleOCR-VL-1.6-GGUF.gguf ^
    --mmproj models\PaddleOCR-VL-1.6-GGUF-mmproj.gguf ^
    --host 127.0.0.1 ^
    --port 8000 ^
    --ctx-size 4096 ^
    --n-gpu-layers 35 ^
    --batch-size 512 ^
    --threads 4 ^
    --temp 0

pause
