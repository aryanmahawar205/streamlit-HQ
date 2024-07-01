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

from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    cast,
    get_args,
    overload,
)

from streamlit.elements.form import current_form_id
from streamlit.elements.widgets.options_selector.feedback_utils import (
    FeedbackOptions,
    FeedbackSerde,
    create_format_func,
    get_mapped_options,
)
from streamlit.elements.widgets.options_selector.options_selector_utils import (
    MultiSelectSerde,
    check_max_selections,
    check_multiselect_policies,
    maybe_coerce,
    transform_options,
)
from streamlit.errors import StreamlitAPIException
from streamlit.proto.ButtonGroup_pb2 import ButtonGroup as ButtonGroupProto
from streamlit.runtime.metrics_util import gather_metrics
from streamlit.runtime.scriptrunner import get_script_run_ctx
from streamlit.runtime.state import register_widget
from streamlit.runtime.state.common import (
    RegisterWidgetResult,
    WidgetDeserializer,
    WidgetSerializer,
    compute_widget_id,
    save_for_app_testing,
)
from streamlit.type_util import Key, OptionSequence, T, V, to_key

if TYPE_CHECKING:
    from streamlit.delta_generator import DeltaGenerator
    from streamlit.runtime.state import (
        WidgetArgs,
        WidgetCallback,
        WidgetKwargs,
    )


def _build_proto(
    widget_id: str,
    formatted_options: list[ButtonGroupProto.Option],
    default_values: list[int],
    disabled: bool,
    current_form_id: str,
    click_mode: ButtonGroupProto.ClickMode.ValueType,
    selection_visualization: ButtonGroupProto.SelectionVisualization.ValueType = (
        ButtonGroupProto.SelectionVisualization.ONLY_SELECTED
    ),
) -> ButtonGroupProto:
    proto = ButtonGroupProto()

    proto.id = widget_id
    proto.default[:] = default_values
    proto.form_id = current_form_id
    proto.disabled = disabled
    proto.click_mode = click_mode

    for formatted_option in formatted_options:
        proto.options.append(formatted_option)
    proto.selection_visualization = selection_visualization
    return proto


