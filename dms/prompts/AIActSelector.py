# By Romain Puech
# 한국어 버전 수정 - By Junbo Koh

import json

from dms.prompts.AIActTaxonomy import PeerAct
from dms.prompts.AIActTaxonomy import TutorAct


class Phase2PeerActSelector():
    """Phase2 '생각하기' 단계에서 학생 발화 의도(Student Intent)에 따라 튜터의 다음 교수 전략을 결정(Act Selection)"""

    def __init__(self, act_history=None) -> None:
        if act_history is None:
            act_history = []
        self.act_history = list(act_history)  # 히스토리 복사본 저장
        self.previous_act = act_history[-1] if act_history != [] else [PeerAct.Peer_PR]

    def get_acts(self, assessment, open=True):
        """학생 평가를 바탕으로 다음 교수 전략을 선택"""
        print("selecting intent... ")
        previous_act = self.previous_act
        assessment_codes = self.extract_assessment_codes(assessment)
        acts = self.get_acts_aux(previous_act, assessment_codes, open=open)
        print(f"selected acts: {acts}")
        return acts
    
    def extract_assessment_codes(self, assessment):
        """평가 결과에서 코드를 추출"""
        json_data = json.loads(assessment)
        selection = json_data['selection']
        codes = list(selection)
        return codes
        
    def get_acts_aux(self, previous_act, assessment_codes, open=True):
        """핵심 의도 선택 로직 - Productive Failure 전략 기반"""
        print(f"평가 코드: {assessment_codes}, 이전 전략: {previous_act}")
        acts = []

        if 'a' in assessment_codes:
            acts.append(PeerAct.Peer_PR)
        elif 'f' in assessment_codes:
            acts.append(PeerAct.Peer_HS)
        elif any(code in assessment_codes for code in ('b', 'c', 'd', 'e')):
            acts.append(PeerAct.Peer_CC)
        elif any(code in assessment_codes for code in ('j', 'k', 'l', 'm')):
            acts.append(PeerAct.Peer_ES)
        else:
            acts.append(PeerAct.Peer_HS)

        self.previous_act = acts
        self.act_history.append(acts)  # 히스토리에 추가
        return acts


class Phase3PeerActSelector():
    """Phase3 '실험하기' 단계에서 학생 발화 의도(Student Intent)에 따라 튜터의 다음 교수 전략을 결정(Act Selection)"""

    def __init__(self, act_history=None) -> None:
        if act_history is None:
            act_history = []
        self.act_history = list(act_history)  # 히스토리 복사본 저장
        self.previous_act = act_history[-1] if act_history != [] else [PeerAct.Peer_HV]

    def get_acts(self, assessment, open=True):
        """학생 평가를 바탕으로 다음 교수 전략을 선택"""
        print("selecting intent... ")
        previous_act = self.previous_act
        assessment_codes = self.extract_assessment_codes(assessment)
        acts = self.get_acts_aux(previous_act, assessment_codes, open=open)
        print(f"selected acts: {acts}")
        return acts
    
    def extract_assessment_codes(self, assessment):
        """평가 결과에서 코드를 추출"""
        json_data = json.loads(assessment)
        selection = json_data['selection']
        codes = list(selection)
        return codes
        
    def get_acts_aux(self, previous_act, assessment_codes, open=True):
        """핵심 의도 선택 로직 - Productive Failure 전략 기반"""
        print(f"평가 코드: {assessment_codes}, 이전 전략: {previous_act}")
        acts = []

        if any(code in assessment_codes for code in ('b', 'h', 'g', 'f')):
            acts.append(PeerAct.Peer_HV)
        elif any(code in assessment_codes for code in ('c', 'e')):
            acts.append(PeerAct.Peer_CC)
        elif any(code in assessment_codes for code in ('j', 'k', 'l', 'm')):
            acts.append(PeerAct.Peer_ES)
        else:
            acts.append(PeerAct.Peer_HS)

        self.previous_act = acts
        self.act_history.append(acts)  # 히스토리에 추가
        return acts


#TODO @minseon: 아래 코드 수정 및 구현 필요 ##완료
class Phase4TutorActSelector():
    """학생 발화 의도(Student Intent)에 따라 튜터의 다음 교수 전략을 결정(Act Selection)"""

    def __init__(self, act_history=None) -> None:
        if act_history is None:
            act_history = []
        self.act_history = list(act_history)  # 히스토리 복사본 저장
        self.previous_act = act_history[-1] if act_history != [] else [TutorAct.Tutor_SP]

    def get_acts(self, assessment, open=True):
        """학생 평가를 바탕으로 다음 교수 전략을 선택"""
        print("selecting intent... ")
        previous_act = self.previous_act
        assessment_codes = self.extract_assessment_codes(assessment)
        acts = self.get_acts_aux(previous_act, assessment_codes, open=open)
        print(f"selected acts: {acts}")
        return acts
    
    def extract_assessment_codes(self, assessment):
        """평가 결과에서 코드를 추출"""
        json_data = json.loads(assessment)
        selection = json_data['selection']
        codes = list(selection)
        return codes
        
    def get_acts_aux(self, previous_act, assessment_codes, open=True):
        """핵심 의도 선택 로직 - Productive Failure 전략 기반"""
        print(f"평가 코드: {assessment_codes}, 이전 전략: {previous_act}")
        acts = []

        if 'f' in assessment_codes:
            acts.append(TutorAct.Tutor_SP)        
        elif any(code in assessment_codes for code in ('d', 'g')):
            acts.append(TutorAct.Tutor_HI)
        elif any(code in assessment_codes for code in ('b')):
            acts.append(TutorAct.Tutor_EC)
        elif any(code in assessment_codes for code in ('a', 'h')):
            acts.append(TutorAct.Tutor_CL)
        else:
            acts.append(TutorAct.Tutor_TP)

        self.previous_act = acts
        self.act_history.append(acts)  # 히스토리에 추가
        return acts
