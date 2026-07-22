# Abidibot Demo Prompts

Use these prompts to demonstrate the app feature-by-feature. After each assistant
response, click the `{...}` trace link to show the reconstructed request and
response JSON.

## 1. Basic Chat + Trace Inspector

Sidebar setup: defaults.

Prompt:

```text
In 3 short bullets, explain what an AI agent is and how it differs from a normal chatbot.
```

Trace focus: model, temperature, system prompt, messages, and response shape.

## 2. System Prompt Injection

Sidebar setup: set System prompt to `You are a pirate tutor. Answer with nautical metaphors.`

Prompt:

```text
Explain tool calling to a beginner in two sentences.
```

Trace focus: the custom system prompt appears in the `system` field.

## 3. Temperature

Sidebar setup: run once with Temperature `0`, then again with Temperature `1.6`.

Prompt:

```text
Give me five names for a tiny robot that cleans a swimming pool.
```

Trace focus: the `temperature` value changes while the user message stays the
same.

## 4. Slash Commands Are Prompt Macros

Sidebar setup: defaults.

Prompt:

```text
/explain vector embeddings
```

Trace focus: the chat shows `/explain ...`, but the trace shows the expanded
prompt and `_expanded_from_command: explain`.

## 5. Summarize Command

Sidebar setup: defaults.

Prompt:

```text
/summarize Agents combine a language model with a loop. The loop receives user input, decides what to do, may call tools, observes the results, and then decides whether to continue or answer. This is useful because the model can interact with external systems instead of only producing text.
```

Trace focus: `/summarize` expands into the command template before the model sees
it.

## 6. Critique Command

Sidebar setup: defaults.

Prompt:

```text
/critique Our app is good because it has AI and tools and users will like it.
```

Trace focus: command expansion plus normal request/response storage.

## 7. Filesystem Tool: Read-Only Exploration

Sidebar setup: enable Tools > Filesystem access.

Prompt:

```text
Use your filesystem tools to list the current directory, read README.md if it exists, and tell me what this project appears to be.
```

Trace focus: tool schemas in `tools`, then tool request/result entries in the
response message contents.

## 8. Web Search Tool

Sidebar setup: enable Tools > Web search. Requires `GOOGLE_SEARCH_ENGINE_ID` and
`GOOGLE_API_KEY`.

Prompt:

```text
Search the web for the current Shiny for Python Chat component documentation, then give me the most relevant link and one sentence about why it matters for this app.
```

Trace focus: `google_search` and/or `http_get` are exposed as tools, and any
tool calls/results are visible.

## 9. Planning Mode: Read-Only First

Sidebar setup: enable Planning mode and Tools > Filesystem access.

Prompt:

```text
Plan how you would inspect this repository and propose one small documentation improvement. Do not edit anything until I approve.
```

Trace focus: the planning suffix is appended to `system`, and state-changing
tools such as `set_current_dir` are removed. After the response, show the
`Approve & execute` button (or `Cancel` to reject the plan and ask for a
revision instead).

## 10. Planning Approval

Sidebar setup: continue from the previous prompt, then click `Approve & execute`.

Prompt:

```text
The button sends this automatically: The plan is approved. Proceed with executing it.
```

Trace focus: the next request has Planning mode off and the full tool list is
available again.

## 11. Skills: Progressive Disclosure

Sidebar setup: enable Skills > regex-builder.

Prompt:

```text
Build a regex that matches ISO dates like 2026-07-21 but rejects 21-07-2026. Explain the pieces.
```

Trace focus: only the skill name/description appears in the system prompt at
first; the model must call `load_skill` to retrieve the full instructions.

## 12. Skills: Commit Message Format

Sidebar setup: enable Skills > commit-messages.

Prompt:

```text
Write a commit message for this change: added planning mode, gated write tools during planning, and added an approve button to execute the plan afterward.
```

Trace focus: `load_skill` returns the commit-message instructions only when the
skill is relevant.

## 13. Skills: CSV Profiler

Sidebar setup: enable Skills > csv-profiler.

Prompt:

```text
Profile this dataset:

id,name,signup_date,age,country
1,Ana,2024-01-03,29,US
2,Bilal,2024-01-04,,PK
3,Chen,2024-01-04,34,CN
4,Chen,2024-01-04,34,CN
5,Dana,03/01/2024,41,US
```

Trace focus: `load_skill` retrieves the profiling checklist, and the response
calls out the missing age, the duplicate row, and the inconsistent date
format.

## 14. Skills: Data Cleaning Checklist

Sidebar setup: enable Skills > data-cleaning-checklist.

Prompt:

```text
I have a customer signups CSV with some missing ages, a duplicate row, one date in a different format (03/01/2024 instead of 2024-01-03), and inconsistent country codes (US vs USA). Walk me through cleaning it before analysis.
```

Trace focus: the response follows the checklist order (missing values,
duplicates, type coercion, outliers, categorical normalization, documented
transformations) rather than an ad hoc list.

