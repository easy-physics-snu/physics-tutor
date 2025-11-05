import os
import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import NoCredentialsError, ClientError
import traceback
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, List
from decimal import Decimal
import streamlit as st

class DynamoDBManager:
    """DynamoDB 관리 클래스"""
    
    def __init__(self, aws_access_key_id: str, aws_secret_access_key: str, 
                 region_name: str):
        """
        DynamoDB 매니저 초기화
        
        Args:
            aws_access_key_id: AWS 액세스 키
            aws_secret_access_key: AWS 시크릿 키
            region_name: AWS 리전
        """
        self.aws_access_key_id = aws_access_key_id
        self.aws_secret_access_key = aws_secret_access_key
        self.region_name = region_name
        
        # DynamoDB 리소스 초기화
        self.dynamodb = boto3.resource(
            'dynamodb',
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=region_name
        )
        
        # 테이블 초기화
        self.create_tables_if_not_exists()
    
    def create_tables_if_not_exists(self):
        """DynamoDB 테이블이 없으면 생성"""
        try:
            existing_tables = [table.name for table in self.dynamodb.tables.all()]
            print(f"Existing tables: {existing_tables}")
            
            # 1. easyphysics_session 테이블 생성
            session_table_name = 'easyphysics_session'
            if session_table_name not in existing_tables:
                try:
                    print(f"Creating session table: {session_table_name}")
                    
                    self.dynamodb.create_table(
                        TableName=session_table_name,
                        KeySchema=[
                            {'AttributeName': 'session_uuid', 'KeyType': 'HASH'}
                        ],
                        AttributeDefinitions=[
                            {'AttributeName': 'session_uuid', 'AttributeType': 'S'}
                        ],
                        BillingMode='PAY_PER_REQUEST',
                        Tags=[
                            {
                                'Key': 'Purpose',
                                'Value': 'session_management'
                            },
                            {
                                'Key': 'Environment',
                                'Value': 'development'
                            }
                        ]
                    )
                    
                    # 테이블이 ACTIVE 상태가 될 때까지 대기
                    waiter = self.dynamodb.meta.client.get_waiter('table_exists')
                    waiter.wait(TableName=session_table_name)
                    
                    print(f"✅ Created session table: {session_table_name}")
                    print(f"  - Table Name: {session_table_name}")
                    print(f"  - Region: {self.dynamodb.meta.client.meta.region_name}")
                    
                except ClientError as e:
                    if e.response['Error']['Code'] != 'ResourceInUseException':
                        print(f"❌ Error creating session table: {e}")
                        raise
                    else:
                        print(f"ℹ️ Session table already exists: {session_table_name}")
            else:
                print(f"ℹ️ Session table already exists: {session_table_name}")
            
            # 2. easyphysics_phase1 ~ easyphysics_phase5 테이블 생성
            for phase_num in range(1, 6):
                phase_table_name = f'easyphysics_phase{phase_num}'
                
                if phase_table_name not in existing_tables:
                    try:
                        print(f"Creating phase table: {phase_table_name}")
                        
                        self.dynamodb.create_table(
                            TableName=phase_table_name,
                            KeySchema=[
                                {'AttributeName': 'session_id', 'KeyType': 'HASH'},
                                {'AttributeName': 'timestamp', 'KeyType': 'RANGE'}
                            ],
                            AttributeDefinitions=[
                                {'AttributeName': 'session_id', 'AttributeType': 'S'},
                                {'AttributeName': 'timestamp', 'AttributeType': 'N'}
                            ],
                            BillingMode='PAY_PER_REQUEST',
                            Tags=[
                                {
                                    'Key': 'Purpose',
                                    'Value': f'phase{phase_num}_messages'
                                },
                                {
                                    'Key': 'Environment',
                                    'Value': 'development'
                                }
                            ]
                        )
                        
                        # 테이블이 ACTIVE 상태가 될 때까지 대기
                        waiter = self.dynamodb.meta.client.get_waiter('table_exists')
                        waiter.wait(TableName=phase_table_name)
                        
                        print(f"✅ Created phase table: {phase_table_name}")
                        print(f"  - Table Name: {phase_table_name}")
                        print(f"  - Region: {self.dynamodb.meta.client.meta.region_name}")
                        
                    except ClientError as e:
                        if e.response['Error']['Code'] != 'ResourceInUseException':
                            print(f"❌ Error creating phase table {phase_table_name}: {e}")
                            raise
                        else:
                            print(f"ℹ️ Phase table already exists: {phase_table_name}")
                else:
                    print(f"ℹ️ Phase table already exists: {phase_table_name}")
                    
        except Exception as e:
            print(f"❌ Error in create_tables_if_not_exists: {e}")
            traceback.print_exc()
            raise
    
    def get_session_table(self):
        """
        easyphysics_session 테이블 참조 가져오기
        
        Returns:
            DynamoDB Table 객체
        """
        return self.dynamodb.Table('easyphysics_session')
    
    def get_phase_table(self, phase_num: int):
        """
        Phase 테이블 참조 가져오기
        
        Args:
            phase_num: Phase 번호 (1-5)
        
        Returns:
            DynamoDB Table 객체
        """
        if phase_num < 1 or phase_num > 5:
            raise ValueError("Phase number must be between 1 and 5")
        
        table_name = f'easyphysics_phase{phase_num}'
        return self.dynamodb.Table(table_name)


