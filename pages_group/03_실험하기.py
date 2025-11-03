import re
import os
import io
import time
import sys
import base64
import uuid
import json
import streamlit as st
import streamlit.components.v1 as components
from typing import List
from PIL import Image

from langchain_openai import ChatOpenAI
from openai import OpenAI as OpenAI_Client
from langchain_core.messages import HumanMessage, BaseMessage, AIMessage
from langchain_core.globals import set_verbose
from langchain_core.messages.chat import ChatMessage
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory

from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
# from langchain_ollama import ChatOllama
# from langchain_anthropic import ChatAnthropic

# from modules.keywords import create_keyword
# import simulation.simulation as simulation

from modules.prompts import PEER_AI_03EXPERIMENT_PROMPT
import dms.Intermediary as Intermediary

set_verbose(False)

st.session_state.api_key = st.secrets["openai_api_key"]

os.environ["LANGCHAIN_TRACING_V2"] = st.secrets["LANGCHAIN_TRACING_V2"]
os.environ["LANGCHAIN_API_KEY"] = st.secrets["LANGCHAIN_API_KEY"]
os.environ["LANGCHAIN_ENDPOINT"] = st.secrets["LANGCHAIN_ENDPOINT"]
os.environ["LANGCHAIN_PROJECT"] = st.secrets["LANGCHAIN_PROJECT"]

if "submit_button_disabled" not in st.session_state:
    st.session_state["submit_button_disabled"] = True

if "tutor_messages" not in st.session_state:
    # 대화기록을 저장하기 위한 용도로 생성한다.
    st.session_state["tutor_messages"] = []

# DEFAULT_OPERATION = "예비실험실"
INQUIRY_ASSISTANT_OPENAI_MODEL = "gpt-4.1"

PROBLEM_IMAGE_PATH = "src/images/satellite_orbit.png"
MOON_IMAGE_PATH = "src/images/satellite_moon.png"

SIDEBAR_AI_AVATAR = "src/images/ai_peer_avatar.png"


if "tutor_messages" not in st.session_state:
    # 대화기록을 저장하기 위한 용도로 생성한다.
    st.session_state["tutor_messages"] = []

# '다음단계로' 버튼 표시 여부를 영구적으로 기록
if "can_proceed_to_next" not in st.session_state:
    st.session_state["can_proceed_to_next"] = False

if "phase3_intermediary" not in st.session_state:
    st.session_state["phase3_intermediary"] = None

if "phase3_act_history" not in st.session_state:
    st.session_state["phase3_act_history"] = []

if "phase3_assess_history" not in st.session_state:
    st.session_state["phase3_assess_history"] = []

# 고유한 세션 ID 생성 (Streamlit 세션별로 고유)
if "chain_session_id" not in st.session_state:
    st.session_state["chain_session_id"] = str(uuid.uuid4())


def enalble_submit_button():
    st.session_state["submit_button_disabled"] = False

def disalble_submit_button():
    st.session_state["submit_button_disabled"] = True

def output_parser(response: str) -> str:
    content = re.search(r'```python\n(.*?)\n```', response, re.DOTALL)

    if content:
        extracted_code = content.group(1)
        print(extracted_code)
        return extracted_code
    else:
        print("No Python code block found.")
        return None

class InMemoryHistory(BaseChatMessageHistory, BaseModel):
    """In memory implementation of chat message history."""

    messages: List[BaseMessage] = Field(default_factory=list)

    def add_messages(self, messages: List[BaseMessage]) -> None:
        """Add a list of messages to the store"""
        self.messages.extend(messages)

    def clear(self) -> None:
        self.messages = []

store = {}

def get_by_session_id(session_id: str) -> BaseChatMessageHistory:
    if session_id not in store:
        store[session_id] = InMemoryHistory()
    return store[session_id]

