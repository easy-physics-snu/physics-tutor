# By Romain Puech
# 한국어 버전 수정 - By Junbo Koh

import dms.prompts.AIPromptGenerator as AIPromptGenerator
import dms.prompts.AIActSelector as AIActSelector
import dms.prompts.IntentAssessor as IntentAssessor


class Intermediary():
    """학습 단계별로 적절한 교육 에이전트 구성요소를 조합하는 중재자"""
    
    def __init__(self, client, model, phase=2, assessor=None, actSelector=None, promptGenerator=None, act_history=None, assessment_history=None) -> None:
        self.client = client
        self.model = model
        self.phase = phase 

        # None을 빈 리스트로 변환
        if act_history is None:
            act_history = []
        if assessment_history is None:
            assessment_history = []
        
        # Phase 유효성 검증
        if phase not in [2, 3, 4]:
            raise ValueError(f"Invalid phase: {phase}. Must be 2, 3 or 4")
        
        # Phase에 따라 적절한 컴포넌트 선택
        if assessor is None:
            self.assessor = IntentAssessor.IntentAssessor(
                self.client, 
                self.model, 
                phase=self.phase,
                assessment_history=assessment_history
            )
        else:
            self.assessor = assessor
            
        if actSelector is None:
            if self.phase == 2:
                self.actSelector = AIActSelector.Phase2PeerActSelector(act_history=act_history)
            elif self.phase == 3:
                self.actSelector = AIActSelector.Phase3PeerActSelector(act_history=act_history)
            #TODO @minseon: 수정 후 아래 코드 주석 해제
            elif self.phase == 4:
                self.actSelector = AIActSelector.Phase4TutorActSelector(act_history=act_history)
        else:
            self.actSelector = actSelector
            
        if promptGenerator is None:
            if self.phase == 2:
                self.promptGenerator = AIPromptGenerator.Phase2PromptGenerator()
            elif self.phase == 3:
                self.promptGenerator = AIPromptGenerator.Phase3PromptGenerator()
            #TODO 수정 후 아래 코드 주석 해제
            elif self.phase == 4:
                self.promptGenerator = AIPromptGenerator.Phase4PromptGenerator()
        else:
            self.promptGenerator = promptGenerator

    # def update_phase(self, phase):
    #     """Phase 변경 및 Phase 의존 컴포넌트 재생성"""
    #     if phase not in [2, 3, 4]:
    #         raise ValueError(f"Invalid phase: {phase}. Must be 2, 3 or 4")
        
    #     self.phase = phase
    #     self.assessor.phase = phase  # assessor는 재생성 불필요 (내부에서 phase 사용)
        
    #     # Phase별 컴포넌트 재생성
    #     if phase == 2:
    #         self.actSelector = AIActSelector.Phase2PeerActSelector(act_history=[])
    #         self.promptGenerator = AIPromptGenerator.Phase2PromptGenerator()
    #     elif phase == 3:
    #         self.actSelector = AIActSelector.Phase3PeerActSelector(act_history=[])
    #         self.promptGenerator = AIPromptGenerator.Phase3PromptGenerator()
    #     #TODO 수정 후 아래 코드 주석 해제
    #     elif phase == 4:
    #         self.actSelector = AIActSelector.Phase4TutorActSelector(act_history=[])
    #         self.promptGenerator = AIPromptGenerator.Phase4PromptGenerator()

    # def update_client(self, client):
    #     """클라이언트 업데이트"""
    #     self.client = client
    #     self.assessor.client = client
    #     # LLMActSelector도 client 가질 수 있음
    #     if hasattr(self.actSelector, 'client'):
    #         self.actSelector.client = client
            
    # def update_model(self, model):
    #     """모델 업데이트"""
    #     self.model = model
    #     self.assessor.model = model

    def get_prompt(self, conversation_history, student_prompt, open=True):
        """학생 발화를 분석하여 교육 에이전트의 응답 프롬프트 생성"""
        # 1. 학생 발화 평가
        assessment = self.assessor.assess(
            conversation_history, 
            student_prompt
        )
        # 2. 평가 결과에 따라 교수 전략(Act) 선택
        acts = self.actSelector.get_acts(assessment, open=open)
        # 3. 선택된 Act에 따라 최종 프롬프트 생성
        prompt = self.promptGenerator.get_prompt(conversation_history, student_prompt, acts)
        return prompt, acts, assessment

    def get_act_history(self):
        """교수 전략(Act) 히스토리 조회"""
        return list(getattr(self.actSelector, 'act_history', []))

    def get_assess_history(self):
        """평가(Assessment) 히스토리 조회"""
        return list(getattr(self.assessor, 'assess_history', []))
