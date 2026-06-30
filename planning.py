"""Planning mode: a 'mode' is just an injected instruction + a gated toolset.

There is nothing special the model does in "planning mode." We change two
things about the request and let the model behave accordingly:

  1. We append an instruction to the system prompt telling it to produce a plan
     and not to act yet.
  2. We remove state-changing tools from the toolset so it *cannot* act.

Learners can compare a planning-on trace against a planning-off trace and see
that the only differences are the extra system text and a shorter `tools` list.
"""

from typing import Callable

# Tools that change state on the user's machine. Removed while planning so the
# model can look but not touch.
WRITE_TOOLS = {"set_current_dir"}

PLANNING_SUFFIX = """\
## Planning mode

You are in PLANNING MODE. Produce a clear, numbered, step-by-step plan to
accomplish the user's request. Do NOT execute the plan or take any action that
changes state — you may only use read-only tools to gather information needed to
plan. End your response by asking the user to approve the plan before you
proceed."""


def planning_system_suffix() -> str:
    """The instruction block appended to the system prompt while planning."""
    return PLANNING_SUFFIX


def filter_tools_for_planning(tools: list[Callable]) -> list[Callable]:
    """Drop state-changing tools, leaving only read-only ones."""
    return [t for t in tools if t.__name__ not in WRITE_TOOLS]
