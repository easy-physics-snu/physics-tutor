import os
import re
import streamlit as st
import pandas as pd

from openai import OpenAI

from langchain_core.messages.chat import ChatMessage
from modules.retrieval import embed_file, create_chain
from langchain_teddynote import logging


# os.environ["LANGCHAIN_TRACING_V2"] = st.secrets["LANGCHAIN_TRACING_V2"]
# os.environ["LANGCHAIN_API_KEY"] = st.secrets["LANGCHAIN_API_KEY"]
# os.environ["LANGCHAIN_ENDPOINT"] = st.secrets["LANGCHAIN_ENDPOINT"]
# os.environ["LANGCHAIN_PROJECT"] = st.secrets["LANGCHAIN_PROJECT"]

st.session_state.api_key = st.secrets["openai_api_key"]

TEXTBOOK_FILE_PATH = "src/textbooks/physics_textbook.pdf"

TUTOR_OPENAI_MODEL = "gpt-4.1"
RAG_OPENAI_MODEL = "gpt-4.1"
RAG_SYSTEM_PROMPT = "prompts/doc-rag-scaffold.yaml"

SIDEBAR_AI_AVATAR = "src/images/ai_tutor_avatar.png"

# 캐시 디렉토리 생성
if not os.path.exists(".cache"):
    os.mkdir(".cache")

if not os.path.exists(".cache/embeddings"):
    os.mkdir(".cache/embeddings")


# 풀이 후 풍선 표시 여부
if "balloons_t1_q1" not in st.session_state:
    st.session_state.balloons_t1_q1 = False
if "balloons_t1_q2" not in st.session_state:
    st.session_state.balloons_t1_q2 = False
if "balloons_t2_q1" not in st.session_state:
    st.session_state.balloons_t2_q1 = False
if "balloons_t2_q2" not in st.session_state:
    st.session_state.balloons_t2_q2 = False
if "balloons_t2_q3" not in st.session_state:
    st.session_state.balloons_t2_q3 = False


# Tab2 진행 상태 플래그 (정답 여부)
if "t2_q1" not in st.session_state:
    st.session_state.t2_q1 = False
if "t2_q2" not in st.session_state:
    st.session_state.t2_q2 = False
if "t2_q3" not in st.session_state:
    st.session_state.t2_q3 = False


# 처음 1번만 실행하기 위한 코드
if "intro_1_tutor_messages" not in st.session_state:
    # 대화기록을 저장하기 위한 용도로 생성한다.
    st.session_state["intro_1_tutor_messages"] = []

if "balloons_done" not in st.session_state:
    st.session_state["balloons_done"] = False


# 파일 업로드 후 retriever 생성 (작업시간이 오래 걸릴 예정...)
if "pdf_retriever" not in st.session_state:
    retriever = embed_file(TEXTBOOK_FILE_PATH)
    st.session_state["pdf_retriever"] = retriever

# 체인 생성 (한 번만 생성하고 session_state에 저장)
# if "pdf_chain" not in st.session_state and st.session_state["pdf_retriever"]:
#     retriever = st.session_state["pdf_retriever"]
#     st.session_state["pdf_chain"] = create_chain(
#         retriever, prompt_path=RAG_SYSTEM_PROMPT, model_name=RAG_OPENAI_MODEL, messages_key="intro_1_tutor_messages"
#     )

######################################
########### Mainpage Logic ###########
######################################
st.title("들어가기 🚀")

st.subheader("오늘 배운 물리 개념은?")
st.info("- 먼저 **[1. 여러 가지 운동]** 과 **[2. 힘과 운동]** 소단원에서 배운 내용을 복습해봅시다. \n - 궁금한게 있으면 왼쪽 사이드바의 🧑🏻‍🏫**AI 선생님**에게 질문해보세요. \n - 아래 2개 탭을 모두 마치고 다음 단계로 넘어가주세요!")

st.image("src/images/find_tab_guide.png", width=500)

tab1, tab2 = st.tabs(["1. 여러 가지 운동", "2. 힘과 운동"])

# tab 전환 감지 및 상태 업데이트
if tab1:
    st.session_state['current_tab'] = 'tab1'
if tab2:
    st.session_state['current_tab'] = 'tab2'

