import streamlit as st
from typing import List, Tuple

from langchain_core.messages.chat import ChatMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI
from langchain_teddynote.prompts import load_prompt


selected_prompt = "prompts/keyword-extract.yaml"


# 체인 생성
def create_chain(prompt_filepath):
    # prompt 적용
    prompt = load_prompt(prompt_filepath, encoding="utf-8")

    # GPT
    llm = ChatOpenAI(model_name="gpt-4.1-mini", temperature=0, api_key=st.session_state.api_key)

    # 출력 파서
    output_parser = StrOutputParser()

    # 체인 생성
    chain = prompt | llm | output_parser
    return chain


def parsing_messages(conv_history: List[ChatMessage]) -> str:
    conv_context = []

    for chat in conv_history:
        if chat.role == "user":
            conv_context.append(f"사용자: {chat.content}")
        elif chat.role == "assistant":
            conv_context.append(f"AI챗봇: {chat.content}")
        else:
            continue
    
    return "\n".join(conv_context)



def create_keyword(conv_history: List[ChatMessage], keyword_section='02_thinking') -> List[str]:
    # chain 을 생성
    chain = create_chain(selected_prompt) #, task=task_input)

    if not conv_history:
        if keyword_section == '02_thinking':
            message_context = "대화 기록이 아직 없습니다. 다음의 두 질문을 추천 질문으로 제시하세요. \n 1. 배운 개념이 이 문제에 어떻게 적용될 수 있는지 구체적인 예를 들어줄 수 있어? / 2. 등속 원운동이 어떤 건지 관련된 개념과 함께 설명해 줄 수 있어?"
        else:
            message_context = "대화 기록이 아직 없습니다. 다음의 두 질문을 추천 질문으로 제시하세요. \n 1. 힘의 방향을 현재 궤도와 다르게 설정해 본다면, 물체의 운동 궤적이 어떻게 변할까요? / 2. 시뮬레이션에서 힘의 방향을 어떻게 설정해야 원운동이 유지될 수 있을까요? 입력창에 직접 작성해 보세요."
    else:
        message_context = parsing_messages(conv_history)

    response = chain.invoke({"context": message_context})

    # res = """추천 질문 1: 무중력 상태에서 우주선의 속도를 조절하는 방법은 무엇인가요? // 추천 질문 2: 우주선의 궤도를 변경하려면 어떤 추가적인 힘이 필요한가요?"""

    q1 = response.split("//")[0].split(":")[-1].strip()
    q2 = response.split("//")[-1].split(":")[-1].strip()

    return [q1, q2]


def create_keyword_textbook(conv_history: List[ChatMessage]) -> List[str]:
    # chain 을 생성
    chain = create_chain(selected_prompt) #, task=task_input)

    if not conv_history:
        message_context = "(개념을 더 자세히 설명해주세요 / 이 개념이 실생활에서 어떻게 쓰이나요? / 다른 상황에서도 이 개념이 쓰이나요?)"
    else:
        message_context = parsing_messages(conv_history)

    response = chain.invoke({"context": message_context})

    # res = """추천 질문 1: 무중력 상태에서 우주선의 속도를 조절하는 방법은 무엇인가요? // 추천 질문 2: 우주선의 궤도를 변경하려면 어떤 추가적인 힘이 필요한가요?"""

    q1 = response.split("//")[0].split(":")[-1].strip()
    q2 = response.split("//")[-1].split(":")[-1].strip()

    return [q1, q2]