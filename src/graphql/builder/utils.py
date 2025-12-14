from __future__ import annotations
from typing import Any


def _to_graphql_value(value: Any) -> str:
    """Преобразует Python-значение в GraphQL literal."""
    if isinstance(value, str) and value.startswith("$"):
        return value
    if isinstance(value, list):
        return "[" + ", ".join(str(v) for v in value) + "]"
    if isinstance(value, dict):
        return "{" + ", ".join(f"{k}: {v}" for k, v in value.items()) + "}"
    if isinstance(value, str):
        return f'"{value}"'
    if isinstance(value, bool):
        return "true" if value else "false"
    
    return str(value)



def _normalize_args(args: dict[str, Any] | None) -> str:
    if not args:
        return ""
    return "(" + ", ".join(f"{k}: {_to_graphql_value(v)}" for k, v in args.items()) + ")"
