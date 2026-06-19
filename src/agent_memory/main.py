from __future__ import annotations

from pathlib import Path

from agent_memory.context.conversation.memory import ConversationMemory
from agent_memory.llm.anthropic import AnthropicChatModel
from agent_memory.llm.interface import ChatModel
from agent_memory.llm.openai_compatible import OpenAICompatibleChatModel
from agent_memory.settings import Settings
from agent_memory.settings import get_settings
from agent_memory.storage.sqlite import SQLiteStorage


def create_conversation_memory(
    database_path: Path | None = None,
) -> ConversationMemory:
    settings = get_settings()
    storage = SQLiteStorage(
        path=database_path or settings.sqlite_database_path,
    )

    return ConversationMemory(storage=storage)


def create_chat_model(settings: Settings | None = None) -> ChatModel:
    resolved_settings = settings or get_settings()

    if resolved_settings.model_api_key is None:
        raise RuntimeError(
            "AGENT_MEMORY_MODEL_API_KEY is required to use the chat command."
        )

    if resolved_settings.model_base_url is None:
        raise RuntimeError(
            "AGENT_MEMORY_MODEL_BASE_URL is required to use the chat command."
        )

    if resolved_settings.model_provider == "anthropic":
        return AnthropicChatModel(
            api_key=resolved_settings.model_api_key.get_secret_value(),
            model=resolved_settings.model_name,
            base_url=resolved_settings.model_base_url,
            anthropic_version=resolved_settings.anthropic_version,
            max_output_tokens=resolved_settings.model_max_output_tokens,
        )

    if resolved_settings.model_provider in {
        "deepseek",
        "openai",
        "openai-compatible",
    }:
        return OpenAICompatibleChatModel(
            api_key=resolved_settings.model_api_key.get_secret_value(),
            model=resolved_settings.model_name,
            base_url=resolved_settings.model_base_url,
            temperature=resolved_settings.model_temperature,
            max_output_tokens=resolved_settings.model_max_output_tokens,
        )

    raise RuntimeError(
        f"Unsupported model provider: {resolved_settings.model_provider}"
    )

def main() -> int:
    from agent_memory.cli import main as cli_main

    return cli_main()
