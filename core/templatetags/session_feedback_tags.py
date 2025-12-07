from django import template

register = template.Library()

@register.filter
def get_feedback(feedbacks, user):
    return feedbacks.filter(user=user).first()

@register.filter
def is_participant(participants, user):
    return participants.filter(id=user.id).exists()
