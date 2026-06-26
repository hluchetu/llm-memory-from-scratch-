from __future__ import annotations

import json
from typing import Any


def parse_json_object(
    text: str,
    error_message: str = "Response must be a JSON object.",
) -> dict[str, Any]:
    stripped = text.strip()

    if stripped.startswith("```json"):
        stripped = stripped.removeprefix("```json").removesuffix("```").strip()
    elif stripped.startswith("```"):
        stripped = stripped.removeprefix("```").removesuffix("```").strip()

    payload = json.loads(stripped)

    if not isinstance(payload, dict):
        raise ValueError(error_message)

    return payload
