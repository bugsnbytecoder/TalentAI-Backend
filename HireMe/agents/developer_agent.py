from __future__ import annotations
import json
from typing import Any, Dict, List, Tuple

from HireMe.models import Submission
from HireMe.agents.developer_prompts import (
    RESUME_SKILL_EXTRACT_PROMPT,
    SUBMISSION_EVAL_PROMPT,
)
from HireMe.utils import generate_response_with_groq

def ai_analyze_resume(resume_text: str, profile: Dict[str, Any]) -> Tuple[int, List[Dict[str, Any]]]:
    prompt = RESUME_SKILL_EXTRACT_PROMPT.replace("<resume_text>", resume_text).replace("<profile_json>", json.dumps(profile))
    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": "Follow the system prompt and return the dev_score and skills in JSON format."},
    ]

    data = generate_response_with_groq(messages, response_format="json")[0]
    print("data", data)
    dev_score = int(data.get("dev_score", 0))
    skills = data.get("skills", [])

    # Minimal post-validate: clamp & coerce
    dev_score = max(0, min(dev_score, 1000))
    cleaned_skills: List[Dict[str, Any]] = []
    for s in skills:
        try:
            name = (s.get("name") or "").strip()
            if not name:
                continue
            level = int(s.get("level", 50))
            level = max(0, min(level, 100))
            validated = bool(s.get("validated", False))
            challenge = s.get("challenge") or {}
            # defaults for challenge
            c = {
                "title": (challenge.get("title") or f"{name} Validation Challenge").strip(),
                "description": (challenge.get("description") or f"Validate {name} with a targeted task.")[:4000],
                "difficulty": challenge.get("difficulty") or "intermediate",
                "time_limit": int(challenge.get("time_limit", 60)),
                "challenge_type": challenge.get("challenge_type") or "coding",
                "challenge_question": (challenge.get("challenge_question") or f"Demonstrate {name} proficiency.")[:4000],
                "max_score": int(challenge.get("max_score", 100)),
            }
            cleaned_skills.append({
                "name": name,
                "level": level,
                "validated": validated,
                "challenge": c,
            })
        except Exception:
            continue

    return {
        "dev_score": dev_score,
        "skills": cleaned_skills,
    }

def ai_evaluate_submission(submission: Submission) -> Dict[str, Any]:
    challenge = submission.challenge
    payload = {
        "challenge": {
            "title": challenge.title,
            "description": challenge.description,
            "difficulty": challenge.difficulty,
            "time_limit": challenge.time_limit,
            "challenge_type": challenge.challenge_type,
            "challenge_question": challenge.challenge_question,
            "max_score": challenge.max_score,
        },
        "submission": {
            "bug_analysis": submission.bug_analysis,
            "answer": submission.answer,
        },
    }

    prompt = SUBMISSION_EVAL_PROMPT.replace("<submission_json>", json.dumps(payload))
    print("prompt", prompt)
    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": "Follow the system prompt and return the score, accuracy_rate, bugs_found, bugs_missed, false_positives, ai_feedback, and evaluation_details in JSON format."},
    ]
    data = generate_response_with_groq(messages, response_format="json")[0]
    print("data", data)

    # Minimal validation with safe defaults
    out = {
        "score": int(max(0, min(int(data.get("score", 0)), challenge.max_score))),
        "accuracy_rate": float(max(0.0, min(float(data.get("accuracy_rate", 0.0)), 100.0))),
        "bugs_found": int(max(0, int(data.get("bugs_found", 0)))),
        "bugs_missed": int(max(0, int(data.get("bugs_missed", 0)))),
        "false_positives": int(max(0, int(data.get("false_positives", 0)))),
        "ai_feedback": str(data.get("ai_feedback", ""))[:4000],
        "evaluation_details": data.get("evaluation_details", {}),
    }
    return out