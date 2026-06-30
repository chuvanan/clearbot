"""File-based skills, demonstrating progressive disclosure.

A skill lives in `skills/<name>/SKILL.md` with frontmatter (`name`,
`description`) and a markdown body of full instructions. The mechanism we teach:

  1. Only the skill *name + description* is injected into the system prompt.
  2. The full instructions are NOT in context until the model decides a skill is
     relevant and calls the `load_skill` tool to pull them in.

This is the real Anthropic Agent Skills pattern — metadata is cheap and always
present; the expensive body is loaded on demand. Learners can watch it happen in
the Trace Inspector: descriptions in the system prompt, then a `load_skill` tool
request/result delivering the body.
"""

from dataclasses import dataclass
from pathlib import Path

from commands import parse_frontmatter
from tools import safe_errors

SKILLS_DIR = Path(__file__).parent / "skills"


@dataclass
class Skill:
    name: str
    description: str
    instructions: str


def load_skills() -> dict[str, Skill]:
    """Load all skills from `skills/<name>/SKILL.md`, keyed by skill name."""
    skills: dict[str, Skill] = {}
    if not SKILLS_DIR.is_dir():
        return skills
    for skill_md in sorted(SKILLS_DIR.glob("*/SKILL.md")):
        meta, body = parse_frontmatter(skill_md.read_text(encoding="UTF-8"))
        name = meta.get("name", skill_md.parent.name)
        skills[name] = Skill(
            name=name,
            description=meta.get("description", ""),
            instructions=body.strip(),
        )
    return skills


def skills_system_prompt(enabled: list[str]) -> str:
    """Render the 'Available skills' block (names + descriptions only).

    Returns an empty string when no skills are enabled. The full instructions
    are deliberately omitted — they arrive only via the `load_skill` tool.
    """
    if not enabled:
        return ""
    skills = load_skills()
    lines = [
        "## Available skills",
        "",
        "You have access to the following skills. Each is a set of instructions "
        "for a particular kind of task. When a skill is relevant to the user's "
        "request, call the `load_skill` tool with its name to read the full "
        "instructions, then follow them.",
        "",
    ]
    for name in enabled:
        skill = skills.get(name)
        if skill is not None:
            lines.append(f"- **{skill.name}**: {skill.description}")
    return "\n".join(lines)


@safe_errors
def load_skill(name: str) -> str:
    """Load the full instructions for a skill by name. Call this when a skill
    listed under 'Available skills' is relevant, then follow what it returns."""
    skills = load_skills()
    skill = skills.get(name)
    if skill is None:
        available = ", ".join(skills.keys()) or "(none)"
        return f"No skill named '{name}'. Available skills: {available}"
    return skill.instructions
