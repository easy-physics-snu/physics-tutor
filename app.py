import streamlit as st

from i18n import DEFAULT_LOCALE, get_locale, reset_learning_session, set_locale, t
from i18n.session import ensure_learning_session


st.set_page_config(layout="wide")

initial_locale = get_locale()

root_page = st.Page(
    "pages_group/locale_default.py",
    title=t("navigation.introduction"),
    default=True,
)
en_page = st.Page(
    "pages_group/locale_en.py",
    title=t("locale.en"),
    url_path="en",
)
ko_page = st.Page(
    "pages_group/locale_ko.py",
    title=t("locale.ko"),
    url_path="ko",
)
introduction_page = st.Page(
    "pages_group/01_들어가기.py",
    title=t("navigation.introduction"),
    url_path="introduction",
)
think_page = st.Page(
    "pages_group/02_생각하기.py",
    title=t("navigation.think"),
    url_path="think",
)
experiment_page = st.Page(
    "pages_group/03_실험하기.py",
    title=t("navigation.experiment"),
    url_path="experiment",
)
review_page = st.Page(
    "pages_group/04_돌아보기.py",
    title=t("navigation.review"),
    url_path="review",
)
apply_page = st.Page(
    "pages_group/05_적용하기.py",
    title=t("navigation.apply"),
    url_path="apply",
)

all_pages = [
    root_page,
    en_page,
    ko_page,
    introduction_page,
    think_page,
    experiment_page,
    review_page,
    apply_page,
]

pg = st.navigation(all_pages, position="hidden")

entry_locale = {"": DEFAULT_LOCALE, "en": "en", "ko": "ko"}.get(pg.url_path)
if entry_locale is not None and entry_locale != initial_locale:
    if st.session_state.get("session_uuid"):
        reset_learning_session(entry_locale)
    else:
        set_locale(entry_locale)
    st.session_state["locale_selector"] = entry_locale
    st.rerun()

set_locale(st.session_state.get("locale", DEFAULT_LOCALE))

if entry_locale is not None:
    pg.run()
    st.stop()

ensure_learning_session()
current_locale = get_locale()
st.session_state.setdefault("locale_selector", current_locale)

with st.sidebar:
    selected_locale = st.selectbox(
        t("navigation.language"),
        options=["en", "ko"],
        key="locale_selector",
        format_func=lambda locale: t(f"locale.{locale}"),
    )

    if selected_locale != current_locale:
        if st.session_state.get("session_uuid"):
            st.session_state["pending_locale"] = selected_locale
        else:
            set_locale(selected_locale)
            st.switch_page(en_page if selected_locale == "en" else ko_page)

    pending_locale = st.session_state.get("pending_locale")
    if pending_locale and pending_locale != current_locale:
        st.warning(t("locale.change_warning"))
        confirm_col, cancel_col = st.columns(2)
        if confirm_col.button(t("locale.confirm"), use_container_width=True):
            reset_learning_session(pending_locale)
            st.switch_page(en_page if pending_locale == "en" else ko_page)
        if cancel_col.button(t("locale.cancel"), use_container_width=True):
            st.session_state["pending_locale"] = None
            st.session_state["locale_selector"] = current_locale
            st.rerun()

    st.markdown("---")
    st.markdown(f"**{t('app.group_title')}**")
    st.page_link(introduction_page, label=t("navigation.introduction"))
    st.page_link(think_page, label=t("navigation.think"))
    st.page_link(experiment_page, label=t("navigation.experiment"))
    st.page_link(review_page, label=t("navigation.review"))
    st.page_link(apply_page, label=t("navigation.apply"))

pg.run()
