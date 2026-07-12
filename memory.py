"""Memory / compaction: keeping the conversation under the context budget.

A model's context window is finite. As a conversation grows, older turns are
summarized into a compact note so the important facts survive while the token
count shrinks. This module reports provider token usage when Chatlas has it,
keeps a rough context-size estimate for pre-request compaction decisions, and
performs compaction.

The mechanism is deliberately visible in the Trace Inspector: before compaction
the request carries many message turns; after, it carries a short summary turn
plus the few most-recent turns.
"""

import chatlas

from models import MyTurn, build_chat_client

SUMMARY_SYSTEM_PROMPT = (
    "You compress conversation history. Given a transcript of an earlier "
    "conversation, write a concise summary that preserves the user's goals, key "
    "facts, decisions, and any details needed to continue. Use compact bullet "
    "points. Do not add commentary or pleasantries."
)

SUMMARY_PREFIX = (
    "Here is a summary of the earlier part of our conversation. Use it as "
    "context for what follows.\n\n"
)

SUMMARY_ACK = "Understood — I'll continue with that context in mind."


def estimate_tokens(turns: list[MyTurn]) -> int:
    """Rough token estimate (~4 chars/token) across all turn contents."""
    chars = 0
    for turn in turns:
        for content in turn.contents:
            chars += len(str(content))
    return chars // 4


def chatlas_token_usage(turns: list[MyTurn]) -> dict[str, int] | None:
    """Aggregate Chatlas/provider-reported token usage from assistant turns.

    Chatlas stores provider usage on completed assistant turns as
    `(input_tokens, output_tokens, cached_input_tokens)`. These are reported by
    the provider after a request completes, so they are exact usage data when
    available. They are not available for manually-created turns such as the
    summary acknowledgement inserted by context compaction.
    """
    input_tokens = 0
    output_tokens = 0
    cached_input_tokens = 0
    found = False

    for turn in turns:
        tokens = getattr(turn, "tokens", None)
        if tokens is None:
            continue
        found = True
        input_tokens += tokens[0]
        output_tokens += tokens[1]
        cached_input_tokens += tokens[2]

    if not found:
        return None

    return {
        "input": input_tokens,
        "output": output_tokens,
        "cached_input": cached_input_tokens,
        "total": input_tokens + output_tokens + cached_input_tokens,
    }


def format_chatlas_token_usage(turns: list[MyTurn]) -> str:
    """Human-readable provider token usage for the sidebar."""
    usage = chatlas_token_usage(turns)
    turn_count = len(turns)
    if usage is None:
        return f"Provider token usage unavailable · {turn_count} turns in context"

    cached = ""
    if usage["cached_input"]:
        cached = f", {usage['cached_input']:,} cached input"

    return (
        "Token usage: "
        f"{usage['input']:,} input, {usage['output']:,} output{cached} "
        f"· {turn_count} turns in context"
    )


def _render_transcript(turns: list[MyTurn]) -> str:
    """Flatten turns into a plain-text transcript for the summarizer."""
    lines = []
    for turn in turns:
        text = "\n".join(str(c) for c in turn.contents)
        lines.append(f"{turn.role.upper()}: {text}")
    return "\n\n".join(lines)


async def compact_turns(
    turns: list[MyTurn],
    model: str,
    keep_recent: int = 2,
    *,
    base_url: str | None = None,
    api_key: str | None = None,
) -> list[MyTurn]:
    """Summarize older turns, keeping the last `keep_recent` turns verbatim.

    Returns a new turns list: [summary_user, summary_ack, *recent]. The recent
    slice is adjusted to start on a user turn so role alternation stays valid.
    Returns the input unchanged if there is too little to compact.

    `base_url`/`api_key` are forwarded to `build_chat_client` so compaction uses
    the same (possibly BYOK) endpoint as the conversation it is summarizing.
    """
    if len(turns) <= keep_recent + 1:
        return turns

    split = max(0, len(turns) - keep_recent)
    # Recent history must begin with a user turn (so summary_ack -> user alternates).
    while split < len(turns) and turns[split].role != "user":
        split += 1
    older, recent = turns[:split], turns[split:]
    if not older:
        return turns

    summarizer = build_chat_client(
        model, SUMMARY_SYSTEM_PROMPT, base_url=base_url, api_key=api_key
    )
    resp = await summarizer.stream_async(_render_transcript(older))
    summary = ""
    async for chunk in resp:
        summary += chunk

    summary_user = chatlas.Turn(SUMMARY_PREFIX + summary.strip(), role="user")
    summary_ack = chatlas.Turn(SUMMARY_ACK, role="assistant")
    return [summary_user, summary_ack] + list(recent)
