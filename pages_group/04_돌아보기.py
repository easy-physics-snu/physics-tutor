import streamlit as st
import io
import os
import base64
import asyncio
import json
import uuid

from PIL import Image
from datetime import datetime
from enum import Enum
# from streamlit_drawable_canvas import st_canvas

from langchain_core.messages.chat import ChatMessage
from langchain_openai import ChatOpenAI
from openai import OpenAI as OpenAI_Client

from modules.multimodal import MultiModalwithHistory
from modules.prompts import TUTOR_AI_04REFLECT_PROMPT
from modules.utils import overlay_png_and_np_from_image, process_png_to_bytesio, create_async_canvas_with_guaranteed_image, ensure_canvas_image_loaded
from modules.dynamo import initialize_session

import dms.Intermediary as Intermediary

# 로그인 상태 확인
if "logged_in" not in st.session_state or not st.session_state.logged_in:
    st.error("로그인이 필요합니다. 메인 페이지에서 로그인해주세요.")
    if st.button("메인 페이지로 이동"):
        st.switch_page("pages_group/00_Main.py")
    st.stop()

st.session_state.api_key = st.secrets["openai_api_key"]

os.environ["LANGCHAIN_TRACING_V2"] = st.secrets["LANGCHAIN_TRACING_V2"]
os.environ["LANGCHAIN_API_KEY"] = st.secrets["LANGCHAIN_API_KEY"]
os.environ["LANGCHAIN_ENDPOINT"] = st.secrets["LANGCHAIN_ENDPOINT"]
os.environ["LANGCHAIN_PROJECT"] = st.secrets["LANGCHAIN_PROJECT"]

st.session_state["init_user_input"] = False

# 캐시 디렉토리 생성
if not os.path.exists(".cache"):
    os.mkdir(".cache")

# 파일 업로드 전용 폴더
if not os.path.exists(".cache/files"):
    os.mkdir(".cache/files")

if not os.path.exists(".cache/embeddings"):
    os.mkdir(".cache/embeddings")

#TODO 문제 이미지가 있어야 AI튜터가 학습자 제출 답안에 대한 의미 있는 피드백을 제공 가능한지 확인
PROBLEM_IMAGE_PATH = "src/images/satellite_orbit.png"
MOON_IMAGE_PATH = "src/images/satellite_moon.png"
CANVAS_IMAGE_PATH = "src/images/satellite_orbit_canvas.png"

REVIEW_IMAGE_PATH = "src/images/new_review_1.png"

INQUIRY_ASSISTANT_OPENAI_MODEL = "gpt-4.1" 

SIDEBAR_AI_AVATAR = "src/images/ai_tutor_avatar.png"

if "submit_button_disabled" not in st.session_state:
    st.session_state["submit_button_disabled"] = True

# 처음 1번만 실행하기 위한 코드
if "messages_explanation" not in st.session_state:
    # 대화기록을 저장하기 위한 용도로 생성한다.
    st.session_state["messages_explanation"] = []

if "show_answer" not in st.session_state:
    st.session_state["show_answer"] = False

if "explanation_multimodal_chain_with_history" not in st.session_state:
    st.session_state["explanation_multimodal_chain_with_history"] = None

if "phase4_intermediary" not in st.session_state:
    st.session_state["phase4_intermediary"] = None

if "phase4_act_history" not in st.session_state:
    st.session_state["phase4_act_history"] = []

if "phase4_assess_history" not in st.session_state:
    st.session_state["phase4_assess_history"] = []

# 대화 턴 추적을 위한 변수 추가
if "phase4_current_turn" not in st.session_state:
    st.session_state["phase4_current_turn"] = 0

def save_draw_image(numpy_array):
    """
    캔버스 이미지와 사용자 그림을 합성하여 저장합니다.
    CANVAS_IMAGE_PATH가 없어도 기본 이미지를 생성하여 처리합니다.
    """
    try:
        # 기존 이미지 사용
        base_image = Image.open(CANVAS_IMAGE_PATH)
        if base_image.mode != 'RGBA':
            base_image = base_image.convert('RGBA')
        # 캔버스 크기에 맞게 리사이즈
        if base_image.size != (500, 500):
            base_image = base_image.resize((500, 500), Image.Resampling.LANCZOS)
        print(f"캔버스 배경 이미지 로드: {CANVAS_IMAGE_PATH}")
        
        # 사용자 그림과 합성
        image = overlay_png_and_np_from_image(base_image, numpy_array)
        
        # 파일 저장
        current_time = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        file_name = f"e-drawing-{current_time}"
        file_path = f"src/draw_images/{file_name}.png"
        
        # 디렉토리가 존재하는지 확인하고 생성
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        image.save(file_path, format="PNG")
        print(f"이미지 저장 완료: {file_path}")
        return file_path

    except Exception as e:
        st.error(f"이미지 저장 중 오류가 발생했습니다: {str(e)}")
        return None