def sync_history_to_store(session_id: str, tutor_messages: List[ChatMessage]):
    """st.session_state의 tutor_messages를 RunnableWithMessageHistory의 히스토리 저장소에 동기화
    
    RunnableWithMessageHistory는 자동으로 새로운 메시지를 히스토리에 추가하므로,
    기존 히스토리가 tutor_messages와 동기화되지 않은 경우에만 업데이트합니다.
    """
    history = get_by_session_id(session_id)
    existing_messages = history.messages
    existing_count = len(existing_messages)
    tutor_count = len(tutor_messages)
    
    # 히스토리와 tutor_messages가 일치하지 않는 경우 동기화
    # RunnableWithMessageHistory가 자동으로 메시지를 추가하므로,
    # existing_count는 tutor_count보다 작거나 같을 수 있습니다
    if existing_count < tutor_count:
        # 누락된 메시지만 추가
        for msg in tutor_messages[existing_count:]:
            if msg.role == "user":
                history.add_messages([HumanMessage(content=msg.content)])
            elif msg.role == "assistant":
                history.add_messages([AIMessage(content=msg.content)])
    elif existing_count == 0 and tutor_count > 0:
        # 히스토리가 비어있고 tutor_messages가 있는 경우 전체 동기화
        history.clear()
        for msg in tutor_messages:
            if msg.role == "user":
                history.add_messages([HumanMessage(content=msg.content)])
            elif msg.role == "assistant":
                history.add_messages([AIMessage(content=msg.content)])


######################################
########### Mainpage Logic ###########
######################################
st.set_page_config(layout="wide")

st.title("실험하기 🧪")

# Create a container for the info message and tooltip
info_container = st.container()
left_col, right_col = info_container.columns([4, 1])

with left_col:
    message = """
- 앞에서 제출한 답을 떠올리며 시뮬레이션을 관찰하고 조작해보세요.
- 시뮬레이션에 대해서 궁금한건 좌측 사이드바의 🤓**AI 친구**에게 물어보세요.
- 🤓**AI 친구**와의 대화를 바탕으로 시뮬레이션을 조작해보고, 관찰 결과를 바탕으로 궁금한 것을 **🤓AI 친구**에게 다시 물어보세요.
"""
#- ⭐ **[내 실험실]에서는 내가 제출한 답을 시뮬레이션 해 볼 수 있어요** ⭐

    st.info(message)

with right_col:
    # Add custom CSS for tooltip and button
    st.markdown("""
            <style>
            .button-container {
                display: flex;
                flex-direction: column;
                gap: 8px;
            }
            .tooltip-wrapper {
                position: relative;
                display: inline-block;
                cursor: pointer;
            }
            .tooltip-wrapper .tooltip-content {
                visibility: hidden;
                width: 400px;
                background-color: white;
                color: black;
                text-align: left;
                border-radius: 8px;
                padding: 16px;
                position: absolute;
                z-index: 1;
                top: 0;
                right: 100%;
                margin-right: 16px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                opacity: 0;
                transition: opacity 0.3s;
            }
            .tooltip-wrapper:hover .tooltip-content {
                visibility: visible;
                opacity: 1;
            }
            .tooltip-content img {
                width: 100%;
                height: auto;
                border-radius: 4px;
                margin-bottom: 8px;
            }
            .tooltip-content .answer-text {
                font-size: 14px;
                line-height: 1.4;
                margin-top: 8px;
                padding: 8px;
                background-color: #f8f9fa;
                border-radius: 4px;
            }
            .custom-button {
                display: inline-flex;
                align-items: center;
                justify-content: center;
                padding: 0.6rem 1.2rem;
                background-color: rgb(255, 255, 255);
                border: 1px solid rgba(49, 51, 63, 0.2);
                border-radius: 0.5rem;
                color: rgb(49, 51, 63);
                font-size: 14px;
                font-weight: 400;
                line-height: 1.6;
                text-decoration: none;
                transition: border-color 200ms ease 0s, background-color 200ms ease 0s;
                cursor: pointer;
                width: 160px;
                white-space: nowrap;
            }
            .custom-button:hover {
                border-color: rgb(49, 51, 63);
                color: rgb(49, 51, 63);
                background-color: rgb(250, 250, 250);
            }
            .custom-button i {
                margin-left: 0.3rem;
                font-size: 1rem;
            }
            </style>
        """, unsafe_allow_html=True)

    # Get user's previous answer and drawing from session state
    user_drawing = st.session_state.get("predict_saved_image_path", None)
    user_reason = st.session_state.get("predict_user_reason", "이전 답안이 없습니다.")
    
    # Convert saved image path to base64 image if it exists
    image_src = PROBLEM_IMAGE_PATH
    if user_drawing is not None:
        # Load image from saved file path
        img = Image.open(user_drawing)
        
        # Convert PIL Image to base64
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        image_src = f"data:image/png;base64,{img_str}"
    
    # Create tooltip content with styled button
    if user_drawing is not None and user_reason is not None:
    
        tooltip_html = f"""
            <div class="button-container">
            <div class="tooltip-wrapper">
                <button class="custom-button">
                        <생각하기>에서 제출한 답
                </button>
                <div class="tooltip-content">
                    <div class="drawing-explanation" style="font-size: 15px;">캔버스</div>
                    <img src="{image_src}" alt="이전 답안 이미지">
                    <div class="drawing-explanation" style="font-size: 15px;">예상의 이유</div>
                    <div class="answer-text">{user_reason}</div>
            </div>"""
    else:
        tooltip_html = f"""
        <div class="button-container">
        <div class="tooltip-wrapper">
            <button class="custom-button">
                    <생각하기>에서 제출한 답
            </button>
            <div class="tooltip-content">
                <div class="answer-text">아직 제출한 답안이 없습니다! '생각하기 🤔'에서 답안을 제출해주세요:)</div>
            </div>"""
    st.markdown(tooltip_html, unsafe_allow_html=True)

