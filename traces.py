"""Reconstruct request/response JSON from chatlas Turns for the Trace Inspector.

These are pure functions that take stored snapshots and rebuild an approximation
of the raw payloads exchanged with the model API, so learners can inspect them.
"""

from typing import Iterable

import chatlas

from models import RequestParams, supports_openai_reasoning, supports_temperature
from prompting import build_system_prompt
from toolsets import resolve_tools


def _turn_contents_to_dicts(turn: chatlas.Turn) -> list[dict]:
    """Convert turn contents to serializable dicts using public API only."""
    results = []
    for content in turn.contents:
        if isinstance(content, chatlas.ContentToolRequest):
            results.append({
                "type": "tool_request",
                "id": content.id,
                "name": content.name,
                "arguments": content.arguments,
            })
        elif isinstance(content, chatlas.ContentToolResult):
            results.append({
                "type": "tool_result",
                "id": content.id,
                "value": str(content.get_model_value()),
            })
        elif getattr(content, "content_type", None) == "thinking":
            results.append({
                "type": "thinking",
                "thinking": getattr(content, "thinking", ""),
                "extra": getattr(content, "extra", None),
            })
        elif getattr(content, "content_type", None) == "thinking_delta":
            results.append({
                "type": "thinking_delta",
                "phase": getattr(content, "phase", "body"),
                "thinking": getattr(content, "thinking", ""),
            })
        else:
            results.append({
                "type": type(content).__name__,
                "text": str(content),
            })
    return results


def reconstruct_request_traces(
    params: RequestParams, turns: Iterable[chatlas.Turn]
) -> dict:
    tools_schema = [_tool_to_schema(t) for t in resolve_tools(params)]

    messages = [
        {"role": turn.role, "contents": _turn_contents_to_dicts(turn)}
        for turn in turns
    ]
    result = dict(
        model=params.model,
        system=build_system_prompt(params),
        tools=tools_schema,
        messages=messages,
    )
    if supports_temperature(params.model):
        result["temperature"] = params.temperature
    else:
        result["_temperature_not_supported"] = (
            "Selected model only supports the API default temperature."
        )
    if params.thinking_enabled:
        if params.model.startswith("gpt") and supports_openai_reasoning(params.model):
            result["reasoning"] = {
                "effort": params.thinking_effort,
                "summary": "auto",
            }
        elif params.model.startswith("gpt"):
            result["_thinking_not_requested"] = (
                "Selected OpenAI model is not reasoning-capable."
            )
        elif params.model.startswith("claude"):
            result["thinking"] = {"type": "adaptive"}
            result["output_config"] = {"effort": params.thinking_effort}
        else:
            result["_thinking_stream_display"] = True
        if params.base_url:
            result["_preserve_thinking"] = True
    if params.base_url:
        # BYOK: the custom endpoint this request was sent to. The API key is
        # intentionally absent here — it is never stored in the snapshot.
        result["_endpoint"] = params.base_url
    if params.command:
        # Annotation (not part of the real API payload): shows that the last
        # user message was produced by expanding this slash command.
        result["_expanded_from_command"] = params.command
    return result


def _tool_to_schema(tool) -> dict:
    """Build a JSON schema for a single tool callable."""
    try:
        from chatlas._tools import func_to_schema
        return func_to_schema(tool)
    except (ImportError, AttributeError):
        # Fallback: build a minimal schema from the function signature
        import inspect as _inspect
        sig = _inspect.signature(tool)
        return {
            "type": "function",
            "function": {
                "name": tool.__name__,
                "description": tool.__doc__ or "",
                "parameters": {
                    "type": "object",
                    "properties": {
                        name: {"type": "string"}
                        for name in sig.parameters
                    },
                },
            },
        }


def reconstruct_message(turn: chatlas.Turn) -> dict:
    return dict(
        role=turn.role,
        contents=_turn_contents_to_dicts(turn),
    )


def _extract_logprobs(turn: chatlas.Turn) -> list[dict] | None:
    """Extract logprobs from the raw completion object, if available."""
    completion = getattr(turn, "completion", None)
    if completion is None:
        return None
    logprobs_data = []
    for output_item in getattr(completion, "output", []):
        for content in getattr(output_item, "content", []):
            token_logprobs = getattr(content, "logprobs", None)
            if token_logprobs:
                for lp in token_logprobs:
                    entry = {
                        "token": lp.token,
                        "logprob": lp.logprob,
                    }
                    top = getattr(lp, "top_logprobs", None)
                    if top:
                        entry["top_logprobs"] = [
                            {"token": t.token, "logprob": t.logprob}
                            for t in top
                        ]
                    logprobs_data.append(entry)
    return logprobs_data or None


def reconstruct_response_traces(turn: chatlas.Turn) -> dict:
    assert turn.role == "assistant"

    result: dict = {
        "choices": [
            {"message": reconstruct_message(turn), "finish_reason": turn.finish_reason}
        ]
    }
    logprobs = _extract_logprobs(turn)
    if logprobs is not None:
        result["logprobs"] = logprobs
    return result
