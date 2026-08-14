from i18n.locale import get_locale


LOCALE_ENTRY_PATHS = {
    "en": "pages_group/locale_en.py",
    "ko": "pages_group/locale_ko.py",
}


def locale_entry_path(locale: str | None = None) -> str:
    return LOCALE_ENTRY_PATHS[get_locale() if locale is None else locale]


def switch_to_locale_home() -> None:
    import streamlit as st

    st.switch_page(locale_entry_path())