with st.expander(
    label="문제 보기 🔍",
    expanded=False
    ):
    main_tab1 = st.container(border=True)
    main_tab1.write("""우주 공간에 새로운 행성을 찾아 다니는 우주선이 있습니다.\n
드디어! 새로운 행성을 발견한 우주선은 행성 주변의 원형 궤도에 진입하여 **등속 원운동**하려고 합니다. \n
**이때, 우주선에 작용하는 (1) 알짜힘의 방향을 캔버스에 화살표로 나타내고 (2) 그렇게 생각한 이유를 그 아래에 적어봅시다.**
""")
    with main_tab1:
        _, col2, _ = st.columns(3, vertical_alignment='center')
        col2.image(
            image=MOON_IMAGE_PATH,
        )
        # col3.image(
        #     image=PROBLEM_IMAGE_PATH,
        #     caption="그림 작성 예시",
        #     width=200
        # )


# 내 실험실 초기 세션 상태 설정
if 'button_timestamp' not in st.session_state:
    st.session_state.button_timestamp = time.time()
if 'last_input' not in st.session_state:
    st.session_state.last_input = ''

###################################
########### 실험실 Logic ###########
###################################
with st.container(border=True):

    st.markdown("<div style='font-size: 1.3rem; font-weight: 600; margin: 0 0 0px 0;'>물리 시뮬레이션 실험실</div>", unsafe_allow_html=True)

    # 로컬 HTML 파일 임베드
    try:
        with open('simulation/circular-motion-sim_responsive.html', 'r', encoding='utf-8') as f:
            circular_html_content = f.read()
        
        components.html(circular_html_content, height=590, width=870, scrolling=False)

        st.markdown("""
        <style>
        /* components.html이 만드는 iframe을 부모 너비에 맞추기 */
        [data-testid="stIFrame"] > iframe { width: 100% !important; }
        </style>""", unsafe_allow_html=True)
    except Exception as e:
        st.error(f"로컬 시뮬레이션을 불러오는 중 오류가 발생했습니다: {e}")
    
    # 커스텀 경계 박스 종료
    st.markdown('</div>', unsafe_allow_html=True)

