import inspect
import json
from html import escape
from pathlib import Path
from typing import Callable

from chatlas import StreamController
from dotenv import load_dotenv
from shiny import App, Inputs, Outputs, Session, bookmark, reactive, render, req, ui
from starlette.requests import Request

from commands import expand_command, load_commands
from memory import compact_turns, estimate_tokens, format_chatlas_token_usage
from models import (
    CUSTOM_MODEL_ID,
    MyTurn,
    RequestParams,
    SessionState,
    build_chat_client,
    default_model,
    model_options,
    supports_temperature,
)
from offcanvas import offcanvas_ui
from planning import save_plan
from prompting import build_system_prompt
from skills import load_skills
from toolsets import resolve_tools
from traces import reconstruct_request_traces, reconstruct_response_traces

load_dotenv()


def skills_ui():
    """Render the skills checkbox group for the sidebar.

    Only descriptions are shown here; the model likewise only sees descriptions
    until it calls `load_skill`.
    """
    skills = load_skills()
    if not skills:
        return ui.TagList()
    choices = {name: skill.name for name, skill in skills.items()}
    return ui.input_checkbox_group("skills", "Skills", choices)


def commands_help_ui():
    """Render the list of available slash commands for the sidebar."""
    cmds = load_commands()
    if cmds:
        items = "\n".join(f"- `/{c.name}` — {c.description}" for c in cmds.values())
    else:
        items = "_No commands found in `commands/`._"
    return ui.TagList(
        ui.hr(),
        ui.markdown("**Slash commands** (type in chat):"),
        ui.markdown(items),
    )


def app_ui(request: Request):
    return ui.page_sidebar(
        ui.sidebar(
            ui.input_select(
                "model",
                "Model",
                model_options,
                selected=default_model,
            ),
            ui.output_ui("byok_inputs"),
            ui.input_text_area("system_prompt", "System prompt", rows=6),
            ui.help_text("Instructs the LLM how to behave"),
            ui.output_ui("temperature_control"),
            ui.input_checkbox("logprobs", "Enable logprobs (OpenAI only)", value=False),
            ui.input_checkbox("thinking_enabled", "Enable thinking", value=False),
            ui.input_select(
                "thinking_effort",
                "Thinking effort",
                {
                    "low": "Low",
                    "medium": "Medium",
                    "high": "High",
                },
                selected="medium",
            ),
            ui.help_text("Provider-supported reasoning summaries/extended thinking."),
            ui.input_checkbox("planning_mode", "Planning mode", value=False),
            ui.help_text(
                "Asks for a plan first and hides write tools. Approve to execute."
            ),
            ui.input_checkbox_group(
                "tools",
                "Tools",
                {
                    "filesystem": "Filesystem access",
                    "websearch": "Web search",
                },
            ),
            skills_ui(),
            ui.markdown("⚠️ Runs arbitrary Python code."),
            ui.input_text_area(
                "custom_tool_code",
                "Custom tool code",
                rows=5,
                placeholder="def my_tool(name: str) -> str:\n    \"\"\"Say hello.\"\"\"\n    return f\"Hello, {name}!\"",
            ),
            ui.input_action_button("register_tools", "Register tools", class_="btn-sm"),
            ui.hr(),
            ui.markdown("**Memory**"),
            ui.output_text("token_estimate"),
            ui.input_numeric(
                "compact_threshold",
                "Auto-compact above estimated context tokens (0 = off)",
                value=0,
                min=0,
                step=500,
            ),
            ui.input_action_button(
                "compact", "🧹 Compact context", class_="btn-sm"
            ),
            commands_help_ui(),
            width=325,
            title="Settings",
            open="closed",
        ),
        offcanvas_ui(
            "trace",
            "Trace Inspector",
            ui.TagList(
                ui.input_select("trace_num", "Select a trace", []),
                ui.output_ui("trace_display"),
            ),
            style="--bs-offcanvas-width: min(600px, 100vw);",
        ),
        ui.chat_ui("chat"),
        ui.output_ui("stop_bar"),
        ui.output_ui("approval_bar"),
        ui.input_action_button(
            "clear",
            "📝 New Chat",
            class_="btn-sm",
            style="position: fixed; top: 0.75rem; right: 1.4rem; z-index: 100;",
        ),
        ui.head_content(
            ui.tags.script(src="json-viewer.js"),
            ui.tags.script(src="main.js"),
            ui.tags.style(
                """
                .help-block {
                    margin-top: -1em;
                }
                .thinking-block {
                    margin: 0.5rem 0 0.75rem;
                    padding: 0.5rem 0.75rem;
                    border-left: 3px solid #6c757d;
                    background: #f8f9fa;
                }
                .thinking-block summary {
                    cursor: pointer;
                    font-weight: 600;
                    margin-bottom: 0.35rem;
                }
                .thinking-content {
                    white-space: pre-wrap;
                    color: #495057;
                }
                """
            ),
        ),
        title="Abidibot",
        fillable=True,
    )


