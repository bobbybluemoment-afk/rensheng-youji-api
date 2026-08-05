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

# 用你自己的模型根据prepared.bazi.analysis_context生成以下字段，并联网核对引文。
card_request = {
    **birth,
    "core_mystic": "甲木生丑月，寅为根，乙劫、癸印透出；丑戌见刑，酉官坐实。",
    "core_plain": [
        "你习惯在现实限制中先找到立足点，再逐步扩展。",
        "让短期成果服务长期方向，责任与资源才会成为支点。",
    ],
    "main_task": "在现实压力中建立长期结构，把责任与资源变成持续生长的支点。",
    "quote": "合抱之木，生于毫末；九层之台，起于累土。",
    "quote_source": "《道德经》第六十四章",
}
card_bytes, content_type = post("/render-card", card_request)
assert content_type == "image/png"
Path("rensheng-youji-card.png").write_bytes(card_bytes)

