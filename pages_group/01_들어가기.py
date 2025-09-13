import os
import re
import streamlit as st
import pandas as pd

from openai import OpenAI

from langchain_core.messages.chat import ChatMessage
from modules.retrieval import embed_file, create_chain
from langchain_teddynote import logging


os.environ["LANGCHAIN_TRACING_V2"] = st.secrets["LANGCHAIN_TRACING_V2"]
os.environ["LANGCHAIN_API_KEY"] = st.secrets["LANGCHAIN_API_KEY"]
os.environ["LANGCHAIN_ENDPOINT"] = st.secrets["LANGCHAIN_ENDPOINT"]
os.environ["LANGCHAIN_PROJECT"] = st.secrets["LANGCHAIN_PROJECT"]

st.session_state.api_key = st.secrets["openai_api_key"]

TEXTBOOK_FILE_PATH = "src/textbooks/physics_textbook.pdf"

TUTOR_OPENAI_MODEL = "gpt-4o"
RAG_OPENAI_MODEL = "gpt-4o"
RAG_SYSTEM_PROMPT = "prompts/doc-rag-scaffold.yaml"

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


# 파일 업로드 후 retriever 생성 (작업시간이 오래 걸릴 예정...)
if "pdf_retriever" not in st.session_state:
    retriever = embed_file(TEXTBOOK_FILE_PATH)
    st.session_state["pdf_retriever"] = retriever

if "pdf_chain" not in st.session_state and st.session_state["pdf_retriever"]:
    retriever = st.session_state["pdf_retriever"]
    st.session_state["pdf_chain"] = create_chain(
        retriever, prompt_path=RAG_SYSTEM_PROMPT, model_name=RAG_OPENAI_MODEL
    )

######################################
########### Mainpage Logic ###########
######################################
st.title("들어가기 🚀")

st.subheader("오늘 배운 물리 개념은?")
st.info("- 먼저 **[1. 여러 가지 운동]** 과 **[2. 힘과 운동]** 소단원에서 배운 내용을 복습해봅시다:) \n - 궁금한게 있으면 왼쪽 사이드바의 **교과서 찾기**를 활용해보세요. \n - 아래 2개 탭을 모두 마치고 다음 단계로 넘어가주세요!")

st.image("src/images/find_tab_guide.png", width=500)

tab1, tab2 = st.tabs(["1. 여러 가지 운동", "2. 힘과 운동"])

# tab 전환 감지 및 상태 업데이트
if tab1:
    st.session_state['current_tab'] = 'tab1'
if tab2:
    st.session_state['current_tab'] = 'tab2'

