import os
import streamlit as st
import pandas as pd

from openai import OpenAI

# from langchain_teddynote import logging

os.environ["LANGCHAIN_TRACING_V2"] = st.secrets["LANGCHAIN_TRACING_V2"]
os.environ["LANGCHAIN_API_KEY"] = st.secrets["LANGCHAIN_API_KEY"]
os.environ["LANGCHAIN_ENDPOINT"] = st.secrets["LANGCHAIN_ENDPOINT"]
os.environ["LANGCHAIN_PROJECT"] = st.secrets["LANGCHAIN_PROJECT"]

st.session_state.api_key = st.secrets["openai_api_key"]

# TEXTBOOK_FILE_PATH = "src/textbooks/physics_textbook.pdf" #제거할 예정

##TODO 민선쌤 성능 이슈로 gpt-4.1 모델로 바꿨어요~
TUTOR_OPENAI_MODEL = "gpt-4.1"
# RAG_OPENAI_MODEL = "gpt-4o"
# RAG_SYSTEM_PROMPT = "prompts/doc-rag-scaffold.yaml"

AI_AVATAR = "src/images/ai_tutor_avatar.png"


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


# 처음 1번만 실행하기 위한 코드
if "intro_1_tutor_messages" not in st.session_state:
    # 대화기록을 저장하기 위한 용도로 생성한다.
    st.session_state["intro_1_tutor_messages"] = []

if "balloons_done" not in st.session_state:
    st.session_state["balloons_done"] = False


# # 파일 업로드 후 retriever 생성 (작업시간이 오래 걸릴 예정...)
# if "pdf_retriever" not in st.session_state:
#     retriever = embed_file(TEXTBOOK_FILE_PATH)
#     st.session_state["pdf_retriever"] = retriever

# if "pdf_chain" not in st.session_state and st.session_state["pdf_retriever"]:
#     retriever = st.session_state["pdf_retriever"]
#     st.session_state["pdf_chain"] = create_chain(
#         retriever, prompt_path=RAG_SYSTEM_PROMPT, model_name=RAG_OPENAI_MODEL
#     )

######################################
########### Mainpage Logic ###########
######################################
st.set_page_config(layout="wide")

st.title("들어가기 🚀")

st.subheader("오늘 배울 물리 개념은?")
st.info("- 먼저 **[1. 여러 가지 운동]** 과 **[2. 힘과 운동]** 소단원에서 배운 내용을 복습해봅시다:) \n - 아래 2개 탭을 모두 마치고 다음 단계로 넘어가주세요!")

