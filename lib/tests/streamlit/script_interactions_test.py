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
import pytest

from streamlit.testing.script_interactions import InteractiveScriptTests


class InteractiveScriptTest(InteractiveScriptTests):
    def test_widgets_script(self):
        script = self.script_from_filename("test_data/widgets_script.py")
        sr = script.run()

        # main and sidebar
        assert len(sr) == 2
        main = sr[0]

        # columns live within a horizontal block, + 2 more elements
        assert len(main) == 3

        # 2 columns
        assert len(main[0]) == 2

        # first column has 4 elements
        assert len(main[0][0]) == 4

        radios = sr.radio
        assert radios[0].value == "1"
        assert radios[1].value == "a"

        # iteration follows delta path order, with a block coming before
        # its children, which come before its siblings. main comes before
        # the sidebar
        assert [e.type for e in sr] == [
            "root",
            "main",
            "horizontal",
            "column",
            "checkbox",
            "text",
            "text_area",
            "text",
            "column",
            "radio",
            "text",
            "button",
            "text",
            "sidebar",
            "radio",
        ]

    def test_cached_widget_replay_rerun(self):
        script = self.script_from_string(
            """
            import streamlit as st

            @st.cache_data(experimental_allow_widgets=True, show_spinner=False)
            def foo(i):
                options = ["foo", "bar", "baz", "qux"]
                r = st.radio("radio", options, index=i)
                return r


            foo(1)
        """,
        )
        sr = script.run()

        assert len(sr.radio) == 1
        sr2 = sr.run()
        assert len(sr2.radio) == 1

    def test_cached_widget_replay_interaction(self):
        script = self.script_from_string(
            """
            import streamlit as st

            @st.cache_data(experimental_allow_widgets=True, show_spinner=False)
            def foo(i):
                options = ["foo", "bar", "baz", "qux"]
                r = st.radio("radio", options, index=i)
                return r


            foo(1)
        """,
        )
        sr = script.run()

        assert len(sr.radio) == 1
        assert sr.radio[0].value == "bar"

        sr2 = sr.radio[0].set_value("qux").run()
        assert sr2.radio[0].value == "qux"

    def test_radio_interaction(self):
        script = self.script_from_string(
            """
            import streamlit as st

            st.radio("radio", options=["a", "b", "c"])
            st.radio("default index", options=["a", "b", "c"], index=2)
            """,
        )
        sr = script.run()
        assert sr.radio
        assert sr.radio[0].value == "a"
        assert sr.radio[1].value == "c"

        r = sr.radio[0].set_value("b")
        assert r.index == 1
        assert r.value == "b"
        sr2 = r.run()
        assert sr2.radio[0].value == "b"
        assert [s.value for s in sr2.radio] == ["b", "c"]

    def test_widget_key_lookup(self):
        script = self.script_from_string(
            """
            import streamlit as st

            st.radio("keyless", options=["a", "b", "c"])
            st.radio("has key", options=["a", "b", "c"], key="r")
            """,
        )
        sr = script.run()
        assert sr.get_widget("r").as_radio
        assert sr.get_widget("r") == sr.radio[1]
        with pytest.raises(KeyError):
            sr.get_widget("s")

    def test_widget_added_removed(self):
        """
        Test that the value of a widget persists, disappears, and resets
        appropriately, as the widget is added and removed from the script execution.
        """
        script = self.script_from_string(
            """
            import streamlit as st

            cb = st.radio("radio emulating a checkbox", options=["off", "on"], key="cb")
            if cb == "on":
                st.radio("radio", options=["a", "b", "c"], key="conditional")
            """,
        )
        sr = script.run()
        assert len(sr.radio) == 1
        with pytest.raises(KeyError):
            sr.get_widget("conditional")

        sr2 = sr.get_widget("cb").as_radio.set_value("on").run()
        assert len(sr2.radio) == 2
        assert sr2.get_widget("conditional").as_radio.value == "a"

        sr3 = sr2.get_widget("conditional").as_radio.set_value("c").run()
        assert len(sr3.radio) == 2
        assert sr3.get_widget("conditional").as_radio.value == "c"

        sr4 = sr3.get_widget("cb").as_radio.set_value("off").run()
        assert len(sr4.radio) == 1
        with pytest.raises(KeyError):
            sr4.get_widget("conditional")

        sr5 = sr4.get_widget("cb").as_radio.set_value("on").run()
        assert len(sr5.radio) == 2
        assert sr5.get_widget("conditional").as_radio.value == "a"

    def test_query_narrowing(self):
        script = self.script_from_string(
            """
            import streamlit as st

            st.text("1")
            with st.expander("open"):
                st.text("2")
                st.text("3")
            st.text("4")
            """,
        )
        sr = script.run()
        assert len(sr.text) == 4
        # querying elements via a block only returns the elements in that block
        assert len(sr.get("expandable")[0].text) == 2

    def test_session_state_immutable(self):
        script = self.script_from_string(
            """
            import streamlit as st

            if "other" not in st.session_state:
                st.session_state["other"] = 5

            st.radio("r", options=["a", "b", "c"], key="radio")
            if st.session_state.radio == "b":
                st.session_state.other = 10
            """,
        )
        sr = script.run()
        state1 = sr.session_state
        assert state1 is not None
        assert state1["radio"] == "a"
        assert state1["other"] == 5

        sr2 = sr.radio[0].set_value("b").run()
        assert sr2.session_state["radio"] == "b"
        assert sr2.session_state["other"] == 10
        # unaffected by second script run
        assert state1["radio"] == "a"
        assert state1["other"] == 5

        sr3 = sr2.radio[0].set_value("c").run()
        assert sr3.session_state["radio"] == "c"
        # has value from second script run despite being a different instance
        assert sr3.session_state["other"] == 10

    def test_radio_option_types(self):
        script = self.script_from_string(
            """
            import streamlit as st

            st.radio("string", options=["a", "b", "c"])
            st.radio("int", options=(1, 2, 3))
            """,
        )
        sr = script.run()
        assert sr.radio[0].value == "a"
        assert sr.radio[1].value == 1

        sr2 = sr.radio[1].set_value(3).run()
        assert sr2.radio[1].value == 3

    def test_script_not_found(self):
        with pytest.raises(AssertionError):
            self.script_from_filename("doesntexist.py")

    def test_timeout(self):
        script = self.script_from_string(
            """
            import time
            time.sleep(0.5)
            """,
            default_timeout=0.2,
        )
        with pytest.raises(RuntimeError, match=r".*timed out.*"):
            script.run()

        # Overrides the default, doesn't raise
        script.run(timeout=1)
