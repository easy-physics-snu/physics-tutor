import re
import os
import io
import time
import sys
import base64
import streamlit as st
import streamlit.components.v1 as components
from typing import List
from PIL import Image

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, BaseMessage
from langchain_core.globals import set_verbose
from langchain_core.messages.chat import ChatMessage
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory

from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
# from langchain_ollama import ChatOllama
# from langchain_anthropic import ChatAnthropic

from modules.keywords import create_keyword
import simulation.simulation as simulation

from modules.prompts import PEER_AI_03EXPERIMENT_PROMPT

set_verbose(False)

st.session_state.api_key = st.secrets["openai_api_key"]

# os.environ["LANGCHAIN_TRACING_V2"] = st.secrets["LANGCHAIN_TRACING_V2"]
# os.environ["LANGCHAIN_API_KEY"] = st.secrets["LANGCHAIN_API_KEY"]
# os.environ["LANGCHAIN_ENDPOINT"] = st.secrets["LANGCHAIN_ENDPOINT"]
# os.environ["LANGCHAIN_PROJECT"] = st.secrets["LANGCHAIN_PROJECT"]

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


######################################
########### Mainpage Logic ###########
######################################

st.title("실험하기 🧪")

# Create a container for the info message and tooltip
info_container = st.container()
left_col, right_col = info_container.columns([4, 1])

with left_col:
    message = """
- 앞에서 제출한 답을 떠올리며 시뮬레이션을 관찰하고 조작해보세요.
- 시뮬레이션에 대해서 궁금한건 🤓**AI 친구**에게 물어보세요.
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
    expanded=True
    ):
    main_tab1 = st.container(border=True)
    main_tab1.write("""우주 공간에 새로운 행성을 찾아 다니는 우주선이 있습니다.\n
드디어! 새로운 행성을 발견한 우주선은 행성 주변의 원형 궤도에 진입하여 **등속 원운동**하려고 합니다. \n
**이때, 우주선에 작용하는 (1) 알짜힘의 방향을 왼쪽의 캔버스에 화살표로 나타내고 (2) 그렇게 생각한 이유를 그 아래에 적어봅시다.**
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

########### 예비 실험실 ###########
with st.container(border=True):

    st.markdown("<div style='font-size: 1.3rem; font-weight: 600; margin: 0 0 0px 0;'>물리 시뮬레이션 실험실</div>", unsafe_allow_html=True)

    operation= "예비실험실"
    # CSS 스타일 적용 (표시 영역은 크게, 콘텐츠는 내부에서 스케일 다운)
    st.markdown("""
        <style>
        .iframe-wrap {
            width: 1400px;
            height: 500px;
            overflow: hidden;
            position: relative;
            margin: -2000px auto 0px; /* 상단 여백 상쇄 */
        }
        .iframe-wrap iframe {
            position: absolute;
            top: 0;
            left:0;
      
            border: none;
            display: block;
        }
        </style>
    """, unsafe_allow_html=True)
    # 로컬 HTML 파일 임베드
    try:
        with open('circular.html', 'r', encoding='utf-8') as f:
            circular_html_content = f.read()
        # 임베드되는 HTML 본문을 축소하여 넓은 표시 영역에 맞춥니다.
        scale = 0.7  # 필요시 0.7~0.9로 조정
        # 불필요한 상단 여백 제거 (#container { margin-top: 40px; })
        circular_html_content = circular_html_content.replace('margin-top: 40px;', 'margin-top: 0px;')
        if '<body' in circular_html_content:
            circular_html_content = circular_html_content.replace(
                '<body>', f'<body style="margin:0;padding:0;transform: scale({scale}); transform-origin: top left;">', 1
            )
        st.markdown('<div class="iframe-wrap">', unsafe_allow_html=True)
        components.html(circular_html_content, height=500, width=1400, scrolling=False)
        st.markdown('</div>', unsafe_allow_html=True)
    except Exception as e:
        st.error(f"로컬 시뮬레이션을 불러오는 중 오류가 발생했습니다: {e}")
    
    # 커스텀 경계 박스 종료
    st.markdown('</div>', unsafe_allow_html=True)

#####################################
########### Sibebar Logic ###########
#####################################

# 사이드바 시스템 체인 생성
def generate_chain(model_name=INQUIRY_ASSISTANT_OPENAI_MODEL):
    # 현재 선택된 operation 값 가져오기
    prompt = ChatPromptTemplate.from_messages([
        ("system", PEER_AI_03EXPERIMENT_PROMPT),
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
    toggle_recommended_questions = st.toggle("**💡추천 질문** 사용하기", value=False)
    st.session_state["toggle_recommended_questions"] = toggle_recommended_questions

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
        messages.chat_message("assistant", avatar=SIDEBAR_AI_AVATAR).write("안녕! 나랑 같이 원운동을 탐구해보자!")
    else:
        pass

    # 이전 대화 기록 출력
    print_messages()

    # 추천 질문 사용 여부에 따라 조건부 표시
    if st.session_state.get("toggle_recommended_questions", True):
        st.text("추천 질문 (클릭 시 다른 질문이 생성됩니다)")
        col1, col2 = st.columns(2)
        placeholder1 = col1.empty()
        placeholder2 = col2.empty()

        # 키워드 질문 처리
        kw_1, kw_2 = create_keyword(st.session_state["tutor_messages"], keyword_section="03_experiment")
        kw_button_1 = placeholder1.button(label=kw_1, use_container_width=True)
        kw_button_2 = placeholder2.button(label=kw_2, use_container_width=True)
    else:
        # 추천 질문을 사용하지 않는 경우 버튼들을 None으로 설정
        kw_button_1 = None
        kw_button_2 = None

    # 사용자의 입력
    user_input = st.chat_input("궁금한 내용을 물어보세요!")

    # 만약에 사용자 입력이 들어오면...
    if user_input and not (kw_button_1 and st.session_state.get("toggle_recommended_questions", False)) and not (kw_button_2 and st.session_state.get("toggle_recommended_questions", False)):
        # 답변 요청
        conv_chain = generate_chain(selected_model)
        # 사용자의 입력
        messages.chat_message("user").write(user_input)

        with messages.chat_message("assistant", avatar=SIDEBAR_AI_AVATAR):
            # 빈 공간(컨테이너)을 만들어서, 여기에 토큰을 스트리밍 출력한다.
            container = st.empty()
            generator = conv_chain.stream(
                {
                    "input": user_input,
                },
                config={"configurable": {"session_id": "ab12"}}
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

# Place the button in the last column
with col3:
    if st.button(
        label="다음단계로",
        icon="⏩",
        help="돌아보기로 이동하기",
        type="primary"
    ):
        st.switch_page("pages_group/04_돌아보기.py")