# find_tab_guide.png 이미지 크기 조정 - 우선순위 높임
st.markdown(
    """
    <style>
    /* Streamlit 컨테이너를 타겟팅하는 더 구체적인 선택자 */
    div[data-testid="stImage"] img[src*="find_tab_guide.png"],
    div[data-testid="stImageContainer"] img[src*="find_tab_guide.png"],
    img[src*="find_tab_guide.png"],
    img[alt*="find_tab_guide"],
    div img[src*="find_tab_guide.png"] {
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

st.image("src/images/find_tab_guide.png", use_container_width=False)

tab1, tab2 = st.tabs(["1. 여러 가지 운동", "2. 힘과 운동"])

# tab 전환 감지 및 상태 업데이트
if tab1:
    st.session_state['current_tab'] = 'tab1'
if tab2:
    st.session_state['current_tab'] = 'tab2'

########### TAB 1 ###########
with tab1:
    st.write("**Q1. 놀이공원에서 볼 수 있는 여러 가지 놀이 기구들의 운동 방향과 속력 변화를 표에 정리해봅시다.** (한 칸에 1개만 선택해주세요)")
    st.write("([운동 방향]과 [속력] 셀을 클릭하여 알맞은 설명을 골라주세요)")
    
    # 원본 순서 정의 (고정 순서)
    original_types = ["자이로드롭", "회전목마", "롤러코스터", "바이킹"]
    images = [
        "https://dimg.donga.com/ugc/CDB/SODA/Article/57/e0/f9/a4/57e0f9a4248cd2738de6.gif",
        "https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExc2w5eWNla2NmbWR0ZnYzdHRjMDRpZnVlNGV4dWJlZGJudWE4dDBvcyZlcD12MV9naWZzX3NlYXJjaCZjdD1n/wJQF23Gt0eEMS2Zcbb/giphy.gif",
        "https://media2.giphy.com/media/v1.Y2lkPTc5MGI3NjExMDM2ZTRueWxqMW00emRyanIxaGVwdGx4amR2aW5scDNnYnMzbTg4YiZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/WqSCrUOEWQpWC8JGNg/giphy.webp",
        "https://mblogthumb-phinf.pstatic.net/MjAyMjEyMjhfMTMx/MDAxNjcyMTYzMDc2Mzc3.RACWbUSQ5ys66npAKl1ABuFkloP9bs3D3Hg6Hv0rhG0g.z4ZBQI_SRDXNCaO8v51EZrYxIkCwLcnawqYXJjqunrsg.GIF.mok5022/3546279707.gif?type=w800"
    ]
    
    # 세션 상태 초기화 (각 행의 선택값 저장)
    if "q1_direction" not in st.session_state:
        st.session_state.q1_direction = {ride: None for ride in original_types}
    if "q1_speed" not in st.session_state:
        st.session_state.q1_speed = {ride: None for ride in original_types}
    
    # 표 스타일링 (행 높이 줄이기 - Q1 질문부터 한 화면에 보이도록 더 축소)
    st.markdown(
        """
        <style>
        /* Q1 질문 텍스트 간격 축소 */
        div[data-testid="stMarkdownContainer"] p:first-of-type {
            margin-bottom: 0.3rem !important;
        }
        
        /* Q1 표 영역 전체 더 축소 */
        div[data-testid="column"] {
            padding-bottom: 0.05rem !important;
            padding-top: 0.05rem !important;
        }
        
        /* selectbox 높이 더 축소 */
        .stSelectbox > div > div {
            padding-top: 0.1rem !important;
            padding-bottom: 0.1rem !important;
            font-size: 0.8rem !important;
            min-height: 1.5rem !important;
        }
        
        /* multiselect 높이 더 축소 */
        .stMultiSelect > div > div {
            padding-top: 0.1rem !important;
            padding-bottom: 0.1rem !important;
            font-size: 0.8rem !important;
            min-height: 1.5rem !important;
        }
        
        /* 표 내부 이미지 컨테이너 크기 고정 (0.3rem × 0.2rem) */
        div[data-testid="column"] .stImage {
            width: 0.2rem !important;
            height: 0.1rem !important;
            margin-top: 0 !important;
            margin-bottom: 0 !important;
            overflow: hidden !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
        }
        
        /* 표 내부 이미지가 컨테이너를 채우도록 설정 */
        div[data-testid="column"] .stImage img {
            width: 100% !important;
            height: 100% !important;
            object-fit: cover !important;
            margin-top: 0 !important;
            margin-bottom: 0 !important;
        }
        
        /* 바이킹 이미지 특별 설정 - 하단 0.5cm 잘림 */
        div[data-testid="column"] .stImage img[src*="3546279707"] {
            object-position: 50% top !important;  /* 상단 중앙을 기준으로 하단 0.5cm가 잘림 */
        }
        
        /* 표 텍스트 크기 더 축소 */
        div[data-testid="column"] p,
        div[data-testid="column"] .stMarkdown {
            font-size: 0.8rem !important;
            margin-bottom: 0.05rem !important;
            margin-top: 0.05rem !important;
            line-height: 1.2 !important;
        }
        
        /* 헤더 텍스트 크기 조정 */
        div[data-testid="column"] strong {
            font-size: 0.85rem !important;
        }
        
        /* 구분선(hr) 마진 축소 */
        hr {
            margin-top: 0.3rem !important;
            margin-bottom: 0.3rem !important;
        }
        
        /* 표 행 높이 통일 - 헤더 행 높이 기준 */
        div[data-testid="stHorizontalBlock"]:has(strong) {
            height: 1.5rem !important;  /* 헤더 행 높이 */
            overflow: hidden !important;
        }
        
        /* 데이터 행 높이 (모두 동일, 내용이 많으면 잘림) */
        div[data-testid="stHorizontalBlock"]:not(:has(strong)) {
            height: 8rem !important;  /* 헤더 행과 동일한 높이 */
            align-items: stretch !important;
            overflow: hidden !important;
        }
        </style>
        """,
        unsafe_allow_html=True
    )
    
    # 헤더 행
    header_cols = st.columns(4)
    with header_cols[0]:
        st.markdown("**놀이 기구**")
    with header_cols[1]:
        st.markdown("**이미지**")
    with header_cols[2]:
        st.markdown("**운동 방향**")
    with header_cols[3]:
        st.markdown("**속력**")
    
    st.markdown("---")
    
    # 데이터 행 (4개)
    for idx, ride_type in enumerate(original_types):
        row_cols = st.columns(4)
        
        with row_cols[0]:
            st.write(ride_type)
        
        with row_cols[1]:
            st.image(images[idx], use_container_width=True)
        
        with row_cols[2]:
            direction_options = ["변한다", "일정하다"]
            current_direction = st.session_state.q1_direction[ride_type]
            
            # 현재 선택값을 리스트로 변환 (multiselect용)
            default_direction = [current_direction] if current_direction else []
            
            selected_direction_list = st.multiselect(
                f"{ride_type} 운동 방향",
                options=direction_options,
                default=default_direction,
                key=f"direction_{idx}",
                label_visibility="collapsed"
            )
            
            # 하나만 선택 가능하도록 - 리스트의 첫 번째 요소만 사용
            if len(selected_direction_list) > 1:
                # 여러 개 선택된 경우 마지막 선택만 유지
                selected_direction = selected_direction_list[-1]
            elif len(selected_direction_list) == 1:
                selected_direction = selected_direction_list[0]
            else:
                selected_direction = None
            
            # 선택값 저장
            st.session_state.q1_direction[ride_type] = selected_direction
        
        with row_cols[3]:
            speed_options = ["변한다", "일정하다"]
            current_speed = st.session_state.q1_speed[ride_type]
            
            # 현재 선택값을 리스트로 변환 (multiselect용)
            default_speed = [current_speed] if current_speed else []
            
            selected_speed_list = st.multiselect(
                f"{ride_type} 속력",
                options=speed_options,
                default=default_speed,
                key=f"speed_{idx}",
                label_visibility="collapsed"
            )
            
            # 하나만 선택 가능하도록 - 리스트의 첫 번째 요소만 사용
            if len(selected_speed_list) > 1:
                # 여러 개 선택된 경우 마지막 선택만 유지
                selected_speed = selected_speed_list[-1]
            elif len(selected_speed_list) == 1:
                selected_speed = selected_speed_list[0]
            else:
                selected_speed = None
            
            # 선택값 저장
            st.session_state.q1_speed[ride_type] = selected_speed
        
        # 행 간격 줄이기 (구분선 제거)
    
    # 정답 체크
    st.session_state.q1 = False
    info_q1 = st.empty()
    
    # 모든 드롭다운이 선택되었는지 확인 (None이 아니면 선택됨)
    all_selected = all(
        st.session_state.q1_direction[ride] is not None and 
        st.session_state.q1_speed[ride] is not None 
        for ride in original_types
    )
    
    # 모든 드롭다운이 선택되었을 때만 정답 체크
    if all_selected:
        # 정답 체크 로직
        correct_answers = {
            "자이로드롭": {"direction": "일정하다", "speed": "변한다"},
            "회전목마": {"direction": "변한다", "speed": "일정하다"},
            "롤러코스터": {"direction": "변한다", "speed": "변한다"},
            "바이킹": {"direction": "변한다", "speed": "변한다"}
        }
        
        is_correct = True
        
        # 틀린 항목을 놀이기구별로 분류
        wrong_by_ride = {}
        
        for ride in original_types:
            student_dir = st.session_state.q1_direction[ride]
            student_speed = st.session_state.q1_speed[ride]
            correct_dir = correct_answers[ride]["direction"]
            correct_speed = correct_answers[ride]["speed"]
            
            wrong_parts = []
            if student_dir != correct_dir:
                wrong_parts.append("운동 방향")
            if student_speed != correct_speed:
                wrong_parts.append("속력")
            
            if wrong_parts:
                is_correct = False
                wrong_by_ride[ride] = wrong_parts
        
        if is_correct:
                                        st.session_state.q1 = True
                                        info_q1.success("정답입니다!")
                                        if not st.session_state.balloons_t1_q1:
                                            st.balloons()
                                            st.session_state.balloons_t1_q1 = True
        else:
            if st.session_state.q1:
                info_q1.success("정답입니다!")
            else:
                # 틀린 항목을 그룹화하여 메시지 생성
                direction_rides = []
                speed_rides = []
                
                for ride, wrong_parts in wrong_by_ride.items():
                    if "운동 방향" in wrong_parts:
                        direction_rides.append(ride)
                    if "속력" in wrong_parts:
                        speed_rides.append(ride)
                
                error_parts = []
                if direction_rides:
                    error_parts.append(f"{', '.join(direction_rides)}의 운동 방향")
                if speed_rides:
                    error_parts.append(f"{', '.join(speed_rides)}의 속력")
                
                if error_parts:
                    error_msg = ", ".join(error_parts) + "을 다시 살펴보세요🔍"
                    info_q1.error(error_msg)
    else:
        # 일부만 선택된 경우 이전 정답 상태 유지
        if st.session_state.q1:
            info_q1.success("정답입니다!")

    st.write("")
    st.write("") 

    st.write("**Q2. 놀이 기구의 운동을 다음과 같이 분류해 봅시다.** (한 칸에 2개가 들어갈 수 있어요)")
    options_1 = st.multiselect(
        "속력만 변하는 운동",
        ["자이로드롭", "회전목마", "롤러코스터", "바이킹"],
    )
    options_2 = st.multiselect(
        "운동 방향만 변하는 운동",
        ["자이로드롭", "회전목마", "롤러코스터", "바이킹"],
    )
    options_3 = st.multiselect(
        "속력과 운동 방향이 모두 변하는 운동",
        ["자이로드롭", "회전목마", "롤러코스터", "바이킹"],
    )

    st.session_state.q2 = False
    info_q2 = st.empty()
    
    correct_q2 = {
        "속력만 변하는 운동": ["자이로드롭"],
        "운동 방향만 변하는 운동": ["회전목마"],
        "속력과 운동 방향이 모두 변하는 운동": ["롤러코스터", "바이킹"]
    }
    
    # 4개의 선택지가 모두 배정되었는지 확인
    all_rides = ["자이로드롭", "회전목마", "롤러코스터", "바이킹"]
    selected_rides = list(options_1) + list(options_2) + list(options_3)
    all_rides_assigned = set(selected_rides) == set(all_rides) and len(selected_rides) == 4
    
    if all_rides_assigned:
        is_correct = True
        wrong_rides = set()  # 잘못 분류된 놀이기구 목록
        
        # 속력만 변하는 운동 체크
        if sorted(options_1) != sorted(correct_q2["속력만 변하는 운동"]):
            is_correct = False
            # 잘못 선택된 항목 (정답이 아닌 것)
            wrong_selected = set(options_1) - set(correct_q2["속력만 변하는 운동"])
            # 누락된 항목 (정답인데 선택되지 않은 것)
            missing = set(correct_q2["속력만 변하는 운동"]) - set(options_1)
            wrong_rides.update(wrong_selected)
            wrong_rides.update(missing)
        
        # 운동 방향만 변하는 운동 체크
        if sorted(options_2) != sorted(correct_q2["운동 방향만 변하는 운동"]):
            is_correct = False
            wrong_selected = set(options_2) - set(correct_q2["운동 방향만 변하는 운동"])
            missing = set(correct_q2["운동 방향만 변하는 운동"]) - set(options_2)
            wrong_rides.update(wrong_selected)
            wrong_rides.update(missing)
        
        # 속력과 운동 방향이 모두 변하는 운동 체크
        if sorted(options_3) != sorted(correct_q2["속력과 운동 방향이 모두 변하는 운동"]):
            is_correct = False
            wrong_selected = set(options_3) - set(correct_q2["속력과 운동 방향이 모두 변하는 운동"])
            missing = set(correct_q2["속력과 운동 방향이 모두 변하는 운동"]) - set(options_3)
            wrong_rides.update(wrong_selected)
            wrong_rides.update(missing)
        
        if is_correct:
                    st.session_state.q2 = True
                    info_q2.success("정답입니다!")
                    if not st.session_state.balloons_t1_q2:
                        st.balloons()
                        st.session_state.balloons_t1_q2 = True
        else:
            if st.session_state.q2:
                info_q2.success("정답입니다!")
            else:
                # for category in wrong_categories:
                #     error_msg += f"- {category}\n"
                # if wrong_rides:
                error_msg = f"다음 놀이기구의 운동을 다시 분류해주세요🔍: {', '.join(sorted(wrong_rides))}"
                # else:
                #     error_msg = "다음 놀이기구의 운동을 다시 분류해주세요🔍"
                info_q2.error(error_msg)

    else:
        # 4개 선택지가 모두 배정되지 않은 경우
        if st.session_state.q2:
            info_q2.success("정답입니다!")
        else:
            missing_rides = set(all_rides) - set(selected_rides)
            if missing_rides:
                info_q2.warning(f"모든 놀이 기구를 분류해주세요. 아직 고르지 않은 항목: {', '.join(sorted(missing_rides))}")
            else:
                # 중복 선택이 있는 경우
                if len(selected_rides) > len(set(selected_rides)):
                    info_q2.warning("각 놀이 기구는 하나의 분류에만 속해야 합니다. 하나의 놀이기구가 여러 군데에 들어가지 않도록 해주세요")
                else:
                    # 카테고리가 비어있는 경우
                    missing = []
                    if not options_1:
                        missing.append("속력만 변하는 운동")
                    if not options_2:
                        missing.append("운동 방향만 변하는 운동")
                    if not options_3:
                        missing.append("속력과 운동 방향이 모두 변하는 운동")
                    if missing:
                        info_q2.warning(f"다음 항목을 선택해주세요: {', '.join(missing)}")

    if st.session_state.q1 and st.session_state.q2:
        st.subheader("**핵심 정리!**")
        st.info("속력이 변하는 운동, 운동 방향이 변하는 운동, 속력과 운동 방향이 모두 변하는 운동은 모두 **가속도 운동**이다.")
        st.image("src/images/explain_2.png", caption="출처: 미래엔 교과서")
        
        # tab1 완료 시 다음 tab으로 안내
        st.success("🎉 Tab 1 완료! 이제 '힘과 운동' 탭으로 이동해주세요.")

########### TAB 2 ###########
with tab2:
    # AI 튜터의 프롬프트 설정
    TUTOR_SYSTEM_PROMPT = """당신은 친근하고 대화형 학습을 돕는 **물리 튜터**입니다. 항상 존댓말을 사용하며 긍정적이고 격려하는 태도로 일관된 대화를 유지하세요.  

    다음 지침을 따라주세요:
    
    **📝 학생의 답변 시도 (문제 풀이)일 때:**
    1. 학생이 이해한 부분과 부족한 부분을 파악합니다.
    2. 부족한 부분에 대해 다시 생각해볼 수 있도록 질문이나 힌트를 제공합니다.
    3. ⚠️ **절대 금지**: 문제의 정답을 직접 말하거나, 정답 예시를 언급하거나, 정확한 답을 암시하지 마세요.
    
    **❓ 학생의 질문 (개념/용어 설명 요청)일 때:**
    1. ✅ **적극 대응**: 물리 개념, 용어, 원리에 대한 질문에는 친절하게 설명해주세요.
       - 예) "알짜힘이 뭐예요?" → "알짜힘은 물체에 작용하는 모든 힘을 합친 것이에요. 줄다리기에서 양쪽 힘을 모두 고려한 최종 힘이 바로 알짜힘이죠."
       - 예) "관성이 뭐예요?" → "관성은 물체가 현재 운동 상태를 유지하려는 성질이에요. 정지한 물체는 계속 정지하려 하고, 움직이는 물체는 계속 움직이려 하죠."
    2. ⚠️ **주의**: 개념을 설명하되, 문제의 직접적인 답은 말하지 마세요.
    3. 설명 후 학생이 직접 문제에 적용해보도록 유도하세요.
    
    **🎭 기타:**
    - 학생이 장난스럽거나 부적절한 답변을 하더라도, 교육자로서 차분하고 친절하게 진지한 답변을 권유하세요.
    - 세 문장을 넘지 않도록 간결하게 대화를 생성하세요.
    - 이모지를 적절히 사용하여 친근감을 줍니다."""

    # 문제와 답변 정의
    QUESTIONS = {
        'Q1': {
            'question': "안녕하세요! 저는 오늘 여러분과 함께 공부할 **AI 선생님**입니다. \n\n먼저 오늘 배운 기본 개념부터 다시 떠올려볼까요? \n\n공을 발로 찰 때처럼 한 사람이 힘을 작용하기도 하지만 줄다리기처럼 여러 사람이 함께 힘을 작용할 때도 있죠. **이처럼 한 물체에 여러 힘이 동시에 작용할 때, 이 힘들과 같은 효과를 나타내는 하나의 힘을 무엇이라고 할까요?** (초성 힌트: ㅇㅉㅎ 또는 ㅎㄹ)",
            'correct_answers': ['알짜힘', '합력'],
            'correct_feedback': "정확합니다!  알짜힘(또는 합력)은 물체에 작용하는 모든 힘들을 하나로 합친 것이에요. 예를 들어, 줄다리기에서 양쪽에서 당기는 힘들을 모두 고려한 최종적인 힘이 바로 알짜힘(또는 합력)이죠.",
            'hint': "실제로 영향을 주는 '알짜배기' 힘이라는 의미를 가지고 있답니다. 또는 여러 힘을 '합친다'는 의미가 담겨있기도 하구요."
        },
        'Q2': {
            'question': "이제 뉴턴의 운동법칙에 대해 알아볼까요? \n\n**다음 키워드를 참고하여 뉴턴 운동 제1법칙을 설명해주세요:**\n[물체, 알짜힘, 운동 상태]",
            'correct_answers': [
                "물체에 작용하는 알짜힘이 0일 때, 물체의 운동 상태가 변하지 않는다",
                "물체에 작용하는 알짜힘이 0이면 물체는 원래의 운동 상태를 유지한다",
                "물체에 작용하는 알짜힘이 0일 때, 물체는 원래의 운동 상태를 유지한다",
                "물체에 알짜힘이 작용하지 않으면, 물체는 원래 하고 있던 운동 상태를 그대로 유지한다",
                "물체는 알짜힘이 0일 때, 현재의 운동 상태를 바꾸지 않고 계속 유지한다",
                "정지해 있던 물체는 계속 정지하고, 운동 중인 물체는 알짜힘이 없을 때 등속 직선 운동을 한다",
                "물체에 작용하는 알짜힘이 없다면, 물체는 관성에 의해 현재의 운동 상태를 그대로 유지하려 한다",
                "물체에 작용하는 알짜힘이 0일 때, 정지해 있는 물체는 계속 정지해 있고, 운동 중인 물체는 계속해서 등속도 운동을 한다",
                "물체에 작용하는 알짜힘이 0일 때, 물체가 현재의 운동 상태를 유지하려는 관성을 갖는다",
                "물체에 알짜힘이 작용하지 않으면 정지 또는 등속도 운동을 한다",
                "물체에 알짜힘이 없을 때 운동상태는 정지 또는 등속도 운동이다"
            ],
            'correct_feedback': "정말 잘 설명했어요!  \n\n뉴턴 제1법칙은 '관성 법칙'이라고도 불러요. 물체가 현재 상태를 유지하려는 성질을 '관성'이라고 하죠.",
            'hint': "알짜힘이 0일 때 물체는 어떻게 될까요? 물체의 운동 상태가 어떻게 변할지(또는 변하지 않을지) 생각해보세요.",
            'evaluation_note': "** 중요 평가 지침: '운동 상태'라는 키워드 자체는 필수가 아닙니다. 대신 '정지', '등속도', '등속 직선 운동' 같은 구체적인 운동 상태를 설명하면 정답으로 인정합니다. 또한 뉴턴 제1법칙은 '관성 법칙', '관성의 법칙' 등으로도 불립니다."
        },
        'Q3': {
            'question': "마지막으로 뉴턴 운동 제2법칙입니다! \n\n**다음 키워드를 참고하여 뉴턴 운동 제2법칙을 설명해주세요:**\n[물체, 알짜힘, 가속도, 질량]",
            'correct_answers': [
                "물체에 작용하는 알짜힘이 클수록 가속도가 크고, 물체의 질량이 클수록 가속도가 작아진다",
                "물체에 작용하는 알짜힘은 물체의 질량과 가속도의 곱과 같다",
                "물체에 작용하는 알짜힘은 가속도와 물체의 질량에 비례한다",
                "물체에 작용하는 알짜힘은 가속도에 비례하고 질량에 비례한다",
                "물체의 가속도는 작용하는 알짜힘에 비례하고 질량에 반비례한다",
                "가속도는 질량이 클수록, 알짜힘이 작을수록 작다",
                "물체에 작용하는 알짜힘은 물체를 가속시키며, 그 크기는 질량과 가속도의 곱으로 나타낼 수 있다",
                "물체의 가속도는 알짜힘에 비례하고 질량에 반비례한다. 즉, 힘이 크면 가속도도 커지고, 질량이 크면 가속도는 작아진다",
                "물체에 알짜힘이 작용하면, 물체는 질량에 반비례하는 크기의 가속도를 얻는다",
                "물체의 운동 상태가 변하는 정도, 즉 가속도는 알짜힘의 크기에 비례하고, 물체의 질량에 따라 그 크기가 달라진다",
                "물체의 속도가 변하는 정도, 즉 가속도는 알짜힘의 크기에 비례하고 물체의 질량에 반비례한다"
            ],
            'correct_feedback': "잘했습니다!  \n\n수식으로 표현하면 F = ma가 되죠. 뉴턴 제2법칙의 핵심은 '가속도가 어떻게 결정되는가'입니다. 같은 힘을 작용해도 질량이 큰 물체는 작은 가속도로, 질량이 작은 물체는 큰 가속도로 운동하게 됩니다.",
            'hint': "알짜힘과 가속도는 어떤 관계가 있을까요? 그리고 질량이 커지면 가속도는 어떻게 될까요? 이 관계를 모두 포함해서 설명해보세요.",
            'evaluation_note': """** 중요 평가 지침: 
