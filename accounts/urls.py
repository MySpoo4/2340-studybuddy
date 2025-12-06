from django.urls import path
from . import views

app_name = "accounts"

urlpatterns = [
    path("signup/", views.signup, name="signup"),
    path("login/", views.login, name="login"),
    path("logout/", views.logout, name="logout"),
    path("profile/", views.profile, name="profile"),
    path("profile/edit/", views.edit_profile, name="edit_profile"),
    path("profile/<str:username>/", views.view_profile, name="view_profile"),
    # path("forms/<str:formset_name>/", views.manage_form_rows, name="manage_form_rows"),
    # path("manage-users/", views.manage_users, name="accounts.manage_users"),
]
