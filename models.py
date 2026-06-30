"""Model configuration, request/session state, and chat-client construction.

Extracted from app.py so that every feature can reuse a single client factory
(`build_chat_client`) and a single place that knows which models are available.
"""

import os
from typing import TypeAlias

import chatlas
from dotenv import load_dotenv
from pydantic import BaseModel

# Load .env before reading API keys below. This module is imported before
# app.py's own load_dotenv() runs, so we must do it here too (it is idempotent).
load_dotenv()

MyTurn: TypeAlias = chatlas.Turn

model_options: dict[str, dict[str, str]] = {}

if "OPENAI_API_KEY" in os.environ:
    model_options["OpenAI"] = {
        "gpt-4.1": "GPT-4.1 (slowest, smartest)",
        "gpt-4.1-mini": "GPT-4.1 mini",
        "gpt-4.1-nano": "GPT-4.1 nano (fastest, cheapest)",
    }
if "ANTHROPIC_API_KEY" in os.environ:
    model_options["Anthropic"] = {
        "claude-opus-4-8": "claude-opus-4-8",
        "claude-sonnet-4-6": "claude-sonnet-4-6",
        "claude-haiku-4-5-20251001": "claude-haiku-4-5",
    }
if "OPENROUTER_API_KEY" in os.environ:
    model_options["OpenRouter"] = {
        "openrouter/anthropic/claude-sonnet-4-5": "Claude Sonnet 4.5",
        "openrouter/google/gemini-2.5-pro": "Gemini 2.5 Pro",
        "openrouter/meta-llama/llama-4-maverick": "Llama 4 Maverick",
        "openrouter/deepseek/deepseek-r1-0528": "DeepSeek R1",
        "openrouter/mistralai/mistral-small-3.2-24b-instruct": "Mistral Small 3.2",
    }

if len(model_options) == 0:
    raise ValueError(
        "No API keys found. Please set OPENAI_API_KEY, ANTHROPIC_API_KEY, and/or OPENROUTER_API_KEY in your environment."
    )

default_model = next(iter(next(iter(model_options.values())).keys()))


class RequestParams(BaseModel):
    """A snapshot of the parameter values at the moment of a request"""

    model: str
    user_prompt: str
    system_prompt: str
    temperature: float
    tools: list[str]
    logprobs: bool = False
    skills: list[str] = []
    planning_mode: bool = False
    command: str | None = None


class SessionState(BaseModel):
    turns: list[MyTurn]
    snapshots: list[tuple[RequestParams, list[MyTurn]]]
    custom_tool_code: str = ""


def build_chat_client(model: str, system_prompt: str) -> chatlas.Chat:
    """Construct a chatlas client for the given model id and system prompt.

    The model id prefix selects the provider. This is the single place that
    knows how to map a model id to a concrete chatlas client.
    """
    if model.startswith("claude"):
        return chatlas.ChatAnthropic(model=model, system_prompt=system_prompt)
    elif model.startswith("gpt"):
        return chatlas.ChatOpenAI(model=model, system_prompt=system_prompt)
    elif model.startswith("openrouter/"):
        return chatlas.ChatOpenRouter(
            model=model.removeprefix("openrouter/"),
            system_prompt=system_prompt,
        )
    else:
        raise ValueError(f"Unknown model: {model}")
