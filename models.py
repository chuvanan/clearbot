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

# Sentinel model id for "bring your own key": the user supplies a custom
# OpenAI-compatible endpoint, model name, and API key at runtime. Selecting it
# in the model picker reveals the BYOK inputs in the sidebar.
CUSTOM_MODEL_ID = "__custom__"

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

# BYOK is always available: even with no provider keys in the environment, a
# user can point Abidibot at any OpenAI-compatible endpoint with their own key.
# This is also why we no longer hard-fail when no env keys are found.
model_options["Custom (BYOK)"] = {CUSTOM_MODEL_ID: "Custom model + endpoint…"}

default_model = next(iter(next(iter(model_options.values())).keys()))


def supports_openai_reasoning(model: str) -> bool:
    """Whether an OpenAI model id accepts the Responses API reasoning param."""
    return model.startswith("o") or model.startswith("gpt-5")


class RequestParams(BaseModel):
    """A snapshot of the parameter values at the moment of a request"""

    model: str
    user_prompt: str
    system_prompt: str
    temperature: float
    tools: list[str]
    logprobs: bool = False
    thinking_enabled: bool = False
    thinking_effort: str = "medium"
    skills: list[str] = []
    planning_mode: bool = False
    command: str | None = None
    # BYOK: the custom endpoint a request was sent to. The model name lives in
    # `model`. We deliberately do NOT store the API key here — RequestParams is
    # bookmarked to the URL and shown in the Trace Inspector, so a secret must
    # never land in it. The base URL is not secret and is informative to show.
    base_url: str | None = None


class SessionState(BaseModel):
    turns: list[MyTurn]
    snapshots: list[tuple[RequestParams, list[MyTurn]]]
    custom_tool_code: str = ""


def build_chat_client(
    model: str,
    system_prompt: str,
    *,
    base_url: str | None = None,
    api_key: str | None = None,
    thinking_enabled: bool = False,
    thinking_effort: str = "medium",
) -> chatlas.Chat:
    """Construct a chatlas client for the given model id and system prompt.

    This is the single place that knows how to map a model to a concrete chatlas
    client.

    - BYOK: when `base_url` is given, the request goes to a custom
      OpenAI-compatible endpoint using the supplied `api_key` and `model` name.
      This covers local servers (Ollama, llama.cpp) and hosted gateways
      (Together, Groq, Fireworks, vLLM, …) — almost all speak the OpenAI API.
    - Otherwise the model id prefix selects a built-in provider.
    """
    reasoning = thinking_effort if thinking_enabled else None
    if base_url:
        # Use the Chat Completions API (not the Responses API) for custom
        # endpoints: it is the lowest common denominator that third-party
        # OpenAI-compatible backends actually implement.
        return chatlas.ChatOpenAICompletions(
            model=model,
            system_prompt=system_prompt,
            base_url=base_url,
            api_key=api_key,
            preserve_thinking=thinking_enabled,
        )
    if model.startswith("claude"):
        return chatlas.ChatAnthropic(
            model=model, system_prompt=system_prompt, reasoning=reasoning
        )
    elif model.startswith("gpt"):
        if not supports_openai_reasoning(model):
            reasoning = None
        return chatlas.ChatOpenAI(
            model=model, system_prompt=system_prompt, reasoning=reasoning
        )
    elif model.startswith("openrouter/"):
        return chatlas.ChatOpenRouter(
            model=model.removeprefix("openrouter/"),
            system_prompt=system_prompt,
        )
    else:
        raise ValueError(f"Unknown model: {model}")
