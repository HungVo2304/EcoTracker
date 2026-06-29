from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("upload/", views.upload_action, name="upload_action"),
    path("ai/classify-action/", views.ai_classify_action, name="ai_classify_action"),
    path("feed/", views.eco_feed, name="eco_feed"),
    path("missions/", views.missions, name="missions"),
    path("actions/<int:action_id>/react/", views.react_action, name="react_action"),
    path("progress/", views.my_progress, name="my_progress"),
    
    path("friends/", views.friends, name="friends"),
    path("friends/accept/<int:friendship_id>/", views.accept_friend, name="accept_friend"),
    path("friends/reject/<int:friendship_id>/", views.reject_friend, name="reject_friend"),
    path("friends/cancel/<int:friendship_id>/", views.cancel_friend_request, name="cancel_friend_request"),
    path("friends/remove/<int:friendship_id>/", views.remove_friend, name="remove_friend"),
    
    path("groups/", views.groups, name="groups"),
    path("groups/<int:group_id>/", views.group_detail, name="group_detail"),
    path("groups/<int:group_id>/invite/", views.send_group_invite, name="send_group_invite"),
    path("groups/invites/<int:invite_id>/accept/", views.accept_group_invite, name="accept_group_invite"),
    path("groups/invites/<int:invite_id>/reject/", views.reject_group_invite, name="reject_group_invite"),
    path("groups/<int:group_id>/remove/<int:user_id>/", views.remove_group_member, name="remove_group_member"),
    path("groups/<int:group_id>/leave/", views.leave_group, name="leave_group"),
    path("groups/<int:group_id>/delete/", views.delete_group, name="delete_group"),

    path("leaderboard/", views.leaderboard, name="leaderboard"),
    path("profile/", views.profile, name="profile"),
    path("shop/", views.frame_shop, name="frame_shop"),
    path("trivia/submit/", views.submit_trivia, name="submit_trivia"),

    path("login/", auth_views.LoginView.as_view(template_name="pages/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("register/", views.register, name="register"),
    
    path("actions/<int:action_id>/edit/", views.edit_action, name="edit_action"),
    path("actions/<int:action_id>/delete/", views.delete_action, name="delete_action"),
    path("profile/avatar/", views.update_avatar, name="update_avatar"),
]