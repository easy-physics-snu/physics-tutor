import os
import re
import streamlit as st

from dotenv import load_dotenv
from openai import OpenAI

from langchain_community.document_loaders import PDFPlumberLoader
from langchain_community.vectorstores import FAISS
from langchain_core.messages.chat import ChatMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_teddynote import logging
from langchain_teddynote.prompts import load_prompt
from langchain_text_splitters import RecursiveCharacterTextSplitter



st.title("들어가기 🚀")

os.environ["LANGCHAIN_TRACING_V2"] = st.secrets["LANGCHAIN_TRACING_V2"]
os.environ["LANGCHAIN_API_KEY"] = st.secrets["LANGCHAIN_API_KEY"]
os.environ["LANGCHAIN_ENDPOINT"] = st.secrets["LANGCHAIN_ENDPOINT"]
os.environ["LANGCHAIN_PROJECT"] = st.secrets["LANGCHAIN_PROJECT"]

st.session_state.api_key = st.secrets["openai_api_key"]

# 캐시 디렉토리 생성
if not os.path.exists(".cache"):
    os.mkdir(".cache")

if not os.path.exists(".cache/embeddings"):
    os.mkdir(".cache/embeddings")

# 처음 1번만 실행하기 위한 코드
if "intro_1_tutor_messages" not in st.session_state:
    # 대화기록을 저장하기 위한 용도로 생성한다.
    st.session_state["intro_1_tutor_messages"] = []

if "pdf_chain" not in st.session_state:
    # 아무런 파일을 업로드 하지 않을 경우
    st.session_state["pdf_chain"] = None

if "pdf_retriever" not in st.session_state:
    st.session_state["pdf_retriever"] = None

if "balloons_done" not in st.session_state:
    st.session_state["balloons_done"] = False

@st.cache_resource(show_spinner="업로드한 파일을 처리 중입니다...")
def embed_file(file_path):
    # Get filename without extension for the vectorstore
    file_base_name = os.path.splitext(os.path.basename(file_path))[0]
    vectorstore_path = f"./.cache/embeddings/{file_base_name}"
    
    # Check if we already have embeddings for this file
    if os.path.exists(vectorstore_path):
        # Load existing vectorstore
        embeddings = OpenAIEmbeddings(model="text-embedding-3-small", openai_api_key=st.secrets["openai_api_key"]) #st.session_state.api_key)
        vectorstore = FAISS.load_local(
            vectorstore_path,
            embeddings,
            allow_dangerous_deserialization=True,
        )
        return vectorstore.as_retriever()

    # ... existing document loading and splitting code ...
    # 단계 1: 문서 로드(Load Documents)
    loader = PDFPlumberLoader(file_path)
    docs = loader.load()

    # 단계 2: 문서 분할(Split Documents)
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    split_documents = text_splitter.split_documents(docs)

    # 단계 3: 임베딩(Embedding) 생성
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small", openai_api_key=st.secrets["openai_api_key"]) # st.session_state.api_key)

    # 단계 4: DB 생성(Create DB) 및 저장
    # 벡터스토어를 생성합니다.
    vectorstore = FAISS.from_documents(documents=split_documents, embedding=embeddings)
    # Save the vectorstore
    vectorstore.save_local(vectorstore_path)
    
    return vectorstore.as_retriever()


