from i18n.locale import normalize_locale


SIMULATION_ENGLISH_REPLACEMENTS = {
    '<html lang="ko">': '<html lang="en">',
    "<title>원운동 힘 방향 탐구</title>": "<title>Circular Motion Force Direction</title>",
    "🌍 원운동 힘 방향 탐구": "🌍 Circular Motion Force Direction",
    "<span>속도</span>": "<span>Velocity</span>",
    "<span>힘</span>": "<span>Force</span>",
    "<span>궤적</span>": "<span>Trail</span>",
    "⚙️ 시뮬레이션 제어": "⚙️ Simulation Controls",
    "힘의 각도 (힘의 방향)": "Force Angle (Force Direction)",
    "힘의 크기": "Force Magnitude",
    "궤도 반지름": "Orbit Radius",
    '<button id="resetBtn">초기화</button>': '<button id="resetBtn">Reset</button>',
    '<button id="stepBtn">스텝</button>': '<button id="stepBtn">Step</button>',
    '<button id="runBtn">연속</button>': '<button id="runBtn">Run</button>',
    "'#0074D9', '속도', 3": "'#0074D9', 'Velocity', 3",
    "'#FF4136', '힘', 3": "'#FF4136', 'Force', 3",
    "runBtn.textContent = '연속'": "runBtn.textContent = 'Run'",
    "runBtn.textContent = '정지'": "runBtn.textContent = 'Stop'",
}


def localize_simulation_html(html: str, locale: str) -> str:
    if normalize_locale(locale) != "en":
        return html
    for korean, english in SIMULATION_ENGLISH_REPLACEMENTS.items():
        html = html.replace(korean, english)
    return html
