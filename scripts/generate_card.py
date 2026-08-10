#!/usr/bin/env python3
from __future__ import annotations

import argparse
import getpass
import json
import os
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


DEFAULT_BASE_URL = "https://rensheng-youji-ap-454189475786.asia-east1.run.app"
MAX_RESPONSE_BYTES = 16 * 1024 * 1024


class ClientError(RuntimeError):
    def __init__(self, message: str, exit_code: int) -> None:
        super().__init__(message)
        self.exit_code = exit_code


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="调用人生有迹私有服务并保存免费PNG卡片。"
    )
    parser.add_argument("--name", default="", help="姓名，可留空")
    parser.add_argument(
        "--birth", required=True, help="当地出生时间，格式 YYYY-MM-DD HH:MM"
    )
    parser.add_argument("--gender", required=True, choices=("male", "female"))
    parser.add_argument("--city", required=True)
    parser.add_argument("--country", default="中国")
    parser.add_argument(
        "--time-basis",
        choices=("local_civil", "true_solar_adjusted"),
        default="local_civil",
    )
    parser.add_argument("--timezone", default=None, help="可选IANA时区")
    parser.add_argument("--longitude", type=float, default=None)
    parser.add_argument("--output", default="rensheng-youji-card.png")
    parser.add_argument(
        "--accept-warnings",
        action="store_true",
        help="仅在用户已明确接受服务警告时继续出图",
    )
    return parser.parse_args()


def read_experience_code() -> str:
    code = os.environ.get("RSY_EXPERIENCE_CODE", "").strip()
    if not code:
        if sys.stdin.isatty():
            code = getpass.getpass("人生有迹一次性体验码：").strip()
        else:
            code = sys.stdin.readline().strip()
    if not code:
        raise ClientError("未提供一次性体验码。", 10)
    return code


def build_payload(args: argparse.Namespace) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "name": args.name,
        "birth": args.birth,
        "gender": args.gender,
        "city": args.city,
        "country": args.country,
        "time_basis": args.time_basis,
    }
    if args.timezone:
        payload["timezone"] = args.timezone
    if args.longitude is not None:
        payload["longitude"] = args.longitude
    return payload


def http_error(status: int) -> ClientError:
    messages = {
        401: ("体验码无效、已过期或已经成功使用。", 10),
        409: ("体验码已核销或出现并发冲突。", 11),
        422: ("出生资料未通过服务校验，请核对输入。", 12),
        503: ("人生有迹服务暂时不可用；未生成PNG时可使用原码重试。", 13),
    }
    message, exit_code = messages.get(
        status, (f"人生有迹服务返回HTTP {status}。", 20)
    )
    return ClientError(message, exit_code)


def post(base_url: str, path: str, payload: dict[str, Any], code: str) -> tuple[bytes, str]:
    request = urllib.request.Request(
        f"{base_url}{path}",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json", "X-API-Key": code},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            content = response.read(MAX_RESPONSE_BYTES + 1)
            if len(content) > MAX_RESPONSE_BYTES:
                raise ClientError("服务响应超过安全大小限制。", 20)
            return content, response.headers.get_content_type()
    except urllib.error.HTTPError as exc:
        raise http_error(exc.code) from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise ClientError("无法连接人生有迹服务；本次未确认生成PNG。", 20) from exc


def parse_prepared(content: bytes, content_type: str) -> dict[str, Any]:
    if content_type != "application/json":
        raise ClientError(f"准备接口返回了非JSON内容：{content_type}。", 20)
    try:
        prepared = json.loads(content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ClientError("准备接口返回的JSON无效。", 20) from exc
    if not isinstance(prepared, dict):
        raise ClientError("准备接口返回的数据结构无效。", 20)
    return prepared


def warning_texts(prepared: dict[str, Any]) -> list[str]:
    warnings = prepared.get("warnings", [])
    if warnings is None:
        return []
    if not isinstance(warnings, list):
        return ["服务返回了需要核实的时间或地点信息。"]
    return [str(item).strip() for item in warnings if str(item).strip()]


def print_warning_result(prepared: dict[str, Any], warnings: list[str]) -> None:
    summary = {
        "status": "needs_confirmation",
        "name": prepared.get("name", ""),
        "birthplace": prepared.get("birthplace", ""),
        "warnings": warnings,
        "code_consumed": False,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def save_png(content: bytes, content_type: str, output: Path) -> Path:
    if content_type != "image/png" or not content.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ClientError(f"出图接口没有返回有效PNG：{content_type}。", 20)
    output = output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(
        prefix=f".{output.stem}-", suffix=".tmp", dir=output.parent
    )
    temp_path = Path(temp_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, output)
    finally:
        if temp_path.exists():
            temp_path.unlink()
    return output


def main() -> int:
    args = parse_args()
    code = read_experience_code()
    payload = build_payload(args)
    base_url = os.environ.get("RENSHENG_API_BASE_URL", DEFAULT_BASE_URL).rstrip("/")

    prepared_bytes, prepared_type = post(base_url, "/generate", payload, code)
    prepared = parse_prepared(prepared_bytes, prepared_type)
    warnings = warning_texts(prepared)
    if warnings and not args.accept_warnings:
        print_warning_result(prepared, warnings)
        return 3

    card_bytes, card_type = post(base_url, "/render-card", payload, code)
    output = save_png(card_bytes, card_type, Path(args.output))
    result = {
        "status": "ok",
        "output": str(output),
        "time_basis": args.time_basis,
        "code_consumed": True,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ClientError as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, ensure_ascii=False))
        raise SystemExit(exc.exit_code) from None
