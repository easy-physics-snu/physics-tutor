import io
import numpy as np
import streamlit as st

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