#####################################
########### Sibebar Logic ###########
#####################################
def get_phase2_learning_context():
    """Phase2에서 겪은 학습자의 어려움을 요약하여 context 문자열로 반환"""
    phase2_assess_history = st.session_state.get("phase2_assess_history", [])
    
    if not phase2_assess_history:
        return ""
    
    # JSON 문자열들을 파싱
    difficulties_summary = []
    for assess_json in phase2_assess_history:
        try:
            assess_data = json.loads(assess_json)
            justification = assess_data.get("justification", "")
            selection = assess_data.get("selection", "")
            formatted_selection = ", ".join(selection) if isinstance(selection, str) else selection
            
            if justification and selection:
                difficulties_summary.append(f"- 선택 지표: {formatted_selection}\n  근거: {justification}")
        except json.JSONDecodeError:
            continue
    
    if not difficulties_summary:
        return ""
    
    context = f"""
# PHASE2 학습 맥락 정보
학습자가 앞 단계(Phase2: 생각하기)에서 겪은 주요 어려움과 평가 기록:
{chr(10).join(difficulties_summary)}

이 정보를 참고하여, 학습자가 겪었던 어려움을 바탕으로 실험 단계에서 더 적절한 안내와 피드백을 제공하세요.
"""
    return context


# 사이드바 시스템 체인 생성
def generate_chain(model_name=INQUIRY_ASSISTANT_OPENAI_MODEL, system_prompt=None):

    if system_prompt is None:
        full_system_prompt = PEER_AI_03EXPERIMENT_PROMPT
    else:
        full_system_prompt = system_prompt

    # 현재 선택된 operation 값 가져오기
    prompt = ChatPromptTemplate.from_messages([
        ("system", full_system_prompt),
        MessagesPlaceholder(variable_name="history"),
        ("human", "{input}")
    ])

    # 객체 생성
    llm = ChatOpenAI(
        temperature=0,
        model_name=model_name,
        openai_api_key = st.session_state.api_key
    )

    # llm_acer_server = ChatOllama(
    #     # model="exaone3.5:7.8b-instruct-q8_0", temperature=0
    #     model="codellama:7b-instruct-q6_K", temperature=0
    # )

    chain = prompt | llm
    chain_with_history = RunnableWithMessageHistory(
        chain,
        get_by_session_id,
        input_messages_key="input",
        history_messages_key="history",
    )

    return chain_with_history


