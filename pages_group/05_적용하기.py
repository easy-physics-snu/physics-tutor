import os
import re
import streamlit as st
import time

from typing import List
from langchain_core.messages.chat import ChatMessage
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_openai import ChatOpenAI #, OpenAIEmbeddings
# from langchain_ollama import ChatOllama

from pydantic import BaseModel, Field
from langchain_core.messages import BaseMessage

from langchain_teddynote import logging


st.session_state.api_key = st.secrets["openai_api_key"]

# 처음 1번만 실행하기 위한 코드
if "messages_application" not in st.session_state:
    # 대화기록을 저장하기 위한 용도로 생성한다.
    st.session_state["messages_application"] = []

# 처음 1번만 실행하기 위한 코드
if "messages_application_tutor" not in st.session_state:
    # 대화기록을 저장하기 위한 용도로 생성한다.
    st.session_state["messages_application_tutor"] = []

# os.environ["LANGCHAIN_TRACING_V2"] = st.secrets["LANGCHAIN_TRACING_V2"]
# os.environ["LANGCHAIN_API_KEY"] = st.secrets["LANGCHAIN_API_KEY"]
# os.environ["LANGCHAIN_ENDPOINT"] = st.secrets["LANGCHAIN_ENDPOINT"]
# os.environ["LANGCHAIN_PROJECT"] = st.secrets["LANGCHAIN_PROJECT"]

# 캐시 디렉토리 생성
if not os.path.exists(".cache"):
    os.mkdir(".cache")

# 세션 기록을 저장할 딕셔너리
store = {} 

class InMemoryHistory(BaseChatMessageHistory, BaseModel):
    """In memory implementation of chat message history."""

    messages: List[BaseMessage] = Field(default_factory=list)

    def add_messages(self, messages: List[BaseMessage]) -> None:
        """Add a list of messages to the store"""
        self.messages.extend(messages)

    def clear(self) -> None:
        self.messages = []


def get_by_session_id(session_id: str) -> BaseChatMessageHistory:
    if session_id not in store:
        store[session_id] = InMemoryHistory()
    return store[session_id]

# 이전 대화를 출력
def print_messages():
    for chat_message in st.session_state["messages_application"]:
        st.chat_message(chat_message.role).write(chat_message.content)

# 새로운 메시지를 추가
def add_message(role, message):
    st.session_state["messages_application"].append(ChatMessage(role=role, content=message))

# 세션 ID를 기반으로 세션 기록을 가져오는 함수
def get_session_history(session_ids: str) -> BaseChatMessageHistory:
    print(session_ids)
    if session_ids not in store:  # 세션 ID가 store에 없는 경우
        # 새로운 ChatMessageHistory 객체를 생성하여 store에 저장
        store[session_ids] = ChatMessageHistory()
    return store[session_ids]  # 해당 세션 ID에 대한 세션 기록 반환


st.title("적용하기 💡")
st.info("- 배운 내용을 새로운 상황에 적용해보며 개념을 더 깊게 이해해봅시다. \n - 지구 주위를 도는 달의 모습을 관찰해보고 그 이유를 설명해보세요. \n - 🧑🏻‍🏫**AI 튜터**와 대화하면서 개념을 새로운 상황에 적용하고 내 이해를 정교화해보세요.")

st.image("https://bobmoler.wordpress.com/wp-content/uploads/2019/03/orbit_360p30-1.gif", caption="지구 주위를 도는 달의 모습")

# textbook_container = st.empty()
with st.container(border=True):  # border=True로 실선 테두리 추가
    st.markdown(body="""
    ## 등속 원운동

    운동 방향만 변하는 운동 놀이공원의 회전하는 관람차, 지구 주위를 도는 인공위성, 시계의 바늘 등은 일정한 속력으로 원을 그리며 운동하는데, 이러한 운동을 등속 원운동이라고 한다.
    등속 원운동 하는 물체는 속력이 변하지 않고 운동 방향만 변한다. (교과서 16쪽)
    """)

