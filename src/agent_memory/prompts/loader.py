from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


PROMPTS_DIR = Path(__file__).parent


def load_prompt(file_name: str, prompt_name: str) -> dict[str, str]:
    prompt_path = PROMPTS_DIR / file_name

    with prompt_path.open("r", encoding="utf-8") as file:
        prompts: dict[str, Any] = yaml.safe_load(file)

    prompt = prompts[prompt_name]

    return {
        "system": prompt["system"],
        "user": prompt["user"],
    }

