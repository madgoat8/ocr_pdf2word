#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试 PaddleOCR-VL-1.5 服务 (OpenAI 兼容 API)
"""
import base64
import requests

SERVER_URL = "http://127.0.0.1:8000"
IMAGE_PATH = r"d:\temp\202605\ScreenShot_2026-05-13_162510_268.png"


def test_ocr():
    print("=" * 60)
    print("开始测试 PaddleOCR-VL-1.5 服务")
    print("=" * 60)

    with open(IMAGE_PATH, "rb") as f:
        image_data = base64.b64encode(f.read()).decode("utf-8")

    print(f"图片已加载：{IMAGE_PATH}")
    print(f"图片大小：{len(image_data)} bytes (base64)\n")

    url = f"{SERVER_URL}/v1/chat/completions"

    payload = {
        "model": "PaddleOCR-VL",
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{image_data}"
                        }
                    },
                    {
                        "type": "text",
                        "text": "请识别这张图片中的所有文字内容，并按顺序输出。"
                    }
                ]
            }
        ],
        "max_tokens": 2048,
        "temperature": 0
    }

    print(f"正在请求：{url}")
    print("请稍候，正在识别图片内容...\n")

    try:
        response = requests.post(url, json=payload, timeout=120)
        response.raise_for_status()

        result = response.json()

        print("=" * 60)
        print("识别结果：")
        print("=" * 60)

        if "choices" in result and len(result["choices"]) > 0:
            content = result["choices"][0].get("message", {}).get("content", "")
            print(content)
        else:
            print(result)

        print("=" * 60)
        print("测试完成！")

    except requests.exceptions.ConnectionError:
        print("错误：无法连接到服务器！")
        print("请确保服务正在运行：http://127.0.0.1:8000")
    except requests.exceptions.Timeout:
        print("错误：请求超时！")
    except Exception as e:
        print(f"错误：{type(e).__name__}: {e}")


if __name__ == "__main__":
    test_ocr()