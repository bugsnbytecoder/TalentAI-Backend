import base64
from typing import Dict, Any, List, Tuple

from django.db import transaction
from django.utils.timezone import now

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response

from HireMe.utils import create_response, extract_pdf_text
from Recruiter.models import Invitation
from Recruiter.serializers import InvitationSerializer
from .models import Challenge, Developer, Skill, Submission
from .serializers import DeveloperSerializer, SubmissionSerializer

from HireMe.agents.developer_agent import ai_analyze_resume, ai_evaluate_submission


def compute_new_dev_score(
    current_dev_score: int,
    submission_score: int,
    challenge_max_score: int,
    weight_current: float = 0.8,
    weight_new: float = 0.2,
) -> int:
    """
    Compute updated dev_score based on current score and normalized challenge performance.

    Args:
        current_dev_score (int): Current developer score (0–1000).
        submission_score (int): Raw score for this challenge (0–max_score).
        challenge_max_score (int): Maximum possible score for this challenge.
        weight_current (float): Weight for existing score (default 0.8).
        weight_new (float): Weight for new challenge performance (default 0.2).

    Returns:
        int: Updated developer score (0–1000).
    """
    if challenge_max_score <= 0:
        normalized_score = 0
    else:
        normalized_score = (submission_score / challenge_max_score) * 1000

    new_score = (current_dev_score * weight_current) + (normalized_score * weight_new)

    # Clamp to 0–1000 range
    return max(0, min(1000, int(round(new_score))))

