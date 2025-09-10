import re
import os
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

DEFAULT_OPERATION = "예비실험실"
INQUIRY_ASSISTANT_OPENAI_MODEL = "gpt-4o-mini"

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
- ⭐ **[내 실험실]에서는 내가 제출한 답을 시뮬레이션 해 볼 수 있어요** ⭐
"""
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
                width: 600px;
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
    user_drawing = st.session_state.get("predict_user_drawing", None)
    user_reason = st.session_state.get("predict_user_reason", "이전 답안이 없습니다.")
    
    # Convert numpy array to base64 image if it exists
    image_src = PROBLEM_IMAGE_PATH
    if user_drawing is not None:
        import base64
        from PIL import Image
        import io
        
        # Convert numpy array to PIL Image
        img = Image.fromarray(user_drawing.astype('uint8'))
        
        # Convert PIL Image to base64
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        image_src = f"data:src/image/png;base64,{img_str}"
    
    # Create tooltip content with styled button
    if user_drawing is not None and user_reason is not None:
    
        tooltip_html = f"""
            <div class="button-container">
            <div class="tooltip-wrapper">
                <button class="custom-button">
                        내가 제출한 답 보기
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
                    내가 제출한 답 보기
            </button>
            <div class="tooltip-content">
                <div class="answer-text">아직 제출한 답안이 없습니다! '생각하기'에서 답안을 제출해주세요:)</div>
            </div>"""
    st.markdown(tooltip_html, unsafe_allow_html=True)

with st.expander(
    label="문제 보기 🔍",
    expanded=True
    ):
    main_tab1 = st.container(border=True)
    main_tab1.write("""무중력 상태의 우주 공간에 새로운 행성을 찾아 다니는 인공 위성이 있습니다. \n
드디어! 새로운 행성을 발견한 인공 위성은 행성의 원형 궤도를 따라 일정한 속력으로 **등속 원운동**을 하기 위해 추진력의 방향을 조정 하려고 합니다. \n
**인공 위성에 적용시켜야 하는 (1) 힘을 아래 캔버스에 원형궤도와 화살표로 나타내고 (2) 그렇게 생각한 이유를 그 아래에  적어봅시다. (그림은 오른쪽에 제시되어 있는 예시의 형태를 참고하여 그리기)**
""")
    with main_tab1:
        _, col2, col3, _ = st.columns(4, vertical_alignment='center')
        col2.image(
            image=MOON_IMAGE_PATH,
        )
        col3.image(
            image=PROBLEM_IMAGE_PATH,
            caption="그림 작성 예시",
            width=200
        )


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

    st.subheader("물리 시뮬레이션 실험실")

    operation= "예비실험실"
    # CSS 스타일 적용
    st.markdown("""
        <style>
        /* iframe 컨테이너 스타일링 */
        .iframe-container {
            width: 950px;
            height: 600px;
            overflow: hidden;
            position: relative;
        }
        
        /* iframe 자체 스타일링 */
        .iframe-container iframe {
            width: 950px;  /* 스크롤바 여유 공간 */
            height: 800px;
            border: none;
            position: absolute;
            top: -250px;  /* 상단 여백 조절 */
            left: 0;
            margin: 0;
            padding: 0;
        }
        </style>
    """, unsafe_allow_html=True)
    # 로컬 HTML 파일 임베드
    try:
        with open('circular.html', 'r', encoding='utf-8') as f:
            circular_html_content = f.read()
        components.html(circular_html_content, height=520, width=950, scrolling=False)
    except Exception as e:
        st.error(f"로컬 시뮬레이션을 불러오는 중 오류가 발생했습니다: {e}")


#####################################
########### Sibebar Logic ###########
#####################################

# 사이드바 시스템 체인 생성
def generate_chain(model_name=INQUIRY_ASSISTANT_OPENAI_MODEL):
    # 현재 선택된 operation 값 가져오기
    prompt = ChatPromptTemplate.from_messages([
        ("system", 
         """당신은 친근하고 대화형 학습을 돕는 **물리 튜터**입니다.  
    **목표:** 학생이 '등속 원운동'에 대한 시뮬레이션에서 변수의 조작에 따른 물체의 운동 변화를 관찰하고, 이를 통해 자신의 추론을 검증해볼 수 있도록 지원하세요.  
    **중요:**  
    1. 절대로 '등속 원운동'에서 힘의 방향이나 크기에 대한 결론을 직접 알려주지 마세요.
       - 학생이 시뮬레이션을 통해 스스로 결과를 관찰하고 해석하도록 도와주세요.
       - 학생이 관찰을 서술하는 과정에서 편견 없이 관찰한 대로 기록하도록 유도하세요.
    2. 항상 **존댓말**로 대화하세요. 친절하고 격려하는 태도를 유지하며 학생이 부담 없이 실험과 기록을 진행하도록 돕습니다.  
    3. **답변 길이 제약:** 각 응답은 **2문장**을 넘지 않도록 간결하고 명확하게 작성하세요.

    **설명 전략:**
    1. 현재 선택되어 있는 {current_operation} 값에 따라 각각 다르게 안내하세요.
        if operation == "예비실험실": 힘과 운동 방향의 각도를 조정하면서 원운동의 조건을 탐구해보도록 안내합니다.
        elif operation == "PhET": 행성의 위치나 크기를 조작해보면서, 어떨 때 행성이 원운동이 일어날 수 있을지 조작해보도록 안내합니다.
        elif operation == "내 실험실": 시뮬레이션 위에 있는 입력창에 내가 생각하는 힘의 방향이나 그 외 다양한 변수를 수정해보도록 안내합니다.

    **핵심 개념 질문 전략:**  
    1. 현재 선택되어 있는 {current_operation} 값에 따라 각각 다르게 질문하여 학생의 생각을 유도하세요.
        if operation == "예비실험실": 힘의 방향과 물체의 운동 궤도 사이의 관계를 탐구해보도록 유도합니다.
        elif operation == "PhET": 행성의 위치나 크기를 조작해보면서, 중력이 무슨 역할을 하는지 탐구해보도록 유도합니다.
        elif operation == "내 실험실": 
            시뮬레이션 위에 있는 입력창에 어떻게 시뮬레이션을 수정하고 싶은지 작성할 수 있도록 예시와 같은 방법으로 학생의 생각을 유도합니다.
            예시:
                "원운동이 계속되려면 힘이 어떤 방향이어야 할 것 같나요?" 
                "'문제'에서 답한 내용을 반영한 시뮬레이션 보기 버튼을 눌러 확인해보세요."
                "시뮬레이션에 반영되어야 한다고 생각하는 내용을 시뮬레이션 위에 있는 입력창에 입력해주세요."
    """
        ),
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

    operation = "예비실험실"

    # 추천 질문 사용 여부 토글 추가
    toggle_recommended_questions = st.toggle("**💡추천 질문** 사용하기", value=False)
    st.session_state["toggle_recommended_questions"] = toggle_recommended_questions

    st.write("**AI 친구** 에게 물어보기")
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
                    "current_operation": DEFAULT_OPERATION
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
