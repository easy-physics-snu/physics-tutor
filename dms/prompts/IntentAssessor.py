# by Romain Puech
# 한국어 버전으로 수정 - Korean Version By Junbo Koh

import json

from i18n import ai_language_instruction, lt
from i18n.prompt_loader import load_localized_values
import dms.prompts.IntentTaxonomy as intent_taxonomy

class IntentAssessor():
   lt("""Student State Assessor - 학생의 발화를 분석하여 학습 상태를 평가""", """Student State Assessor - Analyzes the student's utterances to evaluate their learning state""")
   def __init__(self, client, model, phase, assessment_history=[]) -> None:
      self.client = client
      self.model = model
      self.phase = phase
      self.assess_history = list(assessment_history)

   def get_phase_criteria(self):
      lt("""현재 phase에 해당하는 평가 기준을 반환""", """Returns the assessment criteria for the current phase""")
      default_prompt, phase2_prompt, phase3_prompt, phase4_prompt = load_localized_values(
         intent_taxonomy,
         "DEFAULT_ASSESS_PROMPT",
         "PHASE2_ASSESS_PROMPT",
         "PHASE3_ASSESS_PROMPT",
         "PHASE4_ASSESS_PROMPT",
      )
      phase_prompts = {
         2: phase2_prompt,
         3: phase3_prompt,
         4: phase4_prompt,
      }
      return phase_prompts.get(self.phase, default_prompt)

   def get_purpose(self, conversation_history, student_prompt):
      phase_criteria = self.get_phase_criteria()

      purpose = \
      lt(f"""학생이 물리학 역학 단원에서 원운동 문제에 대한 탐구 학습을 수행하고 있습니다.

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
{{""", f"""A student is conducting inquiry-based learning on circular motion problems in a physics mechanics unit.

The following is the conversation history between the student and the educational agent:
{conversation_history}

The student's latest prompt:
"{student_prompt}"

Analyze the student's utterance above and select the top 2 most likely learning state indicators from the following items "a,b,c,d,e,f,g,h,i,j,k,l,m":

{phase_criteria}

Analyze step by step:
1. Identify the main intent and characteristics of the student's prompt
2. Evaluate whether each indicator applies
3. Briefly explain the selected items

**IMPORTANT**: You must respond in the following JSON format:
##
{{
    "justification": "Reasoning behind the analysis of the student's prompt and the rationale for the selected indicators",
    "selection": "Selected letters separated by commas (e.g., a,c)",

}}
##
Exactly follow JSON format.
Analyze the last student's utterance.
{{""")
      return purpose + ai_language_instruction()

   def create_prompt(self, conversation_history, student_prompt):
      lt("""프롬프트 생성 - 대화 기록과 함께 평가 요청""", """Creates a prompt — requests assessment along with conversation history""")
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
         # max_tokens=300, # should never be reached / # 제거: 모델이 필요한 만큼 토큰을 사용하도록 허용
         temperature=0.0,
         top_p=0.1
      )

      response = (completion.choices[0].message.content).replace("\\(","$").replace("\\)","$").replace("\\[","$$").replace("\\]","$$").replace("\\","")
      #print("ASSESSMENT IS \n",response)
      # postprocess make sure the format is right
      s = response.find('{')
      e = response.rfind('}')

      # Error handling: Check if braces are found
      if s == -1 or e == -1 or s >= e:
          # Log the raw response for debugging
          print(f"ERROR: Invalid JSON response from LLM. Raw response: {completion.choices[0].message.content}")
          print(f"Processed response: {response}")
          # Return a default assessment or raise a more informative error
          raise ValueError(
              f"LLM response does not contain valid JSON. "
              f"Expected JSON object but got: {completion.choices[0].message.content[:200]}"
          )

      response = response[s:e+1]

      try:
          json_data = json.loads(response)
      except json.JSONDecodeError as e:
          # Log the problematic response for debugging
          print(f"ERROR: Failed to parse JSON. Response slice: {response}")
          print(f"Full processed response: {completion.choices[0].message.content}")
          raise ValueError(
              f"Failed to parse JSON from LLM response: {str(e)}\n"
              f"Response content: {response[:500]}"
          ) from e

      selection = json_data['selection']
      selection = selection.replace(' ','').replace(',','')
      json_data['selection'] = selection
      assessment = json.dumps(json_data)

      self.assess_history.append(assessment)

      # total_tokens = completion.usage.total_tokens
      # prompt_tokens = completion.usage.prompt_tokens
      # completion_tokens = completion.usage.completion_tokens

      return assessment
