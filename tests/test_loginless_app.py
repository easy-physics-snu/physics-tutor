"""Offline UI smoke tests; run with the project's Streamlit version installed."""
import importlib.metadata
from pathlib import Path
from types import ModuleType
import unittest
from unittest.mock import patch


try:
    STREAMLIT_VERSION = tuple(
        int(part) for part in importlib.metadata.version("streamlit").split(".")[:2]
    )
except importlib.metadata.PackageNotFoundError:
    STREAMLIT_VERSION = (0, 0)


@unittest.skipIf(STREAMLIT_VERSION < (1, 40), "Requires project Streamlit >= 1.40")
class LoginlessAppTests(unittest.TestCase):
    def test_language_entry_urls_redirect_without_a_main_page(self):
        import streamlit as st
        from streamlit.testing.v1 import AppTest

        root = Path(__file__).resolve().parents[1]
        for filename, locale in (("locale_default.py", "en"),
                                 ("locale_en.py", "en"),
                                 ("locale_ko.py", "ko")):
            with self.subTest(filename=filename):
                path = root / "pages_group" / filename
                app = AppTest.from_string(
                    f"import runpy\nrunpy.run_path({str(path)!r})"
                )
                with patch.object(st, "switch_page") as redirect:
                    app.run()
                self.assertFalse(app.exception)
                redirect.assert_called_once_with("pages_group/01_들어가기.py")
                self.assertFalse(app.text_input)
                self.assertEqual(app.session_state["locale"], locale)
                self.assertTrue(app.session_state["user_id"].startswith("anonymous-"))
                self.assertTrue(app.session_state["session_uuid"])

    def test_root_entry_returns_a_korean_session_to_english(self):
        import streamlit as st
        from streamlit.testing.v1 import AppTest

        root = Path(__file__).resolve().parents[1]
        path = root / "pages_group/locale_default.py"
        app = AppTest.from_string(f"import runpy\nrunpy.run_path({str(path)!r})")
        for key, value in {"locale": "ko", "user_id": "anonymous-visitor",
                           "session_uuid": "old-session", "draft": "old answer"}.items():
            app.session_state[key] = value
        with patch.object(st, "switch_page"):
            app.run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state["locale"], "en")
        self.assertEqual(app.session_state["locale_selector"], "en")
        self.assertEqual(app.session_state["user_id"], "anonymous-visitor")
        self.assertNotEqual(app.session_state["session_uuid"], "old-session")
        self.assertNotIn("draft", app.session_state.filtered_state)

    def test_sidebar_contains_only_the_five_learning_steps(self):
        import streamlit as st
        from streamlit.testing.v1 import AppTest
        from types import SimpleNamespace

        root = Path(__file__).resolve().parents[1]
        app = AppTest.from_file(str(root / "app.py"))
        # Render the real sidebar without running a lesson or external services.
        page = SimpleNamespace(url_path="introduction", run=lambda: None)
        with patch.object(st, "navigation", return_value=page):
            app.run()
        self.assertFalse(app.exception)
        labels = [link.proto.label for link in app.sidebar.get("page_link")]
        self.assertEqual(labels, ["Introduction 🚀", "Think 🤔", "Experiment 🧪",
                                  "Review 🧐", "Apply 💡"])

    def test_introduction_accepts_direct_anonymous_entry_and_keeps_session(self):
        from streamlit.delta_generator import DeltaGenerator
        from streamlit.testing.v1 import AppTest

        database = ModuleType("modules.dynamo")
        database.initialize_session = lambda phase_num: None
        original_image = DeltaGenerator.image

        def local_images(container, image, *args, **kwargs):
            if isinstance(image, str) and image.startswith("https://"):
                return container.caption("External image omitted in offline test")
            return original_image(container, image, *args, **kwargs)

        root = Path(__file__).resolve().parents[1]
        app = AppTest.from_file(str(root / "pages_group/01_들어가기.py"))
        app.secrets.update({
            "openai_api_key": "test-key",
            "LANGCHAIN_TRACING_V2": "false",
            "LANGCHAIN_API_KEY": "",
            "LANGCHAIN_ENDPOINT": "https://example.invalid",
            "LANGCHAIN_PROJECT": "test",
        })
        with patch.dict("sys.modules", {"modules.dynamo": database}), patch.object(
            DeltaGenerator, "image", local_images
        ):
            app.run(timeout=30)
            self.assertFalse(app.exception)
            self.assertIn("Introduction 🚀", [title.value for title in app.title])
            self.assertFalse(app.text_input)
            self.assertTrue(app.session_state["user_id"].startswith("anonymous-"))
            session_id = app.session_state["session_uuid"]
            user_id = app.session_state["user_id"]
            app.run(timeout=30)
            self.assertFalse(app.exception)
            self.assertEqual(app.session_state["session_uuid"], session_id)
            self.assertEqual(app.session_state["user_id"], user_id)
