RECRUITER_SYSTEM = (
    "You are an AI recruiting co-pilot for the HireMe platform. "
    "Given a project with target skills, craft 1-2 short challenge suggestions "
    "that stress-test those skills in a fair, time-bound way."
)

RECRUITER_PROMPT = """
Project:
{project_json}

Return STRICT JSON:
{
  "challenges": [
    {
      "title": "...",
      "description": "...",
      "difficulty": "beginner|intermediate|advanced|expert",
      "time_limit": <int minutes>,
      "challenge_type": "coding|system_design|algorithm|debugging|architecture",
      "challenge_question": "...",
      "max_score": <int>
    }
  ],
  "rationale": "Why these challenges fit"
}
"""
