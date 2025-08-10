from rest_framework import serializers
from .models import Developer, Skill, Challenge, Submission


class ChallengeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Challenge
        fields = "__all__"

class SkillSerializer(serializers.ModelSerializer):
    challenge = ChallengeSerializer(required=False)
    class Meta:
        model = Skill
        fields = "__all__"

class DeveloperSerializer(serializers.ModelSerializer):
    skills = SkillSerializer(many=True, required=False)
    class Meta:
        model = Developer
        fields = "__all__"

class ChallengeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Challenge
        fields = "__all__"

class SubmissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Submission
        fields = "__all__"