# 처음 1번만 실행하기 위한 코드
if "messages_application" not in st.session_state:
    # 대화기록을 저장하기 위한 용도로 생성한다.
    st.session_state["messages_application"] = []


feedback_container = st.container(border=True, height=500)

# 사용자의 입력
user_input_question = st.chat_input("🧑🏻‍🏫AI 튜터의 질문에 대한 답변을 작성해주세요.")


# 적용 질문(나중엔 DB에서 불러오면 좋을 듯)
applyingQuestion = """
다시 등장한 🧑🏻‍🏫AI 튜터입니다:) 마지막으로, 배운 내용을 새로운 상황에 적용해봅시다! \n
위 그림과 같이 달이 공전 궤도를 유지하면서 계속 지구를 돌 수 있는 이유는 무엇일까요?
"""

# 적용하기 모범답안 (나중엔 DB에서 불러오면 좋을 듯)
applyingModeledAnswer = "지구가 달에 지구 중심방향으로 향하는 힘(중력)을 작용하고 있어서, 달은 지구 주변을 계속 원운동할 수 있습니다." 

# 핵심 개념(나중엔 DB에서 불러오면 좋을 듯)
essential_contents = "등속 원운동"


with feedback_container:

    # 답변 체인 생성
    def create_chain(model_name="gpt-4o"):
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
                    2. Progressive improvement in understanding shown through the conversation
                    3. Integration of previous responses with new insights
                    
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
                (
                    "system",
                    """당신은 친근하고 대화형 학습을 돕는 **물리 튜터**입니다. 항상 존댓말을 사용하며 긍정적이고 격려하는 태도로 일관된 대화를 유지하세요.  

                    **목표:** 학생이 새로 익힌 [핵심 개념]과 관련된 개념을 새로운 [문제 상황]에 적용하고, 이를 통해 개념의 유용성을 탐구하며 반성적 사고를 할 수 있도록 대화를 통해 돕습니다.

                    **중요:** 다음 규칙을 반드시 따르세요.
                    1. 첫 문장으로는 반드시 현재 학생의 [답변 점수]를 다음과 같이 안내하세요.
                        - 현재 답변 점수는 약 {score} 입니다.
                    2. 세 문장을 넘지 않도록 대화를 생성하세요.  
                    3. 절대로 정답이나 지나친 암시를 제공하지 마세요.
                    4. 만약 학생의 답변에 [놓친 개념]이 있다면, [놓친 개념]을 질문 형태로 간접적으로 제시해주고, 이를 포함하여 정확하게 답변해달라고 요청하세요.
                    5. 만약 학생의 답변에 [잘못된 개념]이 있다면 
                        - [잘못된 개념]에 대해 직접적으로 말하지 말고, 학생이 스스로 탐색할 수 있도록 열린 질문을 통해 [잘못된 개념]에 불만족을 가질 수 있도록 반례를 들어 학생과 문답하세요.
                        - 만약 [잘못된 개념]에 대하여 3회 이상 문답했지만 계속 [잘못된 개념]을 고수하는 경우에는 올바른 과학적 개념을 알려주세요.
                        - 작동이 끝나면 [답변 점수]가 80점이 넘더라도 [답변 점수]를 초기화하고, 학생에게 다시 한 번 정확하게 답변해달라고 요청하세요.
                    
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

        llm = ChatOpenAI(model_name=model_name, temperature=0, openai_api_key = st.session_state.api_key)

        # llm_scaffolding = ChatOllama(model="exaone3.5:7.8b-instruct-q8_0", temperature=0)

        def process_input(user_input, is_init=False):
            # Only display user message if it's not the initial message
            if not is_init:
                with st.chat_message("user"):
                    st.write(user_input)
                add_message("human", user_input)

            # First, get the relevance check
            relevance_chain = RunnableWithMessageHistory(
                relevance_check_prompt | llm,
                get_session_history,
                input_messages_key="input",
                history_messages_key="history",
            )
            
            relevance_check_response = relevance_chain.invoke(
                {"input": user_input, "applyingModeledAnswer": applyingModeledAnswer},
                config={"configurable": {"session_id": "abc123"}}
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
                scaffolding_prompt | llm, # llm(openAI꺼), llm_scaffolding(Exaone 3.5 경량화 넣어봤음)
                get_session_history,
                input_messages_key="input",
                history_messages_key="history",
            )
            
            final_response = scaffolding_chain.invoke(
                {
                    "input": user_input,
                    "applyingQuestion": applyingQuestion,
                    "applyingModeledAnswer": applyingModeledAnswer,
                    "score": score,
                    "missing_contents": missing_contents,
                    "incorrect_contents": incorrect_contents,
                    "essential_contents": essential_contents
                },
                config={"configurable": {"session_id": "abc123"}}
            )
            
            # Store missing_contents in session state
            st.session_state["missing_contents"] = missing_contents
            
            return final_response
        
        return process_input
    
    # 이전 대화 기록 출력
    print_messages()


    # 체인 생성
    if "application_chain" not in st.session_state:
        st.session_state["application_chain"] = create_chain()

    chain = st.session_state["application_chain"]

    # # 사이드바에 relevance score를 표시할 컨테이너 생성
    # if "relevance_score" not in st.session_state:
    #     st.session_state["relevance_score"] = 0

    # # 사이드바에 점수 표시
    # with st.sidebar:
    #     st.header("모범 답안과의 일치율")
    #     # 점수 표시를 위한 컨테이너들을 미리 생성
    #     score_container = st.empty()
    #     score_text_container = st.empty()
    if len(st.session_state["messages_application"]) == 0:
        # Display the question directly
        with st.chat_message("assistant"):
            st.markdown(applyingQuestion)
        
        # Add the question to history
        add_message("assistant", applyingQuestion)

    else:
        if user_input_question:
            # Process the message with our chain
            response = chain(user_input_question, False)
            
            # relevance score 계산 및 업데이트
            try:
                # 80% 이상 달성 시 축하 효과와 마무리 메시지
                if st.session_state["score"] >= 80:
                    st.balloons()
                    with st.chat_message("assistant"):
                        st.write(" 축하합니다! 충분히 잘 이해하셨네요. 모범 답안은 다음과 같습니다.")
                        st.markdown("   [**" + f"{applyingModeledAnswer}"+"**]")
                        if len(st.session_state['missing_contents']) > 0:
                            missing_text = ''.join(st.session_state['missing_contents']).strip()
                            if missing_text:  # 빈 문자열이 아닌 경우에만 출력
                                st.write(f"   지금도 충분히 좋은 답변이지만, [{missing_text}] 를 포함하여 작성했다면 더 완벽한 답이 작성되었겠네요.")
                        st.write("오늘 수업은 여기까지입니다.")
                        st.subheader("더 알아봅시다!")

                        with st.container(border=True):
                            tab1, tab2 = st.tabs(["읽어보면 좋은 글", "관련 유튜브 영상"])

                            with tab1:
                                st.write("아래 기사를 참고해보세요. (기사 제목 누르기)")
                                st.page_link(page="https://blog.hyundai-rotem.co.kr/671", label="철도에 사용되는 과학기술: 고속 주행에도 안전한 커브는 OOO덕분?!")
                                st.image("https://img1.daumcdn.net/thumb/R1280x0/?scode=mtistory2&fname=https%3A%2F%2Fblog.kakaocdn.net%2Fdn%2Fc4OysX%2FbtruRMLUUsC%2FI2IEaLfd8YNZzB9p6Apzs0%2Fimg.jpg")


                            with tab2:
                                st.write("유튜브 영상으로 알아보는 오늘의 공부")
                                st.video("https://youtu.be/FHrR_W4w_MA?feature=shared")

                    # 대화 종료를 위한 플래그 설정
                    st.session_state["conversation_completed"] = True
                
            except (ValueError, TypeError) as e:
                st.error(f"점수 계산 중 오류가 발생했습니다: {e}")
            
            # 대화가 완료되지 않은 경우에만 AI 응답 표시
            if not st.session_state.get("conversation_completed", False):
                with st.chat_message("assistant"):
                    texts = response.content
                    text_parts = texts.split() 
                    placeholder = st.empty()
                    streamed_text = ""  # Initialize empty string to accumulate streamed content
                    for part in text_parts:
                        streamed_text += part + " "  # Add the next word/character
                        placeholder.markdown(streamed_text)  # Update the placeholder content
                        time.sleep(0.1)
                
                # AI 답변도 대화기록에 저장
                add_message("assistant", response.content)

# 사이드바 생성
with st.sidebar:

    st.text("AI와 대화하기")
    messages = st.container(height=400)
    ai_info = st.empty()

    # 모델 선택 메뉴
    selected_model = "gpt-4o" # st.selectbox("LLM 선택", ["gpt-4o", "gpt-4o-mini"], index=0)

    # 사이드바 시스템 체인 생성
    def generate_chain(model_name=selected_model):
        # 현재 선택된 operation 값 가져오기
        prompt = ChatPromptTemplate.from_messages([
            ("system", 
            """당신은 친절하고 대화형 학습을 돕는 **물리 튜터**입니다.  
        **목표:** 학생이 '등속 원운동'에서 힘의 방향이 물체의 운동 궤적에 어떻게 작용하는지를 이해하도록 돕는 것입니다. 정답 화면을 제공한 후, 학생이 정답을 논리적으로 이해하고 설명할 수 있도록 대화형 질문과 설명을 진행하세요.  
        **중요:**  
        1. 정답을 단순히 제시하는 데 그치지 말고, 학생이 그 이유를 이해하고 자신의 언어로 정리할 수 있도록 돕습니다.  
        2. 학생의 관점과 질문을 존중하며, 친근한 존댓말로 대화하세요.  
        3. 각 응답은 간결하고 명확하게 작성하세요(2문단 이내).  
        4. 학생이 이해하지 못한 부분이 있을 경우, 추가적인 설명과 예시를 활용해 개념을 명확히 전달하세요.

        **프롬프트 시작 제안:**  
        (정답 화면을 학생에게 보여준 후 대화를 시작한다고 생각하세요.)
        1. **정답 화면 제시 후**  
        - "이 화면에서 물체가 등속 원운동을 유지하기 위해 힘이 어떤 방향으로 작용하고 있는지 보여주고 있어요. 여기서 힘의 방향이 원의 중심을 향하는 것을 확인할 수 있습니다."  
        2. **첫 질문:**  
        - "이 화면에서 힘이 왜 원의 중심을 향해야 하는지 생각해 보셨나요? 지금까지의 관찰과 그림을 바탕으로 한 번 설명해 보세요."  

        **대화 전략:**  
        1. 학생의 답변을 기반으로 질문을 이어가며 올바른 개념을 도출하도록 돕습니다.  
        2. 대화의 초점은 학생이 '등속 원운동에서 속도의 방향이 계속 바뀌기 때문에 중심 방향의 힘(구심력)이 필요하다'는 점을 논리적으로 이해하는 데 맞춰야 합니다.  
        3. 정답 화면을 참고하며 학생의 추론 과정을 구체화하도록 질문을 활용하세요.

        **핵심 질문 유도:**  
        - "등속 원운동에서는 물체의 속력이 일정하지만, 속도의 방향은 계속 변합니다. 속도의 방향을 바꾸기 위해 힘이 어떤 역할을 한다고 생각하나요?"  
        - "이 정답 화면에서 보이는 힘의 방향이 속도와 직각을 이루는 이유는 무엇일까요?"  
        - "만약 힘이 중심을 향하지 않는다면, 물체의 운동 궤적은 어떻게 될까요?"  

        **추가적인 설명 제공:**  
        학생이 답을 이해하지 못하거나 잘못된 추론을 제시했을 경우, 올바른 개념을 설명하세요.  
        - "등속 원운동은 물체가 일정한 속력으로 원 궤도를 따라 움직이는 운동이에요. 하지만 속도의 방향이 계속 바뀌기 때문에 가속도가 존재하게 됩니다. 이 가속도를 만들어내기 위해서는 항상 원의 중심 방향으로 힘이 작용해야 해요. 이를 구심력이라고 합니다."  
        - "만약 힘이 중심 방향으로 작용하지 않는다면, 물체는 직선으로 운동을 계속하려는 경향(관성)에 의해 원 궤도를 벗어나게 됩니다."  

        **대화 마무리:**  
        학생이 자신의 언어로 개념을 정리할 수 있도록 유도하세요.  
        - "지금까지 배운 내용을 바탕으로 정리해 볼까요? 물체가 등속 원운동을 유지하기 위해 힘의 방향이 왜 원의 중심을 향해야 하는지 설명해 주세요."  
        - "정답 화면을 다시 보면서 힘의 방향과 운동 궤적의 관계를 한 번 더 정리해 보세요. 왜 등속 원운동에서 중심 방향의 힘이 필요한지, 그것이 어떻게 운동을 유지하는지 설명할 수 있나요?"  

        **중요 사항:**  
        - 학생이 스스로 설명하려고 할 때 격려하며, 잘못된 표현이 있어도 바로 정정하지 말고 추가 질문으로 사고를 확장하도록 유도하세요.  
        - 정답 화면과 학생의 추론 과정을 연결시키는 데 집중하며, 이해가 완벽해질 때까지 인내심을 가지고 돕습니다."""
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


        chain = prompt | llm
        chain_with_history = RunnableWithMessageHistory(
            chain,
            get_by_session_id,
            input_messages_key="input",
            history_messages_key="history",
        )

        return chain_with_history


    # 이전 대화를 출력
    def print_messages_tutor():
        for chat_message in st.session_state["messages_application_tutor"]:
            messages.chat_message(chat_message.role).write(chat_message.content)


    # 새로운 메시지를 추가
    def add_message_tutor(role, message):
        st.session_state["messages_application_tutor"].append(ChatMessage(role=role, content=message))


    # 이전 대화 기록 출력
    print_messages_tutor()

    # 사용자의 입력
    user_input_tutor = st.chat_input("🤓AI 탐구도우미에게 궁금한 내용을 물어보세요!")

    # if len(st.session_state["messages_application_tutor"]) == 0:
    #     # Display the question directly
    #     with messages.chat_message("assistant"):
    #         st.markdown(applyingQuestion)
        
    #     # Add the question to history
    #     add_message("assistant", applyingQuestion)

    if user_input_tutor:
        # 답변 요청
        conv_chain = generate_chain(selected_model)

        # 사용자의 입력
        messages.chat_message("user").write(user_input_tutor)

        with messages.chat_message("assistant"):
            # 빈 공간(컨테이너)을 만들어서, 여기에 토큰을 스트리밍 출력한다.
            container = st.empty()
            generator = conv_chain.stream(
                {
                    "input": user_input_tutor,
                },
                config={"configurable": {"session_id": "ab12"}}
            )
            ai_answer = ""
            for token in generator:
                ai_answer += token.content
                container.markdown(ai_answer)

        # 대화기록을 저장한다.
        add_message_tutor("user", user_input_tutor)
        add_message_tutor("assistant", ai_answer)


# Create columns with specific ratios
col1, col2, col3 = st.columns([5, 2, 2])

# Place the button in the last column
with col1:
    if st.button(
        label="이전단계로",
        icon="⏪",
        help="돌아보기로 이동하기",
        type="primary"
    ):
        st.switch_page("pages_group/04_돌아보기.py")
