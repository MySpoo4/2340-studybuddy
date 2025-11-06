from django.contrib import admin
from .models import Swipe, Match, Message


@admin.register(Swipe)
class SwipeAdmin(admin.ModelAdmin):
    """Admin configuration for the Swipe model."""
    list_display = ('swiper', 'swiped', 'liked', 'timestamp')
    list_filter = ('liked',)
    search_fields = ('swiper__username', 'swiped__username')
    date_hierarchy = 'timestamp'


@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    """Admin configuration for the Match model."""
    list_display = ('user1', 'user2', 'timestamp')
    search_fields = ('user1__username', 'user2__username')
    date_hierarchy = 'timestamp'


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    """Admin configuration for the Message model."""
    list_display = ('sender', 'match', 'content_preview', 'timestamp')
    list_filter = ('match',)
    search_fields = ('sender__username', 'content')
    date_hierarchy = 'timestamp'

    def content_preview(self, obj):
        return obj.content[:50]