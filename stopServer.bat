@echo off
echo Stopping PaddleOCR-VL inference server...
taskkill /f /im llama-server.exe 2>nul
echo Server stopped.
pause