# 체인 생성
def create_chain(retriever, prompt_path="prompts/doc-rag.yaml", model_name="gpt-4o"):
    # 단계 6: 프롬프트 생성(Create Prompt)
    # 프롬프트를 생성합니다.
    prompt = load_prompt(prompt_path, encoding="utf-8")

    # 단계 7: 언어모델(LLM) 생성
    # 모델(LLM) 을 생성합니다.
    llm = ChatOpenAI(model_name=model_name, temperature=0, openai_api_key = st.session_state.api_key)
    
    # 단계 8: 체인(Chain) 생성
    chain = (
        {"context": retriever, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )
    return chain

# 파일 업로드 후 retriever 생성 (작업시간이 오래 걸릴 예정...)
retriever = embed_file("textbooks/physics_textbook_trancated.pdf")
selected_model = "gpt-4o"
selected_prompt = "prompts/doc-rag.yaml"

rag_chain = create_chain(
    retriever, prompt_path=selected_prompt, model_name=selected_model
)
st.session_state["pdf_retriever"] = retriever
st.session_state["pdf_chain"] = rag_chain


# 사이드바 생성
with st.sidebar:

    st.text("AI튜터와 대화하기")
    messages = st.container(height=300)
        
    def print_messages():
        for chat_message in st.session_state["intro_1_tutor_messages"]:
           messages.chat_message(chat_message.role).write(chat_message.content)

    # 새로운 메시지를 추가
    def add_message(role, message):
        st.session_state["intro_1_tutor_messages"].append(ChatMessage(role=role, content=message))

    # 이전 대화 기록 출력
    print_messages()

    if user_input := st.chat_input("🤖 AI튜터에게 궁금한 내용을 물어보세요!", key="pdf_chat_input"):

        chain = st.session_state["pdf_chain"]

        if chain is not None:
            # 사용자의 입력
            messages.chat_message("user").write(user_input)
            # 스트리밍 호출
            response = chain.stream(user_input)
            with messages.chat_message("assistant"):
                # 빈 공간(컨테이너)을 만들어서, 여기에 토큰을 스트리밍 출력한다.
                container = st.empty()

                ai_answer = ""
                for token in response:
                    ai_answer += token
                    container.markdown(ai_answer)

            # 대화기록을 저장한다.
            add_message("user", user_input)
            add_message("assistant", ai_answer)


st.subheader("오늘 배운 물리 개념은?")
st.info("- 먼저 [힘과 운동] 소단원에서 배운 내용을 복습해봅시다:) \n - 문제를 풀면서 모르는게 있으면 왼쪽 사이드바의 🤖AI 튜터에게 물어보세요!")

# AI 튜터의 프롬프트 설정
TUTOR_SYSTEM_PROMPT = """당신은 친근하고 대화형 학습을 돕는 **물리 튜터**입니다. 항상 존댓말을 사용하며 긍정적이고 격려하는 태도로 일관된 대화를 유지하세요.  

다음 지침을 따라주세요:
1. 학생이 이해한 부분과 부족한 부분을 파악합니다.
2. 부족한 부분에 대해 다시 작성할 수 있도록 유도하는 피드백을 제공합니다.
3. 절대로 정답에 가까운 내용을 제공하지 마세요.
4. 세 문장을 넘지 않도록 대화를 생성하세요.  
5. 이모지를 적절히 사용하여 친근감을 줍니다"""

# 문제와 답변 정의
QUESTIONS = {
    'Q1_1': {
        'question': "안녕하세요! 저는 오늘 여러분과 함께 공부할 🧑🏻‍🏫 **AI 보조교사**입니다. \n\n먼저 오늘 배운 기본 개념부터 다시 떠올려볼까요? \n\n공을 발로 찰 때처럼 한 사람이 힘을 작용하기도 하지만 줄다리기처럼 여러 사람이 함께 힘을 작용할 때도 있죠. **이처럼 한 물체에 여러 힘이 동시에 작용할 때, 이 힘들과 같은 효과를 나타내는 하나의 힘을 무엇이라고 할까요?** (초성 힌트: ㅇㅉㅎ)",
        'answer': '알짜힘',
        'correct_feedback': "정확합니다!  알짜힘은 물체에 작용하는 모든 힘들을 하나로 합친 것이에요. 예를 들어, 줄다리기에서 양쪽에서 당기는 힘들을 모두 고려한 최종적인 힘이 바로 알짜힘이죠. \n\n이제 알짜힘의 다른 이름에 대해 알아볼까요?",
        'hint': "여러 힘을 모두 합쳐서 실제로 영향을 주는 진짜 힘이라는 의미를 가지고 있답니다."
    },
    'Q1_2': {
        'question': "**알짜힘은 다른 말로도 부르는데요, 그 용어가 무엇인지 아시나요?** (초성 힌트: ㅎㄹ)",
        'answer': '합력',
        'correct_feedback': "훌륭합니다!  알짜힘은 '합력'이라고도 부르죠. 여러 힘을 '합한 힘'이라는 의미에서 이런 이름이 붙었어요.",
        'hint': "여러 힘을 '합친다'는 의미가 담겨있답니다."
    },
    'Q2': {
        'question': "이제 뉴턴의 운동법칙에 대해 알아볼까요? \n\n**다음 키워드를 모두 사용해서 뉴턴 운동 제1법칙을 설명해주세요:**\n[물체, 알짜힘, 운동 상태]",
        'answer_check': lambda x: any(phrase.lower() in x.lower() for phrase in [
            "물체에 작용하는 알짜힘이 0일 때, 물체의 운동 상태가 변하지 않는다",
            "물체에 작용하는 알짜힘이 0일 때, 정지해 있는 물체는 계속 정지해 있고, 운동 중인 물체는 계속해서 등속도 운동을 한다",
            "물체에 작용하는 알짜힘이 0일 때, 물체가 현재의 운동 상태를 유지하려는 관성을 갖는다"
        ]),
        'correct_feedback': "정말 잘 설명했어요!  \n\n뉴턴 제1법칙은 '관성의 법칙'이라고도 불러요. 물체가 현재 상태를 유지하려는 성질을 '관성'이라고 하죠.",
        'hint': "알짜힘이 0일 때 물체는 어떻게 될까요? 물체의 운동 상태가 어떻게 변할지(또는 변하지 않을지) 생각해보세요."
    },
    'Q3': {
        'question': "마지막으로 뉴턴 운동 제2법칙입니다! \n\n**다음 키워드를 모두 사용해서 뉴턴 운동 제2법칙을 설명해주세요:**\n[물체, 알짜힘, 가속도, 질량]",
        'answer_check': lambda x: any(phrase.lower() in x.lower() for phrase in [
            "물체에 작용하는 알짜힘이 클수록 가속도가 크고, 물체의 질량이 클수록 가속도가 작아진다",
            "물체에 작용하는 알짜힘은 물체의 질량과 가속도의 곱과 같다",
            "물체의 가속도는 작용하는 알짜힘에 비례하고 질량에 반비례한다"
        ]),
        'correct_feedback': "완벽한 설명입니다!  \n\n수식으로 표현하면 F = ma가 되죠. 같은 힘을 작용해도 질량이 큰 물체는 작은 가속도로, 질량이 작은 물체는 큰 가속도로 운동하게 됩니다.",
        'hint': "알짜힘과 가속도는 어떤 관계가 있을까요? 그리고 질량이 커지면 가속도는 어떻게 될까요? 이 관계를 모두 포함해서 설명해보세요."
    },
    'End': {
        'question': "수고하셨습니다! 이제 다음 단계로 넘어갈 준비가 되었습니다.",
        'answer': None,
        'correct_feedback': None,
        'is_end': True
    }
}

def is_similar_answer(user_input, correct_answer):
    """오타를 허용하는 답변 체크 함수"""
    # 공백 제거 및 소문자 변환
    user_input = ''.join(user_input.lower().split())
    correct_answer = ''.join(correct_answer.lower().split())
    
    # 완전히 같으면 True
    if user_input == correct_answer:
        return True
    
    # 길이가 비슷하고 대부분의 글자가 일치하면 True
    if abs(len(user_input) - len(correct_answer)) <= 1:
        matches = sum(1 for a, b in zip(user_input, correct_answer) if a == b)
        return matches >= len(correct_answer) - 1
    
    return False

def get_tutor_response(user_answer, question_type, is_correct):
    """AI 튜터의 응답을 생성하는 함수"""
    client = OpenAI(api_key=st.session_state.api_key)
    current_q = QUESTIONS[question_type]
    
    if is_correct:
        return current_q['correct_feedback']
    
    # 오답일 경우 AI 튜터의 맞춤형 피드백 생성
    prompt = f"""학생이 다음 문제에 대해 틀린 답변을 했습니다:
    문제: {current_q['question']}
    학생 답변: {user_answer}
    
    힌트: {current_q.get('hint', '힌트를 참고하세요.')}
    
    위 상황에서 학생에게 해줄 수 있는 격려와 도움이 되는 피드백을 제공해주세요."""
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": TUTOR_SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        temperature=0.1,
        max_tokens=200
    )
    
    return response.choices[0].message.content

