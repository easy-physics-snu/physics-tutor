import os
import streamlit as st
import time
import uuid
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

from i18n import ai_language_instruction, get_locale, lt, t
from i18n.navigation import switch_to_locale_home
# DynamoDB 관련 import 추가
from modules.dynamo import initialize_session
from modules.evaluation import (
    build_application_evaluation_prompt,
    format_concepts,
    parse_application_evaluation,
)

# 로그인 상태 확인
if "logged_in" not in st.session_state or not st.session_state.logged_in or st.session_state.get("user_id") is None:
    st.error(t("auth.required"))
    if st.button(t("auth.go_main")):
        switch_to_locale_home()
    st.stop()

st.session_state.api_key = st.secrets["openai_api_key"]

# 각 사용자별 고유 세션 ID 생성
if "unique_session_id" not in st.session_state:
    st.session_state["unique_session_id"] = st.session_state.get("session_uuid", str(uuid.uuid4()))

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
    st.session_state["missing_contents"] = []

if "incorrect_contents" not in st.session_state:
    st.session_state["incorrect_contents"] = []

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

if "show_sidebar_balloons" not in st.session_state:
    st.session_state["show_sidebar_balloons"] = False

# 대화 턴 추적을 위한 변수 추가
if "phase5_current_turn" not in st.session_state:
    st.session_state["phase5_current_turn"] = 0

##TODO 민선쌤 성능 이슈로 gpt-4.1 모델로 바꿨어요~
TUTOR_OPENAI_MODEL = "gpt-4.1"
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

