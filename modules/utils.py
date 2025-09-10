import io
import os
import numpy as np
import streamlit as st
from concurrent.futures import ThreadPoolExecutor

from PIL import Image


# Function to convert PNG to BytesIO
def png_to_bytesio(file_path):
    # Open the PNG image
    with Image.open(file_path) as img:
        # Create a BytesIO object
        byte_io = io.BytesIO()
        # Save the image into the BytesIO object as PNG
        img.save(byte_io, format='PNG')
        # Reset the file pointer to the beginning
        byte_io.seek(0)
        return byte_io


# 이미지을 캐시 저장(시간이 오래 걸리는 작업을 처리할 예정)
@st.cache_resource(show_spinner="업로드한 이미지를 처리 중입니다...")
def process_png_to_bytesio(file_path) -> str:
    # 업로드한 파일을 캐시 디렉토리에 저장합니다.
    file_content = png_to_bytesio(file_path).getvalue()
    # file_content = file.read()
    file_name = file_path.split("/")[-1].split(".")[0]
    # file_path = f"./.cache/files/{file.name}"
    file_path = f"./.cache/files/{file_name}"

    with open(file_path, "wb") as f:
        f.write(file_content)

    return file_path


def overlay_png_and_np(base_image_path: str, overlay_np: np.ndarray, overlay_alpha=255) -> Image:
    """
    base_image_path: 배경 PNG 이미지 파일 경로
    overlay_np: (H, W, 3) 또는 (H, W, 4) ndarray
    overlay_alpha: 0~255, 드로잉 선의 투명도 (255면 완전 불투명)  
    """

    # base 이미지를 RGBA로 열기
    base_img = Image.open(base_image_path).convert('RGBA')

    # overlay_np를 RGBA로 변환
    if overlay_np.shape[2] == 3:
        # 불투명 알파 채널 추가
        alpha = 255 * np.ones((overlay_np.shape[0], overlay_np.shape[1], 1), dtype=overlay_np.dtype)
        overlay_np = np.concatenate([overlay_np, alpha], axis=-1)
    overlay_img = Image.fromarray(overlay_np.astype('uint8'), 'RGBA')

    # 크기 맞추기
    if overlay_img.size != base_img.size:
        overlay_img = overlay_img.resize(base_img.size, Image.Resampling.LANCZOS)

    # overlay 드로잉 전체 투명도 조정 (선만 있다면 보통 흰배경+검정선)
    if overlay_alpha < 255:
        r, g, b, a = overlay_img.split()
        # 기존 alpha가 255인 부분만 overlay_alpha로 바꿔줌
        new_alpha = a.point(lambda p: overlay_alpha if p > 0 else 0)
        overlay_img = Image.merge('RGBA', (r, g, b, new_alpha))

    # 합성
    return Image.alpha_composite(base_img, overlay_img)


@st.cache_resource(show_spinner="캔버스 이미지를 최적화하고 로딩 중...")
def load_and_optimize_canvas_image(image_path, target_size=(500, 500)):
    """
    캔버스 이미지를 강제로 로딩하고 최적화합니다.
    캐싱을 통해 성능을 향상시키고, 반드시 이미지를 반환합니다.
    
    Args:
        image_path (str): 이미지 파일 경로
        target_size (tuple): 최적화할 목표 크기 (width, height)
    
    Returns:
        PIL.Image: 최적화된 이미지 (반드시 반환)
    """
    import os
    import tempfile
    
    try:
        # 파일 존재 여부 확인
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"이미지 파일이 존재하지 않습니다: {image_path}")
        
        # 파일 크기 확인
        if os.path.getsize(image_path) == 0:
            raise ValueError(f"이미지 파일이 비어있습니다: {image_path}")
        
        # 이미지 로드
        with Image.open(image_path) as img:
            # 이미지 검증
            img.verify()
            
        # 다시 열어서 처리
        img = Image.open(image_path)
        
        # RGBA 모드로 변환 (투명도 지원)
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        
        # 이미지가 이미 최적화된 크기인지 확인
        if img.size != target_size:
            print(f"이미지 크기 조정: {img.size} -> {target_size}")
            img = img.resize(target_size, Image.Resampling.LANCZOS)
        
        # 메모리 최적화를 위해 이미지 복사
        optimized_img = img.copy()
        
        print(f"캔버스 이미지 로드 성공: {image_path} (크기: {optimized_img.size})")
        return optimized_img
        
    except Exception as e:
        print(f"이미지 로드 실패, 기본 이미지 생성: {str(e)}")
        # 실패 시 기본 이미지 생성 (반드시 반환)
        fallback_img = Image.new('RGBA', target_size, (238, 238, 238, 255))  # #EEEEEE
        print(f"기본 이미지 생성: {target_size}")
        return fallback_img


