from __future__ import annotations

import json
import os
import urllib.request
from pathlib import Path


BASE_URL = os.environ.get(
    "RENSHENG_API_BASE_URL",
    "https://rensheng-youji-ap-454189475786.asia-east1.run.app",
).rstrip("/")
API_KEY = os.environ["RENSHENG_API_KEY"]


def post(path: str, payload: dict) -> tuple[bytes, str]:
    request = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json", "X-API-Key": API_KEY},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        return response.read(), response.headers.get_content_type()


birth = {
    "name": "",
    "birth": "1999-01-22 17:45",
    "gender": "male",
    "city": "泉州",
    "country": "中国",
    "time_basis": "true_solar_adjusted",
}

prepared_bytes, _ = post("/generate", birth)
prepared = json.loads(prepared_bytes)
print(json.dumps(prepared, ensure_ascii=False, indent=2))

# /generate 已包含由人生有迹私有方法生成的 card_copy；渲染时只需同一份出生信息。
card_bytes, content_type = post("/render-card", birth)
assert content_type == "image/png"
Path("rensheng-youji-card.png").write_bytes(card_bytes)
