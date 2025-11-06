from django.db import models
from django.conf import settings


class Swipe(models.Model):
    """Records a swipe action from one user to another."""

    swiper = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="swipes_given", on_delete=models.CASCADE)
    swiped = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="swipes_received", on_delete=models.CASCADE)
    liked = models.BooleanField()  # True for right swipe (like), False for left swipe (pass)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("swiper", "swiped")
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.swiper.username} swiped on {self.swiped.username}: {'Like' if self.liked else 'Pass'}"


class Match(models.Model):
    """Represents a mutual 'like' between two users."""

    user1 = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="matches1", on_delete=models.CASCADE)
    user2 = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="matches2", on_delete=models.CASCADE)
    # Flags to track if each user has been notified about the match
    user1_notified = models.BooleanField(default=False)
    user2_notified = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user1", "user2")
        verbose_name_plural = "Matches"

    def __str__(self):
        return f"Match between {self.user1.username} and {self.user2.username}"


class Message(models.Model):
    """Represents a single message within a match conversation."""
    match = models.ForeignKey(Match, related_name="messages", on_delete=models.CASCADE)
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ["timestamp"]

    def __str__(self):
        return f"Message from {self.sender.username} in match {self.match.id}"


class StudySession(models.Model):
    """Represents a study session created by a user."""
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="created_sessions", on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    location = models.CharField(max_length=255)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    participants = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="study_sessions", blank=True)
    google_calendar_event_id = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["start_time"]

    def __str__(self):
        return f"{self.title} - {self.start_time.strftime('%Y-%m-%d %H:%M')}"