class S3Manager:
    """S3 관리 클래스 - 대화 단계에서 생성된 이미지 저장용"""
    
    def __init__(self, aws_access_key_id: str, aws_secret_access_key: str, 
                 region_name: str, bucket_name: str):
        """
        S3 매니저 초기화
        
        Args:
            aws_access_key_id: AWS 액세스 키
            aws_secret_access_key: AWS 시크릿 키
            region_name: AWS 리전
            bucket_name: S3 버킷 이름
        """
        self.bucket_name = bucket_name
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=region_name
        )
    
    def upload_image_file_to_s3(self, file_path: str, session_id: str) -> Optional[str]:
        """
        이미지 파일을 S3에 업로드하고 파일 경로를 반환
        
        Args:
            file_path: 업로드할 이미지 파일 경로
            session_id: 세션 ID (S3 루트 폴더로 사용)
        
        Returns:
            str: S3 객체 키 또는 None (실패 시)
        """
        try:
            timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
            unique_id = str(uuid.uuid4())[:8]
            
            # 파일 확장자 확인
            file_extension = os.path.splitext(file_path)[1][1:].lower()  # .png -> png
            if file_extension not in ['png', 'jpg', 'jpeg']:
                file_extension = 'png'
            
            # MIME 타입 결정
            mime_types = {
                'png': 'image/png',
                'jpg': 'image/jpeg',
                'jpeg': 'image/jpeg'
            }
            mime_type = mime_types.get(file_extension, 'image/png')
            
            object_name = f"{session_id}/images/{timestamp}_{unique_id}.{file_extension}"
            
            # 파일을 읽어서 S3에 업로드
            with open(file_path, 'rb') as f:
                self.s3_client.put_object(
                    Bucket=self.bucket_name,
                    Key=object_name,
                    Body=f,
                    ContentType=mime_type,
                    Metadata={
                        'upload_timestamp': timestamp,
                        'content_type': 'image',
                        'image_format': file_extension,
                        'session_id': session_id
                    }
                )
            
            return object_name
            
        except FileNotFoundError:
            st.error(f"이미지 파일을 찾을 수 없습니다: {file_path}")
            return None
        except NoCredentialsError:
            st.error("AWS 자격 증명을 찾을 수 없습니다.")
            return None
        except Exception as e:
            st.error(f"S3 이미지 업로드 오류: {e}")
            traceback.print_exc()
            return None