def enalble_submit_button():
    st.session_state["submit_button_disabled"] = False

def disalble_submit_button():
    st.session_state["submit_button_disabled"] = True


def save_message_to_db(role: str, content: str, content_type: str = "text", llm_model: str = None, turn: int = None):
    """
    메시지를 DynamoDB에 저장
    """
    if not st.session_state.get("phase4_manager"):
        return False
    
    if not st.session_state.get("session_uuid"):
        return False
    
    # turn이 제공되지 않으면 현재 턴 사용
    if turn is None:
        turn = st.session_state.get("phase4_current_turn", 0)
    
    try:
        success = st.session_state["phase4_manager"].save_phase_message(
            session_id=st.session_state["session_uuid"],
            role=role,
            content_type=content_type,
            content=content,
            llm_model=llm_model,
            turn=turn
        )
        return success
    except Exception as e:
        print(f"메시지 저장 실패: {e}")
        return False

#--------------------------------#
#            DynamoDB 설정        #
#--------------------------------#
# Phase 4 페이지 초기화
initialize_session(phase_num=4)

# 세션 생성/조회 (페이지 로드 시)
if st.session_state.get("aws_initialized", False) and st.session_state.get("session_manager"):
    try:
        session_info = st.session_state["session_manager"].get_or_create_session(
            session_uuid=st.session_state.get("session_uuid"),
            user_id=st.session_state.get("user_id", "anonymous")
        )
        if session_info:
            st.session_state["session_created"] = True
    except Exception as e:
        st.warning(f"세션 생성/조회 실패: {e}")
        st.session_state["session_created"] = False


def get_phase2_learning_context():
    """Phase2에서 겪은 학습자의 어려움을 요약하여 context 문자열로 반환"""
    phase2_assess_history = st.session_state.get("phase2_assess_history", [])
    
    if not phase2_assess_history:
        return ""
    
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

이 정보를 참고하여, 학습자가 겪었던 어려움을 바탕으로 돌아보기 단계에서 더 적절한 안내와 피드백을 제공하세요.
"""
    return context

def get_phase3_learning_context():
    """Phase3에서 겪은 학습자의 어려움을 요약하여 context 문자열로 반환"""
    phase3_assess_history = st.session_state.get("phase3_assess_history", [])
    
    if not phase3_assess_history:
        return ""
    
    difficulties_summary = []
    for assess_json in phase3_assess_history:
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
# PHASE3 학습 맥락 정보
학습자가 앞 단계(Phase3: 실험하기)에서 겪은 주요 어려움과 평가 기록:
{chr(10).join(difficulties_summary)}

이 정보를 참고하여, 학습자가 겪었던 어려움과 실험 결과를 바탕으로 돌아보기 단계에서 더 적절한 안내와 피드백을 제공하세요.
"""
    return context

def get_learning_context():
    """Phase2/Phase3 맥락을 합쳐서 반환"""
    p2 = get_phase2_learning_context()
    p3 = get_phase3_learning_context()
    if not p2 and not p3:
        return ""
    parts = []
    if p2:
        parts.append(p2)
    if p3:
        parts.append(p3)
    return "\n".join(parts)