def create_canvas_with_guaranteed_image(canvas_image_path, **canvas_kwargs):
    """
    캔버스 이미지를 반드시 로딩하는 캔버스 생성 함수
    이미지 로드에 실패해도 기본 이미지를 생성하여 반드시 캔버스를 표시합니다.
    
    Args:
        canvas_image_path (str): 캔버스 배경 이미지 경로
        **canvas_kwargs: st_canvas의 추가 인자들
    
    Returns:
        st_canvas 결과
    """
    import streamlit as st
    from streamlit_drawable_canvas import st_canvas
    
    # 캔버스 크기 추출 (기본값 500x500)
    canvas_height = canvas_kwargs.get('height', 500)
    canvas_width = canvas_kwargs.get('width', 500)
    target_size = (canvas_width, canvas_height)
    
    # 이미지를 반드시 로딩 (캐싱됨)
    background_image = load_and_optimize_canvas_image(canvas_image_path, target_size)
    
    # 기본 캔버스 설정
    default_kwargs = {
        "fill_color": "rgba(255, 165, 0, 0.3)",
        "stroke_width": 3,
        "stroke_color": "#000000",
        "background_color": "#EEEEEE",
        "update_streamlit": True,
        "height": canvas_height,
        "width": canvas_width,
        "drawing_mode": "freedraw",
        "point_display_radius": 0,
    }
    
    # 사용자 설정으로 기본값 덮어쓰기
    default_kwargs.update(canvas_kwargs)
    
    # 반드시 background_image 설정 (최적화된 이미지 또는 기본 이미지)
    default_kwargs["background_image"] = background_image
    
    return st_canvas(**default_kwargs)


def load_image_in_thread(image_path, target_size=(500, 500)):
    """
    스레드에서 이미지를 로딩합니다.
    
    Args:
        image_path (str): 이미지 파일 경로
        target_size (tuple): 목표 크기
    
    Returns:
        PIL.Image: 로드된 이미지
    """
    try:
        # 파일 존재 여부 확인
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"이미지 파일이 존재하지 않습니다: {image_path}")
        
        # 파일 크기 확인
        if os.path.getsize(image_path) == 0:
            raise ValueError(f"이미지 파일이 비어있습니다: {image_path}")
        
        # 이미지 로드
        with Image.open(image_path) as img:
            img.verify()
        
        # 다시 열어서 처리
        img = Image.open(image_path)
        
        # RGBA 모드로 변환
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        
        # 크기 조정
        if img.size != target_size:
            img = img.resize(target_size, Image.Resampling.LANCZOS)
        
        return img
        
    except Exception as e:
        print(f"이미지 로드 실패, 기본 이미지 생성: {str(e)}")
        # 기본 이미지 생성
        return Image.new('RGBA', target_size, (238, 238, 238, 255))


@st.cache_resource(show_spinner="캔버스 이미지를 로딩 중...")
def get_cached_image_with_thread(image_path, target_size=(500, 500)):
    """
    스레드 풀을 사용하여 이미지를 로딩합니다.
    """
    def _load_with_thread():
        return load_image_in_thread(image_path, target_size)
    
    # 스레드 풀에서 실행
    with ThreadPoolExecutor() as executor:
        future = executor.submit(_load_with_thread)
        return future.result()


def create_async_canvas_with_guaranteed_image(canvas_image_path, **canvas_kwargs):
    """
    스레드 풀을 사용하여 캔버스 이미지를 로딩하는 캔버스 생성 함수
    """
    import streamlit as st
    from streamlit_drawable_canvas import st_canvas
    
    # 캔버스 크기 추출
    canvas_height = canvas_kwargs.get('height', 500)
    canvas_width = canvas_kwargs.get('width', 500)
    target_size = (canvas_width, canvas_height)
    
    # 스레드 풀을 사용하여 이미지 로딩 (캐싱됨)
    try:
        background_image = get_cached_image_with_thread(canvas_image_path, target_size)
        print(f"캔버스 이미지 로드 성공: {canvas_image_path}")
    except Exception as e:
        print(f"이미지 로드 실패, 기본 이미지 사용: {str(e)}")
        background_image = Image.new('RGBA', target_size, (238, 238, 238, 255))
    
    # 기본 캔버스 설정
    default_kwargs = {
        "fill_color": "rgba(255, 165, 0, 0.3)",
        "stroke_width": 3,
        "stroke_color": "#000000",
        "background_color": "#EEEEEE",
        "update_streamlit": True,
        "height": canvas_height,
        "width": canvas_width,
        "drawing_mode": "freedraw",
        "point_display_radius": 0,
    }
    
    # 사용자 설정으로 기본값 덮어쓰기
    default_kwargs.update(canvas_kwargs)
    
    # 반드시 background_image 설정
    default_kwargs["background_image"] = background_image
    
    print(f"캔버스 생성 완료: {canvas_image_path}")
    return st_canvas(**default_kwargs)


def preload_canvas_image(image_path, target_size=(500, 500)):
    """
    캔버스 이미지를 미리 로딩하여 캐시에 저장합니다.
    앱 시작 시 호출하여 이미지를 미리 준비합니다.
    """
    try:
        # 이미지를 미리 로딩하여 캐시에 저장
        get_cached_image_with_thread(image_path, target_size)
        print(f"캔버스 이미지 프리로딩 완료: {image_path}")
        return True
    except Exception as e:
        print(f"캔버스 이미지 프리로딩 실패: {str(e)}")
        return False


def ensure_canvas_image_loaded(image_path, target_size=(500, 500)):
    """
    캔버스 이미지가 로딩되었는지 확인하고, 필요시 프리로딩합니다.
    """
    try:
        # 캐시에서 이미지 확인
        if hasattr(ensure_canvas_image_loaded, '_loaded_images'):
            if image_path in ensure_canvas_image_loaded._loaded_images:
                return True
        else:
            ensure_canvas_image_loaded._loaded_images = set()
        
        # 이미지 프리로딩
        success = preload_canvas_image(image_path, target_size)
        if success:
            ensure_canvas_image_loaded._loaded_images.add(image_path)
        return success
        
    except Exception as e:
        print(f"캔버스 이미지 로딩 확인 실패: {str(e)}")
        return False
