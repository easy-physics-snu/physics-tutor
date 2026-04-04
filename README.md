# Easy Physics - AI 기반 물리 튜터링 시스템

물리학 원운동 단원 학습을 위한 지능형 튜터링 시스템(ITS)입니다. Productive Failure 학습 이론을 기반으로 학습자의 자기 주도적 탐구를 지원하며, LLM 기반의 동적 교수 전략을 통해 맞춤형 피드백을 제공합니다.

---

## 목차

- [프로젝트 개요](#프로젝트-개요)
- [시스템 아키텍처](#시스템-아키텍처)
- [기술 스택](#기술-스택)
- [프로젝트 구조](#프로젝트-구조)
- [핵심 기능](#핵심-기능)
- [AI 교수 전략 시스템 (DMS)](#ai-교수-전략-시스템-dms)
- [데이터베이스 구조](#데이터베이스-구조)
- [설치 및 실행](#설치-및-실행)
- [환경 설정](#환경-설정)

---

## 프로젝트 개요

### 교육 목표

- **대상 단원**: 물리학 - 원운동과 구심력
- **학습 목표**:
  - 속도(벡터)와 속력(스칼라)의 구분
  - 원운동에서 방향 변화에 따른 가속도 이해
  - 구심력의 정의와 방향 (원 중심을 향함) 이해
  - 뉴턴 제2법칙(F=ma) 적용

### 교육 이론 기반

**Productive Failure** 학습 이론을 적용하여 5단계 학습 경로를 설계:

```
Phase 1 (들어가기) → Phase 2 (생각하기) → Phase 3 (실험하기) → Phase 4 (돌아보기) → Phase 5 (적용하기)
     소개              Peer 모드            Peer 모드           Tutor 모드          Tutor 모드
                    (자연스러운 실패)     (가설 검증)         (오개념 수정)        (지식 전이)
```

---

## 시스템 아키텍처

### 전체 아키텍처

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Frontend (Streamlit)                            │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐               │
│  │ Phase 1 │ │ Phase 2 │ │ Phase 3 │ │ Phase 4 │ │ Phase 5 │               │
│  │들어가기 │ │생각하기 │ │실험하기 │ │돌아보기 │ │적용하기 │               │
│  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘               │
│       │           │           │           │           │                     │
│       └───────────┴───────────┴─────┬─────┴───────────┘                     │
└─────────────────────────────────────┼───────────────────────────────────────┘
                                      │
┌─────────────────────────────────────┼───────────────────────────────────────┐
│                          Intermediary (조율 계층)                            │
│                                     │                                        │
│  ┌──────────────────────────────────┼──────────────────────────────────────┐│
│  │                    DMS (Didactic Management System)                     ││
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────────┐     ││
│  │  │ Intent      │→ │ Act         │→ │ Prompt                      │     ││
│  │  │ Assessor    │  │ Selector    │  │ Generator                   │     ││
│  │  │ (학습자 평가) │  │ (전략 선택)  │  │ (프롬프트 생성)              │     ││
│  │  └─────────────┘  └─────────────┘  └─────────────────────────────┘     ││
│  └──────────────────────────────────┬──────────────────────────────────────┘│
└─────────────────────────────────────┼───────────────────────────────────────┘
                                      │
┌─────────────────────────────────────┼───────────────────────────────────────┐
│                              External Services                               │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────────────────────┐    │
│  │ OpenAI API  │     │ AWS         │     │ LangSmith                   │    │
│  │ (GPT-4)     │     │ DynamoDB    │     │ (Monitoring)                │    │
│  └─────────────┘     └─────────────┘     └─────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 메시지 처리 흐름

```
학생 입력 (텍스트/이미지)
         │
         ▼
┌─────────────────────┐
│   IntentAssessor    │  ← LLM이 학생 발화 분석
│   (학습 상태 평가)   │     13가지 학습 상태 중 2개 선택
└──────────┬──────────┘
           │ assessment_codes: ['b', 'f']
           ▼
┌─────────────────────┐
│   AIActSelector     │  ← 평가 결과 기반 교수 전략 선택
│   (교수 전략 선택)   │     Phase별 다른 선택 로직
└──────────┬──────────┘
           │ acts: [PeerAct.Peer_CC]
           ▼
┌─────────────────────┐
│  AIPromptGenerator  │  ← Act에 맞는 시스템 프롬프트 생성
│  (프롬프트 생성)     │
└──────────┬──────────┘
           │ messages: [{role, content}, ...]
           ▼
┌─────────────────────┐
│    OpenAI GPT-4     │  ← 맞춤형 피드백 생성
│    API 호출         │
└──────────┬──────────┘
           │
           ▼
    AI 피드백 응답
```

---

## 기술 스택

### Frontend
| 기술 | 버전 | 용도 |
|------|------|------|
| Streamlit | 1.40.1 | 웹 앱 프레임워크 |
| streamlit-drawable-canvas | 0.9.3 | 캔버스 드로잉 (화살표 그리기) |
| Pillow | 11.0.0 | 이미지 처리 |
| Altair | 5.4.1 | 데이터 시각화 |

### Backend & LLM
| 기술 | 버전 | 용도 |
|------|------|------|
| OpenAI | 1.54.5 | GPT-4 API |
| LangChain | 0.3.7 | LLM 체인 구성 |
| langchain-openai | 0.2.9 | OpenAI 통합 |
| LangGraph | 0.2.52 | 에이전트 워크플로우 |
| Pydantic | 2.9.2 | 데이터 검증 |

### Database & Storage
| 기술 | 버전 | 용도 |
|------|------|------|
| AWS DynamoDB | - | 메시지/세션 저장 |
| boto3 | 1.40.65 | AWS SDK |
| FAISS | 1.9.0 | 벡터 검색 (RAG) |

### 텍스트 처리
| 기술 | 버전 | 용도 |
|------|------|------|
| NLTK | 3.9.1 | 자연어 처리 |
| kiwipiepy | 0.20.1 | 한국어 형태소 분석 |
| rank-bm25 | 0.2.2 | BM25 검색 |

### 문서 처리
| 기술 | 버전 | 용도 |
|------|------|------|
| PyPDF2 | 3.0.1 | PDF 처리 |
| pdfplumber | 0.11.4 | PDF 텍스트 추출 |
| pdf2image | 1.17.0 | PDF → 이미지 변환 |

---

## 프로젝트 구조

```
physics-tutor/
│
├── app.py                              # Streamlit 메인 앱 (네비게이션 설정)
├── requirements.txt                    # Python 의존성 목록
├── poetry.lock                         # Poetry 패키지 버전 록
│
├── pages_group/                        # Streamlit 멀티페이지 앱
│   ├── 00_Main.py                     # 로그인 페이지
│   ├── 01_들어가기.py                  # Phase 1: 소개 및 초기 탐색
│   ├── 02_생각하기.py                  # Phase 2: Peer 학습 동료 모드
│   ├── 03_실험하기.py                  # Phase 3: 시뮬레이션 기반 가설 검증
│   ├── 04_돌아보기.py                  # Phase 4: Tutor 피드백
│   └── 05_적용하기.py                  # Phase 5: 지식 전이
│
├── dms/                                # Didactic Management System
│   ├── Intermediary.py                 # Phase별 컴포넌트 조율자
│   └── prompts/
│       ├── AIPromptGenerator.py        # 프롬프트 생성 (Phase 2/3/4)
│       ├── AIActSelector.py            # 교수 전략 선택 로직
│       ├── AIActTaxonomy.py            # Peer/Tutor Act 분류 체계
│       ├── IntentAssessor.py           # 학생 의도 평가 (LLM 기반)
│       └── IntentTaxonomy.py           # 학생 학습 상태 분류 기준
│
├── modules/                            # 핵심 기능 모듈
│   ├── dynamo.py                       # AWS DynamoDB 관리
│   ├── retrieval.py                    # RAG (문서 검색 및 임베딩)
│   ├── ExplorationTutor.py             # Phase 1 탐구 튜터
│   ├── ConsolidationTutor.py           # Phase 2 통합 튜터
│   ├── multimodal.py                   # 멀티모달 LLM 체인
│   ├── prompts.py                      # 각 Phase별 시스템 프롬프트
│   ├── utils.py                        # 이미지 처리 및 캔버스 유틸
│   └── keywords.py                     # 키워드 추출
│
├── factory/                            # 설정 및 초기화
│   ├── 01_login.py                     # 로그인 관련
│   ├── 01_PDF.py                       # PDF 처리
│   ├── 01_HWP.py                       # HWP 문서 처리
│   └── 03_Database.py                  # 데이터베이스 설정
│
├── simulation/                         # 물리 시뮬레이션
│   ├── simulation.py                   # 시뮬레이션 로직
│   ├── simulation_user.py              # 사용자 입력 기반 시뮬레이션
│   ├── circular.html                   # 원운동 시각화
│   └── circular-motion-sim_responsive.html
│
├── src/                                # 리소스 파일
│   ├── textbooks/                      # 교재 PDF
│   ├── images/                         # UI 이미지 및 문제 이미지
│   └── draw_images/                    # 그리기용 이미지
│
└── .streamlit/
    ├── config.toml                     # Streamlit 설정
    └── secrets.toml                    # API 키 및 민감 정보
```

---

## 핵심 기능

### 1. 5단계 학습 경로

| Phase | 이름 | AI 역할 | 목적 |
|-------|------|---------|------|
| 1 | 들어가기 | - | 개념 소개, 문제 상황 제시 |
| 2 | 생각하기 | **Peer** (학습 동료) | 자기 주도적 탐구, 자연스러운 실패 경험 |
| 3 | 실험하기 | **Peer** (학습 동료) | 시뮬레이션을 통한 가설 검증 |
| 4 | 돌아보기 | **Tutor** (교사) | 오개념 수정 및 개념 정교화 |
| 5 | 적용하기 | **Tutor** (교사) | 학습 내용의 다른 맥락 전이 |

### 2. 멀티모달 상호작용

```python
# modules/multimodal.py
class MultiModalwithHistory:
    """텍스트 + 이미지 입력을 LLM이 처리하도록 지원"""

    def invoke(self, messages, image_data=None):
        # 이미지를 base64로 인코딩
        # LangChain의 HumanMessage에 이미지 내용 추가
        # LLM이 이미지를 분석하여 피드백 생성
```

- **캔버스 드로잉**: 학생이 화살표를 그려 힘의 방향 표현
- **이미지 합성**: 문제 상황 이미지 + 학생 드로잉 합성
- **시뮬레이션**: HTML 기반 원운동 시뮬레이션

### 3. 이미지 처리

```python
# modules/utils.py
def overlay_png_and_np_from_image(base_image, overlay_np, overlay_alpha=255):
    """기본 이미지(문제 상황)에 학생의 드로잉(화살표)을 합성"""
    # Alpha 채널로 투명도 조절

def load_and_optimize_canvas_image(image_path, target_size=(500, 500)):
    """캔버스 이미지 최적화 및 캐싱"""
```

---

## AI 교수 전략 시스템 (DMS)

### 개요

DMS(Didactic Management System)는 학습자의 상태를 실시간으로 평가하고, 적절한 교수 전략을 선택하여 맞춤형 피드백을 생성하는 핵심 시스템입니다.

### 구성 요소

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│ IntentAssessor  │ ──→ │ AIActSelector   │ ──→ │AIPromptGenerator│
│                 │     │                 │     │                 │
│ 학습자 상태     │     │ 교수 전략       │     │ 프롬프트        │
│ 13가지 분류     │     │ Peer/Tutor Act  │     │ 동적 생성       │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

### 1. IntentAssessor - 학습자 상태 평가

LLM을 사용하여 학습자의 발화를 분석하고 13가지 학습 상태 중 2개를 선택합니다.

```python
# dms/prompts/IntentAssessor.py
class IntentAssessor:
    def assess(self, conversation_history, student_prompt):
        # LLM이 학습자 상태를 JSON으로 반환
        # 예: {"codes": ["b", "f"], "reasoning": "..."}
```

#### 13가지 학습 상태 분류 (IntentTaxonomy)

| 코드 | 카테고리 | 상태 설명 | 예시 발화 |
|------|---------|----------|----------|
| **a** | 선행지식 부재 | 기초 개념 부족 | "어디서부터 설명해야 할지 모르겠어" |
| **b** | 오개념 표출 | 부정확한 과학 개념 | "등속 원운동은 힘이 작용하지 않아" |
| **c** | 경험 과잉 일반화 | 일상 경험으로만 해석 | "자동차가 커브 돌 때처럼" |
| **d** | 추상적 개념 부족 | 힘, 에너지, 가속도 이해 부족 | "속력은 같은데 가속도가 있다고?" |
| **e** | 대안 가설 무시 | 다른 설명 거부 | "내 가설이 완벽해" |
| **f** | 논리적 설명 부족 | 근거나 인과관계 설명 어려움 | "그냥 느낌상 그럴 것 같아" |
| **g** | 과학적 모델 이해 부족 | 물리 모델 적용 어려움 | "가속도가 속도를 만드는 건가?" |
| **h** | 지식의 단편화 | 관련 개념 연결 못함 | "원운동을 배운 적이 없어" |
| **i** | 맥락 의존적 지식 | 다른 맥락에 개념 미적용 | "우주에서는 다른 힘이 작용할 거야" |
| **j** | 과학 불안 | 과학 활동 불안감 | "물리 진짜 모르겠어" |
| **k** | 동기 저하 | 학습 의미를 찾지 못함 | "이거 왜 해? 지루해" |
| **l** | 흥미·참여 부족 | 소극적 반응 | "글쎄", "ㅇㅋ" |
| **m** | 부정적 태도 | 탐구 학습 회피 | "그냥 답 알려줘" |

### 2. AIActSelector - 교수 전략 선택

평가 결과를 바탕으로 Phase에 맞는 교수 전략(Act)을 선택합니다.

#### Peer Act (Phase 2-3: 학습 동료 역할)

```python
# dms/prompts/AIActTaxonomy.py
class PeerAct(Enum):
    Peer_PR = 11    # Problem Recognition - 문제 인식 촉진
    Peer_HS = 12    # Hypothesis Setting - 가설 설정 유도
    Peer_HV = 13    # Hypothesis Verification - 가설 검증 지원
    Peer_CC = 14    # Cognitive Conflict - 인지 갈등 유발
    Peer_ES = 15    # Emotional Support - 정서적 지원
```

#### Tutor Act (Phase 4-5: 교사 역할)

```python
class TutorAct(Enum):
    Tutor_SP = 21   # Specification - 구체화 요구
    Tutor_HI = 22   # Explicit Hint - 명시적 힌트
    Tutor_EC = 23   # Error Correction - 오류 수정
    Tutor_CL = 24   # Concept Clarification - 개념 명료화
    Tutor_TR = 25   # Transfer Promotion - 전이 촉진
```

#### Act 선택 로직 예시

```python
# dms/prompts/AIActSelector.py
class Phase2PeerActSelector:
    def get_acts_aux(self, previous_act, assessment_codes, open=True):
        acts = []

        if 'a' in assessment_codes:  # 선행지식 부재
            acts.append(PeerAct.Peer_PR)  # 문제 인식 촉진

        elif 'f' in assessment_codes:  # 논리적 설명 부족
            acts.append(PeerAct.Peer_HS)  # 가설 설정 유도

        elif any(code in assessment_codes for code in ('b', 'c', 'd', 'e')):
            # 오개념, 경험 과잉 일반화, 추상적 개념 부족
            acts.append(PeerAct.Peer_CC)  # 인지 갈등 유발

        elif any(code in assessment_codes for code in ('j', 'k', 'l', 'm')):
            # 과학 불안, 동기 저하, 흥미 부족
            acts.append(PeerAct.Peer_ES)  # 정서적 지원

        return acts
```

### 3. AIPromptGenerator - 프롬프트 생성

선택된 Act에 맞는 시스템 프롬프트를 동적으로 생성합니다.

```python
# dms/prompts/AIPromptGenerator.py
class Phase2PromptGenerator:
    def get_prompt(self, conversation_history, student_prompt, acts):
        # 1. 기본 시스템 메시지 (Peer 역할)
        system_msg = """물리학 원운동 단원 학습을 지원하는 교육 에이전트입니다.
        당신은 학습자와 함께 탐구하는 **학습 동료(Peer)**입니다.

        **핵심 역할**:
        - 학습자가 스스로 생각하고 탐구하도록 격려하기
        - 질문을 통해 사고를 자극하기
        - 정서적으로 지원하기

        **응답 가이드**:
        - 답변은 짧고 간결하게, 1~2문장 이내
        - 친근하고 격려하는 어투 사용
        - 직접 답을 주지 말고 스스로 발견하도록 유도
        """

        # 2. 선택된 Act에 따른 추가 지침
        acts_prompt = self._generate_acts_prompt(acts)

        # 3. 메시지 조합
        messages = self._build_messages(conversation_history, student_prompt,
                                         system_msg, acts_prompt)
        return messages
```

#### Act별 프롬프트 지침 예시

```python
# Peer_CC (인지 갈등 유발) 프롬프트
if PeerAct.Peer_CC in acts:
    acts_prompt += """**[인지 갈등 유발]**
    - 힘은 속도의 변화와 관련이 있으므로 등속 원운동에서
      속도 자체가 아니라 속도의 변화를 만드는 방향을 생각해봐야해요
    → 학습자의 오개념을 파악하여 어떤 부분이 틀렸는지 짚어주고
      올바른 방향으로 안내하는 피드백을 제시해주세요.
    """

# Tutor_EC (오류 수정) 프롬프트
if TutorAct.Tutor_EC in acts:
    acts_prompt += """**[오류 수정]**
    - 학습자의 구체적인 오개념을 직접 지적해주세요
    - 왜 그 개념이 틀렸는지 명확하게 설명해주세요
    - 올바른 개념을 제시해주세요
    """
```

### 4. Intermediary - 조율 계층

Phase별로 적절한 컴포넌트를 조합하여 파이프라인을 실행합니다.

```python
# dms/Intermediary.py
class Intermediary:
    def __init__(self, phase):
        self.phase = phase
        self._init_components()

    def _init_components(self):
        if self.phase == 2:
            self.assessor = IntentAssessor()
            self.selector = Phase2PeerActSelector()
            self.generator = Phase2PromptGenerator()
        elif self.phase == 3:
            self.selector = Phase3PeerActSelector()
            self.generator = Phase3PromptGenerator()
        elif self.phase == 4:
            self.selector = Phase4TutorActSelector()
            self.generator = Phase4PromptGenerator()

    def get_prompt(self, conversation_history, student_prompt):
        # 1. 학습자 상태 평가
        assessment = self.assessor.assess(conversation_history, student_prompt)

        # 2. 교수 전략 선택
        acts = self.selector.get_acts(assessment['codes'])

        # 3. 프롬프트 생성
        messages = self.generator.get_prompt(
            conversation_history, student_prompt, acts
        )

        return messages
```

---

## 데이터베이스 구조

### AWS DynamoDB 스키마

#### 테이블 1: `easyphysics_session`

세션 정보를 저장합니다.

| 속성 | 타입 | 설명 |
|------|------|------|
| `session_uuid` (PK) | String | 세션 고유 ID |
| `user_id` | String | 사용자 ID |
| `username` | String | 사용자명 |
| `created_at` | String | 생성 시간 |
| `updated_at` | String | 수정 시간 |

#### 테이블 2-6: `easyphysics_phase1` ~ `easyphysics_phase5`

각 Phase별 대화 기록을 저장합니다.

| 속성 | 타입 | 설명 |
|------|------|------|
| `session_id` (PK) | String | 세션 ID |
| `timestamp` (SK) | Number | 타임스탬프 |
| `role` | String | "user" \| "assistant" |
| `content` | String | 메시지 내용 |
| `content_type` | String | "text" \| "image" |
| `llm_model` | String | 사용한 LLM 모델 |
| `turn` | Number | 턴 번호 |

### DynamoDB Manager

```python
# modules/dynamo.py
class DynamoDBManager:
    def __init__(self, aws_access_key_id, aws_secret_access_key, region_name):
        self.dynamodb = boto3.resource('dynamodb', ...)
        self.create_tables_if_not_exists()

    def save_phase_message(self, session_id, phase, role, content,
                           content_type="text", llm_model=None, turn=None):
        """Phase별 메시지 저장"""
        table = self.dynamodb.Table(f'easyphysics_phase{phase}')
        table.put_item(Item={
            'session_id': session_id,
            'timestamp': int(time.time() * 1000),
            'role': role,
            'content': content,
            'content_type': content_type,
            'llm_model': llm_model,
            'turn': turn
        })

    def get_phase_messages(self, session_id, phase):
        """Phase별 메시지 조회"""
        table = self.dynamodb.Table(f'easyphysics_phase{phase}')
        response = table.query(
            KeyConditionExpression=Key('session_id').eq(session_id)
        )
        return response['Items']
```

---

## 설치 및 실행

### 사전 요구사항

- Python 3.11+
- AWS 계정 (DynamoDB 사용)
- OpenAI API 키

### 설치

```bash
# 저장소 클론
git clone https://github.com/easy-physics-snu/physics-tutor.git
cd physics-tutor

# 가상환경 생성 및 활성화
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt
```

### 실행

```bash
# 로컬 실행
streamlit run app.py
```

브라우저에서 `http://localhost:8501` 접속

---

## 환경 설정

### `.streamlit/secrets.toml` 설정

`.streamlit/example.secrets.toml` 파일을 복사하여 `secrets.toml`로 이름을 변경한 후, 아래 내용을 채워넣습니다.

```toml
# OpenAI API
openai_api_key = "sk-..."

# 사용자 계정
[users]
[users.student1]
password = "password123"
userID = "user001"

[users.student2]
password = "password456"
userID = "user002"

# AWS DynamoDB
[aws]
aws_access_key_id = "AKIA..."
aws_secret_access_key = "..."
region_name = "ap-northeast-2"

# LangSmith (선택사항)
LANGCHAIN_TRACING_V2 = "true"
LANGCHAIN_API_KEY = "..."
LANGCHAIN_ENDPOINT = "https://api.smith.langchain.com"
LANGCHAIN_PROJECT = "physics-tutor"
```

### `.streamlit/config.toml` 설정

```toml
[theme]
base = "light"

[server]
headless = true
port = 8501
```

---

## 라이선스

이 프로젝트는 서울대학교 Easy Physics 연구팀에서 개발되었습니다.

---

## 연락처

- **프로젝트**: Easy Physics - AI 기반 물리 튜터링 시스템
- **소속**: 서울대학교
- **GitHub**: [easy-physics-snu/physics-tutor](https://github.com/easy-physics-snu/physics-tutor)
