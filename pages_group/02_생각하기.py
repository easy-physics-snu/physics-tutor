import os
import asyncio
import streamlit as st
from PIL import Image
from datetime import datetime

# from streamlit_drawable_canvas import st_canvas
from langchain_core.messages.chat import ChatMessage
from langchain_openai import ChatOpenAI
from openai import OpenAI as OpenAI_Client

from modules.multimodal import MultiModalwithHistory
# from modules.keywords import create_keyword
from modules.utils import overlay_png_and_np_from_image, process_png_to_bytesio, create_async_canvas_with_guaranteed_image, ensure_canvas_image_loaded
from modules.prompts import PEER_AI_02THINK_PROMPT

import dms.Intermediary as Intermediary

st.session_state.api_key = st.secrets["openai_api_key"]

os.environ["LANGCHAIN_TRACING_V2"] = st.secrets["LANGCHAIN_TRACING_V2"]
os.environ["LANGCHAIN_API_KEY"] = st.secrets["LANGCHAIN_API_KEY"]
os.environ["LANGCHAIN_ENDPOINT"] = st.secrets["LANGCHAIN_ENDPOINT"]
os.environ["LANGCHAIN_PROJECT"] = st.secrets["LANGCHAIN_PROJECT"]

PROBLEM_IMAGE_PATH = "src/images/satellite_orbit_canvas.png"
MOON_IMAGE_PATH = "src/images/satellite_moon.png"
CANVAS_IMAGE_PATH = "src/images/satellite_orbit_canvas.png"

INQUIRY_ASSISTANT_OPENAI_MODEL = "gpt-4.1"

SIDEBAR_AI_AVATAR = "src/images/ai_peer_avatar.png"

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

st.set_page_config(layout="wide")

st.title("생각하기 🤔")
st.info("- 다음 문제 상황의 정답을 예상해보고, 그 예상의 이유를 적어봅시다. \n - 하단의 캔버스에 그림을 그려보고, 그렇게 생각한 이유를 생각해보세요. \n - 궁금한게 있으면 좌측 사이드바의 🤓**AI 친구**에게 물어보세요.")


# 처음 1번만 실행하기 위한 코드
if "messages_predict" not in st.session_state:
    # 대화기록을 저장하기 위한 용도로 생성한다.
    st.session_state["messages_predict"] = []

if "submit_button_disabled" not in st.session_state:
    st.session_state["submit_button_disabled"] = True

if "multimodal_chain_with_history" not in st.session_state:
    st.session_state["multimodal_chain_with_history"] = None

# 제출 여부 초기화 (다음단계 버튼 노출 조건)
if "submission_triggered" not in st.session_state:
    st.session_state["submission_triggered"] = False

# show/hide the answer input UI
if "show_predict_input" not in st.session_state:
    st.session_state["show_predict_input"] = False

# '다음단계로' 버튼 표시 여부를 영구적으로 기록
if "can_proceed_to_next" not in st.session_state:
    st.session_state["can_proceed_to_next"] = False

if "phase2_intermediary" not in st.session_state:
    st.session_state["phase2_intermediary"] = None

if "phase2_act_history" not in st.session_state:
    st.session_state["phase2_act_history"] = []

if "phase2_assess_history" not in st.session_state:
    st.session_state["phase2_assess_history"] = []

# 비동기 체인 생성
async def generate_answer_async(image_filepath, system_prompt, user_prompt, model_name="gpt-4.1"):
    # 멀티모달 객체를 세션 상태에서 가져오거나 생성
    if st.session_state["multimodal_chain_with_history"] is None:
        # 객체 생성
        llm = ChatOpenAI(
            temperature=0,
            model_name=model_name,
            openai_api_key = st.session_state.api_key
        )

        # 멀티모달 객체 생성 및 세션에 저장
        multimodal = MultiModalwithHistory(llm, system_prompt=system_prompt, user_prompt=user_prompt)
        st.session_state["multimodal_chain_with_history"] = multimodal
    else:
        # 기존 객체 재사용
        multimodal = st.session_state["multimodal_chain_with_history"]

    # 이미지 파일로 부터 질의(스트림 방식)
    answer = multimodal.stream(user_prompt=user_prompt, image_url=image_filepath)

    ## 메세지 History 잘 유지되는지 확인용
    # print(multimodal.get_history())
    # print(f"LENGTH:{multimodal.get_history_length()}")
    return answer


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
        file_name = f"p-drawing-{current_time}"
        file_path = f"src/draw_images/{file_name}.png"
        
        # 디렉토리가 존재하는지 확인하고 생성
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        image.save(file_path, format="PNG")
        print(f"이미지 저장 완료: {file_path}")
        return file_path
        
    except Exception as e:
        st.error(f"이미지 저장 중 오류가 발생했습니다: {str(e)}")
        return None


