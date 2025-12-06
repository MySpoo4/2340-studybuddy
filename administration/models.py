from django.db import models
from django.contrib.auth.models import User

# Create your models here.
class Report(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('reviewed', 'Reviewed'),
        ('action_taken', 'Action Taken'),
    ]

    reporter = models.ForeignKey(User, related_name='submitted_reports', on_delete=models.CASCADE)
    reported_user = models.ForeignKey(User, related_name='received_reports', on_delete=models.CASCADE)
    reason = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    admin_notes = models.TextField(blank=True, help_text="Notes for other admins regarding this report.")

    def __str__(self):
        return f"Report by {self.reporter.username} against {self.reported_user.username}"

    class Meta:
        ordering = ['-timestamp']
