import uuid
from collections.abc import MutableMapping
from typing import Any

from i18n.locale import set_locale


AUTH_STATE_KEYS = {
    "logged_in",
    "username",
    "user_id",
    "api_key",
}
LOCALE_STATE_KEYS = {
    "locale",
    "locale_selector",
}


def reset_learning_session(
    target_locale: str,
    state: MutableMapping[str, Any] | None = None,
) -> str | None:
    """Clear learning state while preserving authentication and locale choice."""
    if state is None:
        import streamlit as st

        state = st.session_state

    preserved_keys = AUTH_STATE_KEYS | LOCALE_STATE_KEYS
    preserved = {key: state[key] for key in preserved_keys if key in state}
    for key in list(state.keys()):
        del state[key]
    state.update(preserved)

    locale = set_locale(target_locale, state=state)
    state["locale_selector"] = locale
    state.pop("pending_locale", None)

    if state.get("logged_in") and state.get("user_id") is not None:
        new_session_uuid = str(uuid.uuid4())
        state["session_uuid"] = new_session_uuid
        state["session_id"] = new_session_uuid
        return new_session_uuid

    state["session_uuid"] = None
    state["session_id"] = None
    return None
