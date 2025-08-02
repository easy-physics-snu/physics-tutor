from typing import Optional, List, Dict
from langchain_teddynote.models import MultiModal


class MultiModalwithHistory(MultiModal):
    def __init__(self, model, system_prompt=None, user_prompt=None):
        super().__init__(model, system_prompt, user_prompt)
        self.messages_history = []  # 인스턴스 변수로 변경

    def _init_message(self, image_url: Optional[str], user_prompt: Optional[str] = None, 
                     system_prompt: Optional[str] = None):
        """첫 번째 메시지 초기화 (원본 로직 유지)"""
        # Check if image_url is provided
        if image_url:
            try:
                encoded_image = self.encode_image(image_url)
            except Exception as e:
                print(f"이미지 처리 중 오류 발생: {e}")
                encoded_image = None
        else:
            encoded_image = None

        system_prompt = system_prompt if system_prompt is not None else self.system_prompt
        user_prompt = user_prompt if user_prompt is not None else self.user_prompt

        if encoded_image:
            messages = [
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": user_prompt,
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": f"{encoded_image}"},
                        },
                    ],
                },
            ]
        else:
            # 이미지가 없을 때는 텍스트 전용 메시지
            messages = [
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": user_prompt,
                        },
                    ],
                },
            ]
        
        self.messages_history.extend(messages)

    def create_messages(self, user_prompt: str, image_url: Optional[str] = None, 
                       system_prompt: Optional[str] = None) -> List[Dict]:
        """메시지 생성 - 전체 대화 히스토리를 포함해서 반환"""
        if len(self.messages_history) == 0:
            # 첫 번째 대화인 경우 초기화
            self._init_message(image_url, user_prompt, system_prompt)
        else:
            # 후속 메시지 추가
            if image_url:
                try:
                    encoded_image = self.encode_image(image_url)

                    user_prompt = user_prompt if user_prompt is not None else self.user_prompt
                    message = {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": user_prompt,
                            },
                            {
                                "type": "image_url",
                                "image_url": {"url": f"{encoded_image}"},
                            },
                        ],
                    }
                except Exception as e:
                    print(f"이미지 처리 중 오류 발생: {e}")
                    # 이미지 처리 실패 시 텍스트만으로 처리
                    message = {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": user_prompt,
                            },
                        ],
                    }
            else:
                user_prompt = user_prompt if user_prompt is not None else self.user_prompt
                message = {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": user_prompt,
                        },
                    ],
                }
            
            self.messages_history.append(message)

        # 전체 대화 히스토리를 반환 (AI가 맥락을 이해할 수 있도록)
        return self.messages_history.copy()

    def stream(self, user_prompt: str, image_url: Optional[str] = None, 
              system_prompt: Optional[str] = None):
        """스트리밍 응ㅌ 생성"""
        messages = self.create_messages(user_prompt, image_url, system_prompt)
        response = self.model.stream(messages)
        
        # 스트리밍 응답을 수집하여 히스토리에 추가하기 위한 wrapper
        def response_wrapper():
            collected_content = ""
            for chunk in response:
                if hasattr(chunk, 'content'):
                    collected_content += chunk.content
                yield chunk
            
            # 스트리밍이 완료되면 AI의 응답을 히스토리에 추가
            if collected_content:
                self.add_message("assistant", collected_content)
        
        return response_wrapper()

    def invoke(self, user_prompt: str, image_url: Optional[str] = None, 
              system_prompt: Optional[str] = None):
        """단일 응답 생성"""
        messages = self.create_messages(user_prompt, image_url, system_prompt)
        response = self.model.invoke(messages)
        
        # AI의 응답을 히스토리에 추가
        self.add_message("assistant", response.content)
        
        return response.content

    def add_message(self, role: str, content: str, image_url: Optional[str] = None):
        """메시지 히스토리에 메시지 추가"""
        if role not in ["user", "assistant", "system"]:
            raise ValueError("role은 'user', 'assistant', 'system' 중 하나여야 합니다.")

        # 호환성을 위해 "ai"를 "assistant"로 변환
        if role == "ai":
            role = "assistant"

        if image_url and role == "user":
            try:
                encoded_image = self.encode_image(image_url)
                message = {
                    "role": role,
                    "content": [
                        {
                            "type": "text",
                            "text": content,
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": f"{encoded_image}"},
                        },
                    ],
                }
            except Exception as e:
                print(f"이미지 처리 중 오류 발생: {e}")
                message = {"role": role, "content": content}
        else:
            # assistant나 system 메시지는 일반적으로 텍스트만
            if role == "assistant" or role == "system":
                message = {"role": role, "content": content}
            else:
                # user 메시지도 이미지가 없으면 부모 클래스 구조 유지
                message = {
                    "role": role,
                    "content": [
                        {
                            "type": "text",
                            "text": content,
                        },
                    ],
                }

        self.messages_history.append(message)

    def batch(self, user_prompts: List[str], image_urls: List[str] = None, 
             system_prompts: List[str] = None):
        """배치 처리 - 부모 클래스 기능 확장"""
        if image_urls is None:
            image_urls = [None] * len(user_prompts)
        if system_prompts is None:
            system_prompts = [None] * len(user_prompts)

        # 각 요청에 대해 별도의 메시지 생성
        batch_messages = []
        for user_prompt, image_url, system_prompt in zip(user_prompts, image_urls, system_prompts):
            # 임시 인스턴스를 사용하여 각 배치 아이템을 독립적으로 처리
            temp_instance = MultiModalwithHistory(self.model, self.system_prompt, self.user_prompt)
            messages = temp_instance.create_messages(user_prompt, image_url, system_prompt)
            batch_messages.append(messages)

        response = self.model.batch(batch_messages)
        return [r.content for r in response]

    def get_history(self) -> List[Dict]:
        """메시지 히스토리 반환"""
        return self.messages_history.copy()

    def clear_history(self):
        """메시지 히스토리 초기화"""
        self.messages_history.clear()

    def get_history_length(self) -> int:
        """히스토리 길이 반환"""
        return len(self.messages_history)