def save_draw_explanation(text):
    st.session_state["2stage_explanation"] = text

def enalble_submit_button():
    st.session_state["submit_button_disabled"] = False

def disalble_submit_button():
    st.session_state["submit_button_disabled"] = True


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
    

# 사이드바 튜터 대화 턴(사용자 메시지 수) 확인 후 게이트
user_turns = sum(1 for m in st.session_state.get("messages_predict", []) if getattr(m, "role", None) == "user")

if user_turns < 3:
    st.info("좌측 사이드바의 **🤓AI 친구**와 최소 3턴 이상 대화하면 아래 정답 입력창이 열립니다.")
    st.warning(f"현재 대화 {user_turns}턴 진행됨. 계속 질문해보세요!")

# '정답 입력하기' 버튼 (5턴 이상이 되면 활성화)
open_btn = st.button(
    "정답 입력하기",
    type="primary",
    use_container_width=True,
    disabled=(user_turns < 3),
    key="open_predict_input"
)

# 버튼 클릭 시 입력 UI 표시 플래그 설정
if open_btn:
    st.session_state["show_predict_input"] = True

# 플래그가 True일 때만 캔버스와 입력칸 노출
if st.session_state.get("show_predict_input", False):
    st.text("문제의 답을 예상해보세요.")
    st.text("(아래 캔버스에 생각한 내용을 그려보세요🎨)")

    # 캔버스 이미지 미리 로딩
    with st.spinner("캔버스 이미지를 준비 중..."):
        ensure_canvas_image_loaded(CANVAS_IMAGE_PATH, (500, 500))

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
        key="canvas_intermediate_answer",
    )

    st.markdown("**캔버스 사용 방법**: ⬅️실행취소(undo), ➡️다시실행(redo), 🗑️전체초기화(clear)")

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
        disabled=st.session_state["submit_button_disabled"]
    )

    if submit_button:
        # 기본 제출 처리
        saved_image_path = save_draw_image(canvas_result.image_data)
        st.session_state["predict_user_reason"] = reason
        st.session_state["predict_saved_image_path"] = saved_image_path
        st.session_state["submission_triggered"] = True  # 제출이 트리거되었음을 표시
        st.success("좌측 사이드바의 **🤓AI 친구**의 피드백을 확인해주세요!")
        st.info("정답은 '돌아보기' 단계에서 확인할 수 있습니다! 충분히 고민해봤다면, 다음 단계로 넘어가세요:)")

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


# '다음단계로' 버튼은 (1) 5턴 이상 대화 AND (2) 정답 제출 완료 후 노출
# 조건을 만족하면 영구적으로 표시 플래그 설정
current_can_show = (
    st.session_state.get("submission_triggered", False)
    and bool(st.session_state.get("predict_saved_image_path"))
    and bool(st.session_state.get("predict_user_reason"))
)

# 조건을 만족하면 플래그를 True로 설정 (한번 True가 되면 계속 유지)
if current_can_show:
    st.session_state["can_proceed_to_next"] = True

# 플래그가 True면 버튼 표시
if st.session_state.get("can_proceed_to_next", False):
    # Place the button in the last column
    with col3:
        if st.button(
            label="다음단계로",
            icon="⏩",
            help="실험하기로 이동하기",
            type="primary"
        ):
            st.switch_page("pages_group/03_실험하기.py")