########### TAB 1 ###########
with tab1:
    st.write("**Q1. 놀이공원에서 볼 수 있는 여러 가지 놀이 기구들의 운동 방향과 속력 변화를 표에 정리해봅시다.**")
    st.write("([운동 방향]과 [속력] 셀을 더블클릭한 후 알맞은 설명을 골라주세요)")
    df = pd.DataFrame(
        {
            "Type" : ["자이로드롭", "대관람차", "롤러코스터", "바이킹"],
            "Image": ["https://dimg.donga.com/ugc/CDB/SODA/Article/57/e0/f9/a4/57e0f9a4248cd2738de6.gif", "https://mblogthumb-phinf.pstatic.net/MjAyNDAxMTJfMjM3/MDAxNzA1MDQxNTI4NTI5.H9ncgGIDHPaCqa0i3Mz-2s8NU-qvEye8YQwlSQaFWZUg.wDDf8kJoDCbWyuVEBEqkzxfxQCv5GnNAMYw0Bo4nZnIg.GIF.onnamong/743084218.gif?type=w800", "https://media2.giphy.com/media/v1.Y2lkPTc5MGI3NjExMDM2ZTRueWxqMW00emRyanIxaGVwdGx4amR2aW5scDNnYnMzbTg4YiZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/WqSCrUOEWQpWC8JGNg/giphy.webp", "https://mblogthumb-phinf.pstatic.net/MjAyMjEyMjhfMTMx/MDAxNjcyMTYzMDc2Mzc3.RACWbUSQ5ys66npAKl1ABuFkloP9bs3D3Hg6Hv0rhG0g.z4ZBQI_SRDXNCaO8v51EZrYxIkCwLcnawqYXJjqunrsg.GIF.mok5022/3546279707.gif?type=w800"],
            "Direction": [None, None, None, None],
            "Speed": [None, None, None, None]
        }
    )

    column_configuration = {
        "Type": st.column_config.TextColumn("놀이 기구", disabled=True),
        "Image": st.column_config.ImageColumn("이미지 (더블클릭해서 확대해보세요)"),
        "Direction": st.column_config.SelectboxColumn(
            "운동 방향", options=["변한다", "일정하다"]
        ),
        "Speed": st.column_config.SelectboxColumn(
            "속력", options=["변한다", "일정하다"]
        ),
    }

    edited_df = st.data_editor(
        data=df,
        column_config=column_configuration,
        use_container_width=True,
        hide_index=True,
        num_rows="fixed",
        )

    st.session_state.q1 = False
    info_q1 = st.empty()
    if edited_df.notnull().all().all():
        if edited_df.iloc[0, 2] == "일정하다":
            if edited_df.iloc[0, 3] == "변한다":         
                if edited_df.iloc[1, 2] == "변한다":
                    if edited_df.iloc[1, 3] == "일정하다":
                        if edited_df.iloc[2, 2] == "변한다":
                            if edited_df.iloc[2, 3] == "변한다":
                                if edited_df.iloc[3, 2] == "변한다":
                                    if edited_df.iloc[3, 3] == "변한다":
                                        st.session_state.q1 = True
                                        info_q1.success("정답입니다!")
                                        if not st.session_state.balloons_t1_q1:
                                            st.balloons()
                                            st.session_state.balloons_t1_q1 = True
        if st.session_state.q1:
            info_q1.success("정답입니다!")
        else:
            info_q1.error("틀렸습니다. 다시 시도하세요.")

    st.write("")
    st.write("") 

    st.write("**Q2. 놀이 기구의 운동을 다음과 같이 분류해 봅시다.**")
    st.write("(각 놀이 기구는 중복없이 한가지에만 포함됩니다)")
    options_1 = st.multiselect(
        "속력만 변하는 운동",
        ["자이로드롭", "대관람차", "롤러코스터", "바이킹"],
    )
    options_2 = st.multiselect(
        "운동 방향만 변하는 운동",
        ["자이로드롭", "대관람차", "롤러코스터", "바이킹"],
    )
    options_3 = st.multiselect(
        "속력과 운동 방향이 모두 변하는 운동",
        ["자이로드롭", "대관람차", "롤러코스터", "바이킹"],
    )

    st.session_state.q2 = False
    info_q2 = st.empty()
    if options_1 and options_2 and options_3:
        if options_1 == ["자이로드롭"]:
            if options_2 == ["대관람차"]:
                if options_3 == ["롤러코스터", "바이킹"] or options_3 == ["바이킹", "롤러코스터"]:
                    st.session_state.q2 = True
                    info_q2.success("정답입니다!")
                    if not st.session_state.balloons_t1_q2:
                        st.balloons()
                        st.session_state.balloons_t1_q2 = True
        if st.session_state.q2:
            info_q2.success("정답입니다!")
        else:
            info_q2.error("틀렸습니다. 다시 시도하세요.")

    if st.session_state.q1 and st.session_state.q2:
        st.subheader("**핵심 정리!**")
        st.info("속력이 변하는 운동, 운동 방향이 변하는 운동, 속력과 운동 방향이 모두 변하는 운동은 모두 **가속도 운동**이다.")
        st.image("src/images/explain_2.png")
        
        # tab1 완료 시 다음 tab으로 안내
        st.success("🎉 Tab 1 완료! 이제 '힘과 운동' 탭으로 이동해주세요.")

