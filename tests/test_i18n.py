import unittest
from pathlib import Path
from html.parser import HTMLParser
import re

from i18n.assets import LOCALIZED_IMAGES, localized_image_path
from i18n.catalog import load_catalog, translate
from i18n import ai_language_instruction
from i18n.locale import DEFAULT_LOCALE, get_locale, normalize_locale, set_locale
from i18n.session import ensure_learning_session, reset_learning_session
from i18n.simulation import localize_simulation_html
from modules.evaluation import (
    build_application_evaluation_prompt,
    format_concepts,
    parse_application_evaluation,
)


def flatten_keys(value, prefix=""):
    keys = set()
    for key, child in value.items():
        path = f"{prefix}.{key}" if prefix else key
        if isinstance(child, dict):
            keys.update(flatten_keys(child, path))
        else:
            keys.add(path)
    return keys


class LocaleTests(unittest.TestCase):
    def test_english_is_the_default_locale(self):
        self.assertEqual(DEFAULT_LOCALE, "en")
        self.assertEqual(normalize_locale(None), "en")
        self.assertEqual(normalize_locale("EN-us"), "en")
        self.assertEqual(normalize_locale("/ko/"), "ko")
        self.assertEqual(normalize_locale("fr"), "en")

    def test_locale_helpers_work_with_an_explicit_state(self):
        state = {}
        self.assertEqual(get_locale(state), "en")
        self.assertEqual(set_locale("ko", state), "ko")
        self.assertEqual(get_locale(state), "ko")

    def test_ai_instruction_follows_the_selected_locale(self):
        self.assertIn("in English", ai_language_instruction("en"))
        self.assertIn("한국어로", ai_language_instruction("ko"))


class CatalogTests(unittest.TestCase):
    def test_catalogs_have_the_same_leaf_keys(self):
        self.assertEqual(flatten_keys(load_catalog("en")), flatten_keys(load_catalog("ko")))

    def test_catalog_translates_and_falls_back(self):
        self.assertEqual(translate("navigation.language", "en"), "Language")
        self.assertEqual(translate("navigation.language", "ko"), "언어")
        self.assertEqual(translate("missing.key", "ko"), "[missing.key]")


class LearningSessionTests(unittest.TestCase):
    def test_first_visit_creates_identifiers_without_login(self):
        state = {}
        session_id = ensure_learning_session(state)
        self.assertTrue(state["user_id"].startswith("anonymous-"))
        self.assertEqual(state["session_uuid"], session_id)
        self.assertEqual(state["session_id"], session_id)
        self.assertNotIn("logged_in", state)
        self.assertNotIn("username", state)

    def test_reruns_and_page_changes_reuse_identifiers(self):
        state = {}
        session_id = ensure_learning_session(state)
        user_id = state["user_id"]
        state["draft"] = "answer"
        self.assertEqual(ensure_learning_session(state), session_id)
        self.assertEqual(state["user_id"], user_id)
        self.assertEqual(state["draft"], "answer")

    def test_separate_visitors_get_separate_identifiers(self):
        first, second = {}, {}
        self.assertNotEqual(ensure_learning_session(first), ensure_learning_session(second))
        self.assertNotEqual(first["user_id"], second["user_id"])

    def test_empty_legacy_identifiers_are_repaired(self):
        state = {"logged_in": False, "user_id": None, "session_uuid": None,
                 "session_id": "stale"}
        session_id = ensure_learning_session(state)
        self.assertTrue(state["user_id"].startswith("anonymous-"))
        self.assertEqual(state["session_id"], session_id)

    def test_language_reset_preserves_identity_and_clears_learning(self):
        state = {"api_key": "test-key", "locale": "en"}
        old_session = ensure_learning_session(state)
        user_id = state["user_id"]
        state.update({"chat_history": ["old answer"], "current_phase": 3,
                      "pending_locale": "ko"})
        new_session = reset_learning_session("ko", state)
        self.assertNotEqual(new_session, old_session)
        self.assertEqual(state["session_uuid"], new_session)
        self.assertEqual(state["session_id"], new_session)
        self.assertEqual(state["user_id"], user_id)
        self.assertEqual(state["api_key"], "test-key")
        self.assertEqual(state["locale"], "ko")
        self.assertEqual(state["locale_selector"], "ko")
        self.assertNotIn("chat_history", state)
        self.assertNotIn("current_phase", state)
        self.assertNotIn("pending_locale", state)

    def test_reset_also_works_before_first_visit(self):
        state = {"draft": "answer"}
        self.assertTrue(reset_learning_session("en", state))
        self.assertTrue(state["user_id"].startswith("anonymous-"))
        self.assertNotIn("draft", state)