########### TAB 1 ###########
with tab1:
    st.write("**Q1. 놀이공원에서 볼 수 있는 여러 가지 놀이 기구들의 운동 방향과 속력 변화를 표에 정리해봅시다.**")
    st.write("([운동 방향]과 [속력] 셀을 더블클릭한 후 알맞은 설명을 골라주세요)")
    df = pd.DataFrame(
        {
            "Type" : ["자이로드롭", "대관람차", "롤러코스터", "바이킹"],
            "Image": ["https://dimg.donga.com/ugc/CDB/SODA/Article/57/e0/f9/a4/57e0f9a4248cd2738de6.gif", "https://mblogthumb-phinf.pstatic.net/MjAyNDAxMTJfMjM3/MDAxNzA1MDQxNTI4NTI5.H9ncgGIDHPaCqa0i3Mz-2s8NU-qvEye8YQwlSQaFWZUg.wDDf8kJoDCbWyuVEBEqkzxfxQCv5GnNAMYw0Bo4nZnIg.GIF.onnamong/743084218.gif?type=w800", "https://media2.giphy.com/media/v1.Y2lkPTc5MGI3NjExMDM2ZTRueWxqMW00emRyanIxaGVwdGx4amR2aW5scDNnYnMzbTg4YiZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/WqSCrUOEWQpWC8JGNg/giphy.webp", "https://mblogthumb-phinf.pstatic.net/MjAyMjEyMjhfMTMx/MDAxNjcyMTYzMDc2Mzc3.RACWbUSQ5ys66npAKl1ABuFkloP9bs3D3Hg6Hv0rhG0g.z4ZBQI_SRDXNCaO8v51EZrYxIkCwLcnawqYXJjqunrsg.GIF.mok5022/3546279707.gif?type=w800"],
            "Direction": [None, None, None, None],
            "Speed": [None, None, None, None]
        }
    )

    column_configuration = {
        "Type": st.column_config.TextColumn("놀이 기구", disabled=True),
        "Image": st.column_config.ImageColumn("이미지 (더블클릭해서 확대해보세요)"),
        "Direction": st.column_config.SelectboxColumn(
            "운동 방향", options=["변한다", "일정하다"]
        ),
        "Speed": st.column_config.SelectboxColumn(
            "속력", options=["변한다", "일정하다"]
        ),
    }

    edited_df = st.data_editor(
        data=df,
        column_config=column_configuration,
        use_container_width=True,
        hide_index=True,
        num_rows="fixed",
        )

    st.session_state.q1 = False
    info_q1 = st.empty()
    if edited_df.notnull().all().all():
        if edited_df.iloc[0, 2] == "일정하다":
            if edited_df.iloc[0, 3] == "변한다":         
                if edited_df.iloc[1, 2] == "변한다":
                    if edited_df.iloc[1, 3] == "일정하다":
                        if edited_df.iloc[2, 2] == "변한다":
                            if edited_df.iloc[2, 3] == "변한다":
                                if edited_df.iloc[3, 2] == "변한다":
                                    if edited_df.iloc[3, 3] == "변한다":
                                        st.session_state.q1 = True
                                        info_q1.success("정답입니다!")
                                        if not st.session_state.balloons_t1_q1:
                                            st.balloons()
                                            st.session_state.balloons_t1_q1 = True
        if st.session_state.q1:
            info_q1.success("정답입니다!")
        else:
            info_q1.error("틀렸습니다. 다시 시도하세요.")

    st.write("")
    st.write("") 

    st.write("**Q2. 놀이 기구의 운동을 다음과 같이 분류해 봅시다.**")
    st.write("(각 놀이 기구는 중복없이 한가지에만 포함됩니다)")
    options_1 = st.multiselect(
        "속력만 변하는 운동",
        ["자이로드롭", "대관람차", "롤러코스터", "바이킹"],
    )
    options_2 = st.multiselect(
        "운동 방향만 변하는 운동",
        ["자이로드롭", "대관람차", "롤러코스터", "바이킹"],
    )
    options_3 = st.multiselect(
        "속력과 운동 방향이 모두 변하는 운동",
        ["자이로드롭", "대관람차", "롤러코스터", "바이킹"],
    )

    st.session_state.q2 = False
    info_q2 = st.empty()
    if options_1 and options_2 and options_3:
        if options_1 == ["자이로드롭"]:
            if options_2 == ["대관람차"]:
                if options_3 == ["롤러코스터", "바이킹"] or options_3 == ["바이킹", "롤러코스터"]:
                    st.session_state.q2 = True
                    info_q2.success("정답입니다!")
                    if not st.session_state.balloons_t1_q2:
                        st.balloons()
                        st.session_state.balloons_t1_q2 = True
        if st.session_state.q2:
            info_q2.success("정답입니다!")
        else:
            info_q2.error("틀렸습니다. 다시 시도하세요.")

    if st.session_state.q1 and st.session_state.q2:
        st.subheader("**핵심 정리!**")
        st.info("속력이 변하는 운동, 운동 방향이 변하는 운동, 속력과 운동 방향이 모두 변하는 운동은 모두 **가속도 운동**이다.")
        st.image("src/images/explain_2.png")
        
        # tab1 완료 시 다음 tab으로 안내
        st.success("🎉 Tab 1 완료! 이제 '힘과 운동' 탭으로 이동해주세요.")

