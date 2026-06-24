from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("upload/", views.upload_action, name="upload_action"),
    path("progress/", views.my_progress, name="my_progress"),
    path("friends/", views.friends, name="friends"),
    path("friends/accept/<int:friendship_id>/", views.accept_friend, name="accept_friend"),
    path("friends/remove/<int:friendship_id>/", views.remove_friend, name="remove_friend"),
    path("groups/", views.groups, name="groups"),
    path("leaderboard/", views.leaderboard, name="leaderboard"),
    path("profile/", views.profile, name="profile"),

    path("login/", auth_views.LoginView.as_view(template_name="pages/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("register/", views.register, name="register"),
]