from i18n.locale import get_locale, normalize_locale, set_locale
from i18n.session import ensure_learning_session, reset_learning_session


def enter_introduction(locale: str) -> None:
    """Resolve language entry URLs to the first learning step."""
    import streamlit as st

    target_locale = normalize_locale(locale)
    if get_locale() != target_locale and st.session_state.get("session_uuid"):
        reset_learning_session(target_locale)
    else:
        set_locale(target_locale)
    st.session_state["locale_selector"] = target_locale
    ensure_learning_session()
    st.switch_page("pages_group/01_들어가기.py")