########### TAB 2 ###########
with tab2:
    st.write("**Q1. 다음의 (괄호)안에 들어갈 표현으로 알맞은 과학 용어를 쓰세요.**")
    st.write("공을 발로 찰 때처럼 한 사람이 힘을 작용하기도 하지만 줄다리기처럼 여러 사람이 함께 힘을 작용할 때도 있다. 이처럼 한 물체에 여러 힘이 동시에 작용할 때 이 힘들과 같은 효과를 나타내는 하나의 힘을 1.(ㅇㅉㅎ)이라고 하며, 2.(ㅎㄹ)이라고도 한다.")
    t2_q1_1_input = st.text_input("1번 괄호의 답: ")
    t2_q1_2_input = st.text_input("2번 괄호의 답: ")

    if t2_q1_1_input and t2_q1_2_input:
        if t2_q1_1_input == "알짜힘" and t2_q1_2_input == "합력":
            st.success("정답입니다!")
            if not st.session_state.balloons_t2_q1:
                st.balloons()
                st.session_state.balloons_t2_q1 = True
            st.session_state.t2_q1 = True
            st.image("src/images/explain_3.png")
        else:
            st.error("틀렸습니다. 다시 시도하세요.")
            st.session_state.t2_q1 = False

    st.write("") 
    st.write("") 

    st.write("**Q2. 다음의 키워드를 이용해 뉴턴 운동 제1법칙을 설명해보세요.**")
    st.write("물체, 알짜힘, 운동 상태")
    t2_q2_input = st.text_area("뉴턴 운동 제1법칙이란: ")
    if t2_q2_input and st.button("제출", key="btn2"):
        with st.spinner("채점 중..."):
            client = OpenAI(api_key=st.session_state.api_key)
            system_prompt_q2 = """당신은 물리 교사입니다. 학생이 "물체, 알짜힘, 운동 상태" 키워드를 사용하여 뉴턴 운동 제1법칙을 설명하는 답안을 제출했습니다.

다음 기준에 따라 답안을 평가하고 점수와 피드백을 제공해주세요:

[평가 기준]
1. 필수 키워드 포함 (30점)
- "물체" 키워드 사용 (10점)
- "알짜힘" 키워드 사용 (10점)
- "운동 상태" 키워드 사용 (10점)

2. 뉴턴 제1법칙의 핵심 개념 설명 (70점)
- 알짜힘이 0인 조건 명시 (35점)
- 운동 상태 유지/변화 없음 설명 (35점)

[모범 답안 예시]
- "물체에 작용하는 알짜힘이 0일 때, 물체의 운동 상태가 변하지 않는다"
- "물체에 작용하는 알짜힘이 0일 때, 정지해 있는 물체는 계속 정지해 있고, 운동 중인 물체는 계속해서 등속도 운동을 한다"
- "물체에 작용하는 알짜힘이 0일 때, 물체가 현재의 운동 상태를 유지하려는 관성을 갖는다"

[출력 형식]
점수: [0-100점]

피드백: [2문장 이내로 부족한 부분이나 보완할 점을 구체적으로 제시]

예시 답변:
점수: 85점

피드백: 알짜힘이 0이라는 조건은 잘 설명했으나, 운동 상태가 변하지 않는다는 점을 더 명확히 표현하면 좋겠습니다. 모든 키워드를 자연스럽게 연결하여 하나의 완성된 문장으로 표현해보세요."""
            messages_q2 = [
                {"role": "system", "content": system_prompt_q2},
                {"role": "user", "content": t2_q2_input}
            ]
            response_q2 = client.chat.completions.create(model="gpt-4.1-mini", messages=messages_q2)
            msg_q2 = response_q2.choices[0].message.content
        st.info(msg_q2)
        score_match = re.search(r'(\d+)점', msg_q2)
        score_q2 = score_match.group(1) if score_match else "0"
        if int(score_q2) >= 80:
            st.success("축하합니다!")
            if not st.session_state.balloons_t2_q2:
                st.balloons()
                st.session_state.balloons_t2_q2 = True
            st.session_state.t2_q2 = True
            st.image("src/images/explain_4.png")
        else:
            st.error("조금 더 분발해서 다시 시도하세요.")
            st.session_state.t2_q2 = False


    st.write("") 
    st.write("") 

    st.write("**Q3. 다음의 키워드를 이용해 뉴턴 운동 제2법칙을 설명해보세요.**")
    st.write("물체, 알짜힘, 가속도, 질량")
    t2_q3_input = st.text_area("뉴턴 운동 제2법칙이란: ")
    st.spinner("채점 중...")
    if t2_q3_input and st.button("제출", key="btn3"):
        with st.spinner("채점 중..."):
            client = OpenAI(api_key=st.session_state.api_key)
            system_prompt_q3 = """당신은 물리 교사입니다. 학생이 "물체, 알짜힘, 가속도, 질량" 키워드를 사용하여 뉴턴 운동 제2법칙을 설명하는 답안을 제출했습니다.

다음 기준에 따라 답안을 평가하고 점수와 피드백을 제공해주세요:

[평가 기준]
1. 필수 키워드 포함 (40점)
- "물체" 키워드 사용 (10점)
- "알짜힘" 키워드 사용 (10점)
- "가속도" 키워드 사용 (10점)
- "질량" 키워드 사용 (10점)

2. 뉴턴 제2법칙의 핵심 개념 설명 (60점)
- 알짜힘과 가속도의 비례 관계 설명 (30점)
- 질량과 가속도의 반비례 관계 설명 (30점)

[모범 답안 예시]
- "물체에 작용하는 알짜힘이 클수록 가속도가 크고, 물체의 질량이 클수록 가속도가 작아진다"
- "물체에 작용하는 알짜힘이 물체의 질량과 가속도의 곱과 같다"
- "물체의 가속도는 작용하는 알짜힘에 비례하고 질량에 반비례한다"

[출력 형식]
점수: [0-100점]

피드백: [2문장 이내로 부족한 부분이나 보완할 점을 구체적으로 제시]

예시 답변:
점수: 80점

피드백: 알짜힘과 가속도의 비례 관계는 잘 설명했으나, 질량과의 관계가 명확하지 않습니다. 물체의 질량이 가속도에 미치는 영향을 추가로 설명해보세요."""
            messages_q3 = [
                {"role": "system", "content": system_prompt_q3},
                {"role": "user", "content": t2_q3_input}
            ]
            response_q3 = client.chat.completions.create(model="gpt-4.1-mini", messages=messages_q3)
            msg_q3 = response_q3.choices[0].message.content
        st.info(msg_q3)
        score_match = re.search(r'(\d+)점', msg_q3)
        score_q3 = score_match.group(1) if score_match else "0"
        if int(score_q3) >= 80:
            st.success("축하합니다!")
            if not st.session_state.balloons_t2_q3:
                st.balloons()
                st.session_state.balloons_t2_q3 = True
            st.session_state.t2_q3 = True
            st.image("src/images/explain_5.png")
        else:
            st.error("조금 더 분발해서 다시 시도하세요.")     
            st.session_state.t2_q3 = False

    # 진행률 계산 (탭2의 변경된 문항 기준으로)
    tab1_questions = ['Q1', 'Q2']
    tab2_questions = ['Q1', 'Q2', 'Q3']

    completed_tab1 = int(st.session_state.get('q1', False)) + int(st.session_state.get('q2', False))
    completed_tab2 = (
        int(st.session_state.get('t2_q1', False))
        + int(st.session_state.get('t2_q2', False))
        + int(st.session_state.get('t2_q3', False))
    )

    total_all_questions = len(tab1_questions) + len(tab2_questions)
    current_progress = completed_tab1 + completed_tab2
    progress = current_progress / total_all_questions