class SessionManager:
    """세션 관리 클래스"""
    
    def __init__(self, dynamo_manager: DynamoDBManager):
        """
        세션 매니저 초기화
        
        Args:
            dynamo_manager: DynamoDB 매니저 인스턴스
        """
        self.dynamo_manager = dynamo_manager
        self.session_table = dynamo_manager.get_session_table()
    
    def get_or_create_session(self, session_uuid: str, user_id: Optional[str] = None) -> Optional[Dict]:
        """
        세션 생성 또는 조회
        
        Args:
            session_uuid: 세션 UUID
            user_id: 사용자 ID
        
        Returns:
            dict: 세션 정보 또는 None (실패 시)
        """
        try:
            response = self.session_table.get_item(Key={'session_uuid': session_uuid})
            
            if 'Item' in response:
                return response['Item']
            else:
                # 새 세션 생성
                now = datetime.now(timezone.utc)
                session_item = {
                    'session_uuid': session_uuid,
                    'user_id': user_id or 'anonymous',
                    'created_at': self._datetime_to_timestamp(now)
                }
                self.session_table.put_item(Item=session_item)
                return session_item
        except Exception as e:
            st.error(f"세션 생성/조회 오류: {e}")
            return None
    
    def get_session(self, session_uuid: str) -> Optional[Dict]:
        """
        세션 조회
        
        Args:
            session_uuid: 세션 UUID
        
        Returns:
            dict: 세션 정보 또는 None (실패 시)
        """
        try:
            response = self.session_table.get_item(Key={'session_uuid': session_uuid})
            
            if 'Item' in response:
                return response['Item']
            else:
                return None
        except Exception as e:
            st.error(f"세션 조회 오류: {e}")
            return None
    
    def _datetime_to_timestamp(self, dt: datetime) -> Decimal:
        """datetime을 DynamoDB timestamp(Decimal)로 변환"""
        return Decimal(str(dt.timestamp()))


class PhaseManager:
    """Phase 메시지 관리 클래스"""
    
    def __init__(self, dynamo_manager: DynamoDBManager, phase_num: int):
        """
        Phase 매니저 초기화
        
        Args:
            dynamo_manager: DynamoDB 매니저 인스턴스
            phase_num: Phase 번호 (1-5)
        """
        if phase_num < 1 or phase_num > 5:
            raise ValueError("Phase number must be between 1 and 5")
        
        self.dynamo_manager = dynamo_manager
        self.phase_num = phase_num
        self.phase_table = dynamo_manager.get_phase_table(phase_num)
    
    def load_phase_messages(self, session_id: str) -> List[Dict]:
        """
        Phase 메시지 로드
        
        Args:
            session_id: 세션 ID
        
        Returns:
            list: 메시지 목록
        """
        try:
            response = self.phase_table.query(
                KeyConditionExpression=Key('session_id').eq(session_id),
                ScanIndexForward=True  # 시간순 정렬
            )
            
            messages = []
            for item in response.get('Items', []):
                messages.append({
                    'role': item['role'],
                    'content_type': item['content_type'],
                    'content': item['content'],
                    'timestamp': self._timestamp_to_datetime(item['timestamp']),
                    'LLM_model': item.get('LLM_model', ''),
                    'turn': item.get('turn', None)  # turn 정보 추가
                })
            return messages
        except Exception as e:
            st.error(f"Phase {self.phase_num} 메시지 로드 오류: {e}")
            return []
    
    def save_phase_message(self, session_id: str, role: str, content_type: str, 
                          content: str, llm_model: str = None, turn: int = None) -> bool:
        """
        Phase 메시지 저장
        
        Args:
            session_id: 세션 ID
            role: 메시지 역할 (user/assistant/system)
            content_type: 콘텐츠 타입
            content: 메시지 내용
            llm_model: 사용된 LLM 모델명 (assistant 역할일 때만 사용)
            turn: 대화 턴 번호
        
        Returns:
            bool: 저장 성공 여부
        """
        try:
            now = datetime.now(timezone.utc)
            message_item = {
                'session_id': session_id,
                'timestamp': self._datetime_to_timestamp(now),
                'role': role,
                'content_type': content_type,
                'content': content
            }
            
            # 턴 번호 추가 (없으면 None 저장)
            if turn is not None:
                message_item['turn'] = turn
            else:
                message_item['turn'] = None  # 또는 0으로 기본값 설정 가능
            
            # LLM 모델 정보 추가 (assistant 역할이거나 값이 있는 경우)
            if llm_model:
                message_item['LLM_model'] = llm_model
            elif role == 'assistant':
                # assistant인데 모델이 없으면 빈 문자열
                message_item['LLM_model'] = ''
            else:
                # user인 경우 빈 문자열
                message_item['LLM_model'] = ''
            
            self.phase_table.put_item(Item=message_item)
            return True
        except Exception as e:
            st.error(f"Phase {self.phase_num} 메시지 저장 오류: {e}")
            traceback.print_exc()
            return False
    
    def _datetime_to_timestamp(self, dt: datetime) -> Decimal:
        """datetime을 DynamoDB timestamp(Decimal)로 변환"""
        return Decimal(str(dt.timestamp()))
    
    def _timestamp_to_datetime(self, timestamp: Decimal) -> datetime:
        """DynamoDB timestamp를 datetime으로 변환"""
        return datetime.fromtimestamp(float(timestamp))


