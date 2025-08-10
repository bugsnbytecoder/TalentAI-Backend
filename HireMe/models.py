from django.db import models

class Challenge(models.Model):
    CHALLENGE_TYPES = [
        ("coding","coding"), ("system_design","system_design"),
        ("algorithm","algorithm"), ("debugging","debugging"), ("architecture","architecture")
    ]
    title = models.CharField(max_length=160)
    description = models.TextField()
    difficulty = models.CharField(max_length=32)
    time_limit = models.IntegerField()
    challenge_type = models.CharField(max_length=32, choices=CHALLENGE_TYPES)
    challenge_question = models.TextField()
    max_score = models.IntegerField(default=100)
    def __str__(self):
        return self.title

class Skill(models.Model):
    name = models.CharField(max_length=64)
    level = models.IntegerField(default=50)
    validated = models.BooleanField(default=False)
    challenge = models.ForeignKey(Challenge, related_name="skills", on_delete=models.CASCADE, null=True, blank=True)
    def __str__(self):
        return self.name

class Developer(models.Model):
    full_name = models.CharField(max_length=120)
    email = models.EmailField(unique=True)
    bio = models.TextField(blank=True)
    location = models.CharField(max_length=120, blank=True)
    experience_level = models.CharField(max_length=32, choices=[
        ("junior","Junior"), ("mid","Mid"), ("senior","Senior"),
        ("lead","Tech Lead"), ("principal","Principal")
    ], default="junior")
    availability = models.CharField(max_length=32, choices=[
        ("available","Available"), ("open_to_offers","Open to Offers"), ("not_available","Not Available")
    ], default="available")
    resume = models.TextField(null=True, blank=True)
    dev_score = models.IntegerField(default=0)
    validation_status = models.CharField(max_length=32, default="not_validated")
    portfolio_links = models.JSONField(null=True, blank=True)
    skills = models.ManyToManyField(Skill, related_name="developers", blank=True)
    def __str__(self):
        return self.full_name

class Submission(models.Model):
    STATUS = [("pending","pending"),("evaluating","evaluating"),("completed","completed")]
    developer = models.ForeignKey(Developer, on_delete=models.CASCADE)
    challenge = models.ForeignKey(Challenge, on_delete=models.CASCADE)
    bug_analysis = models.TextField()
    answer = models.TextField()
    score = models.IntegerField(null=True, blank=True)
    accuracy_rate = models.FloatField(null=True, blank=True)
    bugs_found = models.IntegerField(null=True, blank=True)
    bugs_missed = models.IntegerField(null=True, blank=True)
    false_positives = models.IntegerField(null=True, blank=True)
    status = models.CharField(max_length=16, choices=STATUS, default="pending")
    ai_feedback = models.TextField(blank=True, default="")
    evaluation_details = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return self.developer.full_name