# 비동기 체인 생성
async def generate_answer_async(image_filepath, system_prompt, user_prompt, model_name="gpt-4.1"):
    # 동적 시스템 프롬프트 구성 (앞 단계 학습 맥락 포함)
    full_system_prompt = (system_prompt or "") + get_learning_context()

    # 멀티모달 객체를 세션 상태에서 가져오거나 생성/갱신
    chain_needs_init = (
        st.session_state.get("explanation_multimodal_chain_with_history") is None
        or st.session_state.get("explanation_system_prompt_signature") != full_system_prompt
    )

    # 멀티모달 객체를 세션 상태에서 가져오거나 생성
    if chain_needs_init:
        # 객체 생성
        llm = ChatOpenAI(
            temperature=0,
            model_name=model_name,
            openai_api_key = st.session_state.api_key
        )

        # print(full_system_prompt)

        # 핵심 수정: system_prompt에 full_system_prompt를 전달
        multimodal = MultiModalwithHistory(llm, system_prompt=full_system_prompt, user_prompt=user_prompt)
        st.session_state["explanation_multimodal_chain_with_history"] = multimodal
        st.session_state["explanation_system_prompt_signature"] = full_system_prompt
    else:
        # 기존 객체 재사용
        # print(full_system_prompt)

        multimodal = st.session_state["explanation_multimodal_chain_with_history"]

    # # 멀티모달 객체를 세션 상태에서 가져오거나 생성
    # if st.session_state["explanation_multimodal_chain_with_history"] is None:
    #     # 객체 생성
    #     llm = ChatOpenAI(
    #         temperature=0.2,
    #         model_name=model_name,
    #         openai_api_key = st.session_state.api_key
    #     )

    #     # 멀티모달 객체 생성 및 세션에 저장
    #     multimodal = MultiModalwithHistory(llm, system_prompt=system_prompt, user_prompt=user_prompt)
    #     st.session_state["explanation_multimodal_chain_with_history"] = multimodal
    # else:
    #     # 기존 객체 재사용
    #     multimodal = st.session_state["explanation_multimodal_chain_with_history"]

    # 이미지 파일로 부터 질의(스트림 방식)
    answer = multimodal.stream(user_prompt=user_prompt, image_url=image_filepath)

    ## 메세지 History 잘 유지되는지 확인용
    # print(multimodal.get_history())
    # print(f"LENGTH:{multimodal.get_history_length()}")
    return answer

# 비동기 제출 처리 함수
async def handle_submission_async(image_url, reason_text, system_prompt, selected_model):
    """제출 처리를 비동기적으로 수행"""
    try:
        # AI 답변 생성 (비동기)
        response = await generate_answer_async(
            image_url, system_prompt, reason_text, selected_model
        )     
        return response
        
    except Exception as e:
        st.error(f"제출 처리 중 오류가 발생했습니다: {str(e)}")
        return None


st.set_page_config(layout="wide")

st.title("돌아보기 🧐")

# Create a container for the info message and tooltip
info_container = st.container()
left_col, right_col = info_container.columns([4, 1])

with left_col:
    message = """
- 캔버스에 최종적으로 생각한 **(1)답안**과 그 **(2)이유**를 적어주세요.
- 정답을 적으면 오른쪽 '문제 정답' 탭에 채점 결과와 피드백이 나옵니다.
- 🧑🏻‍🏫**AI 선생님**과 대화하면서 오개념은 없는지 파악하고 내 이해도를 높여보세요.
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

# 탭 텍스트 크기 조정 - 더 강력한 선택자 사용
st.markdown(
    """
    <style>
    /* Streamlit 탭 버튼 - 모든 가능한 선택자 사용 */
    button[data-baseweb="tab"],
    button[role="tab"],
    [data-baseweb="tab"] button,
    div[data-baseweb="tabs"] button[role="tab"],
    div[data-baseweb="tabs"] button {
        font-size: 1.2rem !important;
        font-weight: 600 !important;
        padding: 0.75rem 1.5rem !important;
    }
    
    /* 탭 버튼 내부 모든 요소 타겟팅 */
    button[data-baseweb="tab"] *,
    button[data-baseweb="tab"] > *,
    button[data-baseweb="tab"] > div,
    button[data-baseweb="tab"] span,
    button[data-baseweb="tab"] p,
    [data-baseweb="tab"] button *,
    [data-baseweb="tab"] button > *,
    div[data-baseweb="tabs"] button *,
    div[data-baseweb="tabs"] button > * {
        font-size: 1.2rem !important;
        font-weight: 800 !important;
    }
    
    /* 탭 컨테이너 전체 타겟팅 */
    div[data-baseweb="tabs"],
    div[data-baseweb="tabs"] button,
    div[data-baseweb="tabs"] button > div,
    div[data-baseweb="tabs"] button > span {
        font-size: 1.2rem !important;
        font-weight: 800 !important;
    }
    
    /* Streamlit stTabs 클래스 타겟팅 */
    .stTabs button,
    .stTabs button > div,
    .stTabs [data-baseweb="tab"] {
        font-size: 1.2rem !important;
        font-weight: 800 !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)
