from __future__ import annotations

import json
import os
import urllib.request
from pathlib import Path


BASE_URL = os.environ.get(
    "RENSHENG_API_BASE_URL",
    "https://rensheng-youji-ap-454189475786.asia-east1.run.app",
).rstrip("/")
EXPERIENCE_CODE = os.environ["RENSHENG_API_KEY"]


def post(path: str, payload: dict) -> tuple[bytes, str]:
    request = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json", "X-API-Key": EXPERIENCE_CODE},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=180) as response:
        return response.read(), response.headers.get_content_type()


birth = {
    "name": "",
    "birth": "1999-01-22 17:45",
    "gender": "male",
    "city": "北京",
    "country": "中国",
    "time_basis": "local_civil",
}

# 准备阶段只预占体验码，不永久核销。
prepared_bytes, _ = post("/generate", birth)
prepared = json.loads(prepared_bytes)
print(json.dumps(prepared, ensure_ascii=False, indent=2))

# 使用完全相同的出生信息出图；成功返回PNG后体验码立即失效。
card_bytes, content_type = post("/render-card", birth)
assert content_type == "image/png"
assert card_bytes.startswith(b"\x89PNG\r\n\x1a\n")
Path("rensheng-youji-card.png").write_bytes(card_bytes)

