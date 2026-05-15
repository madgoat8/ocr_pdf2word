@echo off
chcp 65001 >nul
powershell -ExecutionPolicy Bypass -File ".\run.ps1"
pause