######################################
########### SIDEBAR LOGIC ###########
######################################

#### Progress bar ####
    with st.sidebar:
        st.markdown(
            """
            <style>
            [data-testid="stSidebar"] {
                position: fixed;
                right: 0;
                top: 0;
                height: auto;
                width: auto;
            }
            </style>
            """,
            unsafe_allow_html=True
        )
        st.markdown("⏳ 들어가기 진행률")
        st.progress(progress, text=f"진행률: {progress*100:.0f}% ({current_progress}/{total_all_questions})")
        st.caption(f"여러 가지 운동: {completed_tab1}/2, 힘과 운동: {completed_tab2}/3")

        remaining = []
        if not st.session_state.get('q1', False):
            remaining.append("Tab1 Q1")
        if not st.session_state.get('q2', False):
            remaining.append("Tab1 Q2")
        if not st.session_state.get('t2_q1', False):
            remaining.append("Tab2 Q1")
        if not st.session_state.get('t2_q2', False):
            remaining.append("Tab2 Q2")
        if not st.session_state.get('t2_q3', False):
            remaining.append("Tab2 Q3")

        if not remaining:
            st.success("모든 항목을 완료했습니다!")
            if not st.session_state.balloons_done:
                st.balloons()
                st.session_state.balloons_done = True
    
    # 다음 단계로 버튼 (모든 항목 완료 시 노출)
    if current_progress == total_all_questions:
        col1, col2, col3 = st.columns([5, 2, 2])
        with col3:
            if st.button(
                label="다음단계로",
                icon="⏩",
                help="생각하기로 이동하기",
                type="primary"
            ):
                st.switch_page("pages_group/02_생각하기.py")


