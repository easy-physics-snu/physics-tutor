import os
import streamlit as st
import time
# # from pydantic import BaseModel, Field
# from langchain_core.messages.chat import ChatMessage
# from langchain_core.runnables.history import RunnableWithMessageHistory
# from langchain_core.chat_history import BaseChatMessageHistory
# from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
# from langchain_community.chat_message_histories import ChatMessageHistory
# from langchain_openai import ChatOpenAI #, OpenAIEmbeddings

# from modules.retrieval import create_chain

# # from langchain_teddynote import logging
from openai import OpenAI

st.session_state.api_key = st.secrets["openai_api_key"]

# 각 사용자별 고유 세션 ID 생성
if "unique_session_id" not in st.session_state:
    import uuid
    st.session_state["unique_session_id"] = str(uuid.uuid4())

# 대화 기록 초기화 (적용하기 페이지 전용)
if "chat_history_applying" not in st.session_state:
    st.session_state["chat_history_applying"] = []

if "show_answer" not in st.session_state:
    st.session_state["show_answer"] = False

if "last_submission_time" not in st.session_state:
    st.session_state["last_submission_time"] = 0

if "score" not in st.session_state:
    st.session_state["score"] = 0

if "missing_contents" not in st.session_state:
    st.session_state["missing_contents"] = ""

if "incorrect_contents" not in st.session_state:
    st.session_state["incorrect_contents"] = ""

# 메인 페이지 하단 리소스 섹션 노출 플래그
if "show_resources" not in st.session_state:
    st.session_state["show_resources"] = False

if "conversation_completed" not in st.session_state:
    st.session_state["conversation_completed"] = False

if "completion_balloons_done" not in st.session_state:
    st.session_state["completion_balloons_done"] = False

if "is_processing" not in st.session_state:
    st.session_state["is_processing"] = False

if "final_answer_submitted" not in st.session_state:
    st.session_state["final_answer_submitted"] = False


TUTOR_OPENAI_MODEL = "gpt-4.1-mini"
SIDEBAR_AI_AVATAR = "src/images/ai_tutor_avatar.png"

os.environ["LANGCHAIN_TRACING_V2"] = st.secrets["LANGCHAIN_TRACING_V2"]
os.environ["LANGCHAIN_API_KEY"] = st.secrets["LANGCHAIN_API_KEY"]
os.environ["LANGCHAIN_ENDPOINT"] = st.secrets["LANGCHAIN_ENDPOINT"]
os.environ["LANGCHAIN_PROJECT"] = st.secrets["LANGCHAIN_PROJECT"]

# 캐시 디렉토리 생성
if not os.path.exists(".cache"):
    os.mkdir(".cache")


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


######################################
########### Mainpage Logic ###########
######################################
st.title("적용하기 💡")
st.info("- 배운 내용을 새로운 상황에 적용해보며 개념을 더 깊게 이해해봅시다. \n - 지구 주위를 도는 달의 모습을 관찰해보고 그 이유를 설명해보세요. \n - 좌측 사이드바의 🧑🏻‍🏫**AI 선생님**과 대화하며 내 이해를 확인해보세요.")

with st.container(border=True):
    st.markdown(body="""
    ## 등속 원운동

    놀이공원의 회전하는 관람차, 지구 주위를 도는 인공위성, 시계의 바늘 등은 일정한 속력으로 원을 그리며 운동하는데, 이러한 운동을 등속 원운동이라고 한다.
    등속 원운동 하는 물체는 속력이 변하지 않고 운동 방향만 변한다. (미래엔 교과서 16쪽)
    """)

st.image("https://bobmoler.wordpress.com/wp-content/uploads/2019/03/orbit_360p30-1.gif", caption="지구 주위를 도는 달의 모습")

# 적용 질문
applyingQuestion = "위 그림과 같이 달이 공전 궤도를 유지하면서 계속 지구를 돌 수 있는 이유는 무엇일까요?"