class DeveloperViewSet(viewsets.ModelViewSet):
    queryset = Developer.objects.all().order_by("-id")
    serializer_class = DeveloperSerializer
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    @action(detail=False, methods=["post"], parser_classes=[MultiPartParser, FormParser])
    @transaction.atomic
    def create_developer(self, request):
        try:
            data = request.data.copy()

            # resume handling
            resume_file = data.get("resume")
            if not resume_file:
                return create_response(False, "Resume is required", status_code=status.HTTP_400_BAD_REQUEST)

            resume_text = extract_pdf_text(resume_file)
            resume_b64 = base64.b64encode(resume_text.encode("utf-8")).decode("utf-8")
            data["resume"] = resume_b64

            email = data.get("email", None)
            if not email:
                return create_response(False, "Email is required", status_code=status.HTTP_400_BAD_REQUEST)

            if Developer.objects.filter(email=email).exists():
                developer = Developer.objects.get(email=email)
            else:
                dev_ser = DeveloperSerializer(data=data)
                dev_ser.is_valid(raise_exception=True)
                developer: Developer = dev_ser.save()

            profile_for_ai = {
                "full_name": developer.full_name,
                "email": developer.email,
                "bio": developer.bio,
                "location": developer.location,
                "experience_level": developer.experience_level,
                "availability": developer.availability,
                "portfolio_links": developer.portfolio_links or [],
            }

            dev_score = 0
            skills_data = []
            if resume_text:
                result = ai_analyze_resume(resume_text, profile_for_ai)
                print("result", result)
                dev_score = result.get("dev_score", 0)
                skills_data = result.get("skills", [])

            print("dev_score", dev_score)
            print("skills_data", skills_data)
            developer.dev_score = int(dev_score or 0)
            developer.validation_status = "partially_validated" if skills_data else "not_validated"
            developer.save(update_fields=["dev_score", "validation_status"])

            created_skill_ids = []
            for s in skills_data:
                print("s", s)
                challenge_payload = s.get("challenge")
                challenge_obj = None
                if challenge_payload:
                    challenge_obj, _ = Challenge.objects.get_or_create(
                        title=(challenge_payload.get("title") or "").strip(),
                        defaults={
                            "description": (challenge_payload.get("description") or "")[:4000],
                            "difficulty": challenge_payload.get("difficulty", "intermediate"),
                            "time_limit": int(challenge_payload.get("time_limit", 60)),
                            "challenge_type": challenge_payload.get("challenge_type", "coding"),
                            "challenge_question": (challenge_payload.get("challenge_question") or "")[:4000],
                            "max_score": int(challenge_payload.get("max_score", 100)),
                        },
                    )

                skill_obj, created = Skill.objects.get_or_create(
                    name=(s.get("name") or "").strip(),
                    challenge=challenge_obj,
                    defaults={
                        "level": int(s.get("level", 50)),
                        "validated": False,
                    },
                )
                if not created:
                    changed = False
                    lvl = int(s.get("level", skill_obj.level))
                    if lvl != skill_obj.level:
                        skill_obj.level = lvl
                        changed = True
                    val = bool(s.get("validated", skill_obj.validated))
                    if val != skill_obj.validated:
                        skill_obj.validated = val
                        changed = True
                    if changed:
                        skill_obj.save(update_fields=["level", "validated"])

                created_skill_ids.append(skill_obj.id)

            if created_skill_ids:
                developer.skills.add(*Skill.objects.filter(id__in=created_skill_ids))

            return create_response(True, "Developer created", DeveloperSerializer(developer).data, status_code=status.HTTP_201_CREATED)

        except Exception as e:
            transaction.set_rollback(True)
            return create_response(False, str(e), status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=["post"], parser_classes=[JSONParser])
    @transaction.atomic
    def submit_challenge(self, request):
        try:
            payload = request.data
            developer = Developer.objects.filter(id=payload.get("developer")).first()
            challenge = Challenge.objects.filter(id=payload.get("challenge")).first()
            if not developer or not challenge:
                return Response({"error": "Invalid developer or challenge id."}, status=404)

            submission = Submission.objects.create(
                developer=developer,
                challenge=challenge,
                bug_analysis=payload.get("bug_analysis", ""),
                answer=payload.get("answer", ""),
                status="evaluating",
                created_at=now(),
            )

            scoring = ai_evaluate_submission(submission)

            submission.score = scoring.get("score")
            submission.accuracy_rate = scoring.get("accuracy_rate")
            submission.bugs_found = scoring.get("bugs_found")
            submission.bugs_missed = scoring.get("bugs_missed")
            submission.false_positives = scoring.get("false_positives")
            submission.ai_feedback = scoring.get("ai_feedback", "")
            submission.evaluation_details = scoring.get("evaluation_details", {})
            submission.status = "completed"
            submission.save()

            developer.dev_score = int(developer.dev_score * 0.8 + (submission.score or 0) * 0.2)
            developer.save(update_fields=["dev_score"])

            return create_response(True, "Submission evaluated", SubmissionSerializer(submission).data, status_code=status.HTTP_201_CREATED)

        except Exception as e:
            transaction.set_rollback(True)
            return create_response(False, str(e), status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    @action(detail=False, methods=["get"])
    def fetch_submissions(self, request):
        submissions = Submission.objects.all().order_by("-id")
        return Response(SubmissionSerializer(submissions, many=True).data)
        
    @action(detail=True, methods=["get"])
    def invites(self, request, pk=None):
        dev = self.get_object()
        invites = Invitation.objects.filter(developer=dev).order_by("-sent_at")
        return Response(InvitationSerializer(invites, many=True).data)

    @action(detail=True, methods=["post"])
    def accept_invite(self, request, pk=None):
        dev = self.get_object()
        inv_id = request.data.get("invitation_id")
        inv = Invitation.objects.filter(id=inv_id, developer=dev).first()
        if not inv:
            return Response({"error": "Invalid invitation"}, status=404)
        inv.status = "accepted"
        inv.responded_at = now()
        inv.save()
        return Response(InvitationSerializer(inv).data)

    @action(detail=True, methods=["post"])
    def decline_invite(self, request, pk=None):
        dev = self.get_object()
        inv_id = request.data.get("invitation_id")
        inv = Invitation.objects.filter(id=inv_id, developer=dev).first()
        if not inv:
            return Response({"error": "Invalid invitation"}, status=404)
        inv.status = "declined"
        inv.responded_at = now()
        inv.save()
        return Response(InvitationSerializer(inv).data)