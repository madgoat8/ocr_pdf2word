@echo off
chcp 65001 >nul
echo Testing PaddleOCR-VL-1.5 Inference Server...

set SERVER_URL=http://127.0.0.1:8000
set IMAGE_PATH=%~dp0ScreenShot_2026-05-13_162510_268.png

powershell -ExecutionPolicy Bypass -Command ^
    $img = [Convert]::ToBase64String([IO.File]::ReadAllBytes('%IMAGE_PATH%')); ^
    $body = @{prompt='Please recognize all text in this image.'; image_data='data:image/png;base64,'+$img} ^| ConvertTo-Json -Compress; ^
    Write-Host 'Sending request...' -ForegroundColor Green; ^
    Write-Host ''; ^
    Invoke-RestMethod -Uri '%SERVER_URL%/completion' -Method Post -Body $body -ContentType 'application/json' ^| ConvertTo-Json -Depth 10; ^
    Write-Host ''; ^
    Write-Host 'Done!' -ForegroundColor Green

pause