def check_answer_with_score(user_answer, question_type):
    """답변의 점수를 평가하는 함수"""
    client = OpenAI(api_key=st.session_state.api_key)
    current_q = QUESTIONS[question_type]
    
    prompt = f"""다음은 물리 문제와 학생의 답변입니다:

        문제: {current_q['question']}
        학생 답변: {user_answer}

        답변을 평가하고 점수(0-100)와 피드백을 제공해주세요. 다음 기준을 참고하세요:
        1. 키워드의 적절한 사용 (40점)
        2. 개념의 정확한 설명 (40점)
        3. 답변의 완성도 (20점)

        응답 형식:
        점수: [0-100의 숫자]
        피드백: [구체적인 피드백]"""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": TUTOR_SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        temperature=0.1,
        max_tokens=200
    )
    
    feedback = response.choices[0].message.content
    
    # 정규식을 사용하여 점수 추출
    score_match = re.search(r'점수:\s*(\d+)', feedback)
    if score_match:
        score = int(score_match.group(1))
    else:
        score = 0
    
    return score, feedback

def check_answer(user_answer, question_data):
    """정답 여부를 확인하는 함수"""
    if 'answer' in question_data:
        return is_similar_answer(user_answer, question_data['answer'])
    elif 'answer_check' in question_data:
        return question_data['answer_check'](user_answer)
    else:
        return False