tab1, tab2 = st.tabs(['문제 상황', '문제 정답'])

with tab1:
    with st.expander(
        label="문제 보기 🔍",
        expanded=True
        ):
        main_tab1 = st.container(border=True)
        main_tab1.write("""우주 공간에 새로운 행성을 찾아 다니는 인공위성이 있습니다.\n
드디어! 새로운 행성을 발견한 인공위성은 행성 주변의 원형 궤도에 진입하여 **등속 원운동**하려고 합니다. \n
**이때, 인공위성에 작용하는 (1) 알짜힘의 방향을 캔버스에 화살표로 그리고 (2) 그렇게 생각한 이유를 그 아래에 적어봅시다.**
""")
        with main_tab1:
            _, col2, _ = st.columns(3, vertical_alignment='center')
            col2.image(
                image=MOON_IMAGE_PATH,
            )
           

    st.text("최종적으로 문제를 해결해보세요.")
    st.text("(아래 캔버스에 생각한 내용을 그려보세요🎨)")
    
    # 캔버스 이미지 미리 로딩
    with st.spinner("캔버스 이미지를 준비 중..."):
        ensure_canvas_image_loaded(CANVAS_IMAGE_PATH, (500, 500))
    
    # Create a canvas component
    # 비동기 강제 이미지 로딩 캔버스 생성 (반드시 이미지 표시)
    canvas_result = create_async_canvas_with_guaranteed_image(
        CANVAS_IMAGE_PATH,
        fill_color="rgba(255, 165, 0, 0.3)",  # Fixed fill color with some opacity
        stroke_width=3,
        stroke_color="#000000",
        background_color="#EEEEEE",
        update_streamlit=True,
        height=500,
        width=500,
        drawing_mode="freedraw",
        point_display_radius=0,
        key="canvas_final_answer",
    )

    st.markdown("**캔버스 사용 방법**: ⬅️실행취소(undo), ➡️다시실행(redo), 🗑️전체초기화(clear)")


    reason = st.text_area(
        label="왜 그렇게 생각했는지 자세히 적어보세요.",
        height=200,
        on_change=enalble_submit_button
    )

    if not reason:
        disalble_submit_button()

    submit_button = st.button(
        label="제출하기",
        type="primary",
        use_container_width=True,
        disabled=st.session_state["submit_button_disabled"]
    )

    if submit_button:
        saved_image_path = save_draw_image(canvas_result.image_data)
        st.session_state["explanation_user_reason"] = reason
        st.session_state["explanation_saved_image_path"] = saved_image_path
        st.session_state["explanation_submission_triggered"] = True  # 제출이 트리거되었음을 표시

        # 새로운 턴 시작 (사용자 답안 제출)
        st.session_state["phase4_current_turn"] += 1
        current_turn = st.session_state["phase4_current_turn"]

        # S3에 업로드 (저장된 파일을 직접 사용)
        if saved_image_path and st.session_state.get("s3_manager") and st.session_state.get("session_uuid"):
            try:
                s3_path = st.session_state["s3_manager"].upload_image_file_to_s3(
                    file_path=saved_image_path,
                    session_id=st.session_state["session_uuid"]
                )
                
                if s3_path:
                    print(f"S3 업로드 완료: {s3_path}")
                    st.session_state["explanation_saved_image_s3_path"] = s3_path
                else:
                    print("S3 업로드 실패")
            except Exception as e:
                print(f"S3 업로드 중 오류: {e}")
                # S3 업로드 실패해도 로컬 저장은 유지

        # 제출된 답변을 DB에 저장 (이미지 경로 포함)
        submission_content = f"[제출한 답변 (이유)]: {reason}" + "\n"
        if saved_image_path:
            if st.session_state.get("explanation_saved_image_s3_path"):
                submission_content += f"[캔버스 이미지 S3 경로]: {st.session_state['explanation_saved_image_s3_path']}"

        save_message_to_db(
            role="user",
            content=submission_content,
            content_type="submission",  # 제출 타입으로 표시
            turn=current_turn
        )

        st.success("제출 완료! 상단의 '문제 정답' 탭에서 답을 확인해보세요:)")
        # find_answer_guide.png 이미지 크기 조정 - 우선순위 높임
        st.markdown(
            """
            <style>
            /* Streamlit 컨테이너를 타겟팅하는 더 구체적인 선택자 */
            div[data-testid="stImage"] img[src*="find_answer_guide.png"],
            div[data-testid="stImageContainer"] img[src*="find_answer_guide.png"],
            img[src*="find_answer_guide.png"],
            img[alt*="find_answer_guide"],
            div img[src*="find_answer_guide.png"] {
                width: 50% !important;
                max-width: 50% !important;
                height: auto !important;
                max-height: none !important;
                object-fit: contain !important;
            }
            </style>
            """,
            unsafe_allow_html=True
        )
        
        st.image("src/images/find_answer_guide.png", caption="'문제 정답' 탭 위치", use_container_width=False)


