## 실행 방법

### 1. Python 가상 환경 설치

### 2. (가상 환경 내에서) 필요 패키지들 설치
```
pip install -r requirements.txt
```

### 3. secrets 파일 관리

- .streamlit 폴더 안의 'example.secrets.toml' 파일 복사
- 파일명을 'secrets.toml'로 변경
- 파일 내 'openai_api_key'에 API-KEY 입력
    - ex) openai_api_key="sk-eio20d..."

### 4. streamlit 실행
```
streamlit run app.py
```

## 영어 학습 화면

기본 언어는 영어이며, 사이드바에서 한국어로 전환할 수 있습니다. 교재·정답·탭 안내 이미지 6종은 `src/images/en/`에 영어 대체본을 두고, `i18n/assets.py`의 `localized_image_path()`로 선택합니다. 한국어 원본과 글자가 없는 문제·캔버스 이미지는 그대로 유지합니다. 교재 이미지는 원자료를 바탕으로 영어로 재구성했습니다.

시뮬레이션 문구는 `i18n/simulation.py`에서 변환합니다. 영어 이미지가 추가될 때는 `LOCALIZED_IMAGES`에 등록하고, 표시할 때 공통 선택 함수를 사용하세요. ‘더 알아보기’의 외부 자료는 한국어 자료를 유지합니다.

검증: `python -m unittest discover -s tests -v`