# 유틸리티 함수들
def datetime_to_timestamp(dt: datetime) -> Decimal:
    """datetime을 DynamoDB timestamp(Decimal)로 변환"""
    return Decimal(str(dt.timestamp()))

def timestamp_to_datetime(timestamp: Decimal) -> datetime:
    """DynamoDB timestamp를 datetime으로 변환"""
    return datetime.fromtimestamp(float(timestamp))


#--------------------------------#
#       공통 초기화 함수들        #
#--------------------------------#

def initialize_aws_services():
    """
    AWS 서비스 초기화 (전역 - 한 번만 실행)
    이미 초기화되어 있으면 재사용
    """
    if "aws_initialized" in st.session_state and st.session_state.get("aws_initialized"):
        # 이미 초기화됨
        return True
    
    try:
        aws_access_key_id = st.secrets.get("AWS_ACCESS_KEY_ID", "")
        aws_secret_access_key = st.secrets.get("AWS_SECRET_ACCESS_KEY", "")
        aws_region = st.secrets.get("AWS_REGION", "ap-northeast-2")
        s3_bucket_name = st.secrets.get("AWS_S3_BUCKET_NAME", "")
        
        st.session_state["dynamo_manager"] = DynamoDBManager(
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=aws_region
        )
        
        if s3_bucket_name:
            st.session_state["s3_manager"] = S3Manager(
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key,
                region_name=aws_region,
                bucket_name=s3_bucket_name
            )
        else:
            st.session_state["s3_manager"] = None
        
        st.session_state["session_manager"] = SessionManager(
            dynamo_manager=st.session_state["dynamo_manager"]
        )
        
        st.session_state["aws_initialized"] = True
        return True
    except Exception as e:
        st.warning(f"AWS 연결 초기화 실패: {e}")
        st.session_state["aws_initialized"] = False
        st.session_state["dynamo_manager"] = None
        st.session_state["s3_manager"] = None
        st.session_state["session_manager"] = None
        return False


def ensure_phase_manager(phase_num: int) -> Optional[PhaseManager]:
    """
    해당 Phase의 PhaseManager가 존재하는지 확인하고, 없으면 생성
    
    Args:
        phase_num: Phase 번호 (1-5)
    
    Returns:
        PhaseManager 인스턴스 또는 None (실패 시)
    """
    if phase_num < 1 or phase_num > 5:
        raise ValueError("Phase number must be between 1 and 5")
    
    manager_key = f"phase{phase_num}_manager"
    
    # 이미 존재하면 재사용
    if manager_key in st.session_state and st.session_state[manager_key] is not None:
        return st.session_state[manager_key]
    
    # AWS 서비스 먼저 초기화
    if not initialize_aws_services():
        return None
    
    # PhaseManager 생성
    try:
        dynamo_manager = st.session_state.get("dynamo_manager")
        phase_manager = PhaseManager(dynamo_manager=dynamo_manager, phase_num=phase_num)
        st.session_state[manager_key] = phase_manager
        return phase_manager
    except Exception as e:
        st.warning(f"Phase {phase_num} 매니저 초기화 실패: {e}")
        return None


def initialize_session(phase_num: int):
    """
    페이지별 초기화 - 한 번의 호출로 모든 필요한 초기화 수행
    
    Args:
        phase_num: Phase 번호 (1-5)
    """
    # 1. AWS 서비스 초기화
    initialize_aws_services()
    
    # 2. PhaseManager 보장 (핵심!)
    ensure_phase_manager(phase_num)
    
    # 3. Session UUID 생성 (단순 처리)
    if "session_uuid" not in st.session_state:
        st.session_state["session_uuid"] = str(uuid.uuid4())
    
    # 4. 세션 생성/조회
    session_manager = st.session_state.get("session_manager")
    session_uuid = st.session_state.get("session_uuid")
    user_id = st.session_state.get("user_id", "anonymous")
    if session_manager and session_uuid:
        try:
            session_info = session_manager.get_or_create_session(
                session_uuid=session_uuid,
                user_id=user_id
            )
            if session_info:
                st.session_state["session_created"] = True
        except Exception as e:
            st.warning(f"세션 생성/조회 실패: {e}")