with tab2:
    togle = st.empty()
    if "explanation_saved_image_path" in st.session_state and "explanation_user_reason" in st.session_state:
        togle.empty()
        st.subheader("문제 정답")
        st.image(REVIEW_IMAGE_PATH)
        # st.write(st.session_state)
        st.session_state["show_answer"] = True
    else:
        togle.error("답안을 먼저 제출해주세요!")
        pass

    # Create columns with specific ratios
    col1, col2, col3 = st.columns([5, 2, 2])

    # Place the button in the last column
    with col1:
        if st.button(
            label="이전단계로",
            icon="⏪",
            help="실험하기로 이동하기",
            type="primary"
        ):
            st.switch_page("pages_group/03_실험하기.py")

    # Place the button in the last column
    # 답안 제출이 완료되었는지 확인
    submission_complete = (
        "explanation_saved_image_path" in st.session_state 
        and "explanation_user_reason" in st.session_state
    )

    # 한 번 표시된 이후는 계속 유지되도록 세션 상태 체크
    if "next_step_button_shown" not in st.session_state:
        st.session_state["next_step_button_shown"] = False
    
    # 제출이 완료되면 버튼 표시 상태를 True로 설정
    if submission_complete and not st.session_state["next_step_button_shown"]:
        st.session_state["next_step_button_shown"] = True
    
    # 버튼 표시 조건: 제출 완료되었거나 이전에 표시된 적이 있는 경우
    if submission_complete or st.session_state["next_step_button_shown"]:
        # Place the button in the last column
        with col3:
            if st.button(
                label="다음단계로",
                icon="⏩",
                help="적용하기로 이동하기",
                type="primary"
            ):
                st.switch_page("pages_group/05_적용하기.py")