#--------------------------------#
#            DynamoDB 설정        #
#--------------------------------#
def save_message_to_db(role: str, content: str, content_type: str = "text", llm_model: str = None, turn: int = None):
    """
    메시지를 DynamoDB에 저장
    """
    if not st.session_state.get("phase5_manager"):
        return False
    
    if not st.session_state.get("session_uuid"):
        return False
    
    # turn이 제공되지 않으면 현재 턴 사용
    if turn is None:
        turn = st.session_state.get("phase5_current_turn", 0)
    
    try:
        success = st.session_state["phase5_manager"].save_phase_message(
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

# Phase 5 페이지 초기화
initialize_session(phase_num=5)

######################################
########### Mainpage Logic ###########
######################################
st.title(lt("적용하기 💡", "Apply 💡"))
st.info(lt("- 배운 내용을 새로운 상황에 적용해보며 개념을 더 깊게 이해해봅시다. \n - 지구 주위를 도는 달의 모습을 관찰해보고 그 이유를 설명해보세요. \n - 좌측 사이드바의 🧑🏻‍🏫**AI 선생님**과 대화하며 내 이해를 확인해보세요.", "- Apply what you've learned to new situations to deepen your understanding of the concepts. \n - Observe the Moon orbiting the Earth and explain why it behaves that way. \n - Chat with the 🧑🏻‍🏫**AI Tutor** in the left sidebar to check your understanding."))

with st.container(border=True):
    st.markdown(body=lt("""
    ## 등속 원운동

    놀이공원의 회전하는 관람차, 지구 주위를 도는 인공위성, 시계의 바늘 등은 일정한 속력으로 원을 그리며 운동하는데, 이러한 운동을 등속 원운동이라고 한다.
    등속 원운동 하는 물체는 속력이 변하지 않고 운동 방향만 변한다. (미래엔 교과서 16쪽)
    """, """
    ## Uniform Circular Motion

    A Ferris wheel at an amusement park, a satellite orbiting the Earth, and the hands of a clock all move in a circular path at a constant speed. This type of motion is called uniform circular motion.
    In uniform circular motion, the speed of an object does not change — only its direction of motion changes. (Textbook p. 16)
    """))

st.image("https://bobmoler.wordpress.com/wp-content/uploads/2019/03/orbit_360p30-1.gif", caption=lt("지구 주위를 도는 달의 모습", "Moon's Orbit"))

# 적용 질문
applyingQuestion = lt("위 그림과 같이 달이 공전 궤도를 유지하면서 계속 지구를 돌 수 있는 이유는 무엇일까요?", "As shown in the figure above, why is the Moon able to maintain its orbital path and keep orbiting the Earth?")

# 적용하기 모범답안 (나중에 DB에서 불러오면 좋을 듯)
applyingModeledAnswer = [
    lt("지구가 달에 지구 중심방향으로 향하는 힘(중력)을 작용하고 있어서, 달은 지구 주변을 계속 원운동할 수 있습니다.", "Because Earth exerts a gravitational force on the Moon directed toward Earth's center, the Moon is able to continuously orbit the Earth."),
    lt("지구의 중력이 구심력으로 작용하여 달이 계속 원운동을 할 수 있습니다.", "Earth's gravity acts as centripetal force, allowing the Moon to continuously undergo circular motion."),
    lt("지구가 달을 끌어당기는 중력이 작용하고 있어서, 달은 공전 궤도를 유지할 수 있습니다.", "Because the gravitational force that pulls the Moon toward Earth is acting, the Moon is able to maintain its orbital path."),
    lt("중력이 구심력 역할을 하여 달이 지구 주변을 원운동할 수 있습니다.", "Gravity acts as centripetal force, allowing the Moon to orbit the Earth in circular motion."),
    lt("지구 중심 방향으로 중력이 작용해서 달이 등속 원운동을 유지할 수 있습니다.", "Because gravity acts in the direction of Earth's center, the Moon is able to maintain uniform circular motion."),
    lt("지구가 달에 지구 중심 방향으로 중력을 작용하고, 이 힘이 달의 원운동을 가능하게 합니다.", "Earth exerts gravity on the Moon directed toward Earth's center, and this force enables the Moon's circular motion."),
    lt("달에 작용하는 지구의 중력(구심력) 때문에 달은 궤도를 이탈하지 않고 계속 공전할 수 있습니다.", "Due to Earth's gravity (centripetal force) acting on the Moon, the Moon is able to keep orbiting without leaving its orbit."),
    lt("달과 지구 사이의 만유인력(중력) 때문에 달이 지구 중심 방향으로 힘을 받아 원운동 하게 됩니다.", "Due to the gravitational force (universal gravitation) between the Moon and Earth, the Moon receives a force directed toward Earth's center and undergoes circular motion.")
]

# 핵심 개념(나중엔 DB에서 불러오면 좋을 듯)
essential_contents = lt("등속 원운동", "uniform circular motion")

# AI 튜터의 시스템 프롬프트
TUTOR_SYSTEM_PROMPT = lt("""당신은 친근하고 대화형 학습을 돕는 **물리 튜터**입니다. 항상 존댓말을 사용하며 긍정적이고 격려하는 태도로 일관된 대화를 유지하세요.

다음 지침을 따라주세요:

**📝 학생의 답변 시도 (문제 풀이)일 때:**
1. 학생이 이해한 부분과 부족한 부분을 파악합니다.
2. 부족한 부분에 대해 다시 생각해볼 수 있도록 질문이나 힌트를 제공합니다.
3. ⚠️ **절대 금지**: 문제의 정답을 직접 말하거나, 정답 예시를 언급하거나, 정확한 답을 암시하지 마세요.

**❓ 학생의 질문 (개념/용어 설명 요청)일 때:**

⚠️ **중요: 질문과 답변 시도를 구분하세요!**

**판단 원칙 (의도를 분석하세요):**

**질문의 본질:**
- 학생의 의도: "나에게 정보/지식을 제공해줘", "설명해줘", "가르쳐줘"
- 형태 특징: 
  * 질문문(?, 무엇, 왜, 어떻게 등)을 포함하거나
  * 설명/정보 요청 표현("알려주세요", "설명해줘", "정의", "의미", "차이" 등)
- 목적: 개념/용어/원리에 대한 이해를 얻으려는 것
- 내용: 문제에 대한 답변이 아니라, 개념 자체에 대한 질문

**답변 시도의 본질:**
- 학생의 의도: "문제에 대한 내 답을 평가해줘"
- 형태 특징: 서술문 형태, 문제의 정답을 시도하는 문장
- 목적: 문제 풀이의 정확성을 확인받으려는 것
- 내용: 문제 상황(달의 원운동)에 대한 설명을 시도

**판단 기준 (의도를 먼저 파악):**
1. 학생이 "무엇인지 모르겠으니 설명해달라"는 의도인가? → 질문 (개념 설명 제공)
2. 학생이 "내가 쓴 답이 맞는지 확인받고 싶다"는 의도인가? → 답변 시도 (평가 제공)
3. 학생의 문장이 개념/용어 자체를 묻는가? → 질문
4. 학생의 문장이 문제 상황에 대한 해석을 시도하는가? → 답변 시도

**예외 상황 대응:**
- 명확하지 않은 경우: 학생의 의도를 가장 그럴듯하게 해석하되, 질문형 표현이 조금이라도 있으면 질문으로 판단하는 것이 안전합니다.
- 애매한 표현: "원운동이 필요해요" 같은 경우, 문맥상 답변 시도일 가능성이 높지만, 확실하지 않으면 질문으로 판단 후 친절하게 안내하세요.

질문으로 판단되면 → **학생의 질문에 직접 답변하고**, 맥락에 따라 자연스럽게 처리하세요
답변 시도로 판단되면 → 위의 "📝 학생의 답변 시도" 규칙 적용

**질문 처리 원칙 (명확하게):**

**핵심 원칙:**

1. ✅ **대부분의 질문은 직접 답변**: 물리 개념, 용어, 원리, 관계에 대한 질문은 모두 직접 답변
   - 일반 개념 질문 예시:
     * "중력이 알짜힘이 되나요?" → 직접 답변: "네, 맞아요! 달에 작용하는 알짜힘은 지구가 달에 작용하는 중력이에요. 달에는 이 중력만 작용하므로 중력이 바로 알짜힘이죠. 😊"
     * "구심력이 알짜힘인가요?" → 직접 답변
     * "중력과 만유인력의 차이는?" → 직접 답변
     * "원운동의 정의는?" → 직접 답변
     * "등속 원운동이 뭐예요?" → 직접 답변
     * "중력의 단위는?" → 직접 답변
     * "중력이 뭐예요?" → 직접 답변
     * 기타 모든 물리 개념 질문 → 직접 답변
   - **예시에 없는 질문이 나오면**: 학생의 의도를 파악하고, 물리적 지식을 활용하여 맥락에 맞게 답변해주세요. 질문을 피하거나 다른 내용을 설명하지 마세요.

2. ⚠️ **매우 제한적인 예외**: 이 문제의 **구체적인 정답**을 직접 묻는 질문만 유도
   - 이 문제의 정답 = "지구 중심 방향", "중력", "원운동" 중 어느 것인지 직접 묻는 질문
   - 판단 기준: 질문이 **이 문제의 구체적인 답(방향, 힘의 이름, 운동 결과)**을 묻는 경우만 유도
   - 예시:
     - ✅ 유도: "중력은 어느 방향으로 작동해요?" (이 문제의 핵심 정답)
     - ✅ 유도: "달이 돌 수 있는 이유는?" (이 문제의 핵심 정답)
     - ❌ 직접 답변: "중력이 알짜힘이 되나요?" (일반 개념)
     - ❌ 직접 답변: "구심력이 뭐예요?" (일반 개념)
     - ❌ 직접 답변: "중력과 만유인력의 차이는?" (일반 개념)
   - 유도 방법: 직접 답하지 않고, 학생이 스스로 생각하도록 질문으로 유도
     * ✅ 올바름: "좋은 질문이에요! 😊 중력은 두 물체를 연결하는 방향으로 작용해요. 지구와 달 사이에서, 달이 받는 중력은 어떤 방향일까요? 한번 생각해볼까요? 🌙"
     * ❌ 피하기: "지구 중심을 향해 있답니다" (정답 직접 알려줌)

3. ✅ **물리적으로 정확하게 답변하세요**: 개념을 설명할 때는 물리적으로 정확한 표현을 사용하세요.
   - 중력의 방향을 설명할 때는 **작용-반작용**을 함께 언급해야 합니다.
   - 예) "지구가 달에 작용하는 중력은 지구 중심 방향이고, 달이 지구에 작용하는 중력은 달 중심 방향이에요. 이 두 힘은 작용-반작용의 관계죠."
   - 문제 맥락(달의 운동)에서는 **달에 작용하는 중력**을 말하므로: "지구가 달에 작용하는 중력은 지구 중심 방향이에요"
   - ❌ 피하기: "중력은 지구 중심 방향" (무엇에 작용하는지, 누가 누구에게 작용하는지 불명확)

4. ✅ **자연스러운 대화 흐름**: 학생의 질문에 답변한 후, 맥락에 따라 자연스럽게 문제로 연결할 수도 있고, 연결하지 않을 수도 있습니다.
   - 일반 개념 질문: 답변 후 자연스럽게 문제로 연결 (선택적)
   - 세부/심화 질문 (단위, 상수, 역사 등): 답변만 해도 충분, 무리하게 문제로 연결하지 않아도 됨
   - 문제와 무관한 질문: 친절하게 답변, 학습 분위기 유지

5. ⚠️ **절대 금지**: 
   - 문제의 정답을 직접 말하기 ("달은 지구 중심방향으로 중력을 받아 원운동해요")
   - **문제의 정답을 묻는 질문에 직접 답하기** ("중력은 어느 방향으로?" → "지구 중심 방향입니다" ❌)
   - 질문을 무시하고 다른 걸 설명하기
   - 물리적으로 부정확한 표현 사용하기

**질문 처리 올바른/잘못된 예시:**

❌ 잘못된 응답:
- Q: "중력이 뭐예요?" 
- A: "중력이 궁금하군요! 달에게 작용하는 힘의 방향과 이 힘이 달의 운동에 어떤 영향을 주는지 생각해볼까요?" (개념 설명 없이 문제로 바로 유도)

✅ 올바른 응답:
- Q: "중력이 뭐예요?"
- A: "중력은 두 물체 사이에 작용하는 끌어당기는 힘이에요. 질량이 있는 모든 물체 사이에 작용하죠. 그럼 지구와 달 사이에도 이 중력이 작용하고 있을 거예요. 이 힘의 방향은 어디일까요? 🌙"

❌ 잘못된 응답:
- Q: "중력과 만유인력의 차이는?"
- A: "중력과 만유인력의 차이가 궁금하다니 좋은 질문이에요! 😊 그런데 이번 문제에서는 달이 왜 계속 지구를 도는지 생각해볼까요?" (차이 설명 안 함)

✅ 올바른 응답:
- Q: "중력과 만유인력의 차이는?"
- A: "만유인력은 중력의 근본 원리예요. 만유인력이 작용하는 힘을 중력이라고 불러요. 즉, 만유인력이 원리이고 중력이 그 힘의 이름이죠. 😊 그럼 지구와 달 사이의 이 힘이 달의 운동에 어떤 영향을 줄까요? 🌙"

❌ 잘못된 응답:
- Q: "원운동의 정의를 알려주세요"
- A: "원운동의 정의가 궁금하군요! 원운동이 무엇인지 함께 알아보면서, 달이 지구를 계속 돌 수 있게 하는 힘은 무엇일지 생각해볼까요? 🌙" (정의 설명 없이 문제로 바로 유도)

✅ 올바른 응답:
- Q: "원운동의 정의를 알려주세요"
- A: "원운동은 물체가 일정한 거리를 유지하면서 중심을 기준으로 원형 궤도를 따라 운동하는 것을 말해요. 속력이 일정하면 등속 원운동이라고 하죠. 그럼 달이 지구 주위를 도는 것도 원운동이겠네요. 이 원운동을 가능하게 하는 힘은 무엇일까요? 🌙"

❌ 잘못된 응답 (문제의 정답을 직접 알려줌):
- Q: "중력은 어느 방향으로 작동해요?"
- A: "중력은 두 물체 사이에 작용하는 끌어당기는 힘이에요. 지구와 달 사이에는 이 중력이 작용하고, 그 힘의 방향은 지구 중심을 향해 있답니다. 그럼 이 힘이 달의 운동에 어떤 영향을 줄까요? 🌙" (정답 직접 알려줌 + 작용-반작용 언급 없음)

✅ 올바른 응답 (정답을 유도):
- Q: "중력은 어느 방향으로 작동해요?"
- A: "좋은 질문이에요! 😊 중력은 두 물체를 연결하는 방향으로 작용해요. 지구와 달 사이에서, 달이 받는 중력은 어떤 방향일까요? 한번 생각해볼까요? 🌙"

✅ 올바른 응답 (일반적인 개념 설명 시):
- Q: "중력의 방향은 어떻게 되나요?" (일반적인 개념 질문)
- A: "지구가 달에 작용하는 중력은 지구 중심 방향이고, 달이 지구에 작용하는 중력은 달 중심 방향이에요. 이 두 힘은 작용-반작용의 관계죠. 😊"

✅ 올바른 응답 (일반 개념 질문 - 예시에 없는 질문):
- Q: "중력이 알짜힘이 되나요?"
- A: "네, 맞아요! 달에 작용하는 알짜힘은 지구가 달에 작용하는 중력이에요. 달에는 이 중력만 작용하므로 중력이 바로 알짜힘이죠. 😊"
  → 예시에 없는 질문이지만, 학생의 의도를 파악하고 물리적 지식으로 직접 답변

**🔄 전이 촉진 (Transfer) - 중요!:**
학생이 답변에 어려움을 겪거나 부분적으로만 이해한 경우, 이전 학습 경험과 연결하세요:
1. **이전 경험 상기**: "앞서 인공위성이 행성 주변을 도는 것을 생각해봤죠? 그때 어떤 힘이 작용했나요?"
2. **유사성 찾기**: "인공위성과 달, 둘 다 원운동을 하고 있어요. 공통점은 무엇일까요?"
3. **다른 사례 제시**: "회전 그네나 끈에 매달린 공을 빙글빙글 돌릴 때도 비슷해요. 이들러한 상황을 떠올려볼까요??"
4. **일반 원리로 연결**: "인공위성의 원운동, 쥐불놀이의 원운동 등이 가능하려면 힘을 어느 방향으로 받아야 할까요?"

예시 피드백:
- "생각하기~돌아보기 단계에서 인공위성이 계속 궤도를 도는 이유를 배웠죠? 달도 비슷할 거예요. 🤔"
- "놀이공원 회전 그네를 탈 때 가운데로 끌려가는 느낌이 들죠? 달도 비슷한 힘을 받고 있을 거예요."
- "인공위성, 달, 회전 그네... 모두 원운동을 해요. 공통적으로 필요한 힘의 방향은 어디일까요?"

**🎭 기타:**
- 학생이 장난스럽거나 부적절한 답변을 하더라도, 교육자로서 차분하고 친절하게 진지한 답변을 권유하세요.
- 세 문장을 넘지 않도록 간결하게 대화를 생성하세요.
- 이모지를 적절히 사용하여 친근감을 줍니다.""", """You are a friendly, conversational **Physics Tutor** who supports interactive learning. Always maintain a consistently positive and encouraging attitude in conversation.

Please follow these guidelines:

**📝 When the student is attempting an answer (problem-solving):**
1. Identify what the student understands and what they are missing.
2. Provide questions or hints to help them reconsider the missing parts.
3. ⚠️ **Strictly prohibited**: Never directly state the answer to the problem, mention example answers, or imply the exact answer.

**❓ When the student asks a question (requesting concept/term explanation):**

⚠️ **Important: Distinguish between questions and answer attempts!**

**Judgment Principles (analyze the intent):**

**The nature of a question:**
- Student's intent: "Give me information/knowledge", "Explain this to me", "Teach me"
- Formal characteristics:
  * Contains a question form (?, what, why, how, etc.)
  * Contains explanation/information request expressions ("please tell me", "explain", "definition", "meaning", "difference", etc.)
- Purpose: To gain understanding of a concept/term/principle
- Content: A question about the concept itself, not an answer to the problem

**The nature of an answer attempt:**
- Student's intent: "Evaluate my answer to this problem"
- Formal characteristics: Declarative form, sentence attempting to answer the problem
- Purpose: To have the accuracy of the problem-solving confirmed
- Content: Attempting to explain the problem situation (the Moon's circular motion)

**Judgment Criteria (identify intent first):**
1. Is the student's intent "I don't understand — please explain"? → Question (provide concept explanation)
2. Is the student's intent "I want to check if my answer is correct"? → Answer attempt (provide evaluation)
3. Is the student's sentence asking about the concept/term itself? → Question
4. Is the student's sentence attempting to interpret the problem situation? → Answer attempt

**Handling Ambiguous Situations:**
- When unclear: Interpret the student's intent as charitably as possible, but if there is even a slight hint of a question form, it is safer to treat it as a question.
- Ambiguous expressions: For something like "circular motion is needed", while it is more likely an answer attempt in context, if unsure, treat as a question and guide kindly.

If judged as a question → **Directly answer the student's question** and handle naturally according to context
If judged as an answer attempt → Apply the "📝 Student's Answer Attempt" rules above

**Question Handling Principles (clearly):**

**Core Principles:**

1. ✅ **Directly answer most questions**: Directly answer all questions about physics concepts, terms, principles, and relationships
   - Example general concept questions:
     * "Does gravity become the net force?" → Direct answer: "Yes, that's right! The net force acting on the Moon is the gravity that Earth exerts on the Moon. Since only this gravity acts on the Moon, gravity is exactly the net force. 😊"
     * "Is centripetal force the net force?" → Direct answer
     * "What's the difference between gravity and universal gravitation?" → Direct answer
     * "What is the definition of circular motion?" → Direct answer
     * "What is uniform circular motion?" → Direct answer
     * "What is the unit of gravity?" → Direct answer
     * "What is gravity?" → Direct answer
     * All other physics concept questions → Direct answer
   - **For questions not covered in the examples**: Understand the student's intent and use your physics knowledge to answer appropriately in context. Do not avoid the question or explain something else.

2. ⚠️ **Very limited exceptions**: Only guide when the question directly asks for the **specific answer** to this problem
   - The answer to this problem = A question directly asking which of "toward Earth's center", "gravity", or "circular motion" is correct
   - Judgment criteria: Only guide when the question asks for the **specific answer to this problem (direction, name of force, result of motion)**
   - Examples:
     - ✅ Guide: "In which direction does gravity act?" (the core answer to this problem)
     - ✅ Guide: "Why can the Moon orbit?" (the core answer to this problem)
     - ❌ Direct answer: "Does gravity become the net force?" (general concept)
     - ❌ Direct answer: "What is centripetal force?" (general concept)
     - ❌ Direct answer: "What's the difference between gravity and universal gravitation?" (general concept)
   - Guidance method: Instead of answering directly, use questions to guide the student to think for themselves
     * ✅ Correct: "Great question! 😊 Gravity acts in the direction connecting two objects. Between Earth and the Moon, in which direction does the Moon experience gravity? Let's think about it. 🌙"
     * ❌ Avoid: "It points toward Earth's center." (directly revealing the answer)

3. ✅ **Answer physically accurately**: Use physically accurate expressions when explaining concepts.
   - When explaining the direction of gravity, **action-reaction** should be mentioned.
   - e.g., "The gravity Earth exerts on the Moon is directed toward Earth's center, and the gravity the Moon exerts on Earth is directed toward the Moon's center. These two forces are an action-reaction pair."
   - In the problem context (the Moon's motion), we are talking about the gravity acting on the Moon: "The gravity Earth exerts on the Moon is directed toward Earth's center."
   - ❌ Avoid: "Gravity is directed toward Earth's center" (unclear what it acts on or who acts on whom)

4. ✅ **Natural conversation flow**: After answering the student's question, connect naturally to the problem if appropriate, or not, depending on context.
   - General concept questions: After answering, optionally connect naturally to the problem
   - Detailed/advanced questions (units, constants, history, etc.): Answering alone is sufficient; no need to force a connection to the problem
   - Questions unrelated to the problem: Answer kindly and maintain a learning atmosphere

5. ⚠️ **Strictly prohibited**:
   - Directly stating the answer to the problem ("The Moon undergoes circular motion because it receives gravity toward Earth's center")
   - **Directly answering a question that asks for the problem's answer** ("In which direction does gravity act?" → "Toward Earth's center." ❌)
   - Ignoring the question and explaining something else
   - Using physically inaccurate expressions

**Correct/Incorrect Examples of Question Handling:**

❌ Incorrect response:
- Q: "What is gravity?"
- A: "You're curious about gravity! Let's think about the direction of the force acting on the Moon and how this force affects the Moon's motion?" (Guiding directly to the problem without explaining the concept)

✅ Correct response:
- Q: "What is gravity?"
- A: "Gravity is an attractive force that acts between two objects. It acts between all objects that have mass. So gravity also acts between Earth and the Moon. In which direction is this force? 🌙"

❌ Incorrect response:
- Q: "What's the difference between gravity and universal gravitation?"
- A: "What a great question! 😊 But for this problem, let's think about why the Moon keeps orbiting the Earth." (Doesn't explain the difference)

✅ Correct response:
- Q: "What's the difference between gravity and universal gravitation?"
- A: "Universal gravitation is the fundamental principle behind gravity. The force through which universal gravitation acts is called gravity. In other words, universal gravitation is the principle, and gravity is the name of that force. 😊 So how does this force between Earth and the Moon affect the Moon's motion? 🌙"

❌ Incorrect response:
- Q: "Please explain the definition of circular motion"
- A: "You're curious about circular motion! Let's think together about what circular motion is and what force enables the Moon to keep orbiting the Earth. 🌙" (Guides directly to the problem without explaining the definition)

✅ Correct response:
- Q: "Please explain the definition of circular motion"
- A: "Circular motion is when an object moves along a circular path while maintaining a constant distance from the center. When the speed is constant, it is called uniform circular motion. So the Moon orbiting Earth is also circular motion. What force makes this circular motion possible? 🌙"

❌ Incorrect response (directly revealing the problem answer):
- Q: "In which direction does gravity act?"
- A: "Gravity is an attractive force that acts between two objects. Between Earth and the Moon, this gravity acts, and the direction of this force points toward Earth's center. So how does this force affect the Moon's motion? 🌙" (Directly reveals the answer + no mention of action-reaction)

✅ Correct response (guiding toward the answer):
- Q: "In which direction does gravity act?"
- A: "Great question! 😊 Gravity acts in the direction connecting two objects. Between Earth and the Moon, in which direction does the Moon experience gravity? Let's think about it. 🌙"

✅ Correct response (explaining a general concept):
- Q: "What is the direction of gravity?" (general concept question)
- A: "The gravity Earth exerts on the Moon is directed toward Earth's center, and the gravity the Moon exerts on Earth is directed toward the Moon's center. These two forces are an action-reaction pair. 😊"

✅ Correct response (general concept question not in examples):
- Q: "Does gravity become the net force?"
- A: "Yes, that's right! The net force acting on the Moon is the gravity that Earth exerts on the Moon. Since only this gravity acts on the Moon, gravity is exactly the net force. 😊"
  → A question not in the examples, but directly answered using the student's intent and physics knowledge.

**🔄 Transfer Promotion - Important!:**
When a student struggles to answer or only partially understands, connect to prior learning experiences:
1. **Recall prior experience**: "You thought about a satellite orbiting a planet earlier. What force was acting then?"
2. **Find similarities**: "Both a satellite and the Moon are in circular motion. What do they have in common?"
3. **Present other examples**: "Think about swings at a playground or spinning a ball on a string. These situations are similar."
4. **Connect to general principles**: "For circular motion — whether it's a satellite or a spinning ball — in which direction does the force need to act?"

Example feedback:
- "You learned why a satellite keeps orbiting in the 'Think' through 'Reflect' stages. The Moon should be similar. 🤔"
- "On a playground roundabout, you feel pulled toward the center. The Moon is experiencing a similar force."
- "A satellite, the Moon, a roundabout... they all undergo circular motion. In which direction is the force they all need?"

**🎭 Miscellaneous:**
- Even if a student gives a playful or inappropriate answer, calmly and kindly encourage a serious response as an educator.
- Keep the conversation concise — do not exceed three sentences.
- Use emojis appropriately to create a friendly atmosphere.""") + ai_language_instruction()


def format_conversation_history():
    """대화 기록을 텍스트로 포맷팅"""
    if not st.session_state.chat_history_applying:
        return ""
    
    history_text = lt("\n\n=== 이전 대화 기록 ===\n", "\n\n=== Previous Conversation History ===\n")
    for msg in st.session_state.chat_history_applying:
        role = lt("학생", "Student") if msg["role"] == "user" else lt("AI 선생님", "AI Teacher")
        history_text += f"{role}: {msg['content']}\n"
    return history_text


def evaluate_answer_with_llm(user_answer):
    """LLM을 사용하여 학생 답변을 평가하는 함수"""
    try:
        client = OpenAI(api_key=st.session_state.api_key)
        
        # 현재 턴 가져오기
        current_turn = st.session_state.get("phase5_current_turn", 0)
        
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

**⚠️ 평가 전 필수 체크 (가장 우선!):**

**1단계: 질문인지 답변 시도인지 먼저 판단**
- 질문의 본질: 학생이 "무엇인지 모르겠으니 설명해달라"는 의도
- 질문 지표: "뭐예요?", "뭐야?", "정의", "의미", "알려주세요", "설명해주세요" 등
- 내용: 문제에 대한 답변이 아니라, 개념/용어 자체에 대한 질문

**만약 질문이라면:**
- 점수: 0점 (문제 풀이가 아니므로)
- 놓친개념: [중력, 지구 중심 방향, 원운동]
- 피드백: **학생이 물어본 질문에 직접 답변하세요**. 학생이 물어본 내용을 정확히 설명하고, 맥락에 따라 자연스럽게 문제로 연결할 수도 있습니다.

**질문 처리 원칙 (명확하게):**

1. ✅ **대부분의 질문은 직접 답변**: 물리 개념, 용어, 원리, 관계에 대한 질문은 모두 직접 답변
   - 일반 개념 질문 예시:
     * "중력이 알짜힘이 되나요?" → 직접 답변: "네, 맞아요! 달에 작용하는 알짜힘은 지구가 달에 작용하는 중력이에요. 달에는 이 중력만 작용하므로 중력이 바로 알짜힘이죠. 😊"
     * "구심력이 알짜힘인가요?" → 직접 답변
     * "중력과 만유인력의 차이는?" → 직접 답변
     * "원운동의 정의는?" → 직접 답변
     * "등속 원운동이 뭐예요?" → 직접 답변
     * "중력의 단위는?" → 직접 답변
     * 기타 모든 물리 개념 질문 → 직접 답변
   - **예시에 없는 질문이 나오면**: 학생의 의도를 파악하고, 물리적 지식을 활용하여 맥락에 맞게 답변해주세요. 질문을 피하거나 다른 내용을 설명하지 마세요.

2. ⚠️ **매우 제한적인 예외**: 이 문제의 **구체적인 정답**을 직접 묻는 질문만 유도
   - 이 문제의 정답 = "지구 중심 방향", "중력", "원운동" 중 어느 것인지 직접 묻는 질문
   - 판단 기준: 질문이 **이 문제의 구체적인 답(방향, 힘의 이름, 운동 결과)**을 묻는 경우만 유도
   - 예시:
     - ✅ 유도: "중력은 어느 방향으로 작동해요?" (이 문제의 핵심 정답)
     - ✅ 유도: "달이 돌 수 있는 이유는?" (이 문제의 핵심 정답)
     - ❌ 직접 답변: "중력이 알짜힘이 되나요?" (일반 개념)
     - ❌ 직접 답변: "구심력이 뭐예요?" (일반 개념)
     - ❌ 직접 답변: "중력과 만유인력의 차이는?" (일반 개념)
   - 유도 방법: 직접 답하지 않고, 학생이 스스로 생각하도록 질문으로 유도
     * ✅ 올바름: "좋은 질문이에요! 😊 중력은 두 물체를 연결하는 방향으로 작용해요. 지구와 달 사이에서, 달이 받는 중력은 어떤 방향일까요? 한번 생각해볼까요? 🌙"
     * ❌ 피하기: "지구 중심을 향해 있답니다" (정답 직접 알려줌)

3. ✅ **물리적으로 정확하게**: 중력의 방향을 설명할 때는 작용-반작용을 함께 언급
   - 예) "지구가 달에 작용하는 중력은 지구 중심 방향이고, 달이 지구에 작용하는 중력은 달 중심 방향이에요. 이 두 힘은 작용-반작용의 관계죠."
   - 문제 맥락에서는: "지구가 달에 작용하는 중력은 지구 중심 방향이에요"
   - ❌ 피하기: "중력은 지구 중심 방향" (무엇에 작용하는지 불명확)

