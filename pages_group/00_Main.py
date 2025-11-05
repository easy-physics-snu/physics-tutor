import os
import streamlit as st
import time
import uuid

# Langchain 환경 변수 설정
os.environ["LANGCHAIN_TRACING_V2"] = st.secrets["LANGCHAIN_TRACING_V2"]
os.environ["LANGCHAIN_API_KEY"] = st.secrets["LANGCHAIN_API_KEY"]
os.environ["LANGCHAIN_ENDPOINT"] = st.secrets["LANGCHAIN_ENDPOINT"]
os.environ["LANGCHAIN_PROJECT"] = st.secrets["LANGCHAIN_PROJECT"]

# OpenAI API 키 설정
st.session_state.api_key = st.secrets["openai_api_key"]

# 캐시 디렉토리 생성
if not os.path.exists(".cache"):
    os.mkdir(".cache")

if not os.path.exists(".cache/embeddings"):
    os.mkdir(".cache/embeddings")

# 로그인 상태 관리
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

if "session_uuid" not in st.session_state:
    st.session_state["session_uuid"] = None

if "session_id" not in st.session_state:
    st.session_state["session_id"] = None # 호환성 유지 (사용하지 않을 수도 있음)

st.set_page_config(layout="wide")

st.title("📚얘들아 물리 쉬워 (Easy Physics)✨")
st.write("**얘들아 물리 쉬워**는 물리 개념을 학습하고 문제를 풀어볼 수 있는 AI 기반 학습 도구입니다.")

# secrets.toml에서 사용자 정보 가져오기
users_info = st.secrets["users"]

# 로그인 UI
username = st.text_input("Username")
password = st.text_input("Password", type="password")

if st.button("Log in", type="primary"):
    if username not in users_info:
        st.error("Username을 확인해주세요.")
    else:
        if password != users_info[username]["password"]:
            st.error("Password를 확인해주세요.")
        else:
            # 로그인 성공 시 모든 필요한 session state 업데이트
            st.session_state.logged_in = True
            st.session_state["username"] = username
            st.session_state["user_id"] = users_info[username]["userID"]
            
            # 세션 ID 초기화
            st.session_state["session_uuid"] = str(uuid.uuid4())
            st.session_state["session_id"] = st.session_state["session_uuid"]

            st.success(f"로그인 성공! 환영합니다, {username}님!")
            time.sleep(0.5)
            st.switch_page("pages_group/01_들어가기.py")
