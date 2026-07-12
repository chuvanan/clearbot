# A guided tour of Clearbot

This tutorial walks you through Clearbot's features in the order that best builds intuition for how AI agents work. The whole point of the app is that **nothing is hidden** — after each step, open the Trace Inspector and confirm the mechanism with your own eyes.

## 0. Start the app

```bash
uv run shiny run app.py
```

Open the printed URL. Click the **Settings** label on the left to expand the sidebar — that is where every feature lives. The `📝 New Chat` button (top-right) clears the conversation at any time.

> **The most important habit:** after every model response, click the small `{…}` link next to it. This opens the **Trace Inspector**, showing the reconstructed **Request** (model, system prompt, tools, message history) and **Response** (message, finish reason, logprobs). Everything below is about watching these change.

### Optional: bring your own model (BYOK)

Clearbot ships with whichever providers your environment keys unlock, but it can talk to *any* OpenAI-compatible endpoint — a local model via Ollama, a vLLM/LiteLLM proxy, or a gateway like Groq or Together.

1. In **Model**, choose **Custom model + endpoint…**. Three fields appear.
2. Fill them in, e.g. for a local Ollama server: endpoint `http://localhost:11434/v1`, model `llama3.2`, and any non-empty key.
3. Chat as normal, then open the trace. Notice the request carries an `_endpoint` field pointing at your URL — but the API key is nowhere in it.

That last point is the lesson: the key is used only for the live call. It is never written into the URL bookmark or the trace, while the (non-secret) endpoint is shown so you can see exactly where the request went.

**Takeaway:** "which model" is just a base URL + a model string + a key — there is nothing provider-magic about it.

## 1. System prompt & temperature — the basic knobs

1. In the sidebar, set **System prompt** to `You are a pirate. Always answer in pirate speak.`
2. Send a message like `Tell me about the weather.`
3. Open the trace. Notice the `system` field carries your instruction — that single string is the entire "personality."
4. Now drag **Temperature** to `0` and ask the same thing twice, then to `2` and ask again. Low temperature is repetitive and safe; high temperature is wild. (Logprobs, OpenAI-only, lets you see the per-token probabilities behind this.)

**Takeaway:** "behavior" is mostly one string of text plus one sampling number.

## 2. Tools — letting the model act

1. Under **Tools**, check **Filesystem access**.
2. Ask: `What files are in the current directory?`
3. Watch the model call a tool. In the trace, the **Request** now has a `tools` array (the function schemas), and the message history contains a `tool_request` followed by a `tool_result`.

The model never touches your disk directly — it *requests* a tool call, the app runs it, and the result is fed back. Try **Custom tool code** too: paste a small function with a docstring, click **Register tools**, and ask the model to use it.

**Takeaway:** tools are just function schemas the model can request; the app does the actual work.

## 3. Commands — prompts as macros

1. The sidebar lists available **Slash commands** (e.g. `/summarize`, `/explain`, `/critique`).
2. In the chat, type: `/explain how does HTTPS work`
3. The chat shows what you typed, but open the trace: the user message is the **fully expanded template**, labeled with `_expanded_from_command`.

Commands are markdown files in `commands/`. Open `commands/explain.md` to see the template and the `$ARGUMENTS` placeholder. Add your own file and it appears automatically.

**Takeaway:** a slash command is a text-substitution macro — the model only ever sees the expanded prompt.

## 4. Skills — progressive disclosure

1. Under **Skills**, check **commit-messages**.
2. Ask: `Write a commit message for: added dark mode toggle to settings`
3. Open the trace and look at two things:
   - The `system` prompt now has an **"Available skills"** block — but it only contains the skill's *name and description*, not the instructions.
   - The model then issues a `load_skill` tool request, and the `tool_result` delivers the **full instructions**. The model reads them and only then writes the commit message.

This is exactly how Anthropic's Agent Skills work: cheap metadata is always present, and the expensive body is pulled in only when relevant. Skills live in `skills/<name>/SKILL.md`.

**Takeaway:** the model decides *when* to load detailed instructions, keeping context lean until a skill is actually needed.

## 5. Planning mode — a "mode" is prompt + tool gating

1. Check **Planning mode** and keep **Filesystem access** on.
2. Ask something multi-step: `Reorganize the files in this project into folders by type.`
3. The model responds with a plan and asks for approval. Open the trace and compare it to step 2's trace:
   - The `system` prompt has an extra **planning** instruction.
   - The `tools` array is **shorter** — the write tool (`set_current_dir`) has been removed, so the model *cannot* act even if it wanted to.
4. Click **✅ Approve & execute**. Planning mode turns off, the full toolset returns, and the model proceeds. Inspect that trace to see the difference.

**Takeaway:** there is no special "planning brain" — a mode is just an injected instruction plus a restricted toolset.

## 6. Memory / compaction — staying under the budget

1. Watch the **Memory** line in the sidebar: after provider responses, it shows Chatlas-reported input/output token usage and the number of turns.
2. Have a longer back-and-forth (5+ exchanges).
3. Click **🧹 Compact context**. A note appears: the conversation collapsed from N turns to a short summary plus the most recent turns, and the estimated context size drops.
4. Send one more message and open its trace: the message history now begins with a single **summary** turn instead of the full transcript.

You can automate this with **Auto-compact above estimated context tokens** — set it to a small number (e.g. `300`) and compaction triggers itself once the estimated context grows past that.

**Takeaway:** "memory" is not infinite — old turns get summarized so the important context survives within a finite window.

## Where to go next

- Open the files in `commands/` and `skills/` and add your own — no code changes needed.
- Read `prompting.py` and `toolsets.py`: these build the system prompt and tool list that *both* the live request and the trace use, which is why the inspector always tells the truth.
- Bookmark a session (the URL updates as you chat) and share it to reproduce a conversation.
