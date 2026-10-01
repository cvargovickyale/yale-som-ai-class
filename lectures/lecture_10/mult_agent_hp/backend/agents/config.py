"""Portkey / model configuration.

Loads .env files from this project folder upward, so the real PORTKEY_API_KEY
can stay in the workspace root .env instead of being copied here. The nearest
file wins because load_dotenv never overrides a value that is already set.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from openai import AsyncOpenAI
from pydantic_ai.models.openai import OpenAIResponsesModel
from pydantic_ai.providers.openai import OpenAIProvider

BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BACKEND_DIR.parent

for folder in (PROJECT_ROOT, *PROJECT_ROOT.parents):
    env_file = folder / ".env"
    if env_file.is_file():
        load_dotenv(env_file)

BOSS_NAME = "Albus Dumbledore"
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-6-luna")
PORTKEY_BASE_URL = os.getenv("PORTKEY_BASE_URL", "https://api.portkey.ai/v1")


def require_api_key() -> str:
    key = os.getenv("PORTKEY_API_KEY", "").strip()
    if not key:
        raise RuntimeError(
            "PORTKEY_API_KEY is not set. Add it to a .env file in this project "
            "or any parent folder."
        )
    return key


def build_model() -> OpenAIResponsesModel:
    """OpenAI model routed through Portkey.

    Uses the Responses API: gpt-6-luna rejects function tools on
    /v1/chat/completions while reasoning is on.
    """
    key = require_api_key()
    client = AsyncOpenAI(
        api_key=key,
        base_url=PORTKEY_BASE_URL,
        default_headers={"x-portkey-api-key": key},
    )
    return OpenAIResponsesModel(MODEL_NAME, provider=OpenAIProvider(openai_client=client))