#### AI Tutor ####
with st.sidebar:

    st.write("⏬ 혼자서 문제 풀기 너무 어렵다면? ⏬")

    toggle_ai_helper = st.toggle("**AI 선생님**과 대화하기", value=False)

    if toggle_ai_helper:

        st.warning("단, 스스로 충분히 고민해도 정말 모르겠을 때 사용하기!")

        messages = st.container(height=400)
            
        def print_messages():
            for chat_message in st.session_state["intro_1_tutor_messages"]:
                if chat_message.role == "assistant":
                    messages.chat_message(name=chat_message.role, avatar=SIDEBAR_AI_AVATAR).write(chat_message.content)
                else:
                    messages.chat_message(name=chat_message.role).write(chat_message.content)

        # 새로운 메시지를 추가
        def add_message(role, message):
            st.session_state["intro_1_tutor_messages"].append(ChatMessage(role=role, content=message))

        # 초기 대화 기록 추가
        if len(st.session_state["intro_1_tutor_messages"]) == 0:
            messages.chat_message("assistant", avatar=SIDEBAR_AI_AVATAR).write("안녕하세요. 어떤게 궁금한가요?")
        else:
            pass

        # 이전 대화 기록 출력
        print_messages()

        if user_input := st.chat_input("궁금한 내용을 물어보세요!", key="pdf_chat_input"):

            if st.session_state["pdf_retriever"]:
                # 매번 최신 대화 기록으로 체인 생성
                chain = create_chain(
                    st.session_state["pdf_retriever"], 
                    prompt_path=RAG_SYSTEM_PROMPT, 
                    model_name=RAG_OPENAI_MODEL, 
                    messages=st.session_state.get("intro_1_tutor_messages", [])
                )
                # 사용자의 입력
                messages.chat_message("user").write(user_input)
                
                # AI 답변 생성 중 스피너 표시
                with st.spinner("AI가 답변을 생성하고 있습니다..."):
                    # 스트리밍 호출
                    response = chain.stream(user_input)
                    with messages.chat_message("assistant", avatar=SIDEBAR_AI_AVATAR):
                        # 빈 공간(컨테이너)을 만들어서, 여기에 토큰을 스트리밍 출력한다.
                        container = st.empty()

                        ai_answer = ""
                        for token in response:
                            ai_answer += token
                            container.markdown(ai_answer)

                # 대화기록을 저장한다.
                add_message("user", user_input)
                add_message("assistant", ai_answer)