1. '물체'라는 키워드 자체는 필수가 아닙니다.
2. "알짜힘은 가속도와 질량에 비례한다" 또는 "F=ma"는 수식적으로는 맞지만, 가속도를 주어로 설명하지 않았습니다.
   → 이 경우 "부분적으로 맞지만 불완전하다"고 판정하고, "F=ma를 잘 설명했네요! 그런데 뉴턴 제2법칙은 가속도가 어떻게 결정되는지를 설명하는 법칙이에요. 가속도 입장에서 다시 생각해볼까요?"와 같이 피드백하세요."""
        },
        'End': {
            'question': "수고하셨습니다! 이제 다음 단계로 넘어갈 준비가 되었습니다.",
            'correct_feedback': None,
            'is_end': True
        }
    }

    def evaluate_answer_with_llm(user_answer, question_type):
        """LLM을 사용하여 학생 답변을 평가하는 함수"""
        try:
            client = OpenAI(api_key=st.session_state.api_key)
            current_q = QUESTIONS[question_type]
            
            # 정답 예시 목록 가져오기
            if 'correct_answers' in current_q:
                correct_answers_text = "\n".join([f"- {ans}" for ans in current_q['correct_answers']])
            else:
                correct_answers_text = "정답 기준이 설정되지 않았습니다."
            
            # 힌트 가져오기
            hint_text = current_q.get('hint', '')
            hint_section = f"\n\n힌트: {hint_text}" if hint_text else ""
            
            # 특별 평가 지침 가져오기
            evaluation_note = current_q.get('evaluation_note', '')
            evaluation_note_section = f"\n\n{evaluation_note}" if evaluation_note else ""
            
            prompt = f"""당신은 물리 교육 평가 전문가입니다. 학생의 답변을 평가해주세요.

