from django.urls import path
from . import views

app_name = "core"

urlpatterns = [
    path("swipe/", views.swipe_view, name="swipe"),
    path("api/swipe/", views.swipe_action_view, name="swipe_action"),
    path("matches/", views.matches_view, name="matches"),
    path("api/check-matches/", views.check_new_matches_view, name="check_new_matches"),
    path("likes-you/", views.likes_you_view, name="likes_you"),
    path("messages/", views.inbox_view, name="inbox"),
    path("messages/<int:match_id>/", views.chat_room_view, name="chat_room"),
    path("api/messages/<int:match_id>/", views.fetch_messages_view, name="fetch_messages"),
    path("api/messages/<int:match_id>/send/", views.send_message_view, name="send_message"),
]