## 15. Skills: SQL Query Builder

Sidebar setup: enable Skills > sql-query-builder.

Prompt:

```text
Write a query to find the top 5 customers by total order value in the last 90 days, given tables customers(id, name) and orders(id, customer_id, amount, created_at).
```

Trace focus: the query is built clause by clause before the final code block,
and dialect/indexing notes appear.

## 16. Skills: Schema Design Review

Sidebar setup: enable Skills > schema-design-review.

Prompt:

```text
Review this schema: a single orders table with columns id, customer_name, customer_email, product_name, product_price, quantity, order_date. Is this well designed for a growing e-commerce app?
```

Trace focus: the response flags normalization issues (customer/product data
repeated per order) and proposes a split schema with keys.

## 17. Skills: Chart Recommender

Sidebar setup: enable Skills > chart-recommender.

Prompt:

```text
I have monthly revenue for the last 3 years across 4 product lines. I want to show how each product line's share of total revenue changed over time. What chart should I use?
```

Trace focus: the recommendation reasons about data shape (categorical x
numeric x time) before naming a chart, and includes example plotting code.

## 18. Custom Tool Registration

Sidebar setup: paste this into Custom tool code, click `Register tools`, then run
the prompt below.

```python
def calculate_pool_volume(length_m: float, width_m: float, depth_m: float) -> str:
    """Calculate rectangular pool volume in liters from dimensions in meters."""
    liters = float(length_m) * float(width_m) * float(depth_m) * 1000
    return f"{liters:,.0f} liters"
```

Prompt:

```text
Use the custom tool to calculate the volume of a pool that is 8 m long, 4 m wide, and 1.5 m deep. Then explain the formula.
```

Trace focus: runtime custom tools are registered for the live request. Compare
the streamed behavior with the trace's built-in tool list.

## 19. Logprobs

Sidebar setup: choose an OpenAI `gpt*` model and enable Logprobs.

Prompt:

```text
Answer with exactly one word: yes or no. Is water wet?
```

Trace focus: response JSON includes `logprobs` when the provider returns token
log probabilities.

## 20. Thinking / Reasoning

Sidebar setup: enable Thinking, choose effort `low`, `medium`, or `high`. Use a
reasoning-capable model when available.

Prompt:

```text
Solve this carefully: A robot has 3 batteries. Each battery powers it for 45 minutes. It spends 20 minutes cleaning, rests for 10 minutes, then repeats. How many full cleaning sessions can it complete?
```

Trace focus: request fields such as `reasoning`, `thinking`, or
`_thinking_stream_display` appear depending on provider/model support.

## 21. Stop / Interrupt

Sidebar setup: defaults. Start the prompt, then click `Stop (Esc)` while it is
streaming.

Prompt:

```text
Write a detailed 40-point checklist for evaluating an educational AI agent app. Make each point two sentences long.
```

Trace focus: the partial assistant turn is preserved in conversation context, and
the app unlocks the chat input cleanly.

## 22. Memory Token Estimate

Sidebar setup: defaults. Run this prompt a few times, then watch the Memory token
estimate in the sidebar.

Prompt:

```text
Add three more implementation notes to our running discussion of this app. Make them specific and non-overlapping.
```

Trace focus: each new request replays prior turns in `messages`, making context
growth visible.

## 23. Manual Context Compaction

Sidebar setup: after several turns, click `Compact context`.

Prompt:

```text
Based on everything we discussed so far, list the main decisions you remember.
```

Trace focus: after compaction, older turns are replaced by a summary turn plus
the most recent conversation turns.

## 24. Auto-Compaction Threshold

Sidebar setup: set Auto-compact threshold to a low value such as `500`, then send
a long prompt.

Prompt:

```text
Generate a detailed teaching script about AI agents, including sections on prompts, tools, traces, memory, planning, skills, and model settings.
```

Trace focus: when the estimated context crosses the threshold, compaction runs
automatically before the next trace-worthy request.

## 25. Custom Model / BYOK

Sidebar setup: choose Custom model + endpoint, provide an OpenAI-compatible base
URL, model name, and API key.

Prompt:

```text
Say which model name and endpoint style I configured, but do not reveal or infer any API key.
```

Trace focus: `_endpoint` and model name appear in the trace, but the API key is
intentionally absent.

## 26. New Chat

Sidebar setup: click `New Chat`, then run this prompt.

Prompt:

```text
What context from the previous conversation do you still have?
```

Trace focus: the `messages` list starts fresh after clearing chat history.

## 27. URL Bookmark / Restore

Sidebar setup: have at least one completed response, then copy/open the current
URL with query parameters in a new tab.

Prompt:

```text
Continue from the restored conversation and summarize the last assistant answer.
```

Trace focus: session state restores turns, snapshots, and custom tool code, while
secrets such as BYOK API keys are not stored.
