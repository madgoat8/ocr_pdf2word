import base64
import re
from io import BytesIO

import httpx
import numpy as np
from PIL import Image

LOC_PATTERN = re.compile(r"<\|LOC_(\d+)\|>")


class OcrVlApiClient:
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model_name: str,
        prompt: str = "Spotting:",
        max_tokens: int = 8192,
        timeout: int = 120,
    ):
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._model_name = model_name
        self._prompt = prompt
        self._max_tokens = max_tokens
        self._timeout = timeout

    def process_image(self, image: np.ndarray) -> str:
        b64 = _numpy_to_base64_jpeg(image)
        payload = {
            "model": self._model_name,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{b64}",
                            },
                        },
                        {"type": "text", "text": self._prompt},
                    ],
                }
            ],
            "max_tokens": self._max_tokens,
        }

        with httpx.Client(timeout=self._timeout) as client:
            resp = client.post(
                f"{self._base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()

        choices = data.get("choices", [])
        if not choices:
            raise RuntimeError(f"API 返回无 choices: {data}")

        content = choices[0].get("message", {}).get("content", "")
        return content or ""


def parse_spotting(
    text: str,
) -> list[tuple[str, tuple[int, int, int, int], list[list[float]]]]:
    results = []
    for line in text.strip().split("\n"):
        line = line.strip()
        if not line:
            continue

        loc_values = [int(m.group(1)) for m in LOC_PATTERN.finditer(line)]
        if len(loc_values) < 8:
            continue

        text_end = line.find("<|LOC_")
        if text_end == -1:
            continue
        line_text = line[:text_end].strip()
        if not line_text:
            continue

        xs = [loc_values[0], loc_values[2], loc_values[4], loc_values[6]]
        ys = [loc_values[1], loc_values[3], loc_values[5], loc_values[7]]
        bbox = (min(xs), min(ys), max(xs), max(ys))
        polygon = [
            [float(loc_values[0]), float(loc_values[1])],
            [float(loc_values[2]), float(loc_values[3])],
            [float(loc_values[4]), float(loc_values[5])],
            [float(loc_values[6]), float(loc_values[7])],
        ]
        results.append((line_text, bbox, polygon))

    if not results:
        for i, ln in enumerate(text.strip().split("\n")):
            ln = ln.strip()
            if not ln:
                continue
            y0 = i * 30
            y1 = y0 + 20
            bbox = (0, y0, 1000, y1)
            polygon = [[0, y0], [1000, y0], [1000, y1], [0, y1]]
            results.append((ln, bbox, polygon))

    return results


def _numpy_to_base64_jpeg(image: np.ndarray, quality: int = 90) -> str:
    pil_img = Image.fromarray(image)
    buf = BytesIO()
    pil_img.save(buf, format="JPEG", quality=quality)
    return base64.b64encode(buf.getvalue()).decode("ascii")