문제: {current_q['question']}

정답으로 인정 가능한 답변 예시들:
{correct_answers_text}{hint_section}{evaluation_note_section}

학생 답변: {user_answer}

**⚠️ 평가 전 필수 체크 (가장 우선!):**

**1단계: 질문인지 답변 시도인지 먼저 판단**
- 질문의 본질: 학생이 "무엇인지 모르겠으니 설명해달라"는 의도
- 질문 지표: "뭐예요?", "뭐야?", "정의", "의미", "알려주세요", "설명해주세요", "차이는?" 등
- 내용: 문제에 대한 답변이 아니라, 개념/용어 자체에 대한 질문

**만약 질문이라면:**
- 판정: 오답 (문제 풀이가 아니므로)
- 피드백: **학생이 물어본 질문에 직접 답변하세요**. 학생이 물어본 내용을 정확히 설명하고, 맥락에 따라 자연스럽게 문제로 연결할 수도 있습니다.

**질문 처리 원칙:**
1. ✅ **대부분의 질문은 직접 답변**: 물리 개념, 용어, 원리, 관계에 대한 질문은 모두 직접 설명
   - 예시: "알짜힘이 뭐예요?" → 직접 답변: "알짜힘은 물체에 작용하는 모든 힘을 합친 것이에요. 줄다리기에서 양쪽 힘을 모두 고려한 최종 힘이 바로 알짜힘이죠."
   - 예시: "관성이 뭐예요?" → 직접 답변: "관성은 물체가 현재 운동 상태를 유지하려는 성질이에요. 정지한 물체는 계속 정지하려 하고, 움직이는 물체는 계속 움직이려 하죠."
   - **예시에 없는 질문이 나오면**: 학생의 의도를 파악하고, 물리적 지식을 활용하여 맥락에 맞게 답변해주세요. 질문을 피하거나 다른 내용을 설명하지 마세요.
