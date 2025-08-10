# Recruiter/agent.py
import json
from typing import Any, Dict

from HireMe.utils import generate_response_with_groq

RECRUITER_SYSTEM = (
    "You are an AI recruiting co-pilot for the HireMe platform. "
    "Given a project with target skills, craft 1-2 short challenge suggestions "
    "that stress-test those skills in a fair, time-bound way. Return STRICT JSON."
)

RECRUITER_PROMPT = """
Project:
{project_json}

Return STRICT JSON:
{{
  "challenges": [
    {{
      "title": "...",
      "description": "...",
      "difficulty": "beginner|intermediate|advanced|expert",
      "time_limit": <int minutes>,
      "challenge_type": "coding|system_design|algorithm|debugging|architecture",
      "challenge_question": "...",
      "max_score": <int>
    }}
  ],
  "rationale": "Why these challenges fit"
}}
"""

def _coerce_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except Exception:
        return default

def _strip_fences(s: str) -> str:
    t = s.strip()
    if t.startswith("```"):
        # remove ```json or ``` then trailing ```
        t = t.split("```", 2)
        if len(t) >= 3:
            return t[1 if t[0].startswith("json") else 1].strip()
        return s.strip("`").strip()
    return t

def ai_suggest_challenges_for_project(project_payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Call LLM and normalize whatever comes back into:
    { "challenges": [...], "rationale": "..." }
    Never throws; returns {} on failure.
    """
    try:
        prompt = RECRUITER_PROMPT.format(
            project_json=json.dumps(project_payload, ensure_ascii=False, indent=2)
        )
        messages = [
            {"role": "system", "content": RECRUITER_SYSTEM},
            {"role": "user", "content": prompt},
        ]

        raw = generate_response_with_groq(messages, response_format="json")

        # Some providers return (parsed, meta), or str JSON, or dict
        if isinstance(raw, tuple) and raw:
            raw = raw[0]

        if isinstance(raw, str):
            try:
                data = json.loads(raw)
            except Exception:
                try:
                    data = json.loads(_strip_fences(raw))
                except Exception:
                    return {}
        elif isinstance(raw, dict):
            data = raw
        else:
            return {}

        # Sometimes wrapped like {"content": {...}} or {"data": {...}} etc.
        for key in ("content", "data", "body", "result"):
            if isinstance(data, dict) and key in data and isinstance(data[key], dict):
                data = data[key]

        out = {"challenges": [], "rationale": ""}

        if isinstance(data, dict):
            ch = data.get("challenges")
            if isinstance(ch, list):
                out["challenges"] = ch
            out["rationale"] = data.get("rationale", "") or ""

        # Final sanitization
        for c in out["challenges"]:
            c["time_limit"] = _coerce_int(c.get("time_limit", 60), 60)
            c["max_score"] = _coerce_int(c.get("max_score", 100), 100)
            # normalize types
            if "challenge_type" in c and isinstance(c["challenge_type"], str):
                c["challenge_type"] = c["challenge_type"].strip().lower().replace(" ", "_")
            if "difficulty" in c and isinstance(c["difficulty"], str):
                c["difficulty"] = c["difficulty"].strip().lower()

        return out
    except Exception:
        # Never let AI issues bubble up
        return {}
