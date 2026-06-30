"""Resolve which predefined tools a request actually exposes to the model.

Centralized so the live request (app.py) and the reconstructed trace (traces.py)
agree on the exact tool list — including how planning mode shrinks it and how
skills add the `load_skill` tool. Custom (user-pasted) tools are handled
separately in app.py since they only exist at runtime.
"""

from typing import Callable

from models import RequestParams
from planning import filter_tools_for_planning
from skills import load_skill
from tools import all_tools


def resolve_tools(params: RequestParams) -> list[Callable]:
    """The predefined tool callables exposed for this request."""
    result: list[Callable] = []
    for toolset in params.tools:
        result.extend(all_tools[toolset])
    if params.skills:
        result.append(load_skill)
    if params.planning_mode:
        result = filter_tools_for_planning(result)
    return result
