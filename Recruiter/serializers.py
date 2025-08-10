from rest_framework import serializers
from Recruiter.models import Project, ProjectSkill, CandidateRecommendation, Invitation
from HireMe.serializers import DeveloperSerializer, ChallengeSerializer


class ProjectSkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectSkill
        fields = ("id", "name", "required_level")

    def validate(self, attrs):
        name = attrs.get('name', '').strip()
        required_level = attrs.get('required_level', 70)
        
        # Check if a ProjectSkill with the same name and level already exists
        if ProjectSkill.objects.filter(name=name, required_level=required_level).exists():
            # If it exists, we don't need to create a new one
            # The existing one will be used in the create/update methods
            pass
        
        return attrs


class ProjectSerializer(serializers.ModelSerializer):
    required_skills = ProjectSkillSerializer(many=True, required=False)

    class Meta:
        model = Project
        fields = "__all__"

    def create(self, validated_data):
        skills_data = validated_data.pop("required_skills", [])
        project = Project.objects.create(**validated_data)

        if skills_data:
            # Filter out duplicates based on name and level
            unique_skills = {}
            for s in skills_data:
                name = s["name"].strip()
                level = int(s.get("required_level", 70))
                key = (name, level)
                if key not in unique_skills:
                    unique_skills[key] = s
            
            skill_ids = []
            for (name, level), skill_data in unique_skills.items():
                skill_obj, _ = ProjectSkill.objects.get_or_create(
                    name=name,
                    required_level=level,
                )
                skill_ids.append(skill_obj.id)
            
            if skill_ids:
                project.required_skills.set(ProjectSkill.objects.filter(id__in=skill_ids))
        return project

    def update(self, instance, validated_data):
        skills_data = validated_data.pop("required_skills", None)
        for k, v in validated_data.items():
            setattr(instance, k, v)
        instance.save()

        if skills_data is not None:
            # Filter out duplicates based on name and level
            unique_skills = {}
            for s in skills_data:
                name = s["name"].strip()
                level = int(s.get("required_level", 70))
                key = (name, level)
                if key not in unique_skills:
                    unique_skills[key] = s
            
            skill_ids = []
            for (name, level), skill_data in unique_skills.items():
                skill_obj, _ = ProjectSkill.objects.get_or_create(
                    name=name,
                    required_level=level,
                )
                skill_ids.append(skill_obj.id)
            
            instance.required_skills.set(ProjectSkill.objects.filter(id__in=skill_ids))
        return instance


class CandidateRecommendationSerializer(serializers.ModelSerializer):
    developer = DeveloperSerializer()

    class Meta:
        model = CandidateRecommendation
        fields = "__all__"


class InvitationSerializer(serializers.ModelSerializer):
    developer = DeveloperSerializer(read_only=True)
    challenge = ChallengeSerializer(read_only=True)

    class Meta:
        model = Invitation
        fields = "__all__"