# 적용하기 모범답안 (나중에 DB에서 불러오면 좋을 듯)
applyingModeledAnswer = [
    "지구가 달에 지구 중심방향으로 향하는 힘(중력)을 작용하고 있어서, 달은 지구 주변을 계속 원운동할 수 있습니다.",
    "지구의 중력이 구심력으로 작용하여 달이 계속 원운동을 할 수 있습니다.",
    "지구가 달을 끌어당기는 중력이 작용하고 있어서, 달은 공전 궤도를 유지할 수 있습니다.",
    "중력이 구심력 역할을 하여 달이 지구 주변을 원운동할 수 있습니다.",
    "지구 중심 방향으로 중력이 작용해서 달이 등속 원운동을 유지할 수 있습니다.",
    "지구가 달에 지구 중심 방향으로 중력을 작용하고, 이 힘이 달의 원운동을 가능하게 합니다.",
    "달에 작용하는 지구의 중력(구심력) 때문에 달은 궤도를 이탈하지 않고 계속 공전할 수 있습니다.",
    "달과 지구 사이의 만유인력(중력) 때문에 달이 지구 중심 방향으로 힘을 받아 원운동 하게 됩니다."
]

# 핵심 개념(나중엔 DB에서 불러오면 좋을 듯)
essential_contents = "등속 원운동"

# AI 튜터의 시스템 프롬프트
TUTOR_SYSTEM_PROMPT = """당신은 친근하고 대화형 학습을 돕는 **물리 튜터**입니다. 항상 존댓말을 사용하며 긍정적이고 격려하는 태도로 일관된 대화를 유지하세요.

다음 지침을 따라주세요:
1. 학생이 이해한 부분과 부족한 부분을 파악합니다.
2. 부족한 부분에 대해 다시 생각해볼 수 있도록 질문이나 힌트를 제공합니다.
3. ⚠️ **절대 금지**: 정답을 직접 말하거나, 정답 예시를 언급하거나, 정확한 답을 암시하지 마세요.
4. 학생이 장난스럽거나 부적절한 답변을 하더라도, 교육자로서 차분하고 친절하게 진지한 답변을 권유하세요.
5. 세 문장을 넘지 않도록 간결하게 대화를 생성하세요.
6. 이모지를 적절히 사용하여 친근감을 줍니다."""


def format_conversation_history():
    """대화 기록을 텍스트로 포맷팅"""
    if not st.session_state.chat_history_applying:
        return ""
    
    history_text = "\n\n=== 이전 대화 기록 ===\n"
    for msg in st.session_state.chat_history_applying:
        role = "학생" if msg["role"] == "user" else "AI 선생님"
        history_text += f"{role}: {msg['content']}\n"
    return history_text


