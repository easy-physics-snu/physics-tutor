import os
import time
import uuid

import streamlit as st

from i18n import t


def render_main() -> None:
    os.environ["LANGCHAIN_TRACING_V2"] = st.secrets["LANGCHAIN_TRACING_V2"]
    os.environ["LANGCHAIN_API_KEY"] = st.secrets["LANGCHAIN_API_KEY"]
    os.environ["LANGCHAIN_ENDPOINT"] = st.secrets["LANGCHAIN_ENDPOINT"]
    os.environ["LANGCHAIN_PROJECT"] = st.secrets["LANGCHAIN_PROJECT"]

    st.session_state.api_key = st.secrets["openai_api_key"]
    os.makedirs(".cache/embeddings", exist_ok=True)

    st.session_state.setdefault("logged_in", False)
    st.session_state.setdefault("user_id", None)
    st.session_state.setdefault("session_uuid", None)
    st.session_state.setdefault("session_id", None)

    st.title(t("app.title"))
    st.write(t("app.description"))

    users_info = st.secrets["users"]
    username = st.text_input(t("auth.username"))
    password = st.text_input(t("auth.password"), type="password")

    if st.button(t("auth.login"), type="primary"):
        if username not in users_info:
            st.error(t("auth.invalid_username"))
        elif password != users_info[username]["password"]:
            st.error(t("auth.invalid_password"))
        else:
            st.session_state.logged_in = True
            st.session_state["username"] = username
            st.session_state["user_id"] = users_info[username]["userID"]

            session_uuid = str(uuid.uuid4())
            st.session_state["session_uuid"] = session_uuid
            st.session_state["session_id"] = session_uuid

            st.success(t("auth.success", username=username))
            time.sleep(0.5)
            st.switch_page("pages_group/01_들어가기.py")
