@echo off
echo === 停止 PaddleOCR-VL-1.5 推理服务 ===
taskkill /f /im llama-server.exe 2>nul
echo 服务已停止
pause
