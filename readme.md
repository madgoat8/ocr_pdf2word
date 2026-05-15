移植到新电脑只需：
1. 复制整个目录
2. 安装 VC++ Redistributable x64
3. 有 NVIDIA 显卡 + CUDA
4. 双击 startServer.bat 启动 OCR 服务 → 双击 run.bat 执行转换

## 目录结构

```
ocr_pdf2word/
├── .gitignore
├── ocr.zip
├── readme.md
├── run.bat                  # 转换入口脚本 (Windows)
├── run.ps1                  # 转换入口脚本 (PowerShell)
├── startServer.bat          # 启动 OCR API 服务
├── stopServer.bat           # 停止 OCR API 服务
├── test_ocr.py              # OCR 测试脚本
├── test_ocr_curl.bat        # OCR 测试脚本 (curl)
├── ScreenShot_2026-05-13_162510_268.png
│
├── bak/                     # 备份目录
├── input/                   # 输入 PDF 文件目录
├── logs/                    # 日志文件目录
├── models/                  # 模型文件目录
├── output/                  # 输出 Word 文件目录
│
├── src/                     # 核心源代码
│   ├── __init__.py
│   ├── api_client.py        # API 客户端，调用 OCR 服务
│   ├── brace_detector.py    # 花括号/公式检测器
│   ├── config.py            # 配置加载模块
│   ├── config.yaml          # 配置文件
│   ├── correction.py        # OCR 结果纠错模块
│   ├── layout.py            # 版面分析模块
│   ├── main.py              # 主程序入口
│   ├── ocr_engine.py        # OCR 引擎封装
│   ├── pdf_loader.py        # PDF 加载与预处理
│   └── word_writer.py       # Word 文档生成器
│
├── python-3.11.5-embed-amd64/   # 嵌入式 Python 运行环境
│   ├── python.exe
│   ├── pymupdf/                  # PyMuPDF (PDF 处理)
│   ├── python_docx/               # python-docx (Word 生成)
│   ├── zhconv/                   # 中文简繁转换
│   ├── yaml/                     # PyYAML
│   └── ...
│
└── llama-b9158-bin-win-cuda-12.4-x64/  # llama.cpp (OCR 后端)
    ├── main.exe
    ├── server.exe
    └── ...
```