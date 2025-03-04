# Copyright (c) Streamlit Inc. (2018-2022) Snowflake Inc. (2022)
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

import os
import time
from typing import Any
from urllib import parse

from streamlit.proto.ForwardMsg_pb2 import ForwardMsg
from streamlit.proto.WidgetStates_pb2 import WidgetStates
from streamlit.runtime.forward_msg_queue import ForwardMsgQueue
from streamlit.runtime.memory_uploaded_file_manager import MemoryUploadedFileManager
from streamlit.runtime.scriptrunner import RerunData, ScriptRunner, ScriptRunnerEvent
from streamlit.runtime.scriptrunner.script_cache import ScriptCache
from streamlit.runtime.state.session_state import SessionState
from streamlit.testing.v1.element_tree import ElementTree, parse_tree_from_messages


class LocalScriptRunner(ScriptRunner):
    """Subclasses ScriptRunner to provide some testing features."""

    def __init__(
        self,
        script_path: str,
        session_state: SessionState,
    ):
        """Initializes the ScriptRunner for the given script_path."""

        assert os.path.isfile(script_path), f"File not found at {script_path}"

        self.forward_msg_queue = ForwardMsgQueue()
        self.script_path = script_path
        self.session_state = session_state

        super().__init__(
            session_id="test session id",
            main_script_path=script_path,
            session_state=self.session_state,
            uploaded_file_mgr=MemoryUploadedFileManager("/mock/upload"),
            script_cache=ScriptCache(),
            initial_rerun_data=RerunData(),
            user_info={"email": "test@test.com"},
        )

        # Accumulates all ScriptRunnerEvents emitted by us.
        self.events: list[ScriptRunnerEvent] = []
        self.event_data: list[Any] = []

        def record_event(
            sender: ScriptRunner | None, event: ScriptRunnerEvent, **kwargs
        ) -> None:
            # Assert that we're not getting unexpected `sender` params
            # from ScriptRunner.on_event
            assert (
                sender is None or sender == self
            ), "Unexpected ScriptRunnerEvent sender!"

            self.events.append(event)
            self.event_data.append(kwargs)

            # Send ENQUEUE_FORWARD_MSGs to our queue
            if event == ScriptRunnerEvent.ENQUEUE_FORWARD_MSG:
                forward_msg = kwargs["forward_msg"]
                self.forward_msg_queue.enqueue(forward_msg)

        self.on_event.connect(record_event, weak=False)

    def join(self) -> None:
        """Wait for the script thread to finish, if it is running."""
        if self._script_thread is not None:
            self._script_thread.join()

    def forward_msgs(self) -> list[ForwardMsg]:
        """Return all messages in our ForwardMsgQueue."""
        return self.forward_msg_queue._queue

    def run(
        self,
        widget_state: WidgetStates | None = None,
        query_params=None,
        timeout: float = 3,
    ) -> ElementTree:
        """Run the script, and parse the output messages for querying
        and interaction.

        Timeout is in seconds.
        """
        # TODO: save the query strings from the script run
        query_string = ""
        if query_params:
            query_string = parse.urlencode(query_params, doseq=True)

        rerun_data = RerunData(widget_states=widget_state, query_string=query_string)
        self.request_rerun(rerun_data)
        if not self._script_thread:
            self.start()
        require_widgets_deltas(self, timeout)

        tree = parse_tree_from_messages(self.forward_msgs())
        return tree

    def script_stopped(self) -> bool:
        for e in self.events:
            if e in (
                ScriptRunnerEvent.SCRIPT_STOPPED_FOR_RERUN,
                ScriptRunnerEvent.SCRIPT_STOPPED_WITH_COMPILE_ERROR,
                ScriptRunnerEvent.SCRIPT_STOPPED_WITH_SUCCESS,
            ):
                return True
        return False


def require_widgets_deltas(runner: LocalScriptRunner, timeout: float = 3) -> None:
    """Wait for the given ScriptRunner to emit a completion event. If the timeout
    is reached, the runner will be shutdown and an error will be thrown.
    """

    t0 = time.time()
    while time.time() - t0 < timeout:
        time.sleep(0.1)
        if runner.script_stopped():
            return

    # If we get here, the runner hasn't yet completed before our
    # timeout. Create an error string for debugging.
    err_string = f"AppTest script run timed out after {timeout}s)"

    # Shutdown the runner before throwing an error, so that the script
    # doesn't hang forever.
    runner.request_stop()
    runner.join()

    raise RuntimeError(err_string)