2. ⚠️ **주의**: 문제의 직접적인 정답은 말하지 마세요. 정답 발문이 아니면, 개념은 설명해도 됩니다.
3. 설명 후 학생이 직접 문제에 적용해보도록 자연스럽게 유도하세요.

**만약 답변 시도라면:**
- 아래 평가 기준에 따라 점수와 피드백 제공

평가 기준:
1. 학생 답변이 물리적으로 올바른 개념을 포함하는가?
2. 정답 예시들과 의미적으로 동일하거나 유사한가?
3. 학생 답변이 키워드를 적절하게 포함하고 있는가?

피드백 작성 규칙 (학생 답변을 고려하여 상황에 맞게):
- 정답이면: 칭찬해주세요
- 오답이면: 
  ⚠️ **절대 금지**: 정답을 직접 말하거나, 정답 예시를 인용하거나, 정확한 답을 암시하지 마세요
  ✅ **반드시 할 것**: 
    1) 학생이 쓴 답변의 어느 부분이 부족한지 구체적으로 짚어주세요
    2) 학생이 다시 생각해볼 수 있도록 질문 형태로 유도하세요
    3) 힌트는 참고만 하고, 힌트를 그대로 반복하지 마세요
    ✅ 학생이 장난스러운 답변을 했다면, 친절하게 진지하게 답변할 것을 권유하세요

