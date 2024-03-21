# Copyright (c) Streamlit Inc. (2018-2022) Snowflake Inc. (2022-2024)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Literal

from streamlit.proto.ForwardMsg_pb2 import ForwardMsg
from streamlit.runtime.scriptrunner.script_run_context import get_script_run_ctx
from streamlit.source_util import page_icon_and_name
from streamlit.util import calc_md5


@dataclass
class Page:
    page: Path | Callable
    title: str | None = None
    icon: str | None = None
    default: bool = False
    key: str | None = None

    def __init__(
        self,
        page: str | Path | Callable,
        *,
        title: str | None = None,
        icon: str | None = None,
        default: bool = False,
        key: str | None = None,
    ):
        ctx = get_script_run_ctx()
        assert ctx

        main_path = Path(ctx.main_script_path).parent
        if isinstance(page, str):
            page = Path(page)
        if isinstance(page, Path):
            page = (main_path / page).resolve()

        inferred_name = ""
        inferred_icon = ""
        if isinstance(page, Path):
            inferred_icon, inferred_name = page_icon_and_name(page)
        else:
            inferred_name = page.__name__

        name = title or inferred_name
        assert name

        self.page = page
        self.title = title or inferred_name
        self.icon = icon or inferred_icon
        self.default = default
        self.key = key

    def run(self) -> None:
        ctx = get_script_run_ctx()
        assert ctx and ctx.script_requests

        ctx.script_requests.request_page_run(self)
        ctx.yield_callback()

    @property
    def _script_hash(self) -> str:
        h = calc_md5(str(self.page))
        return h


def navigation(
    pages: list[Page] | dict[str, list[Page]],
    *,
    position: Literal["sidebar"] | Literal["hidden"] = "sidebar",
) -> Page:
    ctx = get_script_run_ctx()
    assert ctx

    if isinstance(pages, list):
        pages: dict[str, list[Page]] = {"": pages}

    msg = ForwardMsg()
    for section in pages:
        nav_section = msg.navigation.sections.add()
        nav_section.header = section
        for page in pages[section]:
            p = nav_section.app_pages.add()
            p.page_script_hash = page._script_hash
            p.page_name = page.title or ""
            p.icon = page.icon or ""

    ctx.enqueue(msg)

    page_dict = {}
    for section in pages:
        for page in pages[section]:
            page_dict[page._script_hash] = page
    ctx.pages = page_dict
    try:
        page = page_dict[ctx.page_script_hash]
    except KeyError:
        print("falling back to default page")
        page = list(page_dict.values())[0]
    # psh = ctx.page_script_hash
    # idx = [page._script_hash for page in pages].index(psh)
    # page = pages[idx]
    return page
