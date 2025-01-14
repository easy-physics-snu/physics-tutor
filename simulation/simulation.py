"""
# 운동 시뮬레이션 코드
# 이 시뮬레이션은 물체의 운동을 시각적으로 보여줍니다.
# 초기 기본 상수 및 calculate_force 함수만 수정할 수 있습니다.
# simulation plot 함수는 error 발생으로 인해 수정이 불가피한 경우에만 수정할 수 있습니다.
# 그 외 다른 함수는 수정해서는 안 됩니다.
"""

import os
import streamlit as st
import plotly.graph_objects as go
import numpy as np
import math
from datetime import datetime
import time

# 시뮬레이션 초기 기본 상수 설정
# WINDOW_WIDTH, HEIGHT: 시뮬레이션 창의 크기
# ORBIT_RADIUS: 원운동의 반지름
# BALL_MASS: 물체의 질량
# INITIAL_SPEED: 초기 속도
# VECTOR_SCALE: 벡터 표시 크기 조절 상수
WINDOW_WIDTH = 800
WINDOW_HEIGHT = 600
ORBIT_RADIUS = 100
BALL_MASS = 1
BALL_RADIUS = 10
INITIAL_SPEED = 200
VECTOR_SCALE = 0.2
FPS = 60
center_x = WINDOW_WIDTH // 2
center_y = WINDOW_HEIGHT // 2

def calculate_force(position, velocity):
    """
    물체에 작용하는 힘을 계산하는 이 함수는 유저의 요청에 따라 달라지게 되며, 
    요청시 물체의 현재 위치와 속도를 사용하여 함수를 구성할 수도 있습니다.
    """
    # 여기에 실제 힘을 계산하는 코드를 추가할 수 있습니다.
    # 현재는 힘이 0인 상태입니다. 
    # 만약 유저의 요청에 힘의 크기가 명시되지 않은 경우 크기가 100인 힘을 만드세요.
    return np.array([0, 0])

def init_simulation_state():
    """
    시뮬레이션의 초기 상태를 설정하는 함수
    - position: 물체의 초기 위치 (원의 가장 오른쪽 지점)
    - velocity: 초기 속도 (위쪽 방향)
    - trajectory_points: 물체의 궤적을 저장하는 리스트
    - show_velocity_vector: 속도 벡터 표시 여부
    - show_force_vector: 힘 벡터 표시 여부
    """
    if 'simulation_state' not in st.session_state:
        st.session_state.simulation_state = {
            'position': [center_x + ORBIT_RADIUS, center_y],
            'velocity': [0, INITIAL_SPEED],
            'trajectory_points': [],
            'simulation_running': False,
            'show_velocity_vector': True,
            'show_force_vector': True,
        }

# 이 함수는 수정되지 않아야 함.
def update_position(dt):
    """
    물체의 위치를 업데이트하는 함수이며, 이 함수는 물리학 기본 법칙이므로 수정하면 안 됨.
    
    1. 현재 위치에서의 구심력 계산
    2. 가속도 계산 (F = ma)
    3. 속도 업데이트 (v = v₀ + at)
    4. 위치 업데이트 (x = x₀ + vt)
    5. 궤적 점 저장 (최대 500개 제한)
    """
    state = st.session_state.simulation_state
    force = calculate_force(state['position'], state['velocity'])
    acceleration = force / BALL_MASS
    
    # 벡터 연산으로 단순화
    state['velocity'] = [v + a * dt for v, a in zip(state['velocity'], acceleration)]
    state['position'] = [p + v * dt for p, v in zip(state['position'], state['velocity'])]
    
    # 궤적 점 개수 제한 (예: 최대 50개)
    MAX_TRAJECTORY_POINTS = 500
    state['trajectory_points'].append(state['position'].copy())
    if len(state['trajectory_points']) > MAX_TRAJECTORY_POINTS:
        state['trajectory_points'].pop(0)  # 가장 오래된 점 제거