**⚠️ 물리와 무관한 답변 처리 (중요!):**

학생이 물리 개념과 무관한 답변을 하면 **절대로** 평가적 표현을 사용하지 마세요:
- ❌ 금지: "개념을 담고 있지 않아요", "개념과 연결되지 않았어요", "문제에서 묻는 것이 아니에요"
- ✅ 필수: **항상 긍정적으로 공감 → 자연스럽게 질문으로 유도**

**상황별 대응 패턴:**
- 인사말("안녕하세요", "하이") → 인사 받아주고 문제로 유도
  예) "반가워요! 😊 지금은 힘에 대해 생각해볼 시간이에요. 여러 힘을 합친 것을 뭐라고 할까요?"

- 모르겠다("모르겠어요", "몰라요") → 괜찮다고 하고 쉽게 접근
  예) "괜찮아요! 천천히 생각해봐요. 🤔 여러 사람이 줄다리기할 때처럼 여러 힘을 하나로 합친 것은 무엇일까요?"

- 장난/감탄사("ㅋㅋㅋ", "ㅎㅎㅎ") → 긍정적으로 받아들이고 진지하게 유도
  예) "재밌나요? 😄 그럼 진지하게 한번 생각해볼까요? 여러 힘의 효과를 하나로 나타낸 힘은 무엇일까요?"

