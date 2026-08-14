import json
from typing import Any

from i18n.locale import normalize_locale


CONCEPT_IDS = {"gravity", "earth_center_direction", "circular_motion"}
CONCEPT_LABELS = {
    "en": {
        "gravity": "gravity",
        "earth_center_direction": "direction toward Earth's center",
        "circular_motion": "circular motion",
    },
    "ko": {
        "gravity": "중력",
        "earth_center_direction": "지구 중심 방향",
        "circular_motion": "원운동",
    },
}


def format_concepts(concepts: list[str], locale: str) -> str:
    labels = CONCEPT_LABELS[normalize_locale(locale)]
    return ", ".join(labels.get(concept, concept) for concept in concepts)


def build_application_evaluation_prompt(
    *,
    question: str,
    student_answer: str,
    conversation_history: str,
    locale: str,
) -> str:
    locale = normalize_locale(locale)
    response_language = "English" if locale == "en" else "Korean"
    return f"""You are a physics education evaluator.

Problem:
{question}

Student's latest message:
{student_answer}

Conversation history:
{conversation_history or "(none)"}

First determine whether the message is a concept question or an attempted answer.
If it is a general physics question, answer it directly and set score to 0.
If it asks for the exact answer to this problem, guide the student with a question instead of revealing it.

For an attempted answer, assess these three independent concepts:
1. gravity: Earth exerts gravity/a force on the Moon;
2. earth_center_direction: that force points toward Earth's center;
3. circular_motion: the force enables the Moon to remain in orbit/circular motion.
Centripetal force is optional and must never be reported as missing.
An answer containing all three concepts should normally score 95-100. Gravity plus direction
should normally score 80-94. Detect the serious misconception that the force points toward
the Moon's center.

Write feedback in {response_language}, regardless of the language of the student's message.
Keep feedback positive, specific, and no longer than three sentences.

Return exactly one JSON object with these stable fields:
{{
  "is_correct": true or false,
  "score": integer from 0 to 100,
  "missing_concepts": [zero or more of "gravity", "earth_center_direction", "circular_motion"],
  "incorrect_concepts": [short stable English identifiers],
  "feedback": "feedback in {response_language}"
}}
"""


def parse_application_evaluation(raw_response: str) -> dict[str, Any]:
    start = raw_response.find("{")
    end = raw_response.rfind("}")
    if start == -1 or end == -1 or start > end:
        raise ValueError("Evaluation response does not contain a JSON object")

    data = json.loads(raw_response[start : end + 1])
    score = max(0, min(100, int(data.get("score", 0))))
    missing = [
        concept
        for concept in data.get("missing_concepts", [])
        if concept in CONCEPT_IDS
    ]
    incorrect = [str(concept) for concept in data.get("incorrect_concepts", [])]
    feedback = str(data.get("feedback", "")).strip()
    if not feedback:
        raise ValueError("Evaluation response is missing feedback")

    return {
        "is_correct": bool(data.get("is_correct", score >= 80)),
        "score": score,
        "missing_concepts": missing,
        "incorrect_concepts": incorrect,
        "feedback": feedback,
    }