def add_message_to_history(role, content, image_path=None):
    """대화 내용을 히스토리에 추가하는 함수"""
    message = {"role": role, "content": content}
    if image_path:  # 이미지 경로가 있을 때만 추가
        message["image"] = image_path
    st.session_state.chat_history.append(message)

def display_chat_history():
    """대화 기록을 화면에 표시하는 함수"""
    for message in st.session_state.chat_history:
        with chat_container.chat_message(message["role"]):
            st.write(message["content"])
            if "image" in message and message["image"]:  # 이미지가 있고 None이 아닐 때만 표시
                st.image(message["image"], use_container_width=True)

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
        
    # AI 응답 생성
    if 'answer' in current_q:
        is_correct = is_similar_answer(user_input, current_q['answer'])
        if is_correct:
            feedback = current_q['correct_feedback']
            
            # 정답일 때 이미지와 함께 피드백 추가
            image_path = None
            if st.session_state.current_question == 'Q2':
                image_path = "images/explain_4.png"
            elif st.session_state.current_question == 'Q3':
                image_path = "images/explain_5.png"
            
            add_message_to_history("assistant", feedback, image_path)
            
            # 다음 문제로 이동
            next_questions = {'Q1_1': 'Q1_2', 'Q1_2': 'Q2', 'Q2': 'Q3', 'Q3': 'End'}
            next_q = next_questions[st.session_state.current_question]
            
            if next_q:
                st.session_state.current_question = next_q
                if next_q != 'End':
                    add_message_to_history("assistant", QUESTIONS[next_q]['question'])
                else:
                    add_message_to_history("assistant", QUESTIONS['End']['question'])
    else:
        if st.session_state.current_question in ['Q2', 'Q3']:
            score, feedback = check_answer_with_score(user_input, st.session_state.current_question)
            add_message_to_history("assistant", feedback)
            
            if score >= 70:
                # 이미지와 함께 다음 문제로 이동
                if st.session_state.current_question == 'Q2':
                    image_path = "images/explain_4.png"
                    add_message_to_history("assistant", "", image_path)
                    next_q = 'Q3'
                    st.session_state.current_question = next_q
                    add_message_to_history("assistant", QUESTIONS[next_q]['question'])
                elif st.session_state.current_question == 'Q3':
                    image_path = "images/explain_5.png"
                    add_message_to_history("assistant", "", image_path)
                    st.session_state.current_question = 'End'
                    add_message_to_history("assistant", QUESTIONS['End']['question'])

    # 상태 메시지 제거
    status_container.empty()
    st.rerun()

# 문제 상태 관리
if 'current_question' not in st.session_state:
    st.session_state.current_question = 'Q1_1'
    st.session_state.show_next_button = False
    st.session_state.correct_answer_given = False
    st.session_state.current_tries = 0
    st.session_state.chat_history = []
    st.session_state.is_processing = False
    st.session_state.last_input = None

# Progress bar 계산 및 표시
total_questions = len(QUESTIONS)
current_question_index = list(QUESTIONS.keys()).index(st.session_state.current_question)
progress = (current_question_index) / (total_questions - 1)

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
    st.progress(progress, text=f"들어가기 진행률: {progress*100:.0f}%")

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
placeholder = "🧑🏻‍🏫 AI 보조교사의 질문에 대한 답변을 작성해주세요." if not is_end else "복습이 완료되었습니다."
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