# 이 함수는 수정되지 않아야 함.
def create_arrow(start, end, color):
    """
    벡터를 화살표로 표시하는 함수이며, 이 부분은 수정되지 않아야 함.
    
    1. 화살표의 방향 벡터 계산
    2. 화살표 머리 부분 생성 (30도 각도)
    3. 시작점, 끝점, 화살표 머리를 연결하는 선분 생성
    
    Returns:
        화살표 모양의 Plotly Scatter 객체
    """
    # 리스트를 NumPy 배열로 변환
    start = np.array(start)
    end = np.array(end)
    
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    
    length = np.linalg.norm(end - start)
    if np.all(length == 0):
        return None
        
    unit_vector = np.array([dx, dy]) / length
    arrow_head_length = 20
    angle = np.radians(30)
    
    rot_matrix = np.array([[np.cos(angle), -np.sin(angle)],
                          [np.sin(angle), np.cos(angle)]])
    
    head1 = end - arrow_head_length * (rot_matrix @ unit_vector)
    head2 = end - arrow_head_length * (rot_matrix.T @ unit_vector)
    
    arrow_x = [start[0], end[0], None, end[0], head1[0], None, end[0], head2[0]]
    arrow_y = [start[1], end[1], None, end[1], head1[1], None, end[1], head2[1]]
    
    return go.Scatter(x=arrow_x, y=arrow_y, mode='lines',
                     line=dict(color=color, width=2), showlegend=False)

def create_simulation_plot():
    """
    시뮬레이션 화면을 생성하는 함수
    
    표시 요소:
    1. 원형 궤도
    2. 중심점
    3. 운동하는 물체
    4. 물체의 궤적
    5. 벡터 (옵션)
    """
    state = st.session_state.simulation_state
    center = [WINDOW_WIDTH/2, WINDOW_HEIGHT/2]
    
    fig = go.Figure()
    
    # 궤도, 중심점, 공 위치를 한번에 추가
    fig.add_traces([
        # 원형 궤도
        go.Scatter(
            x=center[0] + ORBIT_RADIUS*np.cos(np.linspace(0, 2*np.pi, 100)),
            y=center[1] + ORBIT_RADIUS*np.sin(np.linspace(0, 2*np.pi, 100)),
            mode='lines', line=dict(color='black', width=1)
        ),
        # 중심점
        go.Scatter(
            x=[center[0]],
            y=[center[1]],
            mode='markers',
            marker=dict(color='red', size=8),
            hovertemplate=f'원의 반지름: {int(round(ORBIT_RADIUS))}<extra></extra>',
            showlegend=False
        ),
        # 공
        go.Scatter(
            x=[state['position'][0]],
            y=[state['position'][1]],
            mode='markers',
            marker=dict(color='blue', size=15),
            hovertemplate=f'질량: {int(round(BALL_MASS))}<extra></extra>',
            showlegend=False
        )
    ])
    
    # 궤적이 있는 경우만 추가
    if state['trajectory_points']:
        trajectory = np.array(state['trajectory_points'])
        fig.add_trace(go.Scatter(
            x=trajectory[:, 0], y=trajectory[:, 1],
            mode='markers', marker=dict(color='black', size=2)
        ))
    
    # 벡터 표시 (속도, 힘)
    vectors_info = [
        (state['show_velocity_vector'], state['velocity'], 'blue', '속도'),
        (state['show_force_vector'], calculate_force(state['position'], state['velocity']), 'green', '힘')
    ]
    
    for show_vector, vector_type, color, vector_name in vectors_info:
        if show_vector:
            # 벡터의 크기 계산
            vector_magnitude = np.linalg.norm(vector_type)
            
            # 벡터 화살표 끝점 계산
            vector_end = [
                state['position'][0] + vector_type[0] * VECTOR_SCALE,
                state['position'][1] + vector_type[1] * VECTOR_SCALE
            ]
            
            # 벡터 화살표 추가
            arrow = create_arrow(state['position'], vector_end, color)
            if arrow:
                fig.add_trace(arrow)
            
            # 벡터 크기 텍스트 위치 계산 (물체 아래)
            text_x = state['position'][0]
            text_y = state['position'][1] - (40 if vector_name == "속도" else 60)  # 속도는 40픽셀, 힘은 60픽셀 아래
            
            # 벡터 크기 텍스트 추가
            fig.add_trace(go.Scatter(
                x=[text_x],
                y=[text_y],
                mode='text',
                text=[f'{vector_name} 크기: {int(round(vector_magnitude))}'],
                textfont=dict(color=color, size=12),
                showlegend=False
            ))
    
    # 레이아웃 설정
    fig.update_layout(
        width=WINDOW_WIDTH, height=WINDOW_HEIGHT,
        showlegend=False,
        xaxis=dict(range=[0, WINDOW_WIDTH], scaleanchor="y", scaleratio=1),
        yaxis=dict(range=[0, WINDOW_HEIGHT]),
        margin=dict(l=0, r=0, t=0, b=0),
        plot_bgcolor='white'
    )
    
    # 힌트 텍스트 추가
    hint_text = "물체의 속도는 알짜힘이 작용하지 않으면 변하지 않는다.(뉴턴의 제1운동법칙)<br>물체의 속도는 알짜힘이 작용하는 방향으로 변한다.(뉴턴의 제2운동법칙)"
    
    fig.add_annotation(
        x=WINDOW_WIDTH-10,  # 오른쪽 끝에서 10픽셀 안쪽
        y=10,  # 아래쪽에서 10픽셀 위
        text="💡힌트",
        showarrow=False,
        xanchor="right",
        yanchor="bottom",
        bgcolor="rgba(255, 255, 255, 0.8)",
        bordercolor="rgba(0, 0, 0, 0.3)",
        borderwidth=1,
        borderpad=4,
        hovertext=hint_text,
        font=dict(size=12),
        hoverlabel=dict(
            bgcolor="white",
            bordercolor="black",
            font=dict(size=12)
        )
    )
    
    return fig

