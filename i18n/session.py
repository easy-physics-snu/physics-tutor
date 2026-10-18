import uuid
from collections.abc import MutableMapping
from typing import Any

from i18n.locale import set_locale


PRESERVED_STATE_KEYS = {"user_id", "api_key", "locale", "locale_selector"}


def ensure_learning_session(state: MutableMapping[str, Any] | None = None) -> str:
    """Create anonymous learning identifiers once per browser session."""
    if state is None:
        import streamlit as st

        state = st.session_state

    if not state.get("user_id"):
        state["user_id"] = f"anonymous-{uuid.uuid4()}"
    if not state.get("session_uuid"):
        state["session_uuid"] = str(uuid.uuid4())
    state["session_id"] = state["session_uuid"]
    return state["session_uuid"]


def reset_learning_session(
    target_locale: str,
    state: MutableMapping[str, Any] | None = None,
) -> str:
    """Clear learning state and start a new session with the same anonymous user."""
    if state is None:
        import streamlit as st

        state = st.session_state

    preserved = {key: state[key] for key in PRESERVED_STATE_KEYS if key in state}
    for key in list(state.keys()):
        del state[key]
    state.update(preserved)

    locale = set_locale(target_locale, state=state)
    state["locale_selector"] = locale
    return ensure_learning_session(state)