- 짧은 반응("네!", "응", "좋아요") → 의욕 칭찬하고 실제 답변 유도
  예) "의욕이 넘치네요! 😊 그럼 이제 실제로 답을 생각해볼까요? 여러 힘을 하나로 합친 것은 무엇일까요?"

- 무의미한 글자("ㄴ내내낸", "ㅁㄴㅇㄹ") → 답변을 이해 못했다고 하고 다시 유도
  예) "답변을 잘 이해하지 못했어요. 🤔 다시 한번 생각해볼까요? 여러 힘을 하나로 합친 것은 무엇일까요?"

**핵심 원칙: 어떤 답변이든 부정적 평가 없이 긍정적으로 받아들이고, 학생이 질문을 한다면 그에 맞는 대답을 한 후 자연스럽게 문제로 유도하세요.**

다음 형식으로만 답변해주세요:
판정: [정답/오답]
피드백: [세 문장 이내로 작성]"""

            response = client.chat.completions.create(
                model=TUTOR_OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": TUTOR_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=200
            )
            
            evaluation = response.choices[0].message.content
            
            # 판정 결과 추출
            is_correct = "정답" in evaluation.split("\n")[0]
            
            # 피드백 추출
            feedback_lines = evaluation.split("\n")
            feedback = "\n".join(feedback_lines[1:]).replace("피드백:", "").strip()
            
            return is_correct, feedback
            
        except Exception as e:
            st.error(f"답변 평가 중 오류: {str(e)}")
            return False, "평가 중 오류가 발생했습니다."

    def add_message_to_history(role, content, image_path=None):
        """대화 내용을 히스토리에 추가하는 함수"""
        message = {"role": role, "content": content}
        if image_path:  # 이미지 경로가 있을 때만 추가
            message["image"] = image_path
        st.session_state.chat_history.append(message)

    def display_chat_history():
        """대화 기록을 화면에 표시하는 함수"""
        for message in st.session_state.chat_history:
            if message["role"] == "assistant":
                with chat_container.chat_message(message["role"], avatar=AI_AVATAR):
                    st.write(message["content"])
                    # 이미지가 있으면 메시지 바로 아래에 표시
                    if "image" in message and message["image"]:
                        with st.popover("📖 교과서 본문", use_container_width=True):
                            # Q3 이미지(explain_5.png)일 때만 스크롤 안내 표시
                            if "explain_5.png" in message["image"]:
                                st.caption("💡 아래로 스크롤하여 전체 내용을 확인하세요 ⬇️")
                            st.image(message["image"], use_container_width=True, caption="출처: 미래엔 교과서")
            else:
                with chat_container.chat_message(message["role"]):
                    st.write(message["content"])

    def process_answer(user_input):
        """답변을 처리하는 함수"""
        # 사용자 입력을 먼저 대화 기록에 추가
        add_message_to_history("user", user_input)
        
        current_q = QUESTIONS[st.session_state.current_question]
        
        # End 상태면 입력을 처리하지 않음
        if 'is_end' in current_q and current_q['is_end']:
            return
        
        # AI 응답 생성 중 상태 표시
        with status_container:
            st.info("🤔 AI가 답변을 생성중입니다...")
            
        # LLM을 사용한 답변 평가 (정오답 판정 + 피드백을 한 번에 받음)
        is_correct, ai_feedback = evaluate_answer_with_llm(user_input, st.session_state.current_question)
        
        if is_correct:
        # 정답인 경우 - 미리 정의된 상세한 피드백 사용
            feedback = current_q['correct_feedback']
            
            # 정답일 때 이미지와 함께 피드백 추가
            image_path = None
            if st.session_state.current_question == 'Q2':
                image_path = "src/images/explain_4.png"
            elif st.session_state.current_question == 'Q3':
                image_path = "src/images/explain_5.png"
            
            add_message_to_history("assistant", feedback, image_path)
            
            # 다음 문제로 이동
            next_questions = {'Q1': 'Q2', 'Q2': 'Q3', 'Q3': 'End'}
            next_q = next_questions[st.session_state.current_question]
            
            if next_q:
                st.session_state.current_question = next_q
                if next_q != 'End':
                    add_message_to_history("assistant", QUESTIONS[next_q]['question'])
                else:
                    add_message_to_history("assistant", QUESTIONS['End']['question'])
        else:
            # 오답인 경우 - LLM이 생성한 맞춤형 피드백 사용 (힌트 포함)
            add_message_to_history("assistant", ai_feedback)

        # 상태 메시지 제거
        status_container.empty()
        st.rerun()

    # 문제 상태 관리
    if 'current_question' not in st.session_state:
        st.session_state.current_question = 'Q1'
        st.session_state.show_next_button = False
        st.session_state.correct_answer_given = False
        st.session_state.current_tries = 0
        st.session_state.chat_history = []
        st.session_state.is_processing = False
        st.session_state.last_input = None

    # Progress bar 계산 및 표시
    # tab1의 문제들 (Q1, Q2)
    tab1_questions = ['Q1', 'Q2']
    # tab2의 문제들 (Q1, Q2, Q3)
    tab2_questions = list(QUESTIONS.keys())
    tab2_questions.remove('End')

    # 현재 tab 상태 확인
    current_tab = st.session_state.get('current_tab', 'tab1')
    
    # 전체 문제 수 (tab1: 2개 + tab2: 3개 = 5개)
    total_all_questions = len(tab1_questions) + len(tab2_questions)
    
    # 현재 진행 상황 계산
    if current_tab == 'tab1':
        # tab1에서 현재 완료된 문제 수
        completed_tab1 = 0
        if st.session_state.get('q1', False):
            completed_tab1 += 1
        if st.session_state.get('q2', False):
            completed_tab1 += 1
        
        # tab2는 아직 시작하지 않았으므로 tab1 완료 문제만 계산
        current_progress = completed_tab1
    else:  # tab2
        # tab1 완료 여부 확인
        completed_tab1 = 0
        if st.session_state.get('q1', False):
            completed_tab1 += 1
        if st.session_state.get('q2', False):
            completed_tab1 += 1
        
        # tab2에서 현재 완료된 문제 수 (End 상태는 완료로 간주)
        if st.session_state.current_question == 'End':
            completed_tab2 = len(tab2_questions) - 1  # End를 제외한 모든 문제 완료
        else:
            current_question_index = tab2_questions.index(st.session_state.current_question)
            completed_tab2 = current_question_index
        
        current_progress = completed_tab1 + completed_tab2
    
    progress = current_progress / total_all_questions

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
        st.markdown("⏳ 들어가기 진행률")
        st.progress(progress, text=f"진행률: {progress*100:.0f}% ({current_progress}/{total_all_questions})")

    # 대화 내용을 표시할 컨테이너와 상태 메시지를 위한 컨테이너
    chat_container = st.container()
    status_container = st.empty()

    # 현재 문제 표시
    current_q = QUESTIONS[st.session_state.current_question]

    # 초기 메시지 추가 (한 번만)
    if len(st.session_state.chat_history) == 0:
        add_message_to_history("assistant", current_q['question'])

    # 채팅 히스토리 표시 (한 곳에서만 호출)
    display_chat_history()

    # 현재 문제가 End 상태인지 확인
    is_end = 'is_end' in current_q and current_q['is_end']

    # End 상태일 때 balloons 효과 표시
    if is_end:
        st.success("축하합니다!")
        if not st.session_state.balloons_done:
            st.balloons()
            st.session_state.balloons_done = True

    # End 상태일 때는 입력창을 비활성화
    placeholder = "질문에 대한 답변을 작성해주세요." if not is_end else "복습이 완료되었습니다."
    if user_input := st.chat_input(placeholder, key="qa_chat_input", disabled=is_end):
        process_answer(user_input)

    # 다음 단계로 버튼
    col1, col2, col3 = st.columns([5, 2, 2])
    with col3:
        if is_end:
            if st.button(
                label="다음단계로",
                icon="⏩",
                help="생각하기로 이동하기",
                type="primary"
            ):
                st.switch_page("pages_group/02_생각하기.py")


#####################################
########### Sibebar Logic ###########
#####################################
# with st.sidebar:

#     st.write("⏬ 혼자서 문제 풀기 너무 어렵다면? ⏬")

#     toggle_ai_helper = st.toggle("**교과서 찾기** 사용하기", value=False)

#     if toggle_ai_helper:

#         st.warning("단, 스스로 충분히 고민해도 정말 모르겠을 때 사용하기!")

#         st.text("교과서와 '대화'해봅시다")
#         messages = st.container(height=300)
            
#         def print_messages():
#             for chat_message in st.session_state["intro_1_tutor_messages"]:
#                 messages.chat_message(chat_message.role).write(chat_message.content)

#         # 새로운 메시지를 추가
#         def add_message(role, message):
#             st.session_state["intro_1_tutor_messages"].append(ChatMessage(role=role, content=message))

#         # 이전 대화 기록 출력
#         print_messages()

#         if user_input := st.chat_input("궁금한 내용을 물어보세요!", key="pdf_chat_input"):

#             chain = st.session_state["pdf_chain"]

#             if chain is not None:
#                 # 사용자의 입력
#                 messages.chat_message("user").write(user_input)
#                 # 스트리밍 호출
#                 response = chain.stream(user_input)
#                 with messages.chat_message("assistant"):
#                     # 빈 공간(컨테이너)을 만들어서, 여기에 토큰을 스트리밍 출력한다.
#                     container = st.empty()

#                     ai_answer = ""
#                     for token in response:
#                         ai_answer += token
#                         container.markdown(ai_answer)

#                 # 대화기록을 저장한다.
#                 add_message("user", user_input)
#                 add_message("assistant", ai_answer)
