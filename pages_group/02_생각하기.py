import os
import io
import streamlit as st
from PIL import Image
from datetime import datetime

from streamlit_drawable_canvas import st_canvas

from langchain_core.messages.chat import ChatMessage
from langchain_openai import ChatOpenAI
from langchain_teddynote import logging
from langchain_teddynote.models import MultiModal

from modules.keywords import create_keyword

# API KEY 정보로드
# config = settings.load_config()
# if "api_key" in config:
#     st.session_state.api_key = config["api_key"]
#     st.write(f'사용자 입력 API키 : {st.session_state.api_key[-5:]}')
# else : 
#     st.session_state.api_key = st.secrets["openai_api_key"]
#     st.write(f'API키 : {st.secrets["openai_api_key"][-5:]}')

st.session_state.api_key = st.secrets["openai_api_key"]

os.environ["LANGCHAIN_TRACING_V2"] = st.secrets["LANGCHAIN_TRACING_V2"]
os.environ["LANGCHAIN_API_KEY"] = st.secrets["LANGCHAIN_API_KEY"]
os.environ["LANGCHAIN_ENDPOINT"] = st.secrets["LANGCHAIN_ENDPOINT"]
os.environ["LANGCHAIN_PROJECT"] = st.secrets["LANGCHAIN_PROJECT"]

# Initialize session state for the button
if 'button_pressed' not in st.session_state:
    st.session_state.button_pressed = False

# Function to handle button press
def handle_button_click():
    st.session_state.button_pressed = True

# 캐시 디렉토리 생성
if not os.path.exists(".cache"):
    os.mkdir(".cache")

# 파일 업로드 전용 폴더
if not os.path.exists(".cache/files"):
    os.mkdir(".cache/files")

if not os.path.exists(".cache/embeddings"):
    os.mkdir(".cache/embeddings")

st.title("생각하기 🤔")
st.info("- 다음 문제 상황의 정답을 예상해보고, 그 예상의 이유를 적어봅시다. \n - 하단의 캔버스에 그림을 그려보고, 그렇게 생각한 이유를 생각해보세요.")
# 처음 1번만 실행하기 위한 코드
if "messages_predict" not in st.session_state:
    # 대화기록을 저장하기 위한 용도로 생성한다.
    st.session_state["messages_predict"] = []

if "submit_button_disabled" not in st.session_state:
    st.session_state["submit_button_disabled"] = True


# Function to convert PNG to BytesIO
def png_to_bytesio(file_path):
    # Open the PNG image
    with Image.open(file_path) as img:
        # Create a BytesIO object
        byte_io = io.BytesIO()
        # Save the image into the BytesIO object as PNG
        img.save(byte_io, format='PNG')
        # Reset the file pointer to the beginning
        byte_io.seek(0)
        return byte_io


# 이미지을 캐시 저장(시간이 오래 걸리는 작업을 처리할 예정)
@st.cache_resource(show_spinner="업로드한 이미지를 처리 중입니다...")
def process_imagefile(file_path):
    # 업로드한 파일을 캐시 디렉토리에 저장합니다.
    file_content = png_to_bytesio(file_path).getvalue()
    # file_content = file.read()
    file_name = file_path.split("/")[-1].split(".")[0]
    # file_path = f"./.cache/files/{file.name}"
    file_path = f"./.cache/files/{file_name}"


    with open(file_path, "wb") as f:
        f.write(file_content)

    return file_path


# 체인 생성
def generate_answer(image_filepath, system_prompt, user_prompt, model_name="gpt-4o"):
    # 객체 생성
    llm = ChatOpenAI(
        temperature=0,
        model_name=model_name,
        openai_api_key = st.session_state.api_key
    )

    # 멀티모달 객체 생성
    multimodal = MultiModal(llm, system_prompt=system_prompt, user_prompt=user_prompt)

    # 이미지 파일로 부터 질의(스트림 방식)
    answer = multimodal.stream(image_filepath)
    return answer


def save_draw_image(numpy_array):
    image = Image.fromarray(numpy_array)
    current_time = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    file_name = f"p-drawing-{current_time}"
    image.save(f"draw_images/{file_name}.png", format="PNG")
    # return st.info("이미지 저장됨")

def save_draw_explanation(text):
    st.session_state["2stage_explanation"] = text


def enalble_submit_button():
    st.session_state["submit_button_disabled"] = False

def disalble_submit_button():
    st.session_state["submit_button_disabled"] = True


problem_image = "images/problem_1.png"

with st.expander(
    label="문제 보기 🔍",
    expanded=True
    ):
    main_tab1 = st.container(border=True)
    main_tab1.image(problem_image)


st.text("문제의 답을 예상해보세요.")
st.text("(아래 캔버스에 생각한 내용을 그려보세요🎨)")

