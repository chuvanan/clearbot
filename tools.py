import functools
import json
import os
import traceback
from typing import Callable, ParamSpec, TypeVar, Union

import requests
from duckduckgo_search import DDGS

P = ParamSpec("P")
R = TypeVar("R")


def safe_errors(func: Callable[P, R]) -> Callable[P, Union[R, str]]:
    @functools.wraps(func)
    def wrapped(*args: P.args, **kwargs: P.kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            return f"An error has occurred:\n{traceback.format_exception(e)}"

    return wrapped


@safe_errors
def get_current_dir() -> str:
    """Gets the current working directory."""

    return os.getcwd()


@safe_errors
def set_current_dir(path: str) -> None:
    """Sets the current directory to the given (relative or absolute) path"""

    os.chdir(path)


@safe_errors
def list_dir(path: str = ".") -> list[str]:
    """Returns a list of files and directories in the given directory."""

    return os.listdir(path)


@safe_errors
def read_text_file(path: str, encoding: str = "UTF-8") -> str:
    """Reads the file at the given path as a string."""

    with open(path, encoding=encoding) as f:
        return f.read()


@safe_errors
def google_search(query: str, start: int = 1):
    """Searches the web using the Google search engine."""

    # Make a request to https://customsearch.googleapis.com/customsearch/v1?cx={os.environ.GOOGLE_SEARCH_ENGINE_ID}&q=&key={os.environ.GOOGLE_API_KEY}
    response = requests.get(
        "https://customsearch.googleapis.com/customsearch/v1",
        params={
            "cx": os.environ["GOOGLE_SEARCH_ENGINE_ID"],
            "q": query,
            "key": os.environ["GOOGLE_API_KEY"],
            "num": 10,
            "start": start,
        },
    )
    response.raise_for_status()
    results = response.json()
    return json.dumps(
        [
            {
                "title": item["title"],
                "link": item["link"],
                "snippet": item["snippet"],
            }
            for item in results["items"]
        ],
        indent=2,
    )


@safe_errors
def duckduckgo_search(query: str, max_results: int = 20):
    """Searches the web using the DuckDuckGo search engine."""

    # In theory, max_results shouldn't need to be coerced to an int. In
    # practice, Llama 3.2 passes the wrong type sometimes.
    return DDGS().text(query, max_results=int(max_results))


@safe_errors
def http_get(url: str) -> str:
    """Retrieves the contents of a URL using an HTTP GET request. Turns HTML into plaintext."""
    response = requests.get(url)
    response.raise_for_status()
    # If HTML, convert to text using Pandoc. If plaintext, leave it alone.
    if "text/html" in response.headers["Content-Type"]:
        import pandoc

        doc = pandoc.read(response.text, format="html")
        return pandoc.write(doc, format="plain")
    else:
        # Return plaintext
        return response.text


all_tools: dict[str, list[Callable]] = {
    "filesystem": [
        get_current_dir,
        set_current_dir,
        list_dir,
        read_text_file,
    ],
    "websearch": [
        google_search,
        # duckduckgo_search,
        http_get,
    ],
}
