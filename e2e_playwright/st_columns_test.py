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

import re

from playwright.sync_api import Page, expect

from e2e_playwright.conftest import ImageCompareFunction
from e2e_playwright.shared.app_utils import click_button, expect_exception, get_expander


def _get_basic_column_container(
    app: Page,
):
    column_container = app.get_by_test_id("stHorizontalBlock").nth(0)
    expect(column_container).to_be_visible()
    return column_container


def test_show_columns_horizontally_when_viewport_allows(
    app: Page, assert_snapshot: ImageCompareFunction
):
    """shows columns horizontally when viewport > 640"""
    app.set_viewport_size({"width": 641, "height": 800})
    column_container = _get_basic_column_container(app)
    assert_snapshot(
        column_container.nth(0), name="st_columns-responsive_layout_horizontal"
    )


def test_show_columns_vertically_when_viewport_requires(
    app: Page, assert_snapshot: ImageCompareFunction
):
    """stacks columns vertically when viewport <= 640"""
    app.set_viewport_size({"width": 640, "height": 800})
    column_container = _get_basic_column_container(app)
    assert_snapshot(column_container, name="st_columns-responsive_layout_vertical")


def test_two_level_nested_columns_shows_exception(app: Page):
    """Shows exception when trying to nest columns more than one level deep."""

    click_button(app, "Nested columns - two levels (raises exception)")
    expect_exception(
        app,
        re.compile(
            "Columns can only be placed inside other columns up to one level of nesting."
        ),
    )


def test_nested_columns_in_sidebar_shows_exception(app: Page):
    """Shows exception when trying to nest columns in the sidebar."""

    click_button(app, "Nested columns - in sidebar (raises exception)")
    expect_exception(
        app,
        re.compile(
            "Columns cannot be placed inside other columns in the sidebar. This is only possible in the main area of the app."
        ),
    )


def test_column_gap_small_is_correctly_applied(
    app: Page, assert_snapshot: ImageCompareFunction
):
    """Test that the small column gap is correctly applied."""
    column_gap_small = (
        get_expander(app, "Column gap small").get_by_test_id("stHorizontalBlock").nth(0)
    )
    expect(column_gap_small).to_have_css("gap", "1rem")
    column_gap_small.scroll_into_view_if_needed()
    assert_snapshot(column_gap_small, name="st_columns-column_gap_small")


def test_column_gap_medium_is_correctly_applied(
    app: Page, assert_snapshot: ImageCompareFunction
):
    """Test that the medium column gap is correctly applied."""
    column_gap_small = (
        get_expander(app, "Column gap medium")
        .get_by_test_id("stHorizontalBlock")
        .nth(0)
    )
    expect(column_gap_small).to_have_css("gap", "2rem")
    column_gap_small.scroll_into_view_if_needed()
    assert_snapshot(column_gap_small, name="st_columns-column_gap_medium")


def test_column_gap_large_is_correctly_applied(
    app: Page, assert_snapshot: ImageCompareFunction
):
    """Test that the large column gap is correctly applied."""
    column_gap_small = (
        get_expander(app, "Column gap large").get_by_test_id("stHorizontalBlock").nth(0)
    )
    expect(column_gap_small).to_have_css("gap", "4rem")
    column_gap_small.scroll_into_view_if_needed()
    assert_snapshot(column_gap_small, name="st_columns-column_gap_large")


# ------------------------------


# def test_columns_always_take_up_space(app: Page, assert_snapshot: ImageCompareFunction):
#     """columns still takes up space with no elements present"""
#     horizontal_blocks = app.get_by_test_id("stHorizontalBlock")
#     expect(horizontal_blocks).to_have_count(2)

#     assert_snapshot(horizontal_blocks.nth(1), name="st_columns-with_one_element")


# def test_shows_nested_columns_correctly(
#     app: Page, assert_snapshot: ImageCompareFunction
# ):
#     assert_snapshot(
#         app.get_by_test_id("stVerticalBlock").nth(0),
#         name="st_columns-long_texts",
#     )
