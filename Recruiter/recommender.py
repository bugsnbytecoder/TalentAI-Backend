from typing import Dict, List, Tuple

from HireMe.models import Developer
from Recruiter.models import Project


def _build_dev_skill_map(dev: Developer) -> Dict[str, Tuple[int, bool]]:
    """
    Return {skill_name_lower: (level 0-100, validated bool)}
    """
    out: Dict[str, Tuple[int, bool]] = {}
    for s in dev.skills.all():
        out[s.name.strip().lower()] = (s.level, bool(s.validated))
    return out


def compute_fit_score(project: Project, developer: Developer) -> Tuple[float, Dict]:
    """
    Compute 0-100 fit score from skill match (weighted), validation bonus, and dev_score modifier.
    """
    reqs = list(project.required_skills.all())
    if not reqs:
        base = min(100.0, developer.dev_score / 10.0)  # 0..100
        return base, {"skills": [], "dev_score_component": base, "note": "No project skills; using dev_score only."}

    dev_map = _build_dev_skill_map(developer)

    total_weight = 0.0
    skill_component = 0.0
    details: List[Dict] = []

    for req in reqs:
        weight = max(10, req.required_level)
        total_weight += weight

        level, validated = dev_map.get(req.name.strip().lower(), (0, False))

        ratio = min(1.0, level / max(1.0, req.required_level))
        val_bonus = 0.1 if validated else 0.0  # +10%

        contribution = (ratio + val_bonus) * weight
        skill_component += contribution

        details.append({
            "skill": req.name,
            "required_level": req.required_level,
            "dev_level": level,
            "validated": validated,
            "ratio": round(ratio, 3),
            "weight": weight,
            "contribution": round(contribution, 3),
        })

    skill_score = (skill_component / total_weight) * 100.0 if total_weight > 0 else 0.0
    dev_adj = (developer.dev_score / 1000.0) * 10.0

    final = max(0.0, min(100.0, skill_score + dev_adj))
    breakdown = {
        "skills": details,
        "skill_score": round(skill_score, 2),
        "dev_score_component": round(dev_adj, 2),
        "final": round(final, 2),
    }
    return round(final, 2), breakdown


def recommend_candidates_for_project(project: Project, limit: int = 50) -> List[Tuple[Developer, float, Dict]]:
    """
    Rank all developers by fit for the given project.
    """
    developers = Developer.objects.prefetch_related("skills").all()
    scored: List[Tuple[Developer, float, Dict]] = []
    for dev in developers:
        fit, breakdown = compute_fit_score(project, dev)
        scored.append((dev, fit, breakdown))
    scored.sort(key=lambda t: t[1], reverse=True)
    return scored[:limit]