with st.sidebar:
    # 모델 선택 메뉴
    selected_model = INQUIRY_ASSISTANT_OPENAI_MODEL

    # options = ["예비실험실", "내 실험실"]
    # operation = st.pills("(어떤 시뮬레이션을 하고 있는지 선택해주세요)", options, selection_mode="single")
    # if operation is None:
    #     operation = DEFAULT_OPERATION

    # operation = "예비실험실"

    # 추천 질문 사용 여부 토글 추가
    # toggle_recommended_questions = st.toggle("**💡추천 질문** 사용하기", value=False)
    # st.session_state["toggle_recommended_questions"] = toggle_recommended_questions

    st.write("**AI 친구**에게 물어보기")
    messages = st.container(height=400)

    # 이전 대화를 출력
    def print_messages():
        for chat_message in st.session_state["tutor_messages"]:
            if chat_message.role == "assistant":
                messages.chat_message(chat_message.role, avatar=SIDEBAR_AI_AVATAR).write(chat_message.content)
            else:
                messages.chat_message(chat_message.role).write(chat_message.content)

    # 새로운 메시지를 추가
    def add_message(role, message):
        st.session_state["tutor_messages"].append(ChatMessage(role=role, content=message))

    # 초기 대화 기록 추가
    if len(st.session_state["tutor_messages"]) == 0:
        messages.chat_message("assistant", avatar=SIDEBAR_AI_AVATAR).write("시뮬레이션에 대해서 궁금한게 있으면 뭐든지 물어봐!")
    else:
        pass

    # 이전 대화 기록 출력
    print_messages()

    # 추천 질문 사용 여부에 따라 조건부 표시
    # if st.session_state.get("toggle_recommended_questions", True):
    #     st.text("추천 질문 (클릭 시 다른 질문이 생성됩니다)")
    #     col1, col2 = st.columns(2)
    #     placeholder1 = col1.empty()
    #     placeholder2 = col2.empty()

    #     # 키워드 질문 처리
    #     kw_1, kw_2 = create_keyword(st.session_state["tutor_messages"], keyword_section="03_experiment")
    #     kw_button_1 = placeholder1.button(label=kw_1, use_container_width=True)
    #     kw_button_2 = placeholder2.button(label=kw_2, use_container_width=True)
    # else:
    #     # 추천 질문을 사용하지 않는 경우 버튼들을 None으로 설정
    #     kw_button_1 = None
    #     kw_button_2 = None

    # 사용자의 입력
    user_input = st.chat_input("궁금한 내용을 물어보세요!")

    # 만약에 사용자 입력이 들어오면...
    if user_input: # and not (kw_button_1 and st.session_state.get("toggle_recommended_questions", False)) and not (kw_button_2 and st.session_state.get("toggle_recommended_questions", False)):

        with st.spinner("AI가 답변을 생성하고 있습니다..."):

            # 사용자의 입력
            messages.chat_message("user").write(user_input)

            if st.session_state["phase3_intermediary"] is None:
                intermediary = Intermediary.Intermediary(
                    client=OpenAI_Client(api_key=st.session_state.api_key),
                    model=INQUIRY_ASSISTANT_OPENAI_MODEL,
                    phase=3,
                    act_history=st.session_state.get("phase3_act_history", []),
                    assessment_history=st.session_state.get("phase3_assess_history", [])
                )
                st.session_state["phase3_intermediary"] = intermediary
            else:
                intermediary = st.session_state["phase3_intermediary"]
            
            prompt, acts, assessment = intermediary.get_prompt(
                conversation_history=st.session_state["tutor_messages"],
                student_prompt=user_input
            )

            st.session_state["phase3_act_history"] = intermediary.get_act_history()
            st.session_state["phase3_assess_history"] = intermediary.get_assess_history()

            # 히스토리를 RunnableWithMessageHistory의 저장소에 동기화
            # 현재 입력을 포함한 모든 이전 히스토리를 동기화
            # (RunnableWithMessageHistory는 자동으로 새로운 AI 응답을 추가함)
            sync_history_to_store(st.session_state["chain_session_id"], st.session_state["tutor_messages"])

            # Phase2 학습 맥락 추가
            phase2_context = get_phase2_learning_context()

            print(phase2_context)
            
            # 시스템 프롬프트에 Phase2 맥락 추가
            full_system_prompt = PEER_AI_03EXPERIMENT_PROMPT + phase2_context

            # 답변 요청
            conv_chain = generate_chain(selected_model, full_system_prompt)

            with messages.chat_message("assistant", avatar=SIDEBAR_AI_AVATAR):
                # 빈 공간(컨테이너)을 만들어서, 여기에 토큰을 스트리밍 출력한다.
                container = st.empty()
                generator = conv_chain.stream(
                    {
                        "input": prompt[-1]['content'] + "---" + "\n\n" + "**<사용자의 입력>**:\n" + user_input,
                    },
                    config={"configurable": {"session_id": st.session_state["chain_session_id"]}}
                )
                ai_answer = ""
                for token in generator:
                    ai_answer += token.content
                    container.markdown(ai_answer)

            # 대화기록을 저장한다.
            add_message("user", user_input)
            add_message("assistant", ai_answer)


# Create columns with specific ratios
col1, col2, col3 = st.columns([5, 2, 2])
# Place the button in the last column
with col1:
    if st.button(
        label="이전단계로",
        icon="⏪",
        help="생각하기로 이동하기",
        type="primary"
    ):
        st.switch_page("pages_group/02_생각하기.py")

# 사이드바 튜터 대화 턴(사용자 메시지 수) 확인
user_turns = sum(1 for m in st.session_state.get("tutor_messages", []) if getattr(m, "role", None) == "user")

# 3턴 미만일 때 안내 메시지
if user_turns < 3:
    st.info("좌측 사이드바의 **🤓AI 친구**와 최소 3턴 이상 대화하면 '다음단계로' 버튼이 활성화됩니다.")
    st.warning(f"현재 대화 {user_turns}턴 진행됨. 계속 질문해보세요!")

# 조건을 만족하면 영구적으로 표시 플래그 설정
if user_turns >= 3:
    st.session_state["can_proceed_to_next"] = True

# 플래그가 True면 버튼 표시
if st.session_state.get("can_proceed_to_next", False):
    # Place the button in the last column
    with col3:
        if st.button(
            label="다음단계로",
            icon="⏩",
            help="돌아보기로 이동하기",
            type="primary"
        ):
            st.switch_page("pages_group/04_돌아보기.py")
