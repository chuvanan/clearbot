"""Memory / compaction: keeping the conversation under the context budget.

A model's context window is finite. As a conversation grows, older turns are
summarized into a compact note so the important facts survive while the token
count shrinks. This module estimates the current size and performs compaction.

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


def _render_transcript(turns: list[MyTurn]) -> str:
    """Flatten turns into a plain-text transcript for the summarizer."""
    lines = []
    for turn in turns:
        text = "\n".join(str(c) for c in turn.contents)
        lines.append(f"{turn.role.upper()}: {text}")
    return "\n\n".join(lines)


async def compact_turns(
    turns: list[MyTurn], model: str, keep_recent: int = 2
) -> list[MyTurn]:
    """Summarize older turns, keeping the last `keep_recent` turns verbatim.

    Returns a new turns list: [summary_user, summary_ack, *recent]. The recent
    slice is adjusted to start on a user turn so role alternation stays valid.
    Returns the input unchanged if there is too little to compact.
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

    summarizer = build_chat_client(model, SUMMARY_SYSTEM_PROMPT)
    resp = await summarizer.stream_async(_render_transcript(older))
    summary = ""
    async for chunk in resp:
        summary += chunk

    summary_user = chatlas.Turn(SUMMARY_PREFIX + summary.strip(), role="user")
    summary_ack = chatlas.Turn(SUMMARY_ACK, role="assistant")
    return [summary_user, summary_ack] + list(recent)