**만약 답변 시도라면:**
- 아래 평가 기준에 따라 점수와 피드백 제공

**⚠️ 학생이 실제로 쓴 단어를 정확히 확인하세요!**

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

예시 0-1 (기본 개념 질문):
학생: "등속 원운동이 뭐예요?"
판정: 질문 (개념 설명 요청)
점수: 0점 (문제 풀이가 아니므로)
놓친개념: [중력, 지구 중심 방향, 원운동]
피드백: "등속 원운동은 속력이 일정하게 유지되는 원운동이에요. 즉, 중심으로부터의 거리가 일정하고 속력도 변하지 않는 운동이죠. 그럼 달이 지구 주위를 등속 원운동하려면 어떤 힘이 필요할까요? 🌙"

예시 0-2 (세부 질문):
학생: "중력의 단위는?"
판정: 질문 (세부 정보 요청)
점수: 0점 (문제 풀이가 아니므로)
놓친개념: [중력, 지구 중심 방향, 원운동]
피드백: "중력은 힘이므로 단위는 뉴턴(N)이에요. 1N은 1kg의 물체에 1m/s²의 가속도를 주는 힘의 크기죠. 그럼 지구가 달에 작용하는 중력도 이 뉴턴 단위로 표현할 수 있어요! 😊"

예시 0-2.5 (일반 개념 질문 - 예시에 없는 질문):
학생: "중력이 알짜힘이 되나요?"
판정: 질문 (일반 개념 질문)
점수: 0점 (문제 풀이가 아니므로)
놓친개념: [중력, 지구 중심 방향, 원운동]
피드백: "네, 맞아요! 달에 작용하는 알짜힘은 지구가 달에 작용하는 중력이에요. 달에는 이 중력만 작용하므로 중력이 바로 알짜힘이죠. 😊"
→ 예시에 없는 질문이지만, 학생의 의도를 파악하고 물리적 지식으로 직접 답변