class ButtonGroupMixin:
    # Disable this more generic widget for now
    # ButtonGroupClickMode = Literal["select", "multiselect"]
    # @gather_metrics("button_group")
    # def button_group(
    #     self,
    #     options: OptionSequence[V],
    #     *,
    #     key: Key | None = None,
    #     default: list[bool] | None = None,
    #     click_mode: str = "select",
    #     disabled: bool = False,
    #     format_func: Callable[[V], dict[str, str]] | None = None,
    #     on_change: WidgetCallback | None = None,
    #     args: WidgetArgs | None = None,
    #     kwargs: WidgetKwargs | None = None,
    # ) -> list[V]:
    #     default_values = (
    #         [index for index, default_val in enumerate(default) if default_val is True]
    #         if default is not None
    #         else []
    #     )

    #     def _transformed_format_func(x: V) -> ButtonGroupProto.Option:
    #         if format_func is None:
    #             return ButtonGroupProto.Option(content=str(x))

    #         transformed = format_func(x)
    #         return ButtonGroupProto.Option(
    #             content=transformed["content"],
    #             selected_content=transformed["selected_content"],
    #         )

    # res: RegisterWidgetResult[list[V]] = self._button_group(
    #     options,
    #     key=key,
    #     default=default_values,
    #     click_mode=ButtonGroupProto.ClickMode.MULTI_SELECT
    #     if click_mode == "multiselect"
    #     else ButtonGroupProto.SINGLE_SELECT,
    #     disabled=disabled,
    #     format_func=_transformed_format_func if format_func is not None else None,
    #     on_change=on_change,
    #     args=args,
    #     kwargs=kwargs,
    # )
    # return res.value

    @gather_metrics("feedback")
    def feedback(
        self,
        options: FeedbackOptions = "thumbs",
        *,
        key: str | None = None,
        disabled: bool = False,
        on_change: WidgetCallback | None = None,
        args: Any | None = None,
        kwargs: Any | None = None,
    ) -> int | None:
        """Display a feedback widget.

        This is useful to collect user feedback, especially in chat-based apps.

        Parameters:
        -----------
        options: "thumbs", "faces", or "stars"
            The feedback options displayed to the user. The options are:
            - "thumbs" (default): displays a row of thumbs-up and thumbs-down buttons.
            - "faces": displays a row of five buttons with facial expressions, each
                depicting increasing satisfaction from left to right.
            - "stars": displays a row of star icons typically used for ratings.
        key : str or int
            An optional string or integer to use as the unique key for the widget.
            If this is omitted, a key will be generated for the widget
            based on its content. Multiple widgets of the same type may
            not share the same key.
        disabled : bool
            An optional boolean, which disables the multiselect widget if set
            to True. The default is False. This argument can only be supplied
            by keyword.
        on_change : callable
            An optional callback invoked when this multiselect's value changes.
        args : tuple
            An optional tuple of args to pass to the callback.
        kwargs : dict
            An optional dict of kwargs to pass to the callback.

        Returns
        -------
        An integer indicating the user's selection, where 0 is the lowest
        feedback and higher values indicate more positive feedback.
        If no option was selected, returns None.
            - For "thumbs": a return value of 0 is for thumbs-down and 1 for thumbs-up.
            - For "faces" and "stars":
                values range from 0 (least satisfied) to 4 (most satisfied).


        Examples
        --------
        Example 1: Display a feedback widget with stars and show the selected sentiment
        ```python
        sentiment_mapping: = [0.0, 0.25, 0.5, 0.75, 1.0]
        selected = st.feedback("stars")
        st.write(f"You selected: {sentiment_mapping[selected]}")
        ```

        Example 2: Display a feedback widget with thumbs and show the selected sentiment
        ```python
        sentiment_mapping: = [0.0, 1.0]
        selected = st.feedback("thumbs")
        st.write(f"You selected: {sentiment_mapping[selected]}")
        ```
        """

        if not isinstance(options, list) and options not in get_args(FeedbackOptions):
            raise StreamlitAPIException(
                "The options argument to st.feedback must be one of "
                "['thumbs', 'faces', 'stars']. "
                f"The argument passed was '{options}'."
            )
        transformed_options, options_indices = get_mapped_options(options)
        # format_func maps the option index to the corresponding icon
        format_func = create_format_func(transformed_options)
        serde = FeedbackSerde(options_indices)

        selection_visualization = ButtonGroupProto.SelectionVisualization.ONLY_SELECTED
        if options == "stars":
            selection_visualization = (
                ButtonGroupProto.SelectionVisualization.ALL_UP_TO_SELECTED
            )
        sentiment = self._button_group(
            options_indices,
            key=key,
            click_mode=ButtonGroupProto.SINGLE_SELECT,
            disabled=disabled,
            format_func=format_func,
            deserializer=serde.deserialize,
            serializer=serde.serialize,
            on_change=on_change,
            args=args,
            kwargs=kwargs,
            selection_visualization=selection_visualization,
        )
        return sentiment.value

    @overload
    def _button_group(
        self,
        options: OptionSequence[V],
        *,
        key: Key | None = None,
        default: list[int] | None = None,
        click_mode: ButtonGroupProto.ClickMode.ValueType = (
            ButtonGroupProto.SINGLE_SELECT
        ),
        disabled: bool = False,
        format_func: Callable[[V], ButtonGroupProto.Option] | None = None,
        deserializer: WidgetDeserializer[T] | None = None,
        serializer: WidgetSerializer[T] | None = None,
        on_change: WidgetCallback | None = None,
        args: WidgetArgs | None = None,
        kwargs: WidgetKwargs | None = None,
        selection_visualization: ButtonGroupProto.SelectionVisualization.ValueType = (
            ButtonGroupProto.SelectionVisualization.ONLY_SELECTED
        ),
    ) -> RegisterWidgetResult[T]: ...

    @overload
    def _button_group(
        self,
        options: OptionSequence[V],
        *,
        key: Key | None = None,
        default: list[int] | None = None,
        click_mode: ButtonGroupProto.ClickMode.ValueType = (
            ButtonGroupProto.SINGLE_SELECT
        ),
        disabled: bool = False,
        format_func: Callable[[V], ButtonGroupProto.Option],
        deserializer: None = None,
        serializer: None = None,
        on_change: WidgetCallback | None = None,
        args: WidgetArgs | None = None,
        kwargs: WidgetKwargs | None = None,
        selection_visualization: ButtonGroupProto.SelectionVisualization.ValueType = (
            ButtonGroupProto.SelectionVisualization.ONLY_SELECTED
        ),
    ) -> RegisterWidgetResult[list[V]]: ...

    def _button_group(
        self,
        options: OptionSequence[V],
        *,
        key: Key | None = None,
        default: list[int] | None = None,
        click_mode: ButtonGroupProto.ClickMode.ValueType = (
            ButtonGroupProto.SINGLE_SELECT
        ),
        disabled: bool = False,
        format_func: Callable[[V], ButtonGroupProto.Option] | None = None,
        deserializer: WidgetDeserializer[Any] | None = None,
        serializer: WidgetSerializer[Any] | None = None,
        on_change: WidgetCallback | None = None,
        args: WidgetArgs | None = None,
        kwargs: WidgetKwargs | None = None,
        selection_visualization: ButtonGroupProto.SelectionVisualization.ValueType = (
            ButtonGroupProto.SelectionVisualization.ONLY_SELECTED
        ),
    ) -> RegisterWidgetResult[Any]:
        key = to_key(key)

        check_multiselect_policies(self.dg, key, on_change, default)

        widget_name = "button_group"
        indexable_options, formatted_options, default_values = transform_options(
            options, default, format_func
        )
        ctx = get_script_run_ctx()
        widget_id = compute_widget_id(
            widget_name,
            user_key=key,
            key=key,
            options=formatted_options,
            default=default_values,
            disabled=disabled,
            selection_visualization=selection_visualization,
            page=ctx.active_script_hash if ctx else None,
        )

        proto = _build_proto(
            widget_id,
            formatted_options,
            default_values,
            disabled,
            current_form_id(self.dg),
            click_mode=click_mode,
            selection_visualization=selection_visualization,
        )

        if serializer is None or deserializer is None:
            serde = MultiSelectSerde(indexable_options, default_values)
            deserializer = serde.deserialize
            serializer = serde.serialize

        widget_state = register_widget(
            "button_group",
            proto,
            # user_key=key,
            on_change_handler=on_change,
            args=args,
            kwargs=kwargs,
            deserializer=deserializer,
            serializer=serializer,
            ctx=ctx,
        )

        check_max_selections(widget_state.value, None)
        widget_state = maybe_coerce(widget_state, options, indexable_options)

        if widget_state.value_changed:
            proto.value[:] = serializer(widget_state.value)
            proto.set_value = True

        if ctx:
            save_for_app_testing(ctx, widget_id, format_func)
        self.dg._enqueue(widget_name, proto)

        return widget_state

    @property
    def dg(self) -> DeltaGenerator:
        """Get our DeltaGenerator."""
        return cast("DeltaGenerator", self)
