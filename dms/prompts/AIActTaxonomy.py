"""
시트 링크: https://docs.google.com/spreadsheets/d/1kEYJp8wLjMbwcUOoV0p1XKYa5-07gGiA_GXmDxUMSfs/edit?gid=997379618#gid=997379618

3자 전문가 타당화 시트: https://docs.google.com/spreadsheets/d/1QvnXKE6WvYYgYnmeiWDdhGQYo96VU-K_RPbrYPK2icU/edit?usp=sharing
"""

# 251102 3차 전문가 타당화 결과 반영_By Junbo Koh

from enum import Enum

class PeerAct(Enum):
    """
    AI 챗봇의 Peer(동료) 역할 의도 분류체계
    학습자와 함께 탐구하고 사고를 촉진하는 동료로서의 상호작용
    
    명명 규칙: Peer_{카테고리약어} = {일련번호}
    - PR: Problem Recognition (문제 인식)
    - HS: Hypothesis Setting (가설 설정)
    - HV: Hypothesis Verification (가설 검증)
    - CC: Cognitive Conflict (인지 갈등 유발)
    - ES: Emotional Support (정서적 지원)
    """
    # 문제 인식: 문제 해결에 필요한 핵심 요소를 탐색해보게 하는 질문
    Peer_PR = 11
    # 가설 설정: 문제에 대한 가능한 설명과 예측을 다양하게 탐색하게 하는 질문
    Peer_HS = 12
    # 가설 검증: 가설과 시뮬레이션 결과를 논리적으로 연결시킬 수 있도록 하는 질문
    Peer_HV = 13
    # 인지 갈등 유발: 학습자의 선개념과 과학적 개념 사이의 불일치를 드러내어 인지 갈등을 유도하는 질문
    Peer_CC = 14
    # 정서적 지원: 학습자가 포기하지 않고 학습을 지속하도록 응원하는 피드백
    Peer_ES = 15


class TutorAct(Enum):
    """
    AI 챗봇의 Tutor(교사) 역할 의도 분류체계
    학습자의 이해를 안내하고 명확한 방향을 제시하는 교사로서의 상호작용
    
    명명 규칙: Tutor_{카테고리약어} = {일련번호}
    - SP: Specification Request (구체화 요구)
    - HI: Explicit Hint (명시적 힌트)
    - EC: Error Correction (오류 수정)
    - CL: Concept Clarification (개념 명료화)
    - TP: Transfer Promotion (전이 촉진)
    """
    # 구체화 요구: 직관적 이해를 학습한 개념이나 원리 등을 사용해 명확하게 표현하도록 유도하는 발문
    Tutor_SP = 21
    # 명시적 힌트: 학생의 이해도가 낮을 때 정답을 유도하는 피드백
    Tutor_HI = 22
    # 오류 수정: 학생들의 오개념을 파악하여 어떤 부분이 틀렸는지 짚어주고 올바른 방향으로 안내하는 피드백
    Tutor_EC = 23
    # 개념 명료화: 학습 내용에 대한 구체적인 설명
    Tutor_CL = 24
    # 전이 촉진: 학생들이 학습한 내용을 개별 사례를 넘어서 일반화하도록 유도
    Tutor_TR = 25
