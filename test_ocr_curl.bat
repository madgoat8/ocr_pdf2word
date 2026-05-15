@echo off
REM 使用 curl 测试 PaddleOCR-VL-1.5 服务

set SERVER_URL=http://127.0.0.1:8000
set IMAGE_PATH=d:\temp\202605\ScreenShot_2026-05-13_162510_268.png

echo ============================================================
echo 开始测试 PaddleOCR-VL-1.5 服务 (curl 版本)
echo ============================================================

REM 将图片转换为 base64
for /f "delims=" %%i in ('powershell -Command "[Convert]::ToBase64String([IO.File]::ReadAllBytes('%IMAGE_PATH%'))"') do set IMAGE_BASE64=%%i

echo 图片已加载：%IMAGE_PATH%
echo 正在请求服务...
echo.

REM 构建 JSON 请求
set JSON_PAYLOAD={"prompt": "请识别这张图片中的所有文字内容，并按顺序输出。", "image_data": "data:image/png;base64,%IMAGE_BASE64%"}

REM 发送请求
curl -X POST "%SERVER_URL%/completion" ^
  -H "Content-Type: application/json" ^
  -d "%JSON_PAYLOAD%"

echo.
echo ============================================================
echo 测试完成！
echo ============================================================

pause