########### TAB 2 ###########
with tab2:
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
        'Q1': {
            'question': "안녕하세요! 저는 오늘 여러분과 함께 공부할 **AI 선생님**입니다. \n\n먼저 오늘 배운 기본 개념부터 다시 떠올려볼까요? \n\n공을 발로 찰 때처럼 한 사람이 힘을 작용하기도 하지만 줄다리기처럼 여러 사람이 함께 힘을 작용할 때도 있죠. **이처럼 한 물체에 여러 힘이 동시에 작용할 때, 이 힘들과 같은 효과를 나타내는 하나의 힘을 무엇이라고 할까요?** (초성 힌트: ㅇㅉㅎ 또는 ㅎㄹ)",
            'answer_check': lambda x: any(phrase.lower() in x.lower() for phrase in ['알짜힘', '합력']),
            'correct_feedback': "정확합니다!  알짜힘(또는 합력)은 물체에 작용하는 모든 힘들을 하나로 합친 것이에요. 예를 들어, 줄다리기에서 양쪽에서 당기는 힘들을 모두 고려한 최종적인 힘이 바로 알짜힘(또는 합력)이죠. \n\n이제 뉴턴의 운동법칙에 대해 알아볼까요?",
            'hint': "실제로 영향을 주는 '알짜배기' 힘이라는 의미를 가지고 있답니다. 또는 여러 힘을 '합친다'는 의미가 담겨있기도 하구요."
        },
        'Q2': {
            'question': "이제 뉴턴의 운동법칙에 대해 알아볼까요? \n\n**다음 키워드를 모두 사용해서 뉴턴 운동 제1법칙을 설명해주세요:**\n[물체, 알짜힘, 운동 상태]",
            'answer_check': lambda x: any(phrase.lower() in x.lower() for phrase in [
                "물체에 작용하는 알짜힘이 0일 때, 물체의 운동 상태가 변하지 않는다",
                "물체에 작용하는 알짜힘이 0이면 물체는 원래의 운동 상태를 유지한다",
                "물체에 작용하는 알짜힘이 0일 때, 물체의 원래의 운동 상태를 유지한다",
                "물체에 알짜힘이 작용하지 않으면, 물체는 원래 하고 있던 운동 상태를 그대로 유지한다.",
                "물체는 알짜힘이 0일 때, 현재의 운동 상태를 바꾸지 않고 계속 유지한다.",
                "정지해 있던 물체는 계속 정지하고, 운동 중인 물체는 알짜힘이 없을 때 등속 직선 운동을 한다.",
                "물체에 작용하는 알짜힘이 없다면, 물체는 관성에 의해 현재의 운동 상태를 그대로 유지하려 한다.",
                "물체에 작용하는 알짜힘이 0일 때, 정지해 있는 물체는 계속 정지해 있고, 운동 중인 물체는 계속해서 등속도 운동을 한다",
                "물체에 작용하는 알짜힘이 0일 때, 물체가 현재의 운동 상태를 유지하려는 관성을 갖는다",
            ]),
            'correct_feedback': "정말 잘 설명했어요!  \n\n뉴턴 제1법칙은 '관성의 법칙'이라고도 불러요. 물체가 현재 상태를 유지하려는 성질을 '관성'이라고 하죠.",
            'hint': "알짜힘이 0일 때 물체는 어떻게 될까요? 물체의 운동 상태가 어떻게 변할지(또는 변하지 않을지) 생각해보세요."
        },
        'Q3': {
            'question': "마지막으로 뉴턴 운동 제2법칙입니다! \n\n**다음 키워드를 모두 사용해서 뉴턴 운동 제2법칙을 설명해주세요:**\n[물체, 알짜힘, 가속도, 질량]",
            'answer_check': lambda x: any(phrase.lower() in x.lower() for phrase in [
                "물체에 작용하는 알짜힘이 클수록 가속도가 크고, 물체의 질량이 클수록 가속도가 작아진다",
                "물체에 작용하는 알짜힘은 물체의 질량과 가속도의 곱과 같다",
                "물체의 가속도는 작용하는 알짜힘에 비례하고 질량에 반비례한다",
                "물체에 작용하는 알짜힘은 물체를 가속시키며, 그 크기는 질량과 가속도의 곱으로 나타낼 수 있다.",
                "물체의 가속도는 알짜힘에 비례하고 질량에 반비례한다. 즉, 힘이 크면 가속도도 커지고, 질량이 크면 가속도는 작아진다.",
                "물체에 알짜힘이 작용하면, 물체는 질량에 반비례하는 크기의 가속도를 얻는다.",
                "물체의 운동 상태가 변하는 정도, 즉 가속도는 알짜힘의 크기에 비례하고, 물체의 질량에 따라 그 크기가 달라진다.",
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
        try:
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
                model="gpt-4.1",
                messages=[
                    {"role": "system", "content": TUTOR_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=200
            )
            
            return response.choices[0].message.content
        except Exception as e:
            st.error(f"AI 선생님 응답 생성 중 오류: {str(e)}")
            return "죄송합니다. 피드백을 생성하는 중에 오류가 발생했습니다. 다시 시도해주세요."

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
            model=TUTOR_OPENAI_MODEL,
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
            if message["role"] == "assistant":
                with chat_container.chat_message(message["role"], avatar=AI_AVATAR):
                    st.write(message["content"])
            else:
                with chat_container.chat_message(message["role"]):
                    st.write(message["content"])
            if "image" in message and message["image"]:  # 이미지가 있고 None이 아닐 때만 표시
                with st.popover("교과서 본문"):
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
                # 오답일 경우 AI 튜터의 맞춤형 피드백 생성
                feedback = get_tutor_response(user_input, st.session_state.current_question, False)
                add_message_to_history("assistant", feedback)
        elif 'answer_check' in current_q:
            # answer_check 함수를 사용하는 경우 (Q1, Q2, Q3)
            is_correct = current_q['answer_check'](user_input)
            if is_correct:
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
                # 오답일 경우 AI 튜터의 맞춤형 피드백 생성
                feedback = get_tutor_response(user_input, st.session_state.current_question, False)
                add_message_to_history("assistant", feedback)
        else:
            if st.session_state.current_question in ['Q2', 'Q3']:
                score, feedback = check_answer_with_score(user_input, st.session_state.current_question)
                add_message_to_history("assistant", feedback)
                
                if score >= 70:
                    # 이미지와 함께 다음 문제로 이동
                    if st.session_state.current_question == 'Q2':
                        image_path = "src/images/explain_4.png"
                        add_message_to_history("assistant", "", image_path)
                        next_q = 'Q3'
                        st.session_state.current_question = next_q
                        add_message_to_history("assistant", QUESTIONS[next_q]['question'])
                    elif st.session_state.current_question == 'Q3':
                        image_path = "src/images/explain_5.png"
                        add_message_to_history("assistant", "", image_path)
                        st.session_state.current_question = 'End'
                        add_message_to_history("assistant", QUESTIONS['End']['question'])

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
with st.sidebar:

    st.write("⏬ 혼자서 문제 풀기 너무 어렵다면? ⏬")

    toggle_ai_helper = st.toggle("**교과서 찾기** 사용하기", value=False)

    if toggle_ai_helper:

        st.warning("단, 스스로 충분히 고민해도 정말 모르겠을 때 사용하기!")

        st.text("교과서와 '대화'해봅시다")
        messages = st.container(height=300)
            
        def print_messages():
            for chat_message in st.session_state["intro_1_tutor_messages"]:
                messages.chat_message(chat_message.role).write(chat_message.content)

        # 새로운 메시지를 추가
        def add_message(role, message):
            st.session_state["intro_1_tutor_messages"].append(ChatMessage(role=role, content=message))

        # 이전 대화 기록 출력
        print_messages()

        if user_input := st.chat_input("궁금한 내용을 물어보세요!", key="pdf_chat_input"):

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