def reset_simulation():
    """
    시뮬레이션을 초기 상태로 재설정하는 함수
    """
    return {
        'position': [center_x + ORBIT_RADIUS, center_y],
        'velocity': [0, INITIAL_SPEED],
        'trajectory_points': [],
        'simulation_running': False,
        'show_velocity_vector': True,
        'show_force_vector': True,
    }

def main():
    init_simulation_state()
    
    # 컨트롤 버튼들을 딕셔너리로 관리
    controls = {
        "▶️ 시뮬레이션 시작/정지": lambda: {'simulation_running': not st.session_state.simulation_state['simulation_running']},
        "🟢 힘 표시": lambda: {'show_force_vector': not st.session_state.simulation_state['show_force_vector']},
        "🔵 속도 표시": lambda: {'show_velocity_vector': not st.session_state.simulation_state['show_velocity_vector']},
        "🔄 다시 재생": reset_simulation,
    }
    
    # 버튼 생성 및 상태 업데이트
    cols = st.columns(len(controls))
    for i, (label, update_func) in enumerate(controls.items()):
        unique_key = f"sim_button_{label}_{st.session_state.get('button_timestamp', 0)}"
        if cols[i].button(label, key=unique_key, type="secondary", use_container_width=True):
            st.session_state.simulation_state.update(update_func())
    
    # 플롯 placeholder 생성
    plot_container = st.empty()
    
    # 시뮬레이션 실행 및 표시
    while st.session_state.simulation_state['simulation_running']:
        update_position(1/FPS)
        fig = create_simulation_plot()
        plot_container.plotly_chart(fig, use_container_width=False)
        time.sleep(1/FPS)  # FPS에 맞춰 대기
    
    # 시뮬레이션이 멈춰있을 때도 현재 상태 표시
    if not st.session_state.simulation_state['simulation_running']:
        fig = create_simulation_plot()
        plot_container.plotly_chart(fig, use_container_width=False)

if __name__ == "__main__":
    main()