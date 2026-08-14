from collections.abc import MutableMapping
from typing import Any


DEFAULT_LOCALE = "en"
SUPPORTED_LOCALES = ("en", "ko")
LOCALE_STATE_KEY = "locale"


def normalize_locale(locale: str | None) -> str:
    if not locale:
        return DEFAULT_LOCALE
    normalized = str(locale).lower().split("-")[0].strip("/")
    return normalized if normalized in SUPPORTED_LOCALES else DEFAULT_LOCALE


def _session_state() -> MutableMapping[str, Any]:
    import streamlit as st

    return st.session_state


def get_locale(state: MutableMapping[str, Any] | None = None) -> str:
    state = state if state is not None else _session_state()
    locale = normalize_locale(state.get(LOCALE_STATE_KEY))
    state[LOCALE_STATE_KEY] = locale
    return locale


def set_locale(locale: str, state: MutableMapping[str, Any] | None = None) -> str:
    state = state if state is not None else _session_state()
    normalized = normalize_locale(locale)
    state[LOCALE_STATE_KEY] = normalized
    return normalized