canvas_result = st_canvas(
    fill_color="rgba(255, 165, 0, 0.3)",  # Fixed fill color with some opacity
    stroke_width=3,
    stroke_color="#000000",
    background_color="#EEEEEE",
    background_image=None,
    update_streamlit=True,
    height=400,
    width=700,
    drawing_mode="freedraw",
    point_display_radius=0,
    key="canvas_intermediate_answer",
)

reason = st.text_area(
    label="예상의 이유를 자세히 적어보세요.",
    placeholder="- 화살표(힘)의 방향이 어디로 향해야 할지\n- 왜 화살표(힘)의 방향이 그래야 하는지",
    height=200,
    on_change=enalble_submit_button
)

if not reason:
    disalble_submit_button()

submit_button = st.button(
    label="제출하기",
    type="primary",
    use_container_width=True,
    on_click=save_draw_image,
    args=[canvas_result.image_data],
    disabled=st.session_state["submit_button_disabled"]
)

if submit_button:
    st.session_state["predict_user_drawing"] = canvas_result.image_data
    st.session_state["predict_user_reason"] = reason
    st.success("제출 완료!")
    st.info("정답은 '돌아보기' 단계에서 확인할 수 있습니다! 다음 단계로 넘어가세요:)")

# Create columns with specific ratios
col1, col2, col3 = st.columns([5, 2, 2])

# Place the button in the last column
with col1:
    if st.button(
        label="이전단계로",
        icon="⏪",
        help="들어가기로 이동하기",
        type="primary"
    ):
        st.switch_page("pages_group/01_들어가기.py")

# Place the button in the last column
with col3:
    if st.button(
        label="다음단계로",
        icon="⏩",
        help="실험하기로 이동하기",
        type="primary"
    ):
        st.switch_page("pages_group/03_실험하기.py")

