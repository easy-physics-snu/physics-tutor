import streamlit as st


pages = {
    # "Your account": [
    #     st.Page("create_account.py", title="Create your account"),
    #     st.Page("manage_account.py", title="Manage your account"),
    # ],
    "📚얘들아 물리 쉬워✨": [
        st.Page("pages_group/00_Main.py", title="메인 페이지 🚪"), 
        st.Page("pages_group/01_들어가기.py", title="들어가기 🚀"), 
        st.Page("pages_group/02_생각하기.py", title="생각하기 🤔"),
        st.Page("pages_group/03_실험하기.py", title="실험하기 🧪"),
        st.Page("pages_group/04_돌아보기.py", title="돌아보기 🧐"),
        st.Page("pages_group/05_적용하기.py", title="적용하기 💡"),   
    ],
}

pg = st.navigation(pages)
pg.run()
