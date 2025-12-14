from __future__ import annotations
from typing import Any, Union
import requests

from .utils import _normalize_args


def _normalize_fields(fields: list[Any] | None) -> list["FieldLike"]:
    if not fields:
        return []
    result: list["FieldLike"] = []
    for f in fields:
        if isinstance(f, str):
            result.append(Field(f))
        else:
            result.append(f)
    return result


class Field:
    def __init__(
        self,
        name: str,
        args: dict[str, Any] | None = None,
        fields: list["FieldLike"] | None = None,
    ):
        self.name = name
        self.args = args or {}
        self.fields = _normalize_fields(fields)

    def to_string(self, indent: int = 0) -> str:
        tabs = " " * indent
        args_part = _normalize_args(self.args)
        if not self.fields:
            return f"{tabs}{self.name}{args_part}"
        inner = "\n".join(f.to_string(indent + 2) for f in self.fields)
        return f"{tabs}{self.name}{args_part} {{\n{inner}\n{tabs}}}"


class InlineFragment:
    def __init__(self, type_name: str, fields: list["FieldLike"]):
        self.type_name = type_name
        self.fields = _normalize_fields(fields)

    def to_string(self, indent: int = 0) -> str:
        tabs = " " * indent
        inner = "\n".join(f.to_string(indent + 2) for f in self.fields)
        return f"{tabs}... on {self.type_name} {{\n{inner}\n{tabs}}}"


FieldLike = Union[str, Field, InlineFragment]


class Query:
    def __init__(self, name: str, variables: dict[str, str], fields: list[FieldLike]):
        self.name = name
        self.variables = variables
        self.fields = _normalize_fields(fields)

    def to_string(self) -> str:
        var_def = ", ".join(f"${k}: {v}" for k, v in self.variables.items())
        inner = "\n".join(f.to_string(2) for f in self.fields)
        return f"query {self.name}({var_def}) {{\n{inner}\n}}"

    def execute(
        self,
        variables: dict[str, Any],
        token: str | None = None,
        endpoint: str = "https://api.github.com/graphql",
    ) -> dict:
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"

        response = requests.post(
            endpoint,
            headers=headers,
            json={"query": self.to_string(), "variables": variables},
        )

        if response.status_code != 200:
            raise RuntimeError(
                f"HTTP {response.status_code}: {response.text}"
            )

        data = response.json()
        if "errors" in data:
            raise RuntimeError(f"GraphQL errors: {data['errors']}")

        return data["data"]