#####################################
########### Sibebar Logic ###########
#####################################
with st.sidebar:

    st.write("**AI 선생님**과 대화하기")
    messages = st.container(height=400)
    ai_info = st.empty()

    with tab2:
        if "explanation_saved_image_path" in st.session_state and "explanation_user_reason" in st.session_state:
            if not st.session_state["show_answer"]:
                ai_info.empty()
                togle.empty()
                st.subheader("문제 정답")
                st.image(REVIEW_IMAGE_PATH)
                # st.write(st.session_state)
                st.session_state["show_answer"] = True
            else:
                pass
        else:
            ai_info.info("내 답안을 제출하면 🧑🏻‍🏫AI 선생님과 대화가 시작됩니다!")

    # 모델 선택 메뉴
    selected_model = INQUIRY_ASSISTANT_OPENAI_MODEL
    system_prompt = TUTOR_AI_04REFLECT_PROMPT

    # 이전 대화를 출력
    def print_messages():
        for chat_message in st.session_state["messages_explanation"]:
            if chat_message.role == "assistant":
                messages.chat_message(chat_message.role, avatar=SIDEBAR_AI_AVATAR).write(chat_message.content)
            else:
                messages.chat_message(chat_message.role).write(chat_message.content)

    # 새로운 메시지를 추가
    def add_message(role, message):
        st.session_state["messages_explanation"].append(ChatMessage(role=role, content=message))

    # 초기 질문 표시 (제출 전에만)
    if len(st.session_state["messages_explanation"]) == 0:
        # Display the question directly
        messages.chat_message("assistant", avatar=SIDEBAR_AI_AVATAR).write("앞서 보았던 문제를 다시 한 번 도전해볼까요?")

    # 이전 대화 기록 출력
    print_messages()

    ## 사용자 답변 제출에 대한 추가 로직(캔버스 사용 시)
    if st.session_state.get("explanation_submission_triggered", False) and "explanation_saved_image_path" in st.session_state:
        # 비동기 처리를 위한 상태 설정
        st.session_state["explanation_submission_in_progress"] = True
        
        # 새로운 턴 시작 (사용자 질문)        
        current_turn = st.session_state["phase4_current_turn"]

        # 사용자의 입력
        user_submit_input = f"(제출한 답변): {st.session_state['explanation_user_reason']}"
        messages.chat_message("user").write(user_submit_input)        

        # 비동기 처리를 위한 placeholder
        with st.spinner("AI가 답변을 생성하고 있습니다..."):

            # Intermediary 로직 추가 (Phase 4)
            if st.session_state["phase4_intermediary"] is None:
                intermediary = Intermediary.Intermediary(
                    client=OpenAI_Client(api_key=st.session_state.api_key),
                    model=INQUIRY_ASSISTANT_OPENAI_MODEL,
                    phase=4,
                    act_history=st.session_state.get("phase4_act_history", []),
                    assessment_history=st.session_state.get("phase4_assess_history", [])
                )
                st.session_state["phase4_intermediary"] = intermediary
            else:
                intermediary = st.session_state["phase4_intermediary"]

            prompt, acts, assessment = intermediary.get_prompt(
                conversation_history=st.session_state["messages_explanation"],
                student_prompt=user_submit_input
            )

            st.session_state["phase4_act_history"] = intermediary.get_act_history()
            st.session_state["phase4_assess_history"] = intermediary.get_assess_history()

            # 시스템 프롬프트 저장 (turn 포함)

            # learning_context를 포함한 full_system_prompt 계산
            learning_context = get_learning_context()
            full_system_prompt = (system_prompt or "") + learning_context

            save_message_to_db(
                role="system",
                content=full_system_prompt,
                content_type="system_prompt",
                turn=current_turn
            )

            # 시스템 프롬프트 저장 (learning context 포함)
            save_message_to_db(
                role="system",
                content=f"[Phase2-Phase3 학습 맥락 정보]\n{learning_context}",
                content_type="pre_learning_context",
                turn=current_turn
            )

            # assessment와 acts도 저장 (turn 포함)
            if assessment:
                # assessment가 이미 JSON 문자열이므로, 파싱 후 다시 직렬화하여 한글 유지
                try:
                    if isinstance(assessment, str):
                        assessment_dict = json.loads(assessment)
                    else:
                        assessment_dict = assessment
                    assessment_formatted = json.dumps(assessment_dict, ensure_ascii=False, indent=2)
                except (json.JSONDecodeError, TypeError):
                    # 파싱 실패 시 그대로 저장
                    assessment_formatted = str(assessment)
                
                save_message_to_db(
                    role="assistant",
                    content=f"[Intermediary Assessment]\n{assessment_formatted}",
                    content_type="intermediary_assessment",
                    llm_model=INQUIRY_ASSISTANT_OPENAI_MODEL,
                    turn=current_turn
                )

            if acts:
                # Enum 객체를 문자열로 변환하여 JSON 직렬화 가능하게 만듦
                acts_serializable = [act.name if isinstance(act, Enum) else str(act) for act in acts]
                save_message_to_db(
                    role="assistant",
                    content=f"[Intermediary Acts]\n{json.dumps(acts_serializable, ensure_ascii=False, indent=2)}",
                    content_type="intermediary_acts",
                    llm_model=INQUIRY_ASSISTANT_OPENAI_MODEL,
                    turn=current_turn
                )

            # 비동기 이벤트 루프 실행
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                # 이미지 파일을 bytesio로 변환후 path 반환 처리
                image_filepath = process_png_to_bytesio(st.session_state["explanation_saved_image_path"])

                # LLM에 전달될 사용자 프롬프트 생성
                user_prompt_for_llm = f"{prompt[-1]['content']}---\n\n<문제>\n - 우주 공간에 새로운 행성을 찾아 다니는 인공위성이 있습니다.\n - 드디어! 새로운 행성을 발견한 인공위성은 행성 주변의 원형 궤도에 진입하여 등속 원운동하려고 합니다.\n - 이때, 인공위성에 작용하는 (1) 알짜힘의 방향을 캔버스에 화살표로 그리고 (2) 그렇게 생각한 이유를 그 아래에 적어봅시다.\n\n 다음은 제시된 <문제>에 대해 내가 그린 캔버스 그림과 그 이유를 적은 글이야. 제출된 <그림 답안>과 글로 쓰여진 <이유>를 보고 나에게 적절한 피드백을 제공해줘\n\n <이유>: {st.session_state['explanation_user_reason']}"

                # LLM에 전달되는 사용자 프롬프트를 DB에 저장 (turn 포함)
                save_message_to_db(
                    role="system",
                    content=f"[LLM에 전달된 사용자 프롬프트]\n{user_prompt_for_llm}",
                    content_type="llm_user_prompt",
                    turn=current_turn
                )
                
                # AI 답변과 함께 제출 처리
                # 비동기 요청
                response = loop.run_until_complete(
                    handle_submission_async(
                        image_filepath,
                        user_prompt_for_llm,
                        system_prompt,
                        selected_model
                    )
                )
                                        
                # AI 답변을 스트리밍으로 표시
                with messages.chat_message("assistant", avatar=SIDEBAR_AI_AVATAR):
                    feedback_container = st.empty()
                    ai_feedback = ""
                    
                    for token in response:
                        ai_feedback += token.content
                        feedback_container.markdown(ai_feedback)
                
                if response:
                    st.success("🎉 AI 선생님의 피드백을 확인해보세요!")
                    
                    # 대화 기록에 추가
                    add_message("user", f"(제출한 답변): {st.session_state['explanation_user_reason']}")
                    add_message("assistant", ai_feedback)

                    # 명시적으로 일반 대화 메시지를 DB에 저장 (turn 포함)
                    save_message_to_db(
                        role="user",
                        content=user_submit_input,
                        content_type="submission",
                        turn=current_turn
                    )
                    save_message_to_db(
                        role="assistant",
                        content=ai_feedback,
                        content_type="feedback",
                        llm_model=selected_model,
                        turn=current_turn
                    )
                else:
                    st.error("AI 답변 생성에 실패했습니다.")

            except Exception as e:
                print(e)
                st.error(f"AI 답변 생성 중 오류가 발생했습니다: {str(e)}")

            finally:
                loop.close()
                st.session_state["explanation_submission_in_progress"] = False
                st.session_state["explanation_submission_triggered"] = False  # 트리거 상태 리셋

    # 사용자의 입력 (답안 제출 후에만 표시)
    if "explanation_saved_image_path" in st.session_state and "explanation_user_reason" in st.session_state:
        user_input = st.chat_input("🧑🏻‍🏫AI 선생님의 질문에 대한 답변을 작성해주세요.")
    else:
        user_input = None

    # 만약에 사용자 입력이 들어오면...
    if user_input:
        # 비동기 처리
        
        # 새로운 턴 시작 (사용자 질문)
        st.session_state["phase4_current_turn"] += 1
        current_turn = st.session_state["phase4_current_turn"]
        
        with st.spinner("AI가 답변을 생성하고 있습니다..."):

            # 사용자의 입력
            messages.chat_message("user").write(user_input)

            # Intermediary 로직 (Phase 4)
            if st.session_state["phase4_intermediary"] is None:
                intermediary = Intermediary.Intermediary(
                    client=OpenAI_Client(api_key=st.session_state.api_key),
                    model=INQUIRY_ASSISTANT_OPENAI_MODEL,
                    phase=4,
                    act_history=st.session_state.get("phase4_act_history", []),
                    assessment_history=st.session_state.get("phase4_assess_history", [])
                )
                st.session_state["phase4_intermediary"] = intermediary
            else:
                intermediary = st.session_state["phase4_intermediary"]

            prompt, acts, assessment = intermediary.get_prompt(
                conversation_history=st.session_state["messages_explanation"],
                student_prompt=user_input
            )
            # 히스토리 갱신
            st.session_state["phase4_act_history"] = intermediary.get_act_history()
            st.session_state["phase4_assess_history"] = intermediary.get_assess_history()

            # learning_context를 포함한 full_system_prompt 계산
            learning_context = get_learning_context()
            full_system_prompt = (system_prompt or "") + learning_context

            # 시스템 프롬프트 저장 (turn 포함)
            save_message_to_db(
                role="system",
                content=full_system_prompt,
                content_type="system_prompt",
                turn=current_turn
            )

            # 시스템 프롬프트 저장 (learning context 포함)
            save_message_to_db(
                role="system",
                content=f"[Phase2-Phase3 학습 맥락 정보]\n{learning_context}",
                content_type="pre_learning_context",
                turn=current_turn
            )

            # assessment와 acts도 저장 (turn 포함)
            if assessment:
                # assessment가 이미 JSON 문자열이므로, 파싱 후 다시 직렬화하여 한글 유지
                try:
                    if isinstance(assessment, str):
                        assessment_dict = json.loads(assessment)
                    else:
                        assessment_dict = assessment
                    assessment_formatted = json.dumps(assessment_dict, ensure_ascii=False, indent=2)
                except (json.JSONDecodeError, TypeError):
                    # 파싱 실패 시 그대로 저장
                    assessment_formatted = str(assessment)
                
                save_message_to_db(
                    role="assistant",
                    content=f"[Intermediary Assessment]\n{assessment_formatted}",
                    content_type="intermediary_assessment",
                    llm_model=INQUIRY_ASSISTANT_OPENAI_MODEL,
                    turn=current_turn
                )

            if acts:
                # Enum 객체를 문자열로 변환하여 JSON 직렬화 가능하게 만듦
                acts_serializable = [act.name if isinstance(act, Enum) else str(act) for act in acts]
                save_message_to_db(
                    role="assistant",
                    content=f"[Intermediary Acts]\n{json.dumps(acts_serializable, ensure_ascii=False, indent=2)}",
                    content_type="intermediary_acts",
                    llm_model=INQUIRY_ASSISTANT_OPENAI_MODEL,
                    turn=current_turn
                )

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                # 이미지 파일을 처리: 첫 턴과 동일하게 항상 이미지 포함
                image_source_path = (
                    st.session_state.get("explanation_saved_image_path")
                    or CANVAS_IMAGE_PATH
                )
                # 이미지 파일을 처리: 첫 턴과 동일하게 항상 이미지 포함
                image_filepath = process_png_to_bytesio(image_source_path)

                # LLM에 전달될 사용자 프롬프트 생성
                user_prompt_for_llm = prompt[-1]['content'] + "---" + "\n\n" + "**<사용자의 입력>**:\n" + user_input
                
                # LLM에 전달되는 사용자 프롬프트를 DB에 저장 (turn 포함)
                save_message_to_db(
                    role="system",
                    content=f"[LLM에 전달된 사용자 프롬프트]\n{user_prompt_for_llm}",
                    content_type="llm_user_prompt",
                    turn=current_turn
                )

                # 답변 요청 (비동기)
                response = loop.run_until_complete(
                    generate_answer_async(
                        image_filepath,
                        system_prompt,
                        user_prompt_for_llm,
                        selected_model
                    )
                )

                with messages.chat_message("assistant", avatar=SIDEBAR_AI_AVATAR):
                    # 빈 공간(컨테이너)을 만들어서, 여기에 토큰을 스트리밍 출력한다.
                    container = st.empty()

                    ai_answer = ""
                    for token in response:
                        ai_answer += token.content
                        container.markdown(ai_answer)

                if response:
                    st.success("🎉 AI 선생님의 피드백을 확인해보세요!")
                    # 대화기록을 저장한다.
                    add_message("user", user_input)
                    add_message("assistant", ai_answer)
                    
                    # 명시적으로 일반 대화 메시지를 DB에 저장 (turn 포함)
                    save_message_to_db(
                        role="user",
                        content=user_input,
                        content_type="text",
                        turn=current_turn
                    )
                    save_message_to_db(
                        role="assistant",
                        content=ai_answer,
                        content_type="text",
                        llm_model=selected_model,
                        turn=current_turn
                    )
                else:
                    st.error("AI 답변 생성에 실패했습니다.")
                
            except Exception as e:
                st.error(f"AI 답변 생성 중 오류가 발생했습니다: {str(e)}")
            finally:
                loop.close()
