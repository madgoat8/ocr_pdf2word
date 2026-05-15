@echo off
echo === PaddleOCR-VL-1.5 推理服务启动 ===

if not exist "models\PaddleOCR-VL-1.5.gguf" (
    echo [错误] 模型文件不存在！请先运行: python scripts\download_model.py
    pause
    exit /b 1
)

if not exist "llama-b9158-bin-win-cuda-12.4-x64\llama-server.exe" (
    echo [错误] llama-server.exe 不存在！
    pause
    exit /b 1
)

if not exist "models\PaddleOCR-VL-1.5-mmproj.gguf" (
    echo [错误] mmproj 投影仪文件不存在！
    pause
    exit /b 1
)

REM 针对4GB显存优化
set CUDA_VISIBLE_DEVICES=0
set GGML_CUDA_FORCE_MMQ=1

llama-b9158-bin-win-cuda-12.4-x64\llama-server.exe ^
    --model models\PaddleOCR-VL-1.5.gguf ^
    --mmproj models\PaddleOCR-VL-1.5-mmproj.gguf ^
    --host 127.0.0.1 ^
    --port 8000 ^
    --ctx-size 4096 ^
    --n-gpu-layers 35 ^
    --batch-size 512 ^
    --threads 4 ^
    --temp 0

pause