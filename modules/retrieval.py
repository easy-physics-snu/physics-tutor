import os
import streamlit as st

from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PDFPlumberLoader
from langchain_community.vectorstores import FAISS
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from langchain_teddynote.prompts import load_prompt

# API KEY 정보로드
# config = settings.load_config()
# if "api_key" in config:
#     st.session_state.api_key = config["api_key"]
#     st.write(f'사용자 입력 API키 : {st.session_state.api_key[-5:]}')
# else : 
#     st.session_state.api_key = st.secrets["openai_api_key"]
#     st.write(f'API키 : {st.secrets["openai_api_key"][-5:]}')


st.session_state.api_key = st.secrets["openai_api_key"]


def init_setting():
    # 캐시 디렉토리 생성
    if not os.path.exists(".cache"):
        os.mkdir(".cache")

    # 파일 업로드 전용 폴더
    if not os.path.exists(".cache/files"):
        os.mkdir(".cache/files")

    if not os.path.exists(".cache/embeddings"):
        os.mkdir(".cache/embeddings")

    # 처음 1번만 실행하기 위한 코드
    if "messages" not in st.session_state:
        # 대화기록을 저장하기 위한 용도로 생성한다.
        st.session_state["messages"] = []

    if "pdf_chain" not in st.session_state:
        # 아무런 파일을 업로드 하지 않을 경우
        st.session_state["pdf_chain"] = None

    if "pdf_retriever" not in st.session_state:
        st.session_state["pdf_retriever"] = None


# 파일을 캐시 저장(시간이 오래 걸리는 작업을 처리할 예정)
@st.cache_resource(show_spinner=False)
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
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=50)
    split_documents = text_splitter.split_documents(docs)

    # 단계 3: 임베딩(Embedding) 생성
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small", openai_api_key = st.session_state.api_key)

    # 단계 4: DB 생성(Create DB) 및 저장
    # 벡터스토어를 생성합니다.
    vectorstore = FAISS.from_documents(documents=split_documents, embedding=embeddings)

    # 단계 5: 검색기(Retriever) 생성
    # 문서에 포함되어 있는 정보를 검색하고 생성합니다.
    retriever = vectorstore.as_retriever()
    return retriever


# 체인 생성
def create_chain(retriever, prompt_path, model_name):
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
