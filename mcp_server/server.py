from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP


DEFAULT_BASE_URL = "https://rensheng-youji-ap-454189475786.asia-east1.run.app"
mcp = FastMCP("人生有迹")


def api_config() -> tuple[str, str]:
    base_url = os.environ.get("RENSHENG_API_BASE_URL", DEFAULT_BASE_URL).rstrip("/")
    api_key = os.environ.get("RENSHENG_API_KEY", "")
    if not api_key:
        raise RuntimeError("请配置 RENSHENG_API_KEY；不要把密钥写入提示词或仓库")
    return base_url, api_key


def call_api(path: str, body: dict[str, Any], timeout: int = 120) -> tuple[bytes, str]:
    base_url, api_key = api_config()
    request = urllib.request.Request(
        f"{base_url}{path}",
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json", "X-API-Key": api_key},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read(), response.headers.get_content_type()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"人生有迹 API 返回 {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"无法连接人生有迹 API: {exc.reason}") from exc


def birth_payload(
    birth_datetime: str,
    gender: str,
    birth_city: str,
    country: str,
    name: str,
    time_basis: str,
    timezone: str | None,
    longitude: float | None,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "name": name,
        "birth": birth_datetime,
        "gender": gender,
        "city": birth_city,
        "country": country,
        "time_basis": time_basis,
    }
    if timezone is not None:
        body["timezone"] = timezone
    if longitude is not None:
        body["longitude"] = longitude
    return body


@mcp.tool()
def prepare_birth_card(
    birth_datetime: str,
    gender: str,
    birth_city: str,
    country: str = "中国",
    name: str = "",
    time_basis: str = "local_civil",
    timezone: str | None = None,
    longitude: float | None = None,
) -> dict[str, Any]:
    """校正时间并排出四柱。姓名可空；时间格式YYYY-MM-DD HH:mm。"""
    body = birth_payload(
        birth_datetime, gender, birth_city, country, name,
        time_basis, timezone, longitude,
    )
    content, content_type = call_api("/generate", body)
    if content_type != "application/json":
        raise RuntimeError(f"预期JSON，实际收到{content_type}")
    result = json.loads(content)
    result["writing_brief"] = {
        "method_order": "先判断月令、根气与透干，再从地支关系中只选一至两个最关键者。",
        "core_mystic": "8—90字的一句命理事实，不罗列全部关系。",
        "core_plain": "一至两句白话，每句不超过34字，写成可验证的倾向。",
        "main_task": "基于全盘反复张力提炼20—36个汉字，不从日柱单独推演。",
        "quote": "10—30字真实古诗文或经典原句；调用模型必须联网核对。",
        "quote_source": "标注准确篇名和出处，不拼接、改写或伪造。",
        "safety": "不用注定、必然、灾等恐吓表达；不提供确定性医疗、法律或金融判断。",
    }
    return result


@mcp.tool()
def render_birth_card(
    birth_datetime: str,
    gender: str,
    birth_city: str,
    core_mystic: str,
    core_plain: list[str],
    main_task: str,
    quote: str,
    quote_source: str,
    country: str = "中国",
    name: str = "",
    time_basis: str = "local_civil",
    timezone: str | None = None,
    longitude: float | None = None,
    output_filename: str = "rensheng-youji-card.png",
) -> str:
    """提交已核对文案，渲染并保存1242×1660 PNG卡片。"""
    safe_name = Path(output_filename).name
    if not safe_name.lower().endswith(".png"):
        safe_name += ".png"
    body = birth_payload(
        birth_datetime, gender, birth_city, country, name,
        time_basis, timezone, longitude,
    )
    body.update({
        "core_mystic": core_mystic,
        "core_plain": core_plain,
        "main_task": main_task,
        "quote": quote,
        "quote_source": quote_source,
    })
    content, content_type = call_api("/render-card", body)
    if content_type != "image/png":
        raise RuntimeError(f"预期PNG，实际收到{content_type}")
    output_dir = Path(os.environ.get("RENSHENG_OUTPUT_DIR", ".")).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / safe_name
    output_path.write_bytes(content)
    return f"卡片已保存：{output_path}"


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()

