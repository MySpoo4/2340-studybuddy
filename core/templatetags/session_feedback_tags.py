from django import template
from django.db.models import Avg

register = template.Library()

@register.filter
def get_feedback(feedbacks, user):
    return feedbacks.filter(user=user).first()

@register.filter
def is_participant(participants, user):
    return participants.filter(id=user.id).exists()

@register.filter
def get_average_rating(feedbacks):
    """
    Calculates the average rating from a queryset of feedback objects.
    """
    average = feedbacks.aggregate(Avg('rating'))['rating__avg']
    return average or 0.0

@register.filter
def get_comments(feedbacks):
    """
    Returns a list of non-empty feedback comments from a queryset of feedback objects.
    """
    return list(feedbacks.exclude(feedback__exact='').values_list('feedback', flat=True))
