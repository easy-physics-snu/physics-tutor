# by Romain Puech
# 한국어 버전으로 수정 - Korean Version By Junbo Koh

from dms.prompts.IntentTaxonomy import DEFAULT_ASSESS_PROMPT, PHASE2_ASSESS_PROMPT, PHASE3_ASSESS_PROMPT, PHASE4_ASSESS_PROMPT
import json

class IntentAssessor():
   """Student State Assessor - 학생의 발화를 분석하여 학습 상태를 평가"""
   PHASE_PROMPTS = {
      2: PHASE2_ASSESS_PROMPT,
      3: PHASE3_ASSESS_PROMPT,
      4: PHASE4_ASSESS_PROMPT,
    }

   def __init__(self, client, model, phase, assessment_history=[]) -> None:
      self.client = client
      self.model = model
      self.phase = phase
      self.assess_history = list(assessment_history)

   def get_phase_criteria(self):
      """현재 phase에 해당하는 평가 기준을 반환"""
      return self.PHASE_PROMPTS.get(self.phase, DEFAULT_ASSESS_PROMPT)  # 기본값으로 DEFAULT_ASSESS_PROMPT 사용

   def get_purpose(self, conversation_history, student_prompt):
      phase_criteria = self.get_phase_criteria()

      purpose = \
      f"""학생이 물리학 역학 단원에서 원운동 문제에 대한 탐구 학습을 수행하고 있습니다.

다음은 학생과 교육 에이전트 간의 대화 기록입니다:
{conversation_history}

학생의 최신 프롬프트:
"{student_prompt}"      

위 학생의 발화를 분석하여 다음 항목 "a,b,c,d,e,f,g,h,i,j,k,l,m" 중 가장 해당 가능성이 높은 상위 2개의 학습 상태 지표를 선택하세요:

{phase_criteria}

단계별로 분석하세요:
1. 학생 프롬프트의 주요 의도와 특징을 파악
2. 각 지표별로 해당 여부를 판단
3. 선택한 항목들을 간략히 설명

**IMPORTANT**: 반드시 다음 JSON 형식으로 답변하세요:
##
{{
    "justification": "학생 프롬프트 분석 근거와 선택한 지표들의 이유",
    "selection": "선택한 알파벳들을 쉼표로 구분 (예: a,c)",

}}
##
Exactly follow JSON format.
Analyze the last student's utterance.
{{"""
      return purpose

   def create_prompt(self, conversation_history, student_prompt):
      """프롬프트 생성 - 대화 기록과 함께 평가 요청"""
      purpose = self.get_purpose(conversation_history, student_prompt)
      prompt = [
         {"role": "system", "content": "You are an expert educational assessor specializing in analyzing students' learning behaviors when using AI agent for physics learning."},
         {"role": "user", "content": purpose}
         ]
      return prompt

   def assess(self, conversation_history, student_prompt):
      prompt = self.create_prompt(conversation_history, student_prompt)
      #print("Assessor called with prompt:")
      #print(print_logs(prompt))
      client = self.client
      completion = client.chat.completions.create(
         model=self.model,
         messages=prompt,
         response_format = {"type": "json_object"},
         max_tokens=300, # should never be reached
         temperature=0.0,
         top_p=0.1
      )

      response = (completion.choices[0].message.content).replace("\\(","$").replace("\\)","$").replace("\\[","$$").replace("\\]","$$").replace("\\","")
      #print("ASSESSMENT IS \n",response)
      # postprocess make sure the format is right
      s = response.find('{')
      e = response.rfind('}')
      response = response[s:e+1]
      json_data = json.loads(response)
      selection = json_data['selection']
      selection = selection.replace(' ','').replace(',','')
      json_data['selection'] = selection
      assessment = json.dumps(json_data)

      self.assess_history.append(assessment)

      # total_tokens = completion.usage.total_tokens
      # prompt_tokens = completion.usage.prompt_tokens
      # completion_tokens = completion.usage.completion_tokens
      
      return assessment
    