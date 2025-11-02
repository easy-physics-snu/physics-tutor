import os
import re
import streamlit as st
import time

from typing import List
# from pydantic import BaseModel, Field
from langchain_core.messages.chat import ChatMessage
from langchain_core.messages import BaseMessage
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_openai import ChatOpenAI #, OpenAIEmbeddings

from langchain_teddynote import logging
from modules.retrieval import embed_file, create_chain

st.session_state.api_key = st.secrets["openai_api_key"]

# 각 사용자별 고유 세션 ID 생성
if "unique_session_id" not in st.session_state:
    import uuid
    st.session_state["unique_session_id"] = str(uuid.uuid4())

# 처음 1번만 실행하기 위한 코드
if "messages_application" not in st.session_state:
    # 대화기록을 저장하기 위한 용도로 생성한다.
    st.session_state["messages_application"] = []

# 처음 1번만 실행하기 위한 코드
if "messages_application_tutor" not in st.session_state:
    # 대화기록을 저장하기 위한 용도로 생성한다.
    st.session_state["messages_application_tutor"] = []

# # 제출 버튼 상태 관리
# if "submit_button_disabled" not in st.session_state:
#     st.session_state["submit_button_disabled"] = True

if "show_answer" not in st.session_state:
    st.session_state["show_answer"] = False

if "feedback_processed" not in st.session_state:
    st.session_state["feedback_processed"] = False

if "last_submission_time" not in st.session_state:
    st.session_state["last_submission_time"] = 0

if "score" not in st.session_state:
    st.session_state["score"] = 0

# 메인 페이지 하단 리소스 섹션 노출 플래그
if "show_resources" not in st.session_state:
    st.session_state["show_resources"] = False


TUTOR_OPENAI_MODEL = "gpt-4.1-mini"

SIDEBAR_AI_AVATAR = "src/images/ai_tutor_avatar.png"

os.environ["LANGCHAIN_TRACING_V2"] = st.secrets["LANGCHAIN_TRACING_V2"]
os.environ["LANGCHAIN_API_KEY"] = st.secrets["LANGCHAIN_API_KEY"]
os.environ["LANGCHAIN_ENDPOINT"] = st.secrets["LANGCHAIN_ENDPOINT"]
os.environ["LANGCHAIN_PROJECT"] = st.secrets["LANGCHAIN_PROJECT"]

# 캐시 디렉토리 생성
if not os.path.exists(".cache"):
    os.mkdir(".cache")

# 세션 기록을 저장할 딕셔너리
store = {} 

# class InMemoryHistory(BaseChatMessageHistory, BaseModel):
#     """In memory implementation of chat message history."""

#     messages: List[BaseMessage] = Field(default_factory=list)

#     def add_messages(self, messages: List[BaseMessage]) -> None:
#         """Add a list of messages to the store"""
#         self.messages.extend(messages)

#     def clear(self) -> None:
#         self.messages = []


# def get_by_session_id(session_id: str) -> BaseChatMessageHistory:
#     if session_id not in store:
#         store[session_id] = InMemoryHistory()
#     return store[session_id]

# def enable_submit_button():
#     st.session_state["submit_button_disabled"] = False

# def disable_submit_button():
#     st.session_state["submit_button_disabled"] = True

# 점수를 별 모양으로 변환하는 함수
def score_to_stars(score):
    """점수를 별 모양으로 변환
    0~19: ⭐☆☆☆☆
    20~39: ⭐⭐☆☆☆
    40~59: ⭐⭐⭐☆☆
    60~79: ⭐⭐⭐⭐☆
    80~100: ⭐⭐⭐⭐⭐
    """
    if score < 20:
        return "⭐☆☆☆☆"
    elif score < 40:
        return "⭐⭐☆☆☆"
    elif score < 60:
        return "⭐⭐⭐☆☆"
    elif score < 80:
        return "⭐⭐⭐⭐☆"
    else:
        return "⭐⭐⭐⭐⭐"

# 세션 ID를 기반으로 세션 기록을 가져오는 함수
def get_session_history(session_ids: str) -> BaseChatMessageHistory:
    print(session_ids)
    if session_ids not in store:  # 세션 ID가 store에 없는 경우
        # 새로운 ChatMessageHistory 객체를 생성하여 store에 저장
        store[session_ids] = ChatMessageHistory()
    return store[session_ids]  # 해당 세션 ID에 대한 세션 기록 반환


