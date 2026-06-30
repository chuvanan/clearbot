# Clearbot

Clearbot is a chatbot UI designed to demystify how AI agents work. Instead of treating the model as a black box, it lets you toggle each mechanism on and off and **inspect the raw JSON** that is actually sent to and received from the model. The goal is to show that there is no magic — agent behavior is just prompt engineering, tool definitions, and context management.

It is built using [Shiny](https://shiny.posit.co/py/) (Python) and [Chatlas](https://posit-dev.github.io/chatlas/).

## Features

Each feature surfaces its underlying mechanism in the **Trace Inspector** (the `{…}` link next to each response).

- **System prompt, temperature, logprobs** — the basic knobs of an LLM call.
- **Tools** — toggle-able filesystem access and web search, plus a box to register your own Python functions as custom tools at runtime.
- **Commands** — file-based slash commands (`commands/*.md`). Typing `/summarize some text` expands a prompt template before anything reaches the model. The chat shows what you typed; the trace shows the expanded prompt. *Commands are just macros.*
- **Skills** — file-based skills (`skills/<name>/SKILL.md`). Only a skill's *name and description* are injected into the system prompt; the full instructions are loaded on demand when the model calls the `load_skill` tool. *This is progressive disclosure — visible in the trace.*
- **Planning mode** — a toggle that appends a "make a plan, don't act yet" instruction to the system prompt and removes state-changing tools. An **Approve & execute** button then re-runs with the full toolset. *A "mode" is just an injected instruction plus a gated toolset.*
- **Memory / compaction** — a running token estimate, a manual **Compact context** button, and an auto-compact threshold. Older turns are summarized into a compact note so the conversation stays under the context budget. *Watch a long history collapse into a summary in the trace.*
- **Trace Inspector** — inspect the reconstructed request (system prompt, tools schema, message history) and response (message, finish reason, logprobs) for any turn.

## Requirements

You can either set these environment variables manually, or include a [`.env` file](https://saurabh-kumar.com/python-dotenv/) in the root directory of your project.

At least one of the following environment variables is **required**:

- `OPENAI_API_KEY` — used to access OpenAI LLM models.
- `ANTHROPIC_API_KEY` — used to access Anthropic LLM models.
- `OPENROUTER_API_KEY` — used to access models via OpenRouter (Gemini, Llama, DeepSeek, Mistral, etc.).

### Web search

Web search is an optional feature that allows the chatbot to use Google to perform web searches. This involves creating a [Google Programmable Search Engine](https://programmablesearchengine.google.com/) and [getting an API Key](https://developers.google.com/custom-search/v1/introduction).

- `GOOGLE_SEARCH_ENGINE_ID` - The ID of your Programmable Search Engine instance. Roughly 18 hexadecimal characters.
- `GOOGLE_API_KEY` - Roughly 39 alphanumeric characters.

## Usage

Using uv:

```bash
uv run shiny run app.py
```

Alternatively, use `uv sync` to install the app's dependencies in a virtual environment, and then run the app with `shiny run app.py` (or using VS Code or Positron with the Shiny VS Code extension).

New to the app? Walk through [`TUTORIAL.md`](TUTORIAL.md) to explore each feature and see its mechanism in the trace.

## Project structure

| File | Responsibility |
| --- | --- |
| `app.py` | Shiny UI layout and server wiring. |
| `models.py` | Available models, request/session state, and the `build_chat_client` factory. |
| `tools.py` | Built-in tool definitions (`filesystem`, `websearch`). |
| `toolsets.py` | Resolves the effective tool list for a request (toolsets + skills + planning gating). |
| `prompting.py` | Builds the effective system prompt (user prompt + skills + planning). |
| `commands.py` | Loads and expands `commands/*.md` slash commands. |
| `skills.py` | Loads `skills/<name>/SKILL.md` and the `load_skill` tool. |
| `planning.py` | Planning-mode system suffix and tool gating. |
| `memory.py` | Token estimation and conversation compaction. |
| `traces.py` | Reconstructs the request/response JSON for the Trace Inspector. |

`prompting.py` and `toolsets.py` are the single source of truth shared by the live request and the trace, so what you inspect always matches what was actually sent.

To add your own command or skill, just drop a new markdown file into `commands/` or `skills/<name>/SKILL.md` — they are loaded automatically.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
