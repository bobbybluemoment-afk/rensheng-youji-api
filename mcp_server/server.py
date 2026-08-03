from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP


mcp = FastMCP("人生有迹")


def api_config() -> tuple[str, str]:
    base_url = os.environ.get("RENSHENG_API_BASE_URL", "").rstrip("/")
    api_key = os.environ.get("RENSHENG_API_KEY", "")
    if not base_url or not api_key:
        raise RuntimeError(
            "请配置 RENSHENG_API_BASE_URL 和 RENSHENG_API_KEY"
        )
    return base_url, api_key


def call_api(path: str, body: dict[str, Any]) -> tuple[bytes, str]:
    base_url, api_key = api_config()
    request = urllib.request.Request(
        f"{base_url}{path}",
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "X-API-Key": api_key,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return response.read(), response.headers.get_content_type()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"人生有迹 API 返回 {exc.code}: {detail}") from exc


@mcp.tool()
def prepare_birth_card(
    birth_datetime: str,
    gender: str,
    birth_city: str,
    country: str,
    name: str = "",
    time_basis: str = "local_legal_time",
    timezone: str | None = None,
    longitude: float | None = None,
) -> dict[str, Any]:
    """排出四柱并取得当前日柱配置。姓名可空；时间格式为 YYYY-MM-DD HH:mm。"""
    body: dict[str, Any] = {
        "name": name,
        "birth_datetime": birth_datetime,
        "gender": gender,
        "birth_city": birth_city,
        "country": country,
        "time_basis": time_basis,
    }
    if timezone is not None:
        body["timezone"] = timezone
    if longitude is not None:
        body["longitude"] = longitude
    content, content_type = call_api("/v1/prepare", body)
    if content_type != "application/json":
        raise RuntimeError(f"预期 JSON，实际收到 {content_type}")
    return json.loads(content)


@mcp.tool()
def render_birth_card(
    draft_token: str,
    core_mystic: str,
    core_plain: list[str],
    main_task: str,
    quote: str,
    quote_source: str,
    output_filename: str = "rensheng-youji-card.png",
) -> str:
    """提交模型生成的文案，渲染并保存 3:4 PNG 卡片；draft_token 只能使用一次。"""
    safe_name = Path(output_filename).name
    if not safe_name.lower().endswith(".png"):
        safe_name += ".png"
    output_dir = Path(os.environ.get("RENSHENG_OUTPUT_DIR", ".")).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    content, content_type = call_api(
        "/v1/render",
        {
            "draft_token": draft_token,
            "core_mystic": core_mystic,
            "core_plain": core_plain,
            "main_task": main_task,
            "quote": quote,
            "quote_source": quote_source,
        },
    )
    if content_type != "image/png":
        raise RuntimeError(f"预期 PNG，实际收到 {content_type}")
    output_path = output_dir / safe_name
    output_path.write_bytes(content)
    return f"卡片已保存：{output_path}"


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()

