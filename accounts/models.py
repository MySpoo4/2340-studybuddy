from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

# Create your models here.
class Course(models.Model):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.code} - {self.name}"

class StudyPreference(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    university = models.CharField(max_length=255, blank=True)
    major = models.CharField(max_length=255, blank=True)
    year_of_study = models.IntegerField(null=True, blank=True)
    bio = models.TextField(blank=True)
    courses = models.ManyToManyField(Course, blank=True)
    study_preferences = models.ManyToManyField(StudyPreference, blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    search_radius = models.IntegerField(default=5)
    # Google Calendar OAuth credentials
    google_calendar_refresh_token = models.TextField(blank=True, null=True)
    google_calendar_access_token = models.TextField(blank=True, null=True)
    google_calendar_token_expiry = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"{self.user.username}'s Profile"

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()