class SimulationTests(unittest.TestCase):
    def test_english_localization_replaces_simulation_labels(self):
        korean_html = (
            '<html lang="ko"><title>원운동 힘 방향 탐구</title>'
            '<button id="runBtn">연속</button>'
        )
        english_html = localize_simulation_html(korean_html, "en")
        self.assertIn('<html lang="en">', english_html)
        self.assertIn("Circular Motion Force Direction", english_html)
        self.assertIn(">Run</button>", english_html)
        self.assertEqual(localize_simulation_html(korean_html, "ko"), korean_html)


class LearningAssetTests(unittest.TestCase):
    def test_all_localized_assets_exist_and_originals_are_preserved(self):
        root = Path(__file__).resolve().parents[1]
        for name in LOCALIZED_IMAGES:
            original = f"src/images/{name}"
            with self.subTest(name=name):
                self.assertEqual(localized_image_path(original, "ko"), original)
                english = localized_image_path(original, "en")
                self.assertEqual(english, f"src/images/en/{name}")
                self.assertTrue((root / original).is_file())
                self.assertTrue((root / english).is_file())

    def test_neutral_and_user_images_are_not_redirected(self):
        for path in ("src/images/satellite_orbit_canvas.png",
                     "src/images/satellite_moon.png",
                     "src/draw_images/explain_2.png"):
            self.assertEqual(localized_image_path(path, "en"), path)


class FullSimulationTests(unittest.TestCase):
    def test_real_simulation_has_no_korean_visible_or_dynamic_text(self):
        class ContentParser(HTMLParser):
            def __init__(self):
                super().__init__()
                self.text = []
                self.attributes = []

            def handle_data(self, data):
                self.text.append(data)

            def handle_starttag(self, tag, attrs):
                self.attributes.extend(value or "" for _, value in attrs)

        root = Path(__file__).resolve().parents[1]
        korean = (root / "simulation/circular-motion-sim_responsive.html").read_text()
        english = localize_simulation_html(korean, "en")
        self.assertEqual(localize_simulation_html(korean, "ko"), korean)
        parser = ContentParser()
        parser.feed(english)
        # Include JavaScript strings, excluding source-code comments.
        content = "\n".join(parser.text + parser.attributes)
        content = re.sub(r"/\*.*?\*/", "", content, flags=re.S)
        content = re.sub(r"//[^\n]*", "", content)
        self.assertIsNone(re.search(r"[가-힣]", content))
        self.assertIn("runBtn.textContent = 'Run'", english)
        self.assertIn("runBtn.textContent = 'Stop'", english)
        self.assertIn("Velocity Direction:", english)


class EvaluationTests(unittest.TestCase):
    def test_prompt_requires_selected_ui_language(self):
        english_prompt = build_application_evaluation_prompt(
            question="Why does the Moon orbit Earth?",
            student_answer="Because of gravity.",
            conversation_history="",
            locale="en",
        )
        korean_prompt = build_application_evaluation_prompt(
            question="달은 왜 지구 주위를 도나요?",
            student_answer="중력 때문입니다.",
            conversation_history="",
            locale="ko",
        )
        self.assertIn("Write feedback in English", english_prompt)
        self.assertIn("Write feedback in Korean", korean_prompt)

    def test_evaluation_parser_validates_and_clamps_values(self):
        result = parse_application_evaluation(
            "Result:\n"
            '{"is_correct": true, "score": 120, '
            '"missing_concepts": ["gravity", "unknown"], '
            '"incorrect_concepts": [], "feedback": "Good explanation."}'
        )
        self.assertTrue(result["is_correct"])
        self.assertEqual(result["score"], 100)
        self.assertEqual(result["missing_concepts"], ["gravity"])
        self.assertEqual(format_concepts(["gravity"], "ko"), "중력")

    def test_evaluation_parser_rejects_non_json(self):
        with self.assertRaises(ValueError):
            parse_application_evaluation("not json")


if __name__ == "__main__":
    unittest.main()