def server(input: Inputs, output: Outputs, session: Session):
    turns: reactive.Value[list[MyTurn]] = reactive.Value([])
    snapshots: reactive.Value[list[tuple[RequestParams, list[MyTurn]]]] = (
        reactive.Value([])
    )
    custom_tools: reactive.Value[list[Callable]] = reactive.Value([])
    awaiting_approval: reactive.Value[bool] = reactive.Value(False)
    # `is_streaming` drives the Stop button's visibility. The StreamController is
    # chatlas's cooperative-cancellation handle: the Stop button / Esc key call
    # `ctrl.cancel()`, which stops the stream *after the current chunk* so it
    # ends cleanly (the Chat widget gets its end signal and unlocks the input).
    is_streaming: reactive.Value[bool] = reactive.Value(False)
    ctrl = StreamController()

    chat = ui.Chat("chat")

    def selected_model_config() -> tuple[str, str | None, str | None]:
        """Resolve (model_name, base_url, api_key) for the current selection.

        For built-in providers, base_url/api_key are None (chatlas uses the
        provider default + env key). For BYOK, read the custom inputs — guarded,
        since they only exist in the DOM while the custom option is selected. The
        api_key is for live use only and is never persisted in RequestParams.
        """
        if input.model() != CUSTOM_MODEL_ID:
            return (input.model(), None, None)

        def field(name: str) -> str:
            return (input[name]() or "").strip() if name in input else ""

        return (
            field("custom_model"),
            field("custom_base_url") or None,
            field("custom_api_key") or None,
        )

    def current_params(user_prompt: str) -> RequestParams:
        model_name, base_url, _ = selected_model_config()
        return RequestParams(
            model=model_name,
            user_prompt=user_prompt,
            system_prompt=input.system_prompt(),
            temperature=input.temperature(),
            tools=input.tools(),
            logprobs=input.logprobs(),
            thinking_enabled=input.thinking_enabled(),
            thinking_effort=input.thinking_effort(),
            skills=list(input.skills()) if "skills" in input else [],
            planning_mode=input.planning_mode(),
            base_url=base_url,
        )

    def render_stream_chunk(chunk: object) -> str:
        """Render rich chatlas stream chunks for the Shiny chat."""
        if isinstance(chunk, str):
            return chunk

        content_type = getattr(chunk, "content_type", None)
        if content_type == "thinking_delta":
            phase = getattr(chunk, "phase", "body")
            thinking = escape(getattr(chunk, "thinking", ""))
            if phase == "start":
                return (
                    '<details class="thinking-block" open>'
                    "<summary>Thinking</summary>"
                    '<div class="thinking-content">'
                    f"{thinking}"
                )
            if phase == "end":
                return "</div></details>\n\n"
            return thinking

        # Tool request/result chunks are preserved in Chatlas turns and visible
        # in the trace; suppress them in the streamed assistant prose.
        return ""

    async def run_request(params: RequestParams):
        """Run one model request from a fully-resolved RequestParams.

        Shared by normal submits and the planning "Approve & execute" button so
        the request-building logic lives in exactly one place.
        """
        # BYOK needs both a model name and an endpoint; bail early with a clear
        # message rather than letting an empty request hit the provider.
        if input.model() == CUSTOM_MODEL_ID and not (params.model and params.base_url):
            ui.notification_show(
                "Custom model needs both a model name and an endpoint (base URL).",
                type="warning",
            )
            return

        these_turns = turns()

        api_key = selected_model_config()[2]
        chat_client = build_chat_client(
            params.model,
            build_system_prompt(params),
            base_url=params.base_url,
            api_key=api_key,
            thinking_enabled=params.thinking_enabled,
            thinking_effort=params.thinking_effort,
        )

        if these_turns:
            chat_client.set_turns(these_turns)

        # resolve_tools expands toolsets, adds load_skill when skills are
        # enabled (progressive disclosure), and drops write tools in planning
        # mode. The trace reconstructs from the same function, so they agree.
        for tool in resolve_tools(params):
            chat_client.register_tool(tool)

        # Custom (runtime) tools are also gated off while planning.
        if not params.planning_mode:
            for tool in custom_tools():
                chat_client.register_tool(tool)

        submit_kwargs: dict = {}
        if supports_temperature(params.model):
            submit_kwargs["temperature"] = params.temperature
        if params.logprobs and params.model.startswith("gpt"):
            submit_kwargs["log_probs"] = True

        ctrl.reset()
        resp = await chat_client.stream_async(
            params.user_prompt,
            content="all" if params.thinking_enabled else "text",
            kwargs=submit_kwargs,
            controller=ctrl,
        )

        async def gen():
            thinking_open = False
            async for chunk in resp:
                rendered = render_stream_chunk(chunk)
                if getattr(chunk, "content_type", None) == "thinking_delta":
                    phase = getattr(chunk, "phase", "body")
                    if phase == "start":
                        thinking_open = True
                    elif phase == "end":
                        thinking_open = False
                if rendered:
                    yield rendered
            if thinking_open:
                yield "</div></details>\n\n"
            with reactive.isolate():
                yield button_for_index(len(snapshots.get()))

        task = await chat.append_message_stream(gen())
        is_streaming.set(True)

        @reactive.Effect
        async def resp_on_complete():
            status = task.status()
            if status == "success":
                resp_on_complete.destroy()
                is_streaming.set(False)
                # chatlas preserves the partial turn on a cancelled stream, so
                # we commit either way — the truncated reply stays in context
                # and the conversation can continue normally.
                turns.set(chat_client.get_turns())
                snapshots.set(snapshots.get() + [(params, chat_client.get_turns())])
                with reactive.isolate():
                    ui.update_select(
                        "trace_num", choices=list(range(len(snapshots.get())))
                    )
                    # After a (completed) planning response, offer to approve.
                    awaiting_approval.set(params.planning_mode and not ctrl.cancelled)
                if params.planning_mode and not ctrl.cancelled:
                    plan_text = "\n".join(str(c) for c in turns.get()[-1].contents)
                    plan_path = save_plan(params.user_prompt, plan_text)
                    ui.notification_show(
                        f"Plan saved to {plan_path.relative_to(Path(__file__).parent)}",
                        action=ui.tags.a(
                            "Open plan",
                            href=plan_path.resolve().as_uri(),
                            target="_blank",
                        ),
                        type="message",
                        duration=None,
                    )
                if ctrl.cancelled:
                    await chat.append_message(
                        {
                            "role": "assistant",
                            "content": "⏹️ *Response interrupted. The partial reply above is kept in context.*",
                        }
                    )
                threshold = input.compact_threshold() or 0
                if threshold > 0 and estimate_tokens(turns.get()) > threshold:
                    await do_compaction(notify=False)
                await session.bookmark()
            if status in ["error", "cancelled"]:
                resp_on_complete.destroy()
                is_streaming.set(False)

    @chat.on_user_submit
    async def chat_on_user_submit(user_prompt: str):
        # Commands are just prompt macros: expand `/name args` into the
        # template before anything reaches the model. The chat UI still shows
        # what the user typed; the trace shows the expanded text.
        expanded_prompt, command_name = expand_command(user_prompt)
        params: RequestParams = current_params(expanded_prompt)
        params.command = command_name
        awaiting_approval.set(False)
        await run_request(params)

    @reactive.effect
    @reactive.event(input.approve_plan)
    async def approve_plan():
        # Approving a plan is just another turn — with planning mode off, so
        # the model now has the full toolset and is told to proceed.
        awaiting_approval.set(False)
        ui.update_checkbox("planning_mode", value=False)
        prompt = "The plan is approved. Proceed with executing it."
        await chat.append_message({"role": "user", "content": prompt})
        params = current_params(prompt)
        params.planning_mode = False
        await run_request(params)

    @session.bookmark.on_bookmarked
    async def session_on_bookmarked(url: str):
        print("session_on_bookmarked")
        await session.bookmark.update_query_string(mode="replace")

    @session.bookmark.on_bookmark
    def session_on_bookmark(state: bookmark.BookmarkState):
        ss = SessionState(
            turns=turns(),
            snapshots=snapshots(),
            custom_tool_code=input.custom_tool_code(),
        )
        print(ss.model_dump_json())
        state.values["session_state"] = ss.model_dump(mode="json")

    @session.bookmark.on_restore
    async def session_on_restore(state: bookmark.BookmarkState):
        if "session_state" in state.values:
            ss = SessionState.model_validate(state.values["session_state"])
            last_turns = ss.snapshots[-1][1]
            turns.set(last_turns)
            snapshots.set(ss.snapshots)
            ui.update_select("trace_num", choices=list(range(len(snapshots.get()))))

            if ss.custom_tool_code:
                ui.update_text_area("custom_tool_code", value=ss.custom_tool_code)
                local_ns: dict[str, object] = {"__builtins__": __builtins__}
                try:
                    exec(ss.custom_tool_code, local_ns)
                    tools = [
                        v
                        for v in local_ns.values()
                        if inspect.isfunction(v) and v.__doc__
                    ]
                    if tools:
                        custom_tools.set(tools)
                except Exception:
                    pass

            i = 0
            for turn in last_turns:
                if turn.role == "assistant":
                    suffix = button_for_index(i)
                    i += 1
                else:
                    suffix = ""
                await chat.append_message(
                    {
                        "role": turn.role,
                        "content": "\n".join([str(x) for x in turn.contents]) + suffix,
                    }
                )

    @reactive.effect
    @reactive.event(input.stop_stream)
    def stop_stream():
        # Cooperative cancel: chatlas stops the stream after the current chunk,
        # so it ends cleanly and the Chat input unlocks. Cancelling the asyncio
        # task directly would skip the stream's end signal and freeze the UI.
        ctrl.cancel()

    @reactive.effect
    @reactive.event(input.clear)
    async def clear_messages():
        await chat.clear_messages()
        turns.set([])
        snapshots.set([])
        awaiting_approval.set(False)

    @reactive.effect
    @reactive.event(input.register_tools)
    async def register_custom_tools():
        code = input.custom_tool_code()
        if not code.strip():
            custom_tools.set([])
            ui.notification_show("No custom tool code provided.", type="warning")
            return

        local_ns: dict[str, object] = {"__builtins__": __builtins__}
        try:
            exec(code, local_ns)
        except Exception as e:
            custom_tools.set([])
            ui.notification_show(f"Error parsing custom tool code: {e}", type="error")
            return

        tools = [
            v
            for v in local_ns.values()
            if inspect.isfunction(v) and v.__doc__
        ]

        if not tools:
            custom_tools.set([])
            ui.notification_show(
                "No valid functions found. Each function needs a docstring.",
                type="warning",
            )
            return

        custom_tools.set(tools)
        ui.notification_show(
            f"Registered {len(tools)} custom tool(s): {', '.join(t.__name__ for t in tools)}",
            type="message",
        )

    def button_for_index(i: int) -> str:
        return f"""\n\n<a class="text-decoration-none" href="#" data-snapshot-index="{i}" title="Inspect this request/response">{{…}}</a>"""

    @render.text
    def token_estimate():
        return format_chatlas_token_usage(turns())

    async def do_compaction(notify: bool) -> bool:
        """Compact the live context. Returns True if anything changed."""
        current = turns()
        before = estimate_tokens(current)
        model_name, base_url, api_key = selected_model_config()
        # compact_turns always keeps the last `keep_recent` turns verbatim, so
        # with 2 or fewer turns there is nothing older to summarize — even a
        # single oversized exchange would otherwise never compact. Drop the
        # recent-window in that case so it still gets summarized.
        keep_recent = 2 if len(current) > 2 else 0
        new_turns = await compact_turns(
            current, model_name, keep_recent=keep_recent, base_url=base_url, api_key=api_key
        )
        # Compaction always collapses to [summary_user, summary_ack, *recent],
        # so a short conversation can compact to the same turn count it
        # started with. Judge success by estimated token savings, not by
        # whether the turn count dropped.
        if new_turns is current or estimate_tokens(new_turns) >= before:
            if notify:
                ui.notification_show("Not enough history to compact.", type="message")
            return False
        turns.set(new_turns)
        after = estimate_tokens(new_turns)
        await chat.append_message(
            {
                "role": "assistant",
                "content": (
                    f"🧹 *Context compacted: {len(current)} → {len(new_turns)} turns, "
                    f"estimated context ~{before} → ~{after} tokens. Open the next "
                    f"trace to see the summary in the request.*"
                ),
            }
        )
        return True

    @reactive.effect
    @reactive.event(input.compact)
    async def manual_compact():
        await do_compaction(notify=True)

    @render.ui
    def temperature_control():
        # Reasoning models (gpt-5, o-series) reject a custom temperature value,
        # so swap the slider for an explanatory note instead of sending a value
        # the API would refuse.
        model_name = input.model()
        if model_name != CUSTOM_MODEL_ID and not supports_temperature(model_name):
            return ui.help_text(
                "Temperature is not configurable for this model — it only "
                "supports the API default."
            )
        return ui.TagList(
            ui.input_slider(
                "temperature", "Temperature", min=0, max=2, value=0.7, step=0.05
            ),
            ui.help_text("Lower for coherence, higher for randomness."),
        )

    @render.ui
    def byok_inputs():
        # Only shown when the custom model is selected. The API key uses a
        # password field and is never written to RequestParams/SessionState, so
        # it stays out of the URL bookmark and the Trace Inspector.
        if input.model() != CUSTOM_MODEL_ID:
            return None
        return ui.TagList(
            ui.input_text(
                "custom_base_url",
                "Endpoint (base URL)",
                placeholder="https://api.groq.com/openai/v1",
            ),
            ui.input_text(
                "custom_model",
                "Model name",
                placeholder="llama-3.3-70b-versatile",
            ),
            ui.input_password("custom_api_key", "API key"),
            ui.help_text(
                "Any OpenAI-compatible endpoint (Ollama, vLLM, Groq, Together…). "
                "The key is used only for live requests — never bookmarked or "
                "shown in the trace."
            ),
        )

    @render.ui
    def stop_bar():
        if not is_streaming():
            return None
        return ui.div(
            ui.input_action_button(
                "stop_stream",
                "⏹ Stop (Esc)",
                class_="btn-danger btn-sm",
            ),
            style=(
                "position: fixed; bottom: 5.5rem; left: 50%; "
                "transform: translateX(-50%); z-index: 100;"
            ),
        )

    @render.ui
    def approval_bar():
        if not awaiting_approval():
            return None
        return ui.div(
            ui.input_action_button(
                "approve_plan",
                "✅ Approve & execute",
                class_="btn-success btn-sm",
            ),
            style=(
                "position: fixed; bottom: 5.5rem; left: 50%; "
                "transform: translateX(-50%); z-index: 100;"
            ),
        )

    @render.ui
    def trace_display():
        req(len(snapshots()) > 0)
        (params, turns) = snapshots()[
            int(input.trace_num()) or 0
            if "trace_num" in input and input.trace_num() is not None
            else 0
        ]

        dump = reconstruct_request_traces(params, turns[0:-1])
        print(json.dumps(dump, indent=2))

        resp = reconstruct_response_traces(turns[-1])

        return ui.TagList(
            ui.h4("Request"),
            ui.Tag("json-viewer", data=json.dumps(dump)),
            ui.h4("Response", class_="mt-3"),
            ui.Tag("json-viewer", data=json.dumps(resp)),
        )


app = App(
    app_ui, server, bookmark_store="url", static_assets=Path(__file__).parent / "www"
)
