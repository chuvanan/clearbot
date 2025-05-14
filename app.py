import json
from pathlib import Path
from typing import Iterable, TypeAlias

import chatlas
import openai
from dotenv import load_dotenv
from pydantic import BaseModel
from shiny import App, Inputs, Outputs, Session, bookmark, reactive, render, req, ui
from starlette.requests import Request

from offcanvas import offcanvas_ui
from tools import all_tools

MyTurn: TypeAlias = chatlas.Turn[openai.types.chat.ChatCompletion]

load_dotenv()

def app_ui(request: Request):
    return ui.page_sidebar(
        ui.sidebar(
            ui.input_select(
                "model",
                "Model",
                {
                    "gpt-4.1": "GPT-4.1 (slowest, smartest)",
                    "gpt-4.1-mini": "GPT-4.1 mini",
                    "gpt-4.1-nano": "GPT-4.1 nano (fastest, cheapest)",
                    # "claude-3.7-sonnet-latest": "Claude 3.7 Sonnet",
                    # "claude-3.5-sonnet-latest": "Claude 3.5 Sonnet",
                    # "claude-3.5-haiku-latest": "Claude 3.5 Haiku",
                },
                selected="gpt-4.1-nano",
            ),
            ui.input_text_area("system_prompt", "System prompt", rows=4),
            ui.help_text("Instructs the LLM how to behave"),
            ui.input_slider(
                "temperature", "Temperature", min=0, max=2, value=0.7, step=0.05
            ),
            ui.help_text("Lower for coherence, higher for randomness"),
            ui.input_checkbox_group(
                "tools",
                "Tools",
                {
                    "filesystem": "Filesystem access",
                    "websearch": "Web search",
                },
                selected=["websearch"],
            ),
            # ui.tags.button(
            #     "Show traces",
            #     class_="btn btn-default",
            #     onclick="bootstrap.Offcanvas.getOrCreateInstance(document.querySelector('#trace')).show()",
            # ),
            width=325,
            title="Parameters",
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
        ui.card(
            "This bot helps you understand how LLMs work by showing you the under-the-hood requests and responses.",
            fill=False,
        ),
        ui.card(
            ui.tags.style(
                "#clear { display: none; }",
                id="hide_new_convo_css",
            ),
            ui.input_action_button(
                "clear",
                "📄 New Chat",
                class_="btn-sm btn-default float-right bg-light shadow",
                style="position: fixed; top: 0.5rem; left: 50%; transform: translateX(-50%); --bs-btn-hover-color: unset; z-index: 100;",
            ),
            ui.chat_ui("chat"),
            fillable=True,
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


def server(input: Inputs, output: Outputs, session: Session):
    turns: reactive.Value[list[MyTurn]] = reactive.Value([])
    snapshots: reactive.Value[list[tuple[RequestParams, list[MyTurn]]]] = (
        reactive.Value([])
    )

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

        # chat_client = chatlas.ChatOllama(
        #     model="llama3.2",
        #     system_prompt=params.system_prompt,
        #     turns=these_turns,
        # )
        chat_client = chatlas.ChatOpenAI(
            model=params.model,
            system_prompt=params.system_prompt,
            turns=these_turns,
        )

        for toolset in input.tools():
            for tool in all_tools[toolset]:
                chat_client.register_tool(tool)

        resp = await chat_client.stream_async(
            params.user_prompt, kwargs=dict(temperature=params.temperature)
        )

        for tool in params.tools:
            # TODO: Implement tools
            pass

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
        ss = SessionState(turns=turns(), snapshots=snapshots())
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
    def manage_new_chat_button_visibility():
        if len(chat.messages()) > 1:
            ui.remove_ui("#hide_new_convo_css")
            manage_new_chat_button_visibility.destroy()

    @reactive.effect
    @reactive.event(input.clear)
    async def clear_messages():
        await chat.clear_messages()
        turns.set([])
        snapshots.set([])

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


def reconstruct_request_traces(
    params: RequestParams, turns: Iterable[MyTurn]
) -> list[object]:
    tools_schema = reconstruct_tools_schema(params.tools)

    msgs = chatlas._openai.OpenAIProvider._as_message_param(turns)
    kw = dict(
        model=params.model,
        temperature=params.temperature,
        tools=tools_schema,
        messages=msgs,
    )
    return kw


def reconstruct_tools_schema(toolsets: list[str]) -> object:
    result = []
    for toolset in toolsets:
        for tool in all_tools[toolset]:
            result.append(chatlas._tools.func_to_schema(tool))

    return result


def reconstruct_message(turn: MyTurn) -> object:
    return dict(
        role=turn.role,
        contents=[reconstruct_content(content) for content in turn.contents],
    )


def reconstruct_content(content: list[chatlas._content.Content]) -> object:
    return str(content)

def reconstruct_response_traces(turn: MyTurn) -> object:
    # role: Literal["user", "assistant", "system"]
    # contents: list[ContentUnion] = Field(default_factory=list)
    # tokens: Optional[tuple[int, int]] = None
    # finish_reason: Optional[str] = None
    # completion: Optional[CompletionT] = Field(default=None, exclude=True)

    # model_config = ConfigDict(arbitrary_types_allowed=True)

    assert turn.role == "assistant"

    return {
        "choices": [
            {"message": reconstruct_message(turn), "finish_reason": turn.finish_reason}
        ]
    }

app = App(
    app_ui, server, bookmark_store="url", static_assets=Path(__file__).parent / "www"
)
