"""Dependency-free validator for the JSON Schema features used by this package."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any


def _resolve_ref(root: dict[str, Any], ref: str) -> dict[str, Any]:
    if not ref.startswith("#/"):
        raise ValueError(f"仅支持本地 $ref，收到 {ref}")
    value: Any = root
    for token in ref[2:].split("/"):
        token = token.replace("~1", "/").replace("~0", "~")
        value = value[token]
    if not isinstance(value, dict):
        raise ValueError(f"$ref 没有指向对象：{ref}")
    return value


def _type_matches(value: Any, expected: str) -> bool:
    if expected == "null":
        return value is None
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    return False


def _format_valid(value: str, format_name: str) -> bool:
    try:
        if format_name == "date":
            datetime.strptime(value, "%Y-%m-%d")
        elif format_name == "date-time":
            datetime.fromisoformat(value.replace("Z", "+00:00"))
        else:
            return True
    except ValueError:
        return False
    return True


def validate_schema_instance(
    value: Any,
    schema: dict[str, Any],
    root: dict[str, Any] | None = None,
    path: str = "$",
) -> list[str]:
    root = root or schema
    errors: list[str] = []

    if "$ref" in schema:
        return validate_schema_instance(value, _resolve_ref(root, schema["$ref"]), root, path)

    if "allOf" in schema:
        for child in schema["allOf"]:
            errors.extend(validate_schema_instance(value, child, root, path))

    if "oneOf" in schema:
        results = [validate_schema_instance(value, child, root, path) for child in schema["oneOf"]]
        matched = sum(not result for result in results)
        if matched != 1:
            errors.append(f"{path} 必须且只能匹配 oneOf 中的一个分支，当前匹配 {matched} 个")
        return errors

    if "const" in schema and value != schema["const"]:
        errors.append(f"{path} 必须等于 {schema['const']!r}")
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path} 的值 {value!r} 不在允许范围内")

    expected_types = schema.get("type")
    if expected_types is not None:
        if isinstance(expected_types, str):
            expected_types = [expected_types]
        if not any(_type_matches(value, item) for item in expected_types):
            errors.append(f"{path} 类型不符合要求：{expected_types}")
            return errors

    if isinstance(value, dict):
        required = set(schema.get("required", []))
        for key in sorted(required - value.keys()):
            errors.append(f"{path}.{key} 缺失")
        properties = schema.get("properties", {})
        for key, child in value.items():
            if key in properties:
                errors.extend(validate_schema_instance(child, properties[key], root, f"{path}.{key}"))
                continue
            additional = schema.get("additionalProperties", True)
            if additional is False:
                errors.append(f"{path}.{key} 是未定义字段")
            elif isinstance(additional, dict):
                errors.extend(validate_schema_instance(child, additional, root, f"{path}.{key}"))

    if isinstance(value, list):
        if "minItems" in schema and len(value) < schema["minItems"]:
            errors.append(f"{path} 至少需要 {schema['minItems']} 项")
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            errors.append(f"{path} 最多允许 {schema['maxItems']} 项")
        if schema.get("uniqueItems"):
            serialized = [json.dumps(item, ensure_ascii=False, sort_keys=True) for item in value]
            if len(serialized) != len(set(serialized)):
                errors.append(f"{path} 不允许重复项")
        if isinstance(schema.get("items"), dict):
            for index, child in enumerate(value):
                errors.extend(validate_schema_instance(child, schema["items"], root, f"{path}[{index}]"))

    if isinstance(value, str):
        if "minLength" in schema and len(value) < schema["minLength"]:
            errors.append(f"{path} 长度不能小于 {schema['minLength']}")
        if "format" in schema and not _format_valid(value, schema["format"]):
            errors.append(f"{path} 不符合 {schema['format']} 格式")

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            errors.append(f"{path} 不能小于 {schema['minimum']}")
        if "maximum" in schema and value > schema["maximum"]:
            errors.append(f"{path} 不能大于 {schema['maximum']}")

    return errors