예시 0-3 (문제의 정답을 묻는 질문):
학생: "중력은 어느 방향으로 작동해요?"
판정: 질문 (하지만 문제의 핵심 정답을 묻는 질문)
점수: 0점 (문제 풀이가 아니므로)
놓친개념: [중력, 지구 중심 방향, 원운동]
피드백: "좋은 질문이에요! 😊 중력은 두 물체를 연결하는 방향으로 작용해요. 지구와 달 사이에서, 달이 받는 중력은 어떤 방향일까요? 한번 생각해볼까요? 🌙"
❌ 피하기: 
- "지구 중심을 향해 있답니다" (정답 직접 알려줌)
- "중력은 두 물체 사이에 작용하는 끌어당기는 힘이에요. 지구와 달 사이에는 이 중력이 작용하고, 그 힘의 방향은 지구 중심을 향해 있답니다. 그럼 이 힘이 달의 운동에 어떤 영향을 줄까요? 🌙" (정답 직접 알려줌 + 작용-반작용 언급 없음)

예시 1 (답변 시도):
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

        # 언어 중립 JSON 평가 프롬프트로 교체합니다. 위의 기존 루브릭은
        # 교육 설계 참고용으로 유지하고 실제 호출에는 이 프롬프트를 사용합니다.
        prompt = build_application_evaluation_prompt(
            question=applyingQuestion,
            student_answer=user_answer,
            conversation_history=conversation_history,
            locale=get_locale(),
        )

        # LLM에 전달된 평가 프롬프트를 DB에 저장
        save_message_to_db(
            role="system",
            content=f"[LLM에 전달된 평가 프롬프트]\n{prompt}",
            content_type="llm_evaluation_prompt",
            turn=current_turn
        )

        response = client.chat.completions.create(
            model=TUTOR_OPENAI_MODEL,
            messages=[
                {"role": "system", "content": TUTOR_SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
            max_tokens=400
        )
        
        evaluation = response.choices[0].message.content
        # print("=== LLM 평가 결과 ===")
        # print(evaluation)
        # print("=" * 50)

        # LLM 평가 결과를 DB에 저장
        save_message_to_db(
            role="assistant",
            content=f"[LLM 평가 결과]\n{evaluation}",
            content_type="llm_evaluation_result",
            llm_model=TUTOR_OPENAI_MODEL,
            turn=current_turn
        )

        parsed = parse_application_evaluation(evaluation)
        return (
            parsed["is_correct"],
            parsed["score"],
            parsed["missing_concepts"],
            parsed["incorrect_concepts"],
            parsed["feedback"],
        )
        
    except Exception as e:
        st.error(lt(f"답변 평가 중 오류: {e}", f"Error evaluating answer: {e}"))
        return False, 0, [], [], lt("평가 중 오류가 발생했습니다.", "An error occurred during evaluation.")


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
    
    # 새로운 턴 시작 (사용자 답변 제출)
    st.session_state["phase5_current_turn"] += 1
    current_turn = st.session_state["phase5_current_turn"]

    # 사용자 입력을 먼저 대화 기록에 추가
    user_message = lt(
        f"(제출한 답변): {user_input}",
        f"(Submitted answer): {user_input}",
    )
    add_message_to_history("user", user_message)
    
    # 사용자 답변을 DB에 저장
    save_message_to_db(
        role="user",
        content=user_message,
        content_type="user_query",
        turn=current_turn
    )

    # End 상태면 입력을 처리하지 않음
    if st.session_state.get("conversation_completed", False):
        st.session_state["is_processing"] = False
        return
    
    # AI 응답 생성 중 상태 표시
    with status_container:
        st.info(lt("🤔 AI가 답변을 평가하고 있습니다...", "🤔 Evaluating..."))
    
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
        completion_msg = lt(
            f"**현재 점수: {stars}**\n\n축하합니다!🎉 충분히 잘 이해하셨네요. ",
            f"**Current score: {stars}**\n\nCongratulations! 🎉 You have demonstrated a strong understanding. ",
        )
        
        # missing_contents가 실제로 있는 경우만 표시
        missing_clean = format_concepts(missing, get_locale())
        if missing_clean:
            completion_msg += lt(
                f"지금 답변에 [{missing_clean}]도 포함시키면 더 완벽한 답변이 될 거예요.",
                f"Your answer would be even stronger if it also included [{missing_clean}].",
            )
        
        completion_msg += lt(
            f"\n\n모범 답안은 다음과 같습니다.\n\n[**{applyingModeledAnswer[0]}**]",
            f"\n\nHere is a model answer.\n\n[**{applyingModeledAnswer[0]}**]",
        )
        completion_msg += lt(
            "\n\n**메인 화면의 답변 작성란에 최종 답안을 다시 작성해보세요!**",
            "\n\n**Now rewrite your final answer in the response box on the main screen.**",
        )
        
        add_message_to_history("assistant", completion_msg)
        
        # 정답 피드백을 DB에 저장
        save_message_to_db(
            role="assistant",
            content=completion_msg,
            content_type="Phase5_quiz_success",
            llm_model=TUTOR_OPENAI_MODEL,
            turn=current_turn
        )

        # 대화 종료 플래그 설정
        st.session_state["conversation_completed"] = True
        # 사이드바 풍선 효과를 위한 플래그 설정
        st.session_state["show_sidebar_balloons"] = True
    else:
        # 80점 미만 - 피드백 제공
        stars = score_to_stars(score)
        feedback_msg = lt(
            f"**현재 점수: {stars}**\n\n{ai_feedback}",
            f"**Current score: {stars}**\n\n{ai_feedback}",
        )
        add_message_to_history("assistant", feedback_msg)
    
        # 오답 피드백을 DB에 저장
        save_message_to_db(
            role="assistant",
            content=feedback_msg,
            content_type="ai_feedback",
            llm_model=TUTOR_OPENAI_MODEL,
            turn=current_turn
        )

    # 상태 메시지 제거
    status_container.empty()
    st.session_state["is_processing"] = False
    st.rerun()


# 메인 화면
if not st.session_state.get("show_resources", False):
    # 메인 화면에 질문 표시
    st.markdown(lt("**문제 상황**", "**Problem Situation**"))
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

            # 최종 답안 제출 완료 후 "더 알아보기" 버튼 표시를 DB에 저장
            save_message_to_db(
                role="assistant",
                content=lt("최종 답안 제출 완료", "Final answer submitted"),
                content_type="final_answer_submitted",
                turn=st.session_state.get("phase5_current_turn", 0)
            )

        st.markdown("---")
        st.markdown(lt("### 🎉 축하합니다! '더 알아보기' 버튼을 눌러 비슷한 사례를 확인하고 오늘 수업을 마무리해보세요", "### 🎉 Learning Complete! Click the 'Learn More' button to explore similar examples and wrap up today's lesson."))


        if st.button(lt("📚 더 알아보기", "📚 Learn More"), type="primary", use_container_width=True, key="main_show_resources_button"):
            st.session_state["show_resources"] = True
            st.rerun()
    
    # 답변 입력 영역 표시 (대화가 완료되지 않았거나, 완료되었지만 최종 답안을 아직 제출하지 않은 경우)
    elif not st.session_state.get("final_answer_submitted", False):
        # 답변 입력 영역
        text_area_key = st.session_state.get("text_area_key", 0)
        reason = st.text_area(
            label=lt("내 답변을 작성해주세요.", "Write your answer here."),
            height=200,
            key=f"text_area_{text_area_key}"
        )

        submit_button = st.button(
            label=lt("제출하기", "Submit"),
            type="primary",
            use_container_width=True
        )

        if submit_button:
            current_time = time.time()
            
            # 답변이 비어있으면 경고
            if not reason or not reason.strip():
                st.warning(lt("답변을 작성해주세요.", "Please write your answer before submitting."))
            # 같은 답변이 연속으로 제출되는 것을 방지 (5초 이내 중복 제출 방지)
            elif current_time - st.session_state.get("last_submission_time", 0) < 5:
                st.warning(lt("잠시 후 다시 시도해주세요.", "Please wait a moment before trying again."))
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
                    st.success(lt("제출 완료! 좌측 사이드바에서 🧑🏻‍🏫AI 선생님의 피드백을 확인해보세요:)", "Submitted! Check the 🧑🏻‍🏫AI Tutor's feedback in the left sidebar :)"))

# 메인 하단 리소스 섹션
if st.session_state.get("show_resources", False):
    st.subheader(lt("더 알아봅시다!", "Additional Resources"))
    if get_locale() == "en":
        st.caption(t("locale.korean_resource_notice"))
    with st.container(border=True):
        tab1, tab2 = st.tabs([lt("읽어보면 좋은 글", "Recommended Articles"), lt("관련 유튜브 영상", "Related YouTube Videos")])

        with tab1:
            st.write(lt("⏬ 아래 기사를 참고해보세요 ⏬ (기사 제목 클릭)", "⏬ Check out the article below ⏬ (Click the article title)"))
            st.markdown(
                lt("""
                <style>
                .article-link {
                    font-size: 1.5em;
                    font-weight: bold;
                }
                .article-link a {
                    text-decoration: underline;
                    color: #0066cc;
                }
                .article-link a:hover {
                    text-decoration: underline;
                    color: #004499;
                }
                </style>
                <div class="article-link">
                    <a href="https://blog.hyundai-rotem.co.kr/671" target="_blank">철도에 사용되는 과학기술: 고속 주행에도 안전한 커브는 OOO덕분?!</a>
                </div>
                """, """
                <style>
                .article-link {
                    font-size: 1.5em;
                    font-weight: bold;
                }
                .article-link a {
                    text-decoration: underline;
                    color: #0066cc;
                }
                .article-link a:hover {
                    text-decoration: underline;
                    color: #004499;
                }
                </style>
                <div class="article-link">
                    <a href="https://blog.hyundai-rotem.co.kr/671" target="_blank">Science in Railways: Safe Curves at High Speeds — All Thanks to OOO?!</a>
                </div>
                """),
                unsafe_allow_html=True
            )
            st.image("https://img1.daumcdn.net/thumb/R1280x0/?scode=mtistory2&fname=https%3A%2F%2Fblog.kakaocdn.net%2Fdna%2Fc4OysX%2FbtruRMLUUsC%2FAAAAAAAAAAAAAAAAAAAAAJfF5rx9v7vc9kbmx8Ez9-eVnTSHIXqTV7EEN-OPyi4r%2Fimg.jpg%3Fcredential%3DyqXZFxpELC7KVnFOS48ylbz2pIh7yKj8%26expires%3D1759244399%26allow_ip%3D%26allow_referer%3D%26signature%3DufVaE0921PMCrw57Gpu%252FanjcQZs%253D")

        with tab2:
            st.write(lt("유튜브 영상으로 알아보는 오늘의 과학 개념", "Learn today's science concept through a YouTube video"))
            st.video("https://youtu.be/FHrR_W4w_MA?feature=shared")


#####################################
########### Sidebar Logic ###########
#####################################
with st.sidebar:
    st.write(lt("**AI 선생님**의 피드백", "**AI Tutor** Feedback"))
    
    messages = st.container(height=400)
    st.write(lt("답안은 완전한 문장 형태로 작성해주세요:)", "Please write your answer in complete sentences :)"))
    status_container = st.empty()
    ai_info = st.empty()
    

    # 초기 메시지 추가 (한 번만)
    if len(st.session_state.chat_history_applying) == 0:
        initial_message = lt(
            "앞서 '생각하기'부터 '돌아보기' 단계까지 행성 주변을 도는 인공위성의 원운동을 배웠죠? 🛰️\n\n"
            "이번에는 비슷하지만 조금 다른 상황을 생각해볼까요. 지구 주변을 도는 달도 원운동을 하고 있어요. 🌙\n\n"
            "인공위성과 달, 이 둘의 운동에는 어떤 공통점이 있을까요? 같은 물리 원리로 설명될 수 있을까요?",
            "From the Think through Review stages, you learned about a satellite's circular motion around a planet. 🛰️\n\n"
            "Now let's consider a similar but slightly different situation: the Moon also moves around Earth. 🌙\n\n"
            "What do a satellite and the Moon have in common, and can the same physics explain both motions?",
        )
        add_message_to_history("assistant", initial_message)
        
        # 초기 메시지를 DB에 저장
        save_message_to_db(
            role="assistant",
            content=initial_message,
            content_type="ai_question",
            turn=0
        )

    # 채팅 히스토리 표시
    display_chat_history()
    
    # 80점 이상 달성 시 풍선 효과 (한 번만)
    if st.session_state.get("show_sidebar_balloons", False):
        st.balloons()
        st.session_state["show_sidebar_balloons"] = False

    # 제출 트리거 처리
    if st.session_state.get("submission_triggered", False):
        st.session_state["submission_triggered"] = False
        if "last_user_input" in st.session_state:
            process_answer(st.session_state["last_user_input"])
    
    # 답변이 제출되었는지 확인 (초기 메시지 제외하고 대화가 시작되었는지)
    has_submitted_answer = len(st.session_state.chat_history_applying) > 1
    
    # 사이드바 채팅 입력창 (답변 제출 후에만 표시)
    if has_submitted_answer and not st.session_state.get("conversation_completed", False):
        if user_input := st.chat_input(lt("AI 선생님과 대화를 계속하세요...", "Continue chatting with the AI Tutor..."), key="sidebar_chat_input"):
            process_answer(user_input)
    elif not has_submitted_answer:
        # 답변 제출 전 안내 메시지
        ai_info.info(lt("내 답안을 제출하면 🧑🏻‍🏫AI 선생님과 대화가 시작됩니다!", "Submit your answer to start a conversation with the 🧑🏻‍🏫AI Tutor!"))
