"""Build the effective system prompt for a request.

Centralized here so that the live request (app.py) and the reconstructed trace
(traces.py) always agree on exactly what the model was told. Features that add
to the system prompt (skills, planning mode) plug in here.
"""

from models import RequestParams
from planning import planning_system_suffix
from skills import skills_system_prompt


def build_system_prompt(params: RequestParams) -> str:
    """Assemble the system prompt the model actually receives.

    Starts from the user's system prompt, then appends any feature blocks
    (skill descriptions, planning instructions). Returns the combined string.
    """
    parts: list[str] = []
    if params.system_prompt.strip():
        parts.append(params.system_prompt.strip())

    skills_block = skills_system_prompt(params.skills)
    if skills_block:
        parts.append(skills_block)

    if params.planning_mode:
        parts.append(planning_system_suffix())

    return "\n\n".join(parts)
