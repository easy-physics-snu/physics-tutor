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