#####################################
########### Sibebar Logic ###########
#####################################
with st.sidebar:

    # 추천 질문 사용 여부 토글 추가
    # toggle_recommended_questions = st.toggle("**💡추천 질문** 사용하기", value=False)
    # st.session_state["toggle_recommended_questions"] = toggle_recommended_questions

    st.write("**AI 친구**에게 물어보기")
    spinner_box = st.empty()
    messages = st.container(height=400)

    selected_model = "gpt-4.1"
    system_prompt = PEER_AI_02THINK_PROMPT

    # 이전 대화를 출력
    def print_messages():
        for chat_message in st.session_state["messages_predict"]:
            if chat_message.role == "assistant":
                messages.chat_message(chat_message.role, avatar=SIDEBAR_AI_AVATAR).write(chat_message.content)
            else:
                messages.chat_message(chat_message.role).write(chat_message.content)

    # 새로운 메시지를 추가
    def add_message(role, message):
        st.session_state["messages_predict"].append(ChatMessage(role=role, content=message))

    # 초기 대화 기록 추가
    if len(st.session_state["messages_predict"]) == 0:
        messages.chat_message("assistant", avatar=SIDEBAR_AI_AVATAR).write("안녕! 나랑 같이 차근차근 원운동을 탐구해보자!")
    else:
        pass

    # 이전 대화 기록 출력
    print_messages()

    # 사용자의 입력
    user_input = st.chat_input("궁금한 내용을 물어보세요!")

    ## 사용자 답변 제출에 대한 추가 로직(캔버스 사용 시)
    if st.session_state.get("submission_triggered", False) and "predict_saved_image_path" in st.session_state:
        # 비동기 처리를 위한 상태 설정
        st.session_state["submission_in_progress"] = True
        
        # 사용자의 입력
        user_submit_input = f"(제출한 답변): {st.session_state['predict_user_reason']}"
        messages.chat_message("user").write(user_submit_input)

        # 비동기 처리를 위한 placeholder
        with st.spinner("AI가 답변을 생성하고 있습니다..."):

            # Intermediary 로직 추가
            if st.session_state["phase2_intermediary"] is None:
                intermediary = Intermediary.Intermediary(
                    client=OpenAI_Client(api_key=st.session_state.api_key),
                    model=INQUIRY_ASSISTANT_OPENAI_MODEL,
                    phase=2,
                    act_history=st.session_state.get("phase2_act_history", []),
                    assessment_history=st.session_state.get("phase2_assess_history", [])
                )
                st.session_state["phase2_intermediary"] = intermediary
            else:
                intermediary = st.session_state["phase2_intermediary"]
            
            prompt, acts, assessment = intermediary.get_prompt(
                conversation_history=st.session_state["messages_predict"],
                student_prompt=user_submit_input
            )

            st.session_state["phase2_act_history"] = intermediary.get_act_history()
            st.session_state["phase2_assess_history"] = intermediary.get_assess_history()

            # 비동기 이벤트 루프 실행
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                # 이미지 파일을 bytesio로 변환후 path 반환 처리
                image_filepath = process_png_to_bytesio(st.session_state["predict_saved_image_path"])
                
                # AI 답변과 함께 제출 처리
                # 비동기 요청
                response = loop.run_until_complete(
                    handle_submission_async(
                        image_filepath,
                        f"{prompt[-1]['content']}---\n\n<문제>\n - 우주 공간에 새로운 행성을 찾아 다니는 인공위성이 있습니다.\n - 드디어! 새로운 행성을 발견한 인공위성은 행성 주변의 원형 궤도에 진입하여 등속 원운동하려고 합니다.\n - 이때, 인공위성에 작용하는 (1) 알짜힘의 방향을 캔버스에 화살표로 그리고 (2) 그렇게 생각한 이유를 그 아래에 적어봅시다.\n\n 다음은 제시된 <문제>에 대해 내가 그린 캔버스 그림과 그 이유를 적은 글이야. 제출된 <그림 답안>과 글로 쓰여진 <이유>를 보고 나에게 적절한 피드백을 제공해줘\n\n <이유>: {st.session_state['predict_user_reason']}", 
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
                    st.success("🎉 AI 친구의 피드백을 확인해보세요!")
                    
                    # 대화 기록에 추가
                    add_message("user", f"(제출한 답변): {st.session_state['predict_user_reason']}")
                    add_message("assistant", ai_feedback)
                else:
                    st.error("AI 답변 생성에 실패했습니다.")

            except Exception as e:
                print(e)
                st.error(f"AI 답변 생성 중 오류가 발생했습니다: {str(e)}")

            finally:
                loop.close()
                st.session_state["submission_in_progress"] = False
                st.session_state["submission_triggered"] = False  # 트리거 상태 리셋


    # 추천 질문 사용 여부에 따라 조건부 표시
    # if st.session_state.get("toggle_recommended_questions", True):
    #     st.text("추천 질문 (클릭 시 다른 질문이 생성됩니다)")
    #     col1, col2 = st.columns(2)
    #     placeholder1 = col1.empty()
    #     placeholder2 = col2.empty()

    #     # 키워드 질문 처리
    #     kw_1, kw_2 = create_keyword(st.session_state["messages_predict"])
    #     kw_button_1 = placeholder1.button(label=kw_1, use_container_width=True)
    #     kw_button_2 = placeholder2.button(label=kw_2, use_container_width=True)
    # else:
    #     # 추천 질문을 사용하지 않는 경우 버튼들을 None으로 설정
    #     kw_button_1 = None
    #     kw_button_2 = None


    # 만약에 사용자 입력이 들어오면...
    if user_input: # and not (kw_button_1 and st.session_state.get("toggle_recommended_questions", True)) and not (kw_button_2 and st.session_state.get("toggle_recommended_questions", True)):
        # 비동기 처리
        
        with st.spinner("AI가 답변을 생성하고 있습니다..."):

            # 사용자의 입력
            messages.chat_message("user").write(user_input)

            if st.session_state["phase2_intermediary"] is None:
                intermediary = Intermediary.Intermediary(
                    client=OpenAI_Client(api_key=st.session_state.api_key),
                    model=INQUIRY_ASSISTANT_OPENAI_MODEL,
                    phase=2,
                    act_history=st.session_state.get("phase2_act_history", []),
                    assessment_history=st.session_state.get("phase2_assess_history", [])
                )
                st.session_state["phase2_intermediary"] = intermediary
            else:
                intermediary = st.session_state["phase2_intermediary"]
            
            prompt, acts, assessment = intermediary.get_prompt(
                conversation_history=st.session_state["messages_predict"],
                student_prompt=user_input
            )

            st.session_state["phase2_act_history"] = intermediary.get_act_history()
            st.session_state["phase2_assess_history"] = intermediary.get_assess_history()

            # print(f"prompt: {prompt}")
            # print(f"acts: {acts}")
            # print(f"assessment: {assessment}")

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # act_history = intermediary.get_act_history()
            # assess_history = intermediary.get_assess_history()

            # st.write("act_history (행동 기록):")
            # st.write(act_history)
            # st.write("assess_history (평가 기록):")
            # st.write(assess_history)

            try:
                # 이미지 파일을 처리: 첫 턴과 동일하게 항상 이미지 포함
                image_filepath = process_png_to_bytesio(st.session_state["explanation_saved_image_path"])

                # 답변 요청 (비동기)
                response = loop.run_until_complete(
                    generate_answer_async(
                        image_filepath,
                        system_prompt,
                        prompt[-1]['content'] + "---" + "\n\n" + "**<사용자의 입력>**:\n" + user_input,
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
                    st.success("🎉 AI 친구의 피드백을 확인해보세요!")
                    # 대화기록을 저장한다.
                    add_message("user", user_input)
                    add_message("assistant", ai_answer)
                else:
                    st.error("AI 답변 생성에 실패했습니다.")

                # if st.session_state.get("toggle_recommended_questions", True):
                #     kw_1, kw_2 = create_keyword(st.session_state["messages_predict"])
                #     placeholder1.button(label=kw_1, use_container_width=True)
                #     placeholder2.button(label=kw_2, use_container_width=True)
                
            except Exception as e:
                st.error(f"AI 답변 생성 중 오류가 발생했습니다: {str(e)}")
            finally:
                loop.close()
