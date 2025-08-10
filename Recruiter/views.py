import logging
from django.db import transaction
from django.utils.timezone import now

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from HireMe.models import Developer, Challenge
from Recruiter.models import Project, CandidateRecommendation, Invitation
from Recruiter.serializers import (
    ProjectSerializer,
    CandidateRecommendationSerializer,
    InvitationSerializer,
)
from Recruiter.recommender import recommend_candidates_for_project
from HireMe.utils import create_response
from Recruiter.agent import ai_suggest_challenges_for_project


class ProjectViewSet(viewsets.ModelViewSet):
    queryset = Project.objects.all().order_by("-id")
    serializer_class = ProjectSerializer

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            project: Project = serializer.save(status="matching")

            ranked = recommend_candidates_for_project(project, limit=100)
            CandidateRecommendation.objects.filter(project=project).delete()

            created = 0
            for dev, fit, breakdown in ranked:
                CandidateRecommendation.objects.create(
                    project=project,
                    developer=dev,
                    fit_score=fit,
                    rationale=(
                        f"Skill match {breakdown.get('skill_score', 0)}%, "
                        f"dev adj {breakdown.get('dev_score_component', 0)}"
                    ),
                )
                created += 1

            project.target_count = created
            project.save(update_fields=["target_count"])

            payload = {
                "project_name": project.project_name,
                "description": project.description,
                "required_skills": list(project.required_skills.values("name", "required_level")),
            }

            try:
                ai_suggestions = ai_suggest_challenges_for_project(payload) or {}
            except Exception as e:
                logging.warning("AI suggestions failed: %s", e, exc_info=True)
                ai_suggestions = {}

            resp = {
                "project": ProjectSerializer(project).data,
                "recommendations": CandidateRecommendationSerializer(
                    CandidateRecommendation.objects.filter(project=project)
                    .order_by("-fit_score")[:20],
                    many=True,
                ).data,
                "ai_suggestions": ai_suggestions,
            }
            return create_response(
                True,
                "Project created with recommendations",
                resp,
                status_code=status.HTTP_201_CREATED,
            )
        except Exception as e:
            transaction.set_rollback(True)
            logging.exception("Project creation failed")
            return create_response(False, str(e), status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=["get"])
    def recommendations(self, request, pk=None):
        project = self.get_object()
        recs = CandidateRecommendation.objects.filter(project=project).order_by("-fit_score")
        return Response(CandidateRecommendationSerializer(recs, many=True).data)

    @action(detail=True, methods=["post"])
    def invite(self, request, pk=None):
        """
        Body: { "developer_id": <id>, "challenge_id": <optional>, "message": "..." }
        """
        project = self.get_object()
        dev_id = request.data.get("developer_id")
        ch_id = request.data.get("challenge_id")
        msg = request.data.get("message", "")

        developer = Developer.objects.filter(id=dev_id).first()
        if not developer:
            return Response({"error": "Invalid developer_id"}, status=400)

        challenge = None
        if ch_id:
            challenge = Challenge.objects.filter(id=ch_id).first()
            if not challenge:
                return Response({"error": "Invalid challenge_id"}, status=400)

        inv, created = Invitation.objects.get_or_create(
            project=project,
            developer=developer,
            defaults={"challenge": challenge, "message": msg, "status": "sent"}
        )
        if not created:
            if msg:
                inv.message = msg
            if challenge:
                inv.challenge = challenge
            inv.status = "sent"
            inv.sent_at = now()
            inv.save()

        return Response(InvitationSerializer(inv).data, status=201 if created else 200)
