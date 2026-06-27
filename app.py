import inspect
import json
import os
from pathlib import Path
from typing import Callable, Iterable, TypeAlias

import chatlas
from dotenv import load_dotenv
from pydantic import BaseModel
from shiny import App, Inputs, Outputs, Session, bookmark, reactive, render, req, ui
from starlette.requests import Request

from offcanvas import offcanvas_ui
from tools import all_tools

MyTurn: TypeAlias = chatlas.Turn

load_dotenv()

model_options = {}

if "OPENAI_API_KEY" in os.environ:
    model_options["OpenAI"] = {
        "gpt-4.1": "GPT-4.1 (slowest, smartest)",
        "gpt-4.1-mini": "GPT-4.1 mini",
        "gpt-4.1-nano": "GPT-4.1 nano (fastest, cheapest)",
    }
if "ANTHROPIC_API_KEY" in os.environ:
    model_options["Anthropic"] = {
        "claude-opus-4-8": "claude-opus-4-8",
        "claude-sonnet-4-6": "claude-sonnet-4-6",
        "claude-haiku-4-5-20251001": "claude-haiku-4-5",
    }
if "OPENROUTER_API_KEY" in os.environ:
    model_options["OpenRouter"] = {
        "openrouter/anthropic/claude-sonnet-4-5": "Claude Sonnet 4.5",
        "openrouter/google/gemini-2.5-pro": "Gemini 2.5 Pro",
        "openrouter/meta-llama/llama-4-maverick": "Llama 4 Maverick",
        "openrouter/deepseek/deepseek-r1-0528": "DeepSeek R1",
        "openrouter/mistralai/mistral-small-3.2-24b-instruct": "Mistral Small 3.2",
    }

if len(model_options) == 0:
    raise ValueError(
        "No API keys found. Please set OPENAI_API_KEY, ANTHROPIC_API_KEY, and/or OPENROUTER_API_KEY in your environment."
    )

default_model = next(iter(next(iter(model_options.values())).keys()))


def app_ui(request: Request):
    return ui.page_sidebar(
        ui.sidebar(
            ui.input_select(
                "model",
                "Model",
                model_options,
                selected=default_model,
            ),
            ui.input_text_area("system_prompt", "System prompt", rows=6),
            ui.help_text("Instructs the LLM how to behave"),
            ui.input_slider(
                "temperature", "Temperature", min=0, max=2, value=0.7, step=0.05
            ),
            ui.help_text(
                "Lower for coherence, higher for randomness."
            ),
            ui.input_checkbox_group(
                "tools",
                "Tools",
                {
                    "filesystem": "Filesystem access",
                    "websearch": "Web search",
                },
            ),
            ui.markdown("⚠️ Runs arbitrary Python code."),
            ui.input_text_area(
                "custom_tool_code",
                "Custom tool code",
                rows=5,
                placeholder="def my_tool(name: str) -> str:\n    \"\"\"Say hello.\"\"\"\n    return f\"Hello, {name}!\"",
            ),
            ui.input_action_button("register_tools", "Register tools", class_="btn-sm"),
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
                """
            ),
        ),
        title="Clearbot",
        fillable=True,
    )


class RequestParams(BaseModel):
    """A snapshot of the parameter values at the moment of a request"""

    model: str
    user_prompt: str
    system_prompt: str
    temperature: float
    tools: list[str]


class SessionState(BaseModel):
    turns: list[MyTurn]
    snapshots: list[tuple[RequestParams, list[MyTurn]]]
    custom_tool_code: str = ""


def server(input: Inputs, output: Outputs, session: Session):
    turns: reactive.Value[list[MyTurn]] = reactive.Value([])
    snapshots: reactive.Value[list[tuple[RequestParams, list[MyTurn]]]] = (
        reactive.Value([])
    )
    custom_tools: reactive.Value[list[Callable]] = reactive.Value([])

    chat = ui.Chat("chat")

    def current_params(user_prompt: str) -> RequestParams:
        return RequestParams(
            model=input.model(),
            user_prompt=user_prompt,
            system_prompt=input.system_prompt(),
            temperature=input.temperature(),
            tools=input.tools(),
        )

    @chat.on_user_submit
    async def chat_on_user_submit(user_prompt: str):
        these_turns = turns()
        params: RequestParams = current_params(user_prompt)

        if params.model.startswith("claude"):
            chat_client = chatlas.ChatAnthropic(
                model=params.model,
                system_prompt=params.system_prompt,
            )
        elif params.model.startswith("gpt"):
            chat_client = chatlas.ChatOpenAI(
                model=params.model,
                system_prompt=params.system_prompt,
            )
        elif params.model.startswith("openrouter/"):
            chat_client = chatlas.ChatOpenRouter(
                model=params.model.removeprefix("openrouter/"),
                system_prompt=params.system_prompt,
            )
        else:
            raise ValueError(f"Unknown model: {params.model}")

        if these_turns:
            chat_client.set_turns(these_turns)

        for toolset in input.tools():
            for tool in all_tools[toolset]:
                chat_client.register_tool(tool)

        for tool in custom_tools():
            chat_client.register_tool(tool)

        resp = await chat_client.stream_async(
            params.user_prompt, kwargs=dict(temperature=params.temperature)
        )

        async def gen():
            async for chunk in resp:
                yield chunk
            with reactive.isolate():
                yield button_for_index(len(snapshots.get()))

        task = await chat.append_message_stream(gen())

        @reactive.Effect
        async def resp_on_complete():
            if task.status() == "success":
                resp_on_complete.destroy()
                turns.set(chat_client.get_turns())
                snapshots.set(snapshots.get() + [(params, chat_client.get_turns())])
                with reactive.isolate():
                    ui.update_select(
                        "trace_num", choices=list(range(len(snapshots.get())))
                    )
                await session.bookmark()
            if task.status() in ["error", "cancelled"]:
                resp_on_complete.destroy()

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
    @reactive.event(input.clear)
    async def clear_messages():
        await chat.clear_messages()
        turns.set([])
        snapshots.set([])

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
            # ui.Tag("json-viewer", data=params.model_dump_json(indent=2)),
            ui.Tag("json-viewer", data=json.dumps(dump)),
            ui.h4("Response", class_="mt-3"),
            ui.Tag("json-viewer", data=json.dumps(resp)),
        )


def _turn_contents_to_dicts(turn: chatlas.Turn) -> list[dict]:
    """Convert turn contents to serializable dicts using public API only."""
    results = []
    for content in turn.contents:
        if isinstance(content, chatlas.ContentToolRequest):
            results.append({
                "type": "tool_request",
                "id": content.id,
                "name": content.name,
                "arguments": content.arguments,
            })
        elif isinstance(content, chatlas.ContentToolResult):
            results.append({
                "type": "tool_result",
                "id": content.id,
                "value": str(content.get_model_value()),
            })
        else:
            results.append({
                "type": type(content).__name__,
                "text": str(content),
            })
    return results


def reconstruct_request_traces(
    params: RequestParams, turns: Iterable[chatlas.Turn]
) -> dict:
    tools_schema = reconstruct_tools_schema(params.tools)

    messages = [
        {"role": turn.role, "contents": _turn_contents_to_dicts(turn)}
        for turn in turns
    ]
    return dict(
        model=params.model,
        temperature=params.temperature,
        tools=tools_schema,
        messages=messages,
    )


def reconstruct_tools_schema(toolsets: list[str]) -> list[dict]:
    result = []
    for toolset in toolsets:
        for tool in all_tools[toolset]:
            try:
                from chatlas._tools import func_to_schema
                result.append(func_to_schema(tool))
            except (ImportError, AttributeError):
                # Fallback: build a minimal schema from the function signature
                import inspect as _inspect
                sig = _inspect.signature(tool)
                result.append({
                    "type": "function",
                    "function": {
                        "name": tool.__name__,
                        "description": tool.__doc__ or "",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                name: {"type": "string"}
                                for name in sig.parameters
                            },
                        },
                    },
                })
    return result


def reconstruct_message(turn: chatlas.Turn) -> dict:
    return dict(
        role=turn.role,
        contents=_turn_contents_to_dicts(turn),
    )


def reconstruct_response_traces(turn: chatlas.Turn) -> dict:
    assert turn.role == "assistant"

    return {
        "choices": [
            {"message": reconstruct_message(turn), "finish_reason": turn.finish_reason}
        ]
    }


app = App(
    app_ui, server, bookmark_store="url", static_assets=Path(__file__).parent / "www"
)
