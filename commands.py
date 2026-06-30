"""File-based slash commands.

A command is just a *prompt template* stored in `commands/<name>.md`. When the
user types `/<name> some args`, we expand the template (substituting the args
into `$ARGUMENTS`) and send the expanded text to the model. The model never sees
the slash command — it only ever sees the expanded prompt. That is the whole
lesson: commands are macros, not magic.

File format (frontmatter is optional):

    ---
    description: One-line summary shown in the UI
    ---
    The prompt template body, using $ARGUMENTS as a placeholder.
"""

from dataclasses import dataclass
from pathlib import Path

COMMANDS_DIR = Path(__file__).parent / "commands"

ARGUMENTS_PLACEHOLDER = "$ARGUMENTS"


@dataclass
class Command:
    name: str
    description: str
    template: str


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """Split a markdown string into (frontmatter dict, body).

    Recognizes a leading `---` fenced block of simple `key: value` lines. This
    is a deliberately tiny parser so the project avoids a YAML dependency.
    """
    if text.startswith("---"):
        lines = text.splitlines()
        # lines[0] is the opening "---"; find the closing fence.
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                meta: dict[str, str] = {}
                for line in lines[1:i]:
                    if ":" in line:
                        key, _, value = line.partition(":")
                        meta[key.strip()] = value.strip()
                body = "\n".join(lines[i + 1 :]).lstrip("\n")
                return meta, body
    return {}, text


def load_commands() -> dict[str, Command]:
    """Load all commands from `commands/*.md`, keyed by command name."""
    commands: dict[str, Command] = {}
    if not COMMANDS_DIR.is_dir():
        return commands
    for path in sorted(COMMANDS_DIR.glob("*.md")):
        meta, body = parse_frontmatter(path.read_text(encoding="UTF-8"))
        name = path.stem
        commands[name] = Command(
            name=name,
            description=meta.get("description", ""),
            template=body.strip(),
        )
    return commands


def expand_command(user_prompt: str) -> tuple[str, str | None]:
    """Expand a `/command args` prompt into its template.

    Returns (expanded_prompt, matched_command_name). If the prompt is not a
    recognized command, returns the original prompt unchanged and None.
    """
    stripped = user_prompt.strip()
    if not stripped.startswith("/"):
        return user_prompt, None

    first, _, rest = stripped[1:].partition(" ")
    commands = load_commands()
    command = commands.get(first)
    if command is None:
        return user_prompt, None

    args = rest.strip()
    if ARGUMENTS_PLACEHOLDER in command.template:
        expanded = command.template.replace(ARGUMENTS_PLACEHOLDER, args)
    elif args:
        expanded = f"{command.template}\n\n{args}"
    else:
        expanded = command.template
    return expanded, command.name