######################################
########### Mainpage Logic ###########
######################################
st.set_page_config(layout="wide")

st.title("적용하기 💡")
st.info("- 배운 내용을 새로운 상황에 적용해보며 개념을 더 깊게 이해해봅시다. \n - 지구 주위를 도는 달의 모습을 관찰해보고 그 이유를 설명해보세요. \n - 좌측 사이드바의 🧑🏻‍🏫**AI 선생님**과 대화하며 내 이해를 확인해보세요.")

@st.fragment
def update_progress(progress_value, current_step, total_steps):
    st.progress(progress_value, text=f"진행률: {progress_value*100:.0f}% ({current_step}/{total_steps})")


# Progress bar를 우측 상단에 고정
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
    st.markdown("⏳ 적용하기 진행률")
    
    # 진행률 계산: 대화 완료 여부에 따라
    if st.session_state.get("show_resources", False) or st.session_state.get("conversation_completed", False):
        current_step = 2
        total_steps = 2
        progress_value = 1.0
    elif (len(st.session_state.get("messages_application", [])) > 0 and 
        any(msg.role == "user" for msg in st.session_state.get("messages_application", []))):
        # 사용자 메시지가 한 번이라도 있으면 50% (즉, 실제로 답변을 제출했을 때만)
        current_step = 1
        total_steps = 2
        progress_value = 0.5
    else:
        # 아직 시작 전이면 0%
        current_step = 0
        total_steps = 2
        progress_value = 0.0
    
    update_progress(progress_value, current_step, total_steps)    


with st.container(border=True):  # border=True로 실선 테두리 추가
    st.markdown(body="""
    ## 등속 원운동

    놀이공원의 회전목마, 지구 주위를 도는 인공위성, 시곗바늘 등은 일정한 속력으로 원을 그리며 운동하는데, 이러한 운동을 등속 원운동이라고 한다.
    등속 원운동 하는 물체는 속력이 변하지 않고 운동 방향만 변한다. (교과서 16쪽)
    """)

st.image("https://bobmoler.wordpress.com/wp-content/uploads/2019/03/orbit_360p30-1.gif", caption="지구 주위를 도는 달의 모습")


# 처음 1번만 실행하기 위한 코드
if "messages_application" not in st.session_state:
    # 대화기록을 저장하기 위한 용도로 생성한다.
    st.session_state["messages_application"] = []

# 적용 질문(나중엔 DB에서 불러오면 좋을 듯)
applyingQuestion = """
마지막으로, 배운 내용을 새로운 상황에 적용해봅시다.\n
위 그림과 같이 달이 공전 궤도를 유지하면서 계속 지구를 돌 수 있는 이유는 무엇일까요?
"""

# 적용하기 모범답안 (나중엔 DB에서 불러오면 좋을 듯)
applyingModeledAnswer = "지구가 달에 지구 중심방향으로 향하는 힘(중력)을 작용하고 있어서, 달은 지구 주변을 계속 원운동할 수 있습니다." 

# 핵심 개념(나중엔 DB에서 불러오면 좋을 듯)
essential_contents = "등속 원운동"


