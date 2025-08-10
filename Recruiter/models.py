from django.db import models
from django.utils.timezone import now

from HireMe.models import Developer, Challenge


class ProjectSkill(models.Model):
    name = models.CharField(max_length=64)
    required_level = models.IntegerField(default=70)  # 0–100

    class Meta:
        unique_together = ("name", "required_level")

    def __str__(self) -> str:
        return f"{self.name} ≥ {self.required_level}"


class Project(models.Model):
    STATUS = [
        ("draft", "Draft"),
        ("matching", "Matching"),
        ("challenging", "Challenging"),
        ("closed", "Closed"),
    ]

    project_name = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=32, choices=STATUS, default="draft")
    automation_enabled = models.BooleanField(default=False)
    required_skills = models.ManyToManyField(ProjectSkill, related_name="projects", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # convenience stats
    target_count = models.IntegerField(default=0)

    def __str__(self) -> str:
        return f"{self.project_name} ({self.status})"


class CandidateRecommendation(models.Model):
    project = models.ForeignKey(Project, related_name="recommendations", on_delete=models.CASCADE)
    developer = models.ForeignKey(Developer, related_name="recommended_for", on_delete=models.CASCADE)
    fit_score = models.FloatField(default=0.0)  # 0–100
    rationale = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("project", "developer")


class Invitation(models.Model):
    STATUS = [
        ("sent", "Sent"),
        ("accepted", "Accepted"),
        ("declined", "Declined"),
        ("expired", "Expired"),
        ("completed", "Completed"),
    ]

    project = models.ForeignKey(Project, related_name="invitations", on_delete=models.CASCADE)
    developer = models.ForeignKey(Developer, related_name="invitations", on_delete=models.CASCADE)
    challenge = models.ForeignKey(Challenge, null=True, blank=True, on_delete=models.SET_NULL)
    status = models.CharField(max_length=16, choices=STATUS, default="sent")
    message = models.TextField(blank=True, default="")
    sent_at = models.DateTimeField(default=now)
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("project", "developer")
