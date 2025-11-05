from django.urls import path
from . import views

urlpatterns = [
    path("swipe/", views.swipe, name="core.swipe"),
]