if not st.session_state.get("show_resources", False):

    # 메인 화면에 질문 표시
    st.markdown("**문제 상황**")
    st.markdown("위 그림과 같이 달이 공전 궤도를 유지하면서 계속 지구를 돌 수 있는 이유는 무엇일까요?")

    # text_area의 키보드 단축키 힌트 숨기기
    st.markdown(
        """
        <style>
        /* 키보드 힌트 완전히 숨기기 */
        .stTextArea [data-testid="InputInstructions"] {
            display: none !important;
        }
        .stTextArea div[class*="InputInstructions"] {
            display: none !important;
        }
        .stTextArea textarea ~ div {
            display: none !important;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    # 답변 입력 영역
    text_area_key = st.session_state.get("text_area_key", 0)
    reason = st.text_area(
        label="내 답변을 작성해주세요.",
        height=200,
        key=f"text_area_{text_area_key}"
    )

    # if not reason:
    #     disable_submit_button()

    submit_button = st.button(
        label="제출하기",
        type="primary",
        use_container_width=True
    )

    if submit_button:
        import time
        current_time = time.time()
        
        # 답변이 비어있으면 경고
        if not reason or not reason.strip():
            st.warning("답변을 작성해주세요.")
        # 같은 답변이 연속으로 제출되는 것을 방지 (5초 이내 중복 제출 방지)
        elif current_time - st.session_state.get("last_submission_time", 0) < 5:
            st.warning("잠시 후 다시 시도해주세요.")
        else:
            st.session_state["explanation_user_reason"] = reason
            st.session_state["explanation_submission_triggered"] = True  # 제출이 트리거되었음을 표시
            st.session_state["feedback_processed"] = False  # 피드백 처리 플래그 리셋
            st.session_state["text_area_key"] = st.session_state.get("text_area_key", 0) + 1  # text_area 키 변경
            st.session_state["last_submission_time"] = current_time  # 제출 시간 기록
            st.success("제출 완료! 좌측 사이드바에서 🧑🏻‍🏫AI 선생님의 피드백을 확인해보세요:)")

# 메인 하단 리소스 섹션
if st.session_state.get("show_resources", False):
    st.subheader("더 알아봅시다!")
    with st.container(border=True):
        tab1, tab2 = st.tabs(["읽어보면 좋은 글", "관련 유튜브 영상"])

        with tab1:
            st.write("⏬ 아래 기사를 참고해보세요 ⏬ (기사 제목 클릭)")
            st.page_link(page="https://blog.hyundai-rotem.co.kr/671", label="<철도에 사용되는 과학기술: 고속 주행에도 안전한 커브는 OOO덕분?!>")
            st.image("https://img1.daumcdn.net/thumb/R1280x0/?scode=mtistory2&fname=https%3A%2F%2Fblog.kakaocdn.net%2Fdna%2Fc4OysX%2FbtruRMLUUsC%2FAAAAAAAAAAAAAAAAAAAAAJfF5rx9v7vc9kbmx8Ez9-eVnTSHIXqTV7EEN-OPyi4r%2Fimg.jpg%3Fcredential%3DyqXZFxpELC7KVnFOS48ylbz2pIh7yKj8%26expires%3D1759244399%26allow_ip%3D%26allow_referer%3D%26signature%3DufVaE0921PMCrw57Gpu%252FanjcQZs%253D")

        with tab2:
            st.write("유튜브 영상으로 알아보는 오늘의 과학 개념")
            st.video("https://youtu.be/FHrR_W4w_MA?feature=shared")


#####################################
########### Sibebar Logic ###########
#####################################
with st.sidebar:

    st.write("**AI 선생님**의 피드백")
    messages = st.container(height=400)
    ai_info = st.empty()

    # 답변 체인 생성
    def create_chain(model_name=TUTOR_OPENAI_MODEL):
        # First chain for relevance checking
        relevance_check_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """You are a grader assessing the relevance of a student's essay answer to a given model answer. 
                    Here is the model answer: {applyingModeledAnswer}

                    Consider both the student's current answer and their previous responses in the conversation history to evaluate their understanding.
                    
                    Evaluation criteria:
                    1. Accuracy and relevance compared to the model answer
                    2. Physical correctness: Whether the student's answer is physically accurate and follows proper physics principles
                    3. Progressive improvement in understanding and Integration of previous responses with new insights shown through the conversation
                    
                    Combine the current input and conversation history to form a complete understanding of the student's answer.
                    Then compare this combined answer against the model answer.
                    
                    Analyze the matching and non-matching content between the student's answer and the model answer.
                    
                    Return your response in the following format:
                    score: [0-100 double type relevance score]
                    missing_contents: [List missing concepts]
                    incorrect_contents: [List incorrect concepts]"""
                ),
                MessagesPlaceholder(variable_name="history"),
                ("human", "{input}"),
                ("ai", "Based on both the current answer and previous responses, provide the analysis in the specified format."),
            ]
        )

        # Second chain for scaffolding
        scaffolding_prompt = ChatPromptTemplate.from_messages(
            [
                ( ##지금 핵심 교육 전략 부분이 나와도 5단계에서의 학생 답변이 맞으면 넘어가는 방식이라서 대화를 안 하게 됨!!!
                    "system",
                    """당신은 친근하고 대화형 학습을 돕는 **물리 튜터**입니다. 항상 존댓말을 사용하며 긍정적이고 격려하는 태도로 일관된 대화를 유지하세요.  

                    **목표:** 학생이 새로 익힌 [핵심 개념]과 관련된 개념을 새로운 [문제 상황]에 적용하고, 이를 통해 개념의 유용성을 탐구하며 반성적 사고를 할 수 있도록 대화를 통해 돕습니다.

                    **핵심 교육 전략:**
                        학생이 개별 사례를 넘어서 원리를 일반화하도록 유도하세요:
                            - 학생이 특정 개념을 이해했다면, 다른 유사한 상황에서도 같은 원리가 적용되는지 탐구하도록 질문하세요.
                            - 예: "달뿐만 아니라 인공위성, 심지어 태양을 도는 지구까지 모두 비슷한 원리로 궤도를 유지해요. 이들의 공통적인 특징은 무엇일까요?"
                            - 예: "우리 주변의 원운동을 찾아볼까요? 놀이공원의 회전 그네, 끈에 매달린 공을 돌리는 것, 달의 공전 - 이 세 가지가 모두 같은 물리 원리로 설명될 수 있다고 생각하나요?"
                            - 학생이 배운 개념을 새로운 맥락에 적용할 수 있도록 격려하고, 공통된 원리를 발견하도록 안내하세요.

                    **중요:** 다음 규칙을 반드시 따르세요.
                    1. 세 문장을 넘지 않도록 대화를 생성하세요.  
                    2. ⚠️ **절대 금지**: 정답이나 지나친 암시를 제공하지 마세요.
                    3. 만약 학생의 답변에 [놓친 개념]이 있다면, [놓친 개념]을 질문 형태로 간접적으로 제시해주고, 이를 포함하여 정확하게 답변해달라고 요청하세요.
                    4. 만약 학생의 답변에 [잘못된 개념]이 있다면 
                        - [잘못된 개념]에 대해 직접적으로 말하지 말고, 학생이 스스로 탐색할 수 있도록 열린 질문을 통해 [잘못된 개념]에 불만족을 가질 수 있도록 반례를 들어 학생과 문답하세요.
                        - 만약 [잘못된 개념]에 대하여 3회 이상 문답했지만 계속 [잘못된 개념]을 고수하는 경우에는 올바른 과학적 개념을 알려주세요.
                       

                    [답변 점수]: {score}
                    [문제 상황]: {applyingQuestion}
                    [모범 답안]: {applyingModeledAnswer}
                    [놓친 개념]: {missing_contents}
                    [잘못된 개념]: {incorrect_contents}
                    [핵심 개념]: {essential_contents}
                    """
                ),
                # 대화 기록을 변수로 사용, history 가 MessageHistory 의 key 가 됨
                MessagesPlaceholder(variable_name="history"),
                ("human", "{input}"),
            ]
        )

        llm = ChatOpenAI(model_name=model_name, temperature=0.1, openai_api_key = st.session_state.api_key)

        def process_input(user_input, is_init=False):

            # First, get the relevance check
            relevance_chain = RunnableWithMessageHistory(
                relevance_check_prompt | llm,
                get_session_history,
                input_messages_key="input",
                history_messages_key="history",
            )
            
            relevance_check_response = relevance_chain.invoke(
                {"input": user_input, "applyingModeledAnswer": applyingModeledAnswer},
                config={"configurable": {"session_id": st.session_state["unique_session_id"]}}
            )
            
            # Parse the response
            response_text = relevance_check_response.content
            print(response_text)
            # Extract score
            score_match = re.search(r'score:\s*(\d+\.?\d*)', response_text)
            score = float(score_match.group(1)) if score_match else 0
            st.session_state["score"] = score
            
            # Extract missing contents
            missing_match = re.search(r'missing_contents:\s*\[(.*?)\]', response_text, re.DOTALL)
            missing_contents = missing_match.group(1).strip() if missing_match else ""
            
            # Extract incorrect contents
            incorrect_match = re.search(r'incorrect_contents:\s*\[(.*?)\]', response_text, re.DOTALL)
            incorrect_contents = incorrect_match.group(1).strip() if incorrect_match else ""
            
            # Now get the scaffolding response
            scaffolding_chain = RunnableWithMessageHistory(
                scaffolding_prompt | llm,
                get_session_history,
                input_messages_key="input",
                history_messages_key="history",
            )
            
            # Store missing_contents in session state
            st.session_state["missing_contents"] = missing_contents
            
            # Return streaming response
            return scaffolding_chain.stream(
                {
                    "input": user_input,
                    "applyingQuestion": applyingQuestion,
                    "applyingModeledAnswer": applyingModeledAnswer,
                    "score": score,
                    "missing_contents": missing_contents,
                    "incorrect_contents": incorrect_contents,
                    "essential_contents": essential_contents
                },
                config={"configurable": {"session_id": st.session_state["unique_session_id"]}}
            )
        
        return process_input

    # 이전 대화를 출력
    def print_messages():
        for chat_message in st.session_state["messages_application"]:
            if chat_message.role == "assistant":
                messages.chat_message(chat_message.role, avatar=SIDEBAR_AI_AVATAR).write(chat_message.content)
            else:
                messages.chat_message(chat_message.role).write(chat_message.content)

    # 새로운 메시지를 추가
    def add_message(role, message):
        st.session_state["messages_application"].append(ChatMessage(role=role, content=message))

    # 이전 대화 기록 출력
    print_messages()

    # 체인 생성
    if "application_chain" not in st.session_state:
        st.session_state["application_chain"] = create_chain()

    chain = st.session_state["application_chain"]

    # 제출된 답변에 대한 피드백 처리 (한 번만 실행)
    if (st.session_state.get("explanation_submission_triggered", False) and 
        "explanation_user_reason" in st.session_state and 
        not st.session_state.get("feedback_processed", False)):

        # 즉시 상태 리셋하여 무한 루프 방지
        st.session_state["explanation_submission_triggered"] = False
        st.session_state["feedback_processed"] = True

        # 사용자의 제출된 답변 표시
        messages.chat_message("user").write(f"(제출한 답변): {st.session_state['explanation_user_reason']}")

        # AI 피드백 생성 (스트리밍) - 스피너와 함께
        with st.spinner("AI가 답변을 생성하고 있습니다..."):
            response_stream = chain(st.session_state['explanation_user_reason'], False)
            
            streamed_text = ""
            feedback_placeholder = None
            # 대화가 완료되지 않은 경우에만 AI 응답 표시
            if not st.session_state.get("conversation_completed", False):
                with messages.chat_message("assistant", avatar=SIDEBAR_AI_AVATAR):
                    # 별 모양 표시 (점수 기반)
                    stars = score_to_stars(st.session_state.get("score", 0))
                    st.markdown(f"**현재 점수: {stars}**")
                    
                    feedback_placeholder = st.empty()
                    
                    # 스트리밍 응답 처리
                    for chunk in response_stream:
                        if hasattr(chunk, 'content'):
                            streamed_text += chunk.content
                            feedback_placeholder.markdown(streamed_text)
                            time.sleep(0.02)

        # 사용자 메시지는 항상 대화 기록에 추가
        add_message("user", f"(제출한 답변): {st.session_state['explanation_user_reason']}")

        # relevance score 확인 후 처리
        try:
            # 80% 이상 달성 시 → 일반 피드백은 화면에서 지우고 완료 메시지만 표시
            if st.session_state["score"] >= 80:
                # 방금 표시한 일반 피드백 지우기
                if feedback_placeholder:
                    feedback_placeholder.empty()
                
                st.balloons()
                with messages.chat_message("assistant", avatar=SIDEBAR_AI_AVATAR):
                    st.markdown(f"**현재 점수: ⭐⭐⭐⭐⭐**")
                    st.write("축하합니다! 충분히 잘 이해하셨네요. 모범 답안은 다음과 같습니다.")
                    st.markdown("   [**" + f"{applyingModeledAnswer}"+"**]")
                    if len(st.session_state['missing_contents']) > 0:
                        missing_text = ''.join(st.session_state['missing_contents']).strip()
                        if missing_text:  # 빈 문자열이 아닌 경우에만 출력
                            st.write(f"   지금도 충분히 좋은 답변이지만, [{missing_text}] 를 포함하여 작성했다면 더 완벽한 답이 작성되었겠네요.")
                    st.write("오늘 수업은 여기까지입니다. 잠시 뒤 수업 마무리 화면으로 넘어갑니다.")
                    time.sleep(6)
                
                # 완료 메시지를 대화 기록에 추가 (별 5개 포함)
                completion_msg = f"**현재 점수: ⭐⭐⭐⭐⭐**\n\n축하합니다! 충분히 잘 이해하셨네요. 모범 답안은 다음과 같습니다.\n\n[**{applyingModeledAnswer}**]"
                if len(st.session_state['missing_contents']) > 0:
                    missing_text = ''.join(st.session_state['missing_contents']).strip()
                    if missing_text:
                        completion_msg += f"\n\n지금도 충분히 좋은 답변이지만, [{missing_text}] 를 포함하여 작성했다면 더 완벽한 답이 작성되었겠네요."
                completion_msg += "\n\n오늘 수업은 여기까지입니다. 메인 화면에서 더 알아보기 자료를 확인해보세요!"
                add_message("assistant", completion_msg)
                
                # 대화 종료 및 리소스 섹션 노출 플래그 설정 (모범답안 표시 후)
                st.session_state["conversation_completed"] = True
                st.session_state["show_resources"] = True
                st.rerun()
            else:
                # 80점 미만이면 일반 피드백을 대화 기록에 추가 (별 모양 포함)
                stars = score_to_stars(st.session_state.get("score", 0))
                add_message("assistant", f"**현재 점수: {stars}**\n\n{streamed_text}")
            
        except (ValueError, TypeError) as e:
            st.error(f"처리 중 오류가 발생했습니다: {e}")


    # 초기 질문 표시 (제출 전에만)
    elif len(st.session_state["messages_application"]) == 0:
        # Display the question directly
        messages.chat_message("assistant", avatar=SIDEBAR_AI_AVATAR).write("마지막으로, 배운 내용을 새로운 상황에 적용해봅시다.")
        
        # Add the question to history
        add_message("assistant", "마지막으로, 배운 내용을 새로운 상황에 적용해봅시다.")

    # 사이드바 채팅 입력창 (대화가 시작되었고 아직 완료되지 않은 경우)
    if (len(st.session_state["messages_application"]) > 0 and 
        not st.session_state.get("conversation_completed", False)):
        
        if user_input := st.chat_input("AI 선생님과 대화를 계속하세요...", key="sidebar_chat_input"):
            # 사용자 메시지 추가
            add_message("user", user_input)
            
            # AI 응답 생성
            with st.spinner("AI가 답변을 생성하고 있습니다..."):
                response_stream = chain(user_input, False)
                
                streamed_text = ""
                for chunk in response_stream:
                    if hasattr(chunk, 'content'):
                        streamed_text += chunk.content
            
            # 점수 확인 및 완료 처리
            try:
                if st.session_state.get("score", 0) >= 80:
                    st.balloons()
                    
                    # 완료 메시지만 대화 기록에 추가 (별 5개 포함)
                    completion_message = f"""**현재 점수: ⭐⭐⭐⭐⭐**

축하합니다! 충분히 잘 이해하셨네요. 모범 답안은 다음과 같습니다.

[**{applyingModeledAnswer}**]"""
                    
                    if len(st.session_state.get('missing_contents', '')) > 0:
                        missing_text = ''.join(st.session_state['missing_contents']).strip()
                        if missing_text:
                            completion_message += f"\n\n지금도 충분히 좋은 답변이지만, [{missing_text}] 를 포함하여 작성했다면 더 완벽한 답이 작성되었겠네요."
                    
                    completion_message += "\n\n오늘 수업은 여기까지입니다. 메인 화면에서 더 알아보기 자료를 확인해보세요!"
                    
                    add_message("assistant", completion_message)
                    
                    # 대화 종료 및 리소스 섹션 노출 플래그 설정 (모범답안 추가 후)
                    st.session_state["conversation_completed"] = True
                    st.session_state["show_resources"] = True
                else:
                    # 80점 미만이면 일반 피드백을 대화 기록에 추가 (별 모양 포함)
                    stars = score_to_stars(st.session_state.get("score", 0))
                    add_message("assistant", f"**현재 점수: {stars}**\n\n{streamed_text}")
                    
            except (ValueError, TypeError) as e:
                st.error(f"처리 중 오류가 발생했습니다: {e}")
            
            # 화면 새로고침으로 새 메시지 표시
            st.rerun()

# Create columns with specific ratios
col1, col2, col3 = st.columns([5, 2, 2])

# # Place the button in the last column
# with col1:
#     if st.button(
#         label="이전단계로",
#         icon="⏪",
#         help="돌아보기로 이동하기",
#         type="primary"
#     ):
#         st.switch_page("pages_group/04_돌아보기.py")