# 사이드바 생성
with st.sidebar:

    # 모델 선택 메뉴
    selected_model = "gpt-4o" # st.selectbox("LLM 선택", ["gpt-4o", "gpt-4o-mini"], index=0)

    # 시스템 프롬프트 추가
    system_prompt = """당신은 친근하고 대화형 학습을 돕는 **물리 튜터**입니다.  
    **목표:** 학생이 '등속 원운동'에서 어떤 방향으로 힘이 작용해야 물체가 원 궤도를 따라 운동할 수 있는지 스스로 탐구하도록 돕습니다.  
    **중요:**
    1. 절대로 "등속 원운동에서 작용해야 하는 힘의 방향"에 대한 답을 직접 알려주지 마세요.  
    - 답을 암시하거나 유추하게 하는 표현도 사용하지 마세요.  
    - 학생이 스스로 추론하고 탐구할 수 있도록 도와주세요.  
    - 직접적인 답변은 POE 학습 모형의 취지에 어긋나며, 학습 목표를 방해합니다.  
    2. 항상 **존댓말**로 대화하세요. 반말과 존댓말을 혼용하지 말고, 학생에게 일관성 있는 존댓말로 말하며 친절한 태도를 유지하세요.  
    3. **답변 길이 제약:** 학생과의 대화에서 각 응답은 2문단을 넘지 않도록 간결하게 답변하세요.

    **설명 전략:**
    1. 문제 상황(무중력 상태의 우주 공간에서 원 궤도를 따라 움직이는 우주선)을 학생이 쉽게 이해할 수 있도록 설명하세요.  
    2. 학생에게 힘의 방향과 크기에 대해 상상하고 예측하게 한 뒤, 그 이유를 글로 쓰도록 유도하세요.  
    3. 학생의 기존 개념(직선 운동, 등속 운동 등)을 바탕으로 질문을 통해 사고를 확장하세요.

    **대화 스타일:**  
    - 학생의 호기심을 자극하는 열린 질문을 활용하세요.  
    - 학생의 답변을 격려하며, 추가 질문으로 사고를 깊게 만들어 주세요.  
    - 학생이 실생활에서 경험한 유사 사례를 떠올리도록 격려하세요.  

    **대화 시작 제안:**  
    - "우주선이 원 궤도를 따라 일정한 속도로 움직이려면 어떤 힘이 필요할까요?"  
    - "만약 힘이 없다면 우주선은 어떻게 움직일 것 같나요?"  

    **핵심 질문 유도:**  
    - "우주선이 직선으로 나아가려는 경향이 있다면, 그걸 막으려면 어떤 방향의 힘이 필요할까요?"  
    - "등속 원운동을 유지하려면 속도 방향이 계속 바뀌어야 한다는 것을 어떻게 설명할 수 있을까요?"  

    **중요 개념을 유도하는 과정:**  
    - 학생이 자신만의 말로 논리적 추론을 통해 힘의 방향을 도출하도록 유도하세요.  
    - 원운동에서 속도의 방향이 계속 바뀌며 가속도가 발생한다는 점을 강조하되, 학생의 말로 이를 정리하게 하세요.  
    - 예시를 통해 추론을 돕되, 정답이나 암시를 제공하지 마세요.  

    **금지된 대화 예시:**  
    - "속도의 방향을 바꾸기 위해서는 원의 중심 쪽으로 힘이 작용해야 합니다."  
    - "중심 방향으로 힘이 작용해야 한다고 생각할 수 있을까요?"  

    **대화 마무리:**  
    학생이 자신의 말로 등속 원운동에서 힘의 방향과 필요성을 정리하도록 유도하세요.  
    - 예: "그럼 지금까지 생각하신 내용을 정리해보시면 좋겠습니다. 우주선이 원 궤도를 따라 움직이려면 힘이 어떤 방향으로 작용해야 한다고 생각하시나요? 왜 그렇게 생각하셨는지도 같이 말씀해 주시겠어요?"""


    st.text("AI튜터와 대화하기")
    messages = st.container(height=400)


    # 이전 대화를 출력
    def print_messages():
        for chat_message in st.session_state["messages_predict"]:
            messages.chat_message(chat_message.role).write(chat_message.content)


    # 새로운 메시지를 추가
    def add_message(role, message):
        st.session_state["messages_predict"].append(ChatMessage(role=role, content=message))

    # 이전 대화 기록 출력
    print_messages()

    # # 초기화 버튼이 눌리면...
    # if clear_btn:
    #     st.session_state["messages"] = []

    st.text("추천질문")
    col1, col2 = st.columns(2)
    placeholder1 = col1.empty()
    placeholder2 = col2.empty()

    #TODO 키워드 질문 처리
    kw_1, kw_2 = create_keyword(st.session_state["messages_predict"])
    kw_button_1 = placeholder1.button(label=kw_1, use_container_width=True)
    kw_button_2 = placeholder2.button(label=kw_2, use_container_width=True)

    # 사용자의 입력
    user_input = st.chat_input("🤖 AI튜터에게 궁금한 내용을 물어보세요!")


    if kw_button_1:
        user_input = kw_1
        # 이미지 파일을 처리
        image_filepath = process_imagefile(problem_image)
        # 답변 요청
        response = generate_answer(
            image_filepath, system_prompt, user_input, selected_model
        )

        # 사용자의 입력
        messages.chat_message("user").write(user_input)

        with messages.chat_message("assistant"):
            # 빈 공간(컨테이너)을 만들어서, 여기에 토큰을 스트리밍 출력한다.
            container = st.empty()

            ai_answer = ""
            for token in response:
                ai_answer += token.content
                container.markdown(ai_answer)

        # 대화기록을 저장한다.
        add_message("user", user_input)
        add_message("assistant", ai_answer)


        kw_1, kw_2 = create_keyword(st.session_state["messages_predict"])
        placeholder1.button(label=kw_1, use_container_width=True)
        placeholder2.button(label=kw_2, use_container_width=True)


    if kw_button_2:
        user_input = kw_2

        # 이미지 파일을 처리
        image_filepath = process_imagefile("images/problem_1.png")
        # 답변 요청
        response = generate_answer(
            image_filepath, system_prompt, user_input, selected_model
        )

        # 사용자의 입력
        messages.chat_message("user").write(user_input)

        with messages.chat_message("assistant"):
            # 빈 공간(컨테이너)을 만들어서, 여기에 토큰을 스트리밍 출력한다.
            container = st.empty()

            ai_answer = ""
            for token in response:
                ai_answer += token.content
                container.markdown(ai_answer)

        # 대화기록을 저장한다.
        add_message("user", user_input)
        add_message("assistant", ai_answer)

        kw_1, kw_2 = create_keyword(st.session_state["messages_predict"])
        placeholder1.button(label=kw_1, use_container_width=True)
        placeholder2.button(label=kw_2, use_container_width=True)



    # 만약에 사용자 입력이 들어오면...
    if user_input and not kw_button_1 and not kw_button_2:
        # 이미지 파일을 처리
        image_filepath = process_imagefile("images/problem_1.png")
        # 답변 요청
        response = generate_answer(
            image_filepath, system_prompt, user_input, selected_model
        )

        # 사용자의 입력
        messages.chat_message("user").write(user_input)

        with messages.chat_message("assistant"):
            # 빈 공간(컨테이너)을 만들어서, 여기에 토큰을 스트리밍 출력한다.
            container = st.empty()

            ai_answer = ""
            for token in response:
                ai_answer += token.content
                container.markdown(ai_answer)

        # 대화기록을 저장한다.
        add_message("user", user_input)
        add_message("assistant", ai_answer)