def evaluate_answer_with_llm(user_answer):
    """LLM을 사용하여 학생 답변을 평가하는 함수"""
    try:
        client = OpenAI(api_key=st.session_state.api_key)
        
        # 정답 예시 목록
        correct_answers_text = "\n".join([f"- {ans}" for ans in applyingModeledAnswer])
        
        # 대화 기록 컨텍스트
        conversation_history = format_conversation_history()
        
        prompt = f"""당신은 물리 교육 평가 전문가입니다. 학생의 답변을 평가해주세요.

문제: {applyingQuestion}
학생의 현재 답변: {user_answer}

정답으로 인정 가능한 답변 예시들:
{correct_answers_text}

{conversation_history}

**⚠️ 평가 전 필수: 학생이 실제로 쓴 단어를 정확히 확인하세요!**

**평가 기준 (각 항목을 독립적으로, 단어 단위로 체크):**

1. **중력/힘 언급** 체크:
   ✅ 명시적 언급: "중력", "만유인력", "힘" 단어가 포함되어 있으면 O
      → "중력을", "중력이", "중력 작용", "힘이", "힘을" 등 모두 인정
   ✅ 구심력: "구심력" (있어도 OK, 없어도 OK - 선택적)
   ⚠️ 암묵적만: "끌어당기다", "당기다"만 있고 구체적 힘 이름 없음 → 불충분
   ❌ 없음: 어떤 힘도 언급 안 함

2. **방향 언급** 체크:
   ✅ 있음: "지구 중심", "지구의 중심", "지구 방향", "지구중심" (띄어쓰기 무관)
   ❌ 틀림: "달 중심", "달의 중심" → 치명적 오류!
   ❌ 없음: 방향 언급 전혀 없음

3. **원운동 언급** 체크:
   ✅ 있음: "원운동" 단어가 포함되어 있으면 무조건 O
      → "원운동해요", "원운동합니다", "원운동을", "원운동한다" 등 모두 인정
   ✅ 대체 표현: "공전", "돈다", "돌", "궤도" 등도 인정
   ❌ 없음: 운동 결과 언급 전혀 없음


**🎯 평가 예시 (정확히 이 패턴을 따르세요):**

예시 1:
학생: "달이 지구 중심 방향으로 끌어당겨져서 원운동을 합니다"
분석: 방향 O, 원운동 O, 중력 △ ("끌어당겨"만으로는 불충분)
점수: 65점
놓친개념: [중력, 만유인력 같은 구체적인 힘의 이름]
피드백: "방향과 운동은 잘 설명했어요! 그런데 달을 끌어당기는 힘은 구체적으로 어떤 힘일까요? 🤔"

예시 2:
학생: "지구의 중력 때문에 달이 원운동을 합니다"
분석: 중력 O, 원운동 O, 방향 X
점수: 70점
놓친개념: [지구 중심 방향]
피드백: "중력 개념은 잘 이해하고 있네요! 그런데 그 중력은 어느 방향으로 작용할까요? 🧭"

예시 3:
학생: "지구가 달에 지구 중심 방향으로 중력을 작용합니다"
분석: 중력 O, 방향 O, 원운동 X
점수: 85점
놓친개념: [원운동]
피드백: "중력과 방향은 완벽해요! 그런데 이 힘이 달의 운동에 어떤 영향을 주나요? 달이 계속 어떤 운동을 할 수 있게 하나요? 🌙"

예시 4:
학생: "달이 지구 주위를 계속 돌아요"
분석: 원운동 O, 중력 X, 방향 X
점수: 40점
놓친개념: [중력, 지구 중심 방향으로 작용하는 힘]
피드백: "달이 지구 주위를 도는 것은 맞아요! 그런데 왜 달이 계속 돌 수 있을까요? 어떤 힘이 작용하고 있을까요? 💪"

예시 5:
학생: "지구가 달에 지구 중심 방향으로 중력을 작용하고 있어서, 달은 지구 주변을 계속 원운동할 수 있습니다"
분석: 중력 O, 방향 O, 원운동 O
점수: 95점
놓친개념: []
피드백: "완벽합니다! 모든 핵심 개념을 잘 이해하고 있네요! 👏"

예시 6 (짧은 표현):
학생: "지구가 달에 지구 중심방향으로 중력을 작용해서 달이 원운동해요"
분석: 중력 O ("중력을 작용"), 방향 O ("지구 중심방향"), 원운동 O ("원운동해요")
점수: 95점
놓친개념: []
피드백: "완벽합니다! 간결하면서도 모든 핵심을 담았네요! 👏"

예시 7 (띄어쓰기 변형):
학생: "지구중심방향으로 중력이 작용해서 원운동합니다"
분석: 중력 O ("중력이"), 방향 O ("지구중심방향"), 원운동 O ("원운동합니다")
점수: 95점
놓친개념: []
피드백: "훌륭해요! 핵심 개념을 정확하게 설명했습니다! 👏"


**⚠️ 물리와 무관한 답변 처리 (중요!):**

학생이 물리 개념과 무관한 답변을 하면 **절대로** 평가적 표현을 사용하지 마세요:
- ❌ 금지: "개념을 담고 있지 않아요", "개념과 연결되지 않았어요", "문제에서 묻는 것이 아니에요"
- ✅ 필수: **항상 긍정적으로 공감 → 자연스럽게 질문으로 유도**

**상황별 대응 패턴:**
- 인사말("안녕하세요", "하이") → 인사 받아주고 문제로 유도
  예) "반가워요! 😊 지금은 달의 운동에 대해 생각해볼 시간이에요. 왜 달이 지구 주위를 계속 돌 수 있을까요?"

- 모르겠다("모르겠어요", "몰라요") → 괜찮다고 하고 쉽게 접근
  예) "괜찮아요! 천천히 생각해봐요. 🤔 시뮬레이션을 다시 보면서 달이 어떻게 움직이는지 관찰해볼까요?"

- 장난/감탄사("ㅋㅋㅋ", "ㅎㅎㅎ") → 긍정적으로 받아들이고 진지하게 유도
  예) "재밌나요? 😄 그럼 진지하게 한번 생각해볼까요? 달이 계속 공전하는 이유는 무엇일까요?"

- 짧은 반응("네!", "응", "좋아요") → 의욕 칭찬하고 실제 답변 유도
  예) "의욕이 넘치네요! 😊 그럼 이제 실제로 답을 생각해볼까요? 달이 지구 주위를 계속 도는 이유는 무엇일까요?"

- 무의미한 글자("ㄴ내내낸", "ㅁㄴㅇㄹ") → 답변을 이해 못했다고 하고 다시 유도
  예) "답변을 잘 이해하지 못했어요. 🤔 다시 한번 생각해볼까요? 달이 원운동을 하는 이유는 무엇일까요?"

**핵심 원칙: 어떤 답변이든 부정적 평가 없이 긍정적으로 받아들이고, 자연스럽게 문제로 유도하세요.**
점수는 0-5점, 놓친개념은 [중력, 지구 중심 방향, 원운동]


**점수 가이드라인:**
- 95-100점: 3개 모두 포함 (완벽!)
- 80-94점: 중력 + 방향 포함 (합격!)
- 60-79점: 중 1-2개만 포함
- 40-59점: 1개 또는 매우 불충분
- 0-39점: 거의 없음 또는 "달 중심" 치명적 오류


**🚨 중요 (반드시 준수):**
1. **단어 포함 여부만 체크**: 
   - "원운동" 단어가 있으면 → 원운동 O
   - "중력" 단어가 있으면 → 중력 O
   - "지구 중심" 또는 "지구중심"이 있으면 → 방향 O
   - 띄어쓰기, 조사(-을/-를/-이/-가/-해요/-합니다) 무관!

2. **"구심력"은 선택적** → missing_contents에 절대 포함 금지!

3. **"끌어당기다"만으로는 불충분** → "중력" 같은 구체적 힘 이름 필요

4. **피드백은 학생이 쓴 단어를 활용**하고, 부족한 부분을 질문으로 유도


다음 형식으로만 답변해주세요:
판정: [정답/오답/부분정답]
점수: [0-100]
놓친개념: [학생이 쓰지 않은 필수 개념만, 구심력은 절대 포함 금지. 없으면 빈 괄호만 표시: []]
잘못된개념: [달 중심 같은 물리적 오류만. 없으면 빈 괄호만 표시: []]
피드백: [위 예시 패턴을 따라, 구체적이고 질문 형태로, 세 문장 이내]"""

        response = client.chat.completions.create(
            model=TUTOR_OPENAI_MODEL,
            messages=[
                {"role": "system", "content": TUTOR_SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=400
        )
        
        evaluation = response.choices[0].message.content
        print("=== LLM 평가 결과 ===")
        print(evaluation)
        print("=" * 50)
        
        # 파싱
        lines = evaluation.split("\n")
        is_correct = "정답" in lines[0]
        score = 0
        missing = ""
        incorrect = ""
        feedback = ""
        
        for line in lines:
            if line.startswith("점수:"):
                try:
                    score = int(line.split(":")[1].strip())
                except:
                    score = 0
            elif line.startswith("놓친개념:"):
                missing = line.split(":", 1)[1].strip()
            elif line.startswith("잘못된개념:"):
                incorrect = line.split(":", 1)[1].strip()
            elif line.startswith("피드백:"):
                feedback = line.split(":", 1)[1].strip()
        
        # 여러 줄 피드백 처리
        if not feedback:
            feedback_start = False
            feedback_lines = []
            for line in lines:
                if line.startswith("피드백:"):
                    feedback_start = True
                    feedback_lines.append(line.split(":", 1)[1].strip())
                elif feedback_start and line.strip():
                    feedback_lines.append(line.strip())
            feedback = "\n".join(feedback_lines)
        
        return is_correct, score, missing, incorrect, feedback
        
    except Exception as e:
        st.error(f"답변 평가 중 오류: {str(e)}")
        return False, 0, "", "", "평가 중 오류가 발생했습니다."


def add_message_to_history(role, content):
    """대화 내용을 히스토리에 추가하는 함수"""
    message = {"role": role, "content": content}
    st.session_state.chat_history_applying.append(message)


def display_chat_history():
    """대화 기록을 화면에 표시하는 함수"""
    for message in st.session_state.chat_history_applying:
        if message["role"] == "assistant":
            with messages.chat_message(message["role"], avatar=SIDEBAR_AI_AVATAR):
                st.write(message["content"])
        else:
            with messages.chat_message(message["role"]):
                st.write(message["content"])


def process_answer(user_input):
    """답변을 처리하는 함수"""
    # 처리 중 플래그 설정
    if st.session_state["is_processing"]:
        return
    
    st.session_state["is_processing"] = True
    
    # 사용자 입력을 먼저 대화 기록에 추가
    add_message_to_history("user", f"(제출한 답변): {user_input}")
    
    # End 상태면 입력을 처리하지 않음
    if st.session_state.get("conversation_completed", False):
        st.session_state["is_processing"] = False
        return
    
    # AI 응답 생성 중 상태 표시
    with status_container:
        st.info("🤔 AI가 답변을 평가하고 있습니다...")
    
    # LLM을 사용한 답변 평가
    is_correct, score, missing, incorrect, ai_feedback = evaluate_answer_with_llm(user_input)
    
    # 세션 상태 업데이트
    st.session_state["score"] = score
    st.session_state["missing_contents"] = missing
    st.session_state["incorrect_contents"] = incorrect
    
    # 점수에 따른 처리
    if score >= 80:
        # 정답! 완료 메시지
        stars = "⭐⭐⭐⭐⭐"
        completion_msg = f"**현재 점수: {stars}**\n\n축하합니다!🎉 충분히 잘 이해하셨네요. 모범 답안은 다음과 같습니다.\n\n[**{applyingModeledAnswer[0]}**]"
        
        # missing_contents가 실제로 있는 경우만 표시
        missing_clean = missing.strip().strip("[]").strip()
        if missing_clean and missing_clean.lower() not in ["없음", "none", ""]:
            completion_msg += f"\n\n지금 답변에서 [{missing_clean}] 도 고려하면 더 완벽한 답변이 될 거예요."
        
        completion_msg += "\n\n메인 화면의 답변 작성란에 최종 답안을 다시 작성해보세요!"
        
        add_message_to_history("assistant", completion_msg)
        
        # 대화 종료 플래그 설정
        st.session_state["conversation_completed"] = True
    else:
        # 80점 미만 - 피드백 제공
        stars = score_to_stars(score)
        feedback_msg = f"**현재 점수: {stars}**\n\n{ai_feedback}"
        add_message_to_history("assistant", feedback_msg)
    
    # 상태 메시지 제거
    status_container.empty()
    st.session_state["is_processing"] = False
    st.rerun()


# 메인 화면
if not st.session_state.get("show_resources", False):
    # 메인 화면에 질문 표시
    st.markdown("**문제 상황**")
    st.markdown(applyingQuestion)

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

    # 최종 답안 제출 완료 후 "더 알아보기" 버튼 표시 (메인 화면)
    if st.session_state.get("final_answer_submitted", False) and not st.session_state.get("show_resources", False):
        # 풍선 효과 (한 번만)
        if not st.session_state.get("completion_balloons_done", False):
            st.balloons()
            st.session_state["completion_balloons_done"] = True
        
        st.markdown("---")
        st.markdown("### 🎉 축하합니다! '더 알아보기' 버튼을 눌러 비슷한 사례를 확인하고 오늘 수업을 마무리해보세요")
        if st.button("📚 더 알아보기", type="primary", use_container_width=True, key="main_show_resources_button"):
            st.session_state["show_resources"] = True
            st.rerun()
    
    # 답변 입력 영역 표시 (대화가 완료되지 않았거나, 완료되었지만 최종 답안을 아직 제출하지 않은 경우)
    elif not st.session_state.get("final_answer_submitted", False):
        # 답변 입력 영역
        text_area_key = st.session_state.get("text_area_key", 0)
        reason = st.text_area(
            label="내 답변을 작성해주세요.",
            height=200,
            key=f"text_area_{text_area_key}"
        )

        submit_button = st.button(
            label="제출하기",
            type="primary",
            use_container_width=True
        )

        if submit_button:
            current_time = time.time()
            
            # 답변이 비어있으면 경고
            if not reason or not reason.strip():
                st.warning("답변을 작성해주세요.")
            # 같은 답변이 연속으로 제출되는 것을 방지 (5초 이내 중복 제출 방지)
            elif current_time - st.session_state.get("last_submission_time", 0) < 5:
                st.warning("잠시 후 다시 시도해주세요.")
            else:
                # 대화 완료 상태에서 제출 = 최종 답안 재제출
                if st.session_state.get("conversation_completed", False):
                    st.session_state["final_answer_submitted"] = True
                    st.session_state["text_area_key"] = st.session_state.get("text_area_key", 0) + 1
                    st.session_state["last_submission_time"] = current_time
                    st.rerun()
                else:
                    # 일반 제출
                    st.session_state["last_user_input"] = reason
                    st.session_state["submission_triggered"] = True
                    st.session_state["text_area_key"] = st.session_state.get("text_area_key", 0) + 1
                    st.session_state["last_submission_time"] = current_time
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
########### Sidebar Logic ###########
#####################################
with st.sidebar:
    st.write("**AI 선생님**의 피드백")
    messages = st.container(height=400)
    status_container = st.empty()

    # 초기 메시지 추가 (한 번만)
    if len(st.session_state.chat_history_applying) == 0:
        add_message_to_history("assistant", "마지막으로, 배운 내용을 새로운 상황에 적용해봅시다.")

    # 채팅 히스토리 표시
    display_chat_history()

    # 제출 트리거 처리
    if st.session_state.get("submission_triggered", False):
        st.session_state["submission_triggered"] = False
        if "last_user_input" in st.session_state:
            process_answer(st.session_state["last_user_input"])
    
    # 사이드바 채팅 입력창 (대화가 시작되었고 아직 완료되지 않은 경우)
    if (len(st.session_state.chat_history_applying) > 0 and 
        not st.session_state.get("conversation_completed", False)):
        
        if user_input := st.chat_input("AI 선생님과 대화를 계속하세요...", key="sidebar_chat_input"):
            process_answer(user_input)
