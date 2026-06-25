from datetime import timedelta

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Sum, Count, Q, Value, IntegerField, Subquery, OuterRef, F, ExpressionWrapper
from django.db.models.functions import Coalesce
from django.utils import timezone
from django.http import JsonResponse
from .ai_utils import classify_eco_image

from .models import (
    EcoAction,
    Friendship,
    EcoGroup,
    GroupMember,
    UserProfile,
    GroupInvite,
    UserDailyMission,
    DailyMission,
    Badge,
    UserBadge,
    EcoActionLike,
    GroupWeeklyQuest,
)

from .forms import (
    EcoActionForm,
    EcoGroupForm,
    RegisterForm,
    AvatarForm,
)

from .utils import (
    get_level_info,
    complete_missions_for_action,
    get_today_mission_summary,
    get_user_total_points,
    update_user_streak,
    check_and_award_badges,
    get_or_create_weekly_quest,
    create_default_badges,
)



# =========================
# AUTH
# =========================

def register(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        form = RegisterForm(request.POST)

        if form.is_valid():
            user = form.save()
            UserProfile.objects.get_or_create(user=user)

            login(request, user)
            messages.success(
                request,
                "Account created successfully. Welcome to Eco Tracker!"
            )
            return redirect("dashboard")
        else:
            messages.error(request, "Please check your information and try again.")
    else:
        form = RegisterForm()

    return render(request, "pages/register.html", {"form": form})


# =========================
# DASHBOARD
# =========================

@login_required
def dashboard(request):
    actions = EcoAction.objects.filter(user=request.user).order_by("-created_at")
    recent_actions = actions[:5]

    total_points = get_user_total_points(request.user)
    action_count = actions.count()

    level_info = get_level_info(total_points)
    progress_percent = level_info["progress_percent"]
    impact_level = level_info["name"]

    today = timezone.localdate()
    seven_days_ago = timezone.now() - timedelta(days=6)

    today_actions = actions.filter(created_at__date=today)
    today_points = today_actions.aggregate(total=Sum("points"))["total"] or 0
    today_action_count = today_actions.count()

    weekly_actions = actions.filter(created_at__gte=seven_days_ago)
    weekly_points = weekly_actions.aggregate(total=Sum("points"))["total"] or 0
    weekly_action_count = weekly_actions.count()

    category_map = dict(EcoAction.CATEGORY_CHOICES)

    top_category_data = (
        actions
        .values("category")
        .annotate(total_points=Sum("points"), total_actions=Count("id"))
        .order_by("-total_points")
        .first()
    )

    if top_category_data:
        top_category_name = category_map.get(
            top_category_data["category"],
            top_category_data["category"]
        )
        top_category_points = top_category_data["total_points"] or 0
    else:
        top_category_name = "No category yet"
        top_category_points = 0

    category_breakdown = []

    raw_category_stats = (
        actions
        .values("category")
        .annotate(total_points=Sum("points"), total_actions=Count("id"))
        .order_by("-total_points")
    )

    for item in raw_category_stats:
        category_breakdown.append({
            "name": category_map.get(item["category"], item["category"]),
            "points": item["total_points"] or 0,
            "actions": item["total_actions"] or 0,
        })

    weekly_chart = []
    max_day_points = 1

    for i in range(6, -1, -1):
        day = today - timedelta(days=i)

        day_points = (
            actions
            .filter(created_at__date=day)
            .aggregate(total=Sum("points"))["total"] or 0
        )

        weekly_chart.append({
            "label": day.strftime("%a"),
            "date": day.strftime("%d/%m"),
            "points": day_points,
            "percent": 0,
        })

        if day_points > max_day_points:
            max_day_points = day_points

    for item in weekly_chart:
        item["percent"] = int((item["points"] / max_day_points) * 100)

    active_group = EcoGroup.objects.filter(members=request.user).first()

    mission_summary = get_today_mission_summary(request.user)
    context = {
        "page_title": "Dashboard",
        "page_subtitle": "Upload actions, earn points, and grow your eco impact",

        "total_points": total_points,
        "action_count": action_count,

        "today_points": today_points,
        "today_action_count": today_action_count,

        "weekly_points": weekly_points,
        "weekly_action_count": weekly_action_count,

        "top_category_name": top_category_name,
        "top_category_points": top_category_points,

        "progress_percent": progress_percent,
        "impact_level": impact_level,
        "level_info": level_info,

        "recent_actions": recent_actions,
        "active_group": active_group,

        "weekly_chart": weekly_chart,
        "category_breakdown": category_breakdown,

        "daily_missions": mission_summary["missions"],
        "missions_completed": mission_summary["completed"],
        "missions_total": mission_summary["total"],
        "mission_bonus_points": mission_summary["bonus_points"],
    }

    return render(request, "pages/dashboard.html", context)


# =========================
# ECO ACTIONS
# =========================

@login_required
def upload_action(request):
    if request.method == "POST":
        form = EcoActionForm(request.POST, request.FILES)

        if form.is_valid():
            eco_action = form.save(commit=False)
            eco_action.user = request.user
            
            # Run AI classification automatically
            ai_result = classify_eco_image(eco_action.image, eco_action.caption)
            
            if not ai_result["is_eco_action"]:
                messages.error(
                    request,
                    f"AI Analysis Rejected: This action does not appear to be eco-friendly. Reason: {ai_result['reason']}"
                )
                context = {
                    "page_title": "Upload Action",
                    "page_subtitle": "Upload your eco-friendly action and earn points",
                    "form": form,
                }
                return render(request, "pages/upload_action.html", context)
            
            # Automatically assign the category determined by AI
            eco_action.category = ai_result["category"]
            eco_action.save()

            # Update streak and apply points multiplier
            streak_count, multiplier = update_user_streak(request.user)
            if multiplier > 1.0:
                eco_action.points = int(eco_action.points * multiplier)
                eco_action.save()

            # Check and award badges
            new_badges = check_and_award_badges(request.user)

            completed_missions = complete_missions_for_action(
                request.user,
                eco_action
            )

            category_name = eco_action.get_category_display()
            msg = f"Action classified as {category_name}! +{eco_action.points} points awarded"
            
            if multiplier > 1.0:
                msg += f" (includes {multiplier}x multiplier for {streak_count}-day 🔥 streak!)"
            elif streak_count > 1:
                msg += f" (🔥 {streak_count}-day streak!)"
                
            if completed_missions:
                mission_titles = ", ".join(
                    mission.mission.title for mission in completed_missions
                )
                msg += f". Daily mission completed: {mission_titles}."
                
            if new_badges:
                badge_names = ", ".join(f"{b.icon} {b.name}" for b in new_badges)
                msg += f" 🏆 Achievements Unlocked: {badge_names}!"
                
            msg += f" AI Explanation: {ai_result['reason']}"
            messages.success(request, msg)

            return redirect("dashboard")
        else:
            messages.error(
                request,
                "Upload failed. Please check your image and information."
            )
    else:
        form = EcoActionForm()

    context = {
        "page_title": "Upload Action",
        "page_subtitle": "Upload your eco-friendly action and earn points",
        "form": form,
    }

    return render(request, "pages/upload_action.html", context)


@login_required
def edit_action(request, action_id):
    eco_action = get_object_or_404(
        EcoAction,
        id=action_id,
        user=request.user
    )

    if request.method == "POST":
        form = EcoActionForm(
            request.POST,
            request.FILES,
            instance=eco_action
        )

        if form.is_valid():
            updated_action = form.save(commit=False)
            
            # Automatically re-classify when editing
            ai_result = classify_eco_image(updated_action.image, updated_action.caption)
            
            if not ai_result["is_eco_action"]:
                messages.error(
                    request,
                    f"AI Analysis Rejected: The updated action does not appear to be eco-friendly. Reason: {ai_result['reason']}"
                )
                context = {
                    "page_title": "Edit Eco Action",
                    "page_subtitle": "Update your uploaded action",
                    "form": form,
                    "eco_action": eco_action,
                }
                return render(request, "pages/edit_action.html", context)
                
            updated_action.category = ai_result["category"]
            updated_action.save()

            messages.success(
                request,
                f"Eco action updated and re-classified as {updated_action.get_category_display()}! New score: +{updated_action.points} pts."
            )

            return redirect("my_progress")
        else:
            messages.error(request, "Update failed. Please check your information.")
    else:
        form = EcoActionForm(instance=eco_action)

    context = {
        "page_title": "Edit Eco Action",
        "page_subtitle": "Update your uploaded action",
        "form": form,
        "eco_action": eco_action,
    }

    return render(request, "pages/edit_action.html", context)


@login_required
def delete_action(request, action_id):
    eco_action = get_object_or_404(
        EcoAction,
        id=action_id,
        user=request.user
    )

    if request.method == "POST":
        action_name = eco_action.get_category_display()

        if eco_action.image:
            eco_action.image.delete(save=False)

        eco_action.delete()

        messages.success(request, f"{action_name} action deleted successfully.")
        return redirect("my_progress")

    context = {
        "page_title": "Delete Eco Action",
        "page_subtitle": "Confirm action deletion",
        "eco_action": eco_action,
    }

    return render(request, "pages/delete_action.html", context)


# =========================
# MY PROGRESS
# =========================

@login_required
def my_progress(request):
    actions = EcoAction.objects.filter(user=request.user).order_by("-created_at")

    total_points = get_user_total_points(request.user)
    action_count = actions.count()

    level_info = get_level_info(total_points)
    progress_percent = level_info["progress_percent"]
    impact_level = level_info["name"]

    category_stats = (
        actions
        .values("category")
        .annotate(total=Sum("points"))
        .order_by("-total")
    )

    context = {
        "page_title": "My Progress",
        "page_subtitle": "See how your actions affect your eco level",

        "total_points": total_points,
        "action_count": action_count,

        "progress_percent": progress_percent,
        "impact_level": impact_level,
        "level_info": level_info,

        "category_stats": category_stats,
        "actions": actions,
    }

    return render(request, "pages/my_progress.html", context)


# =========================
# FRIENDS
# =========================

@login_required
def friends(request):
    user_total_points = get_user_total_points(request.user)

    if request.method == "POST":
        username = request.POST.get("username", "").strip()

        if not username:
            messages.error(request, "Please enter a username.")
            return redirect("friends")

        target_user = (
            User.objects
            .filter(username=username)
            .exclude(id=request.user.id)
            .first()
        )

        if not target_user:
            messages.error(request, "User not found or you cannot add yourself.")
            return redirect("friends")

        existing = Friendship.objects.filter(
            Q(sender=request.user, receiver=target_user) |
            Q(sender=target_user, receiver=request.user)
        ).first()

        if existing:
            if existing.status == "pending":
                messages.warning(request, "A friend request already exists.")
            else:
                messages.warning(request, "You are already friends with this user.")

            return redirect("friends")

        Friendship.objects.create(
            sender=request.user,
            receiver=target_user,
            status="pending"
        )

        messages.success(request, f"Friend request sent to {target_user.username}.")
        return redirect("friends")

    received_requests = Friendship.objects.filter(
        receiver=request.user,
        status="pending"
    ).select_related("sender")

    sent_requests = Friendship.objects.filter(
        sender=request.user,
        status="pending"
    ).select_related("receiver")

    accepted_friendships = Friendship.objects.filter(
        Q(sender=request.user) | Q(receiver=request.user),
        status="accepted"
    ).select_related("sender", "receiver")

    friends_data = []

    for friendship in accepted_friendships:
        if friendship.sender == request.user:
            friend = friendship.receiver
        else:
            friend = friendship.sender

        friend_total_points = get_user_total_points(friend)

        difference = user_total_points - friend_total_points

        max_points = max(user_total_points, friend_total_points, 1)
        user_percent = int((user_total_points / max_points) * 100)
        friend_percent = int((friend_total_points / max_points) * 100)

        friends_data.append({
            "friendship": friendship,
            "friend": friend,
            "friend_total_points": friend_total_points,
            "difference": difference,
            "user_percent": user_percent,
            "friend_percent": friend_percent,
        })

    context = {
        "page_title": "Friends",
        "page_subtitle": "Add friends and compare your eco progress",

        "received_requests": received_requests,
        "sent_requests": sent_requests,
        "friends_data": friends_data,
        "user_total_points": user_total_points,
    }

    return render(request, "pages/friends.html", context)


@login_required
def accept_friend(request, friendship_id):
    friendship = get_object_or_404(
        Friendship,
        id=friendship_id,
        receiver=request.user,
        status="pending"
    )

    friendship.status = "accepted"
    friendship.save()

    messages.success(
        request,
        f"You are now friends with {friendship.sender.username}."
    )

    return redirect("friends")


@login_required
def reject_friend(request, friendship_id):
    friendship = get_object_or_404(
        Friendship,
        id=friendship_id,
        receiver=request.user,
        status="pending"
    )

    sender_name = friendship.sender.username
    friendship.delete()

    messages.success(request, f"Friend request from {sender_name} rejected.")
    return redirect("friends")


@login_required
def cancel_friend_request(request, friendship_id):
    friendship = get_object_or_404(
        Friendship,
        id=friendship_id,
        sender=request.user,
        status="pending"
    )

    receiver_name = friendship.receiver.username
    friendship.delete()

    messages.success(request, f"Friend request to {receiver_name} cancelled.")
    return redirect("friends")


@login_required
def remove_friend(request, friendship_id):
    friendship = get_object_or_404(
        Friendship,
        Q(sender=request.user) | Q(receiver=request.user),
        id=friendship_id,
        status="accepted"
    )

    if friendship.sender == request.user:
        friend_name = friendship.receiver.username
    else:
        friend_name = friendship.sender.username

    friendship.delete()

    messages.success(request, f"{friend_name} has been removed from your friends.")
    return redirect("friends")


# =========================
# GROUPS + INVITES
# =========================

@login_required
def groups(request):
    if request.method == "POST":
        form = EcoGroupForm(request.POST)

        if form.is_valid():
            group = form.save(commit=False)
            group.owner = request.user
            group.save()

            GroupMember.objects.create(
                group=group,
                user=request.user
            )

            messages.success(request, f"Group '{group.name}' created successfully.")
            return redirect("group_detail", group_id=group.id)
        else:
            messages.error(request, "Could not create group. Please try again.")
            return redirect("groups")

    form = EcoGroupForm()

    user_groups = (
        EcoGroup.objects
        .filter(members=request.user)
        .distinct()
        .order_by("-created_at")
    )

    received_invites = (
        GroupInvite.objects
        .filter(receiver=request.user, status="pending")
        .select_related("group", "sender")
        .order_by("-created_at")
    )

    context = {
        "page_title": "Groups",
        "page_subtitle": "Create eco groups and respond to group invites",

        "form": form,
        "user_groups": user_groups,
        "received_invites": received_invites,
    }

    return render(request, "pages/groups.html", context)


@login_required
def group_detail(request, group_id):
    group = get_object_or_404(
        EcoGroup,
        id=group_id,
        members=request.user
    )

    members = list(group.members.all())
    for member in members:
        member.total_points = get_user_total_points(member)
    members.sort(key=lambda x: (-x.total_points, x.username))

    group_total_points = sum(member.total_points for member in members)
    target_points = 2000
    target_percent = min(100, int((group_total_points / target_points) * 100))

    # Retrieve or generate the Group Weekly Quest
    quest, quest_count, quest_percent = get_or_create_weekly_quest(group)

    pending_invites = (
        GroupInvite.objects
        .filter(group=group, status="pending")
        .select_related("receiver", "sender")
        .order_by("-created_at")
    )

    context = {
        "page_title": group.name,
        "page_subtitle": "Group challenge and leaderboard",

        "group": group,
        "members": members,
        "group_total_points": group_total_points,
        "pending_invites": pending_invites,
        "target_points": target_points,
        "target_percent": target_percent,
        "quest": quest,
        "quest_count": quest_count,
        "quest_percent": quest_percent,
    }

    return render(request, "pages/group_detail.html", context)


@login_required
def send_group_invite(request, group_id):
    group = get_object_or_404(EcoGroup, id=group_id, owner=request.user)

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        target_user = User.objects.filter(username=username).first()

        if not target_user:
            messages.error(request, "User not found.")
            return redirect("group_detail", group_id=group.id)

        if target_user == request.user:
            messages.error(request, "You cannot invite yourself.")
            return redirect("group_detail", group_id=group.id)

        if group.members.filter(id=target_user.id).exists():
            messages.warning(request, "This user is already in the group.")
            return redirect("group_detail", group_id=group.id)

        if group.member_count() >= 5:
            messages.error(request, "This group already has the maximum of 5 members.")
            return redirect("group_detail", group_id=group.id)

        existing_invite = GroupInvite.objects.filter(
            group=group,
            receiver=target_user,
            status="pending"
        ).first()

        if existing_invite:
            messages.warning(request, "This user already has a pending invite.")
            return redirect("group_detail", group_id=group.id)

        GroupInvite.objects.create(
            group=group,
            sender=request.user,
            receiver=target_user
        )

        messages.success(request, f"Invite sent to {target_user.username}.")

    return redirect("group_detail", group_id=group.id)


@login_required
def accept_group_invite(request, invite_id):
    invite = get_object_or_404(
        GroupInvite,
        id=invite_id,
        receiver=request.user,
        status="pending"
    )

    group = invite.group

    if group.member_count() >= 5:
        messages.error(request, "This group is already full.")
        return redirect("groups")

    GroupMember.objects.get_or_create(
        group=group,
        user=request.user
    )

    invite.status = "accepted"
    invite.save()

    messages.success(request, f"You joined '{group.name}'.")
    return redirect("group_detail", group_id=group.id)


@login_required
def reject_group_invite(request, invite_id):
    invite = get_object_or_404(
        GroupInvite,
        id=invite_id,
        receiver=request.user,
        status="pending"
    )

    group_name = invite.group.name

    invite.status = "rejected"
    invite.save()

    messages.success(request, f"You rejected the invite to '{group_name}'.")
    return redirect("groups")


@login_required
def remove_group_member(request, group_id, user_id):
    group = get_object_or_404(EcoGroup, id=group_id, owner=request.user)

    member = get_object_or_404(
        GroupMember,
        group=group,
        user_id=user_id
    )

    if member.user == group.owner:
        messages.error(request, "You cannot remove the group owner.")
        return redirect("group_detail", group_id=group.id)

    removed_username = member.user.username
    member.delete()

    messages.success(request, f"{removed_username} has been removed from the group.")
    return redirect("group_detail", group_id=group.id)


@login_required
def leave_group(request, group_id):
    group = get_object_or_404(EcoGroup, id=group_id, members=request.user)

    if group.owner == request.user:
        messages.error(request, "Group owner cannot leave. Delete the group instead.")
        return redirect("group_detail", group_id=group.id)

    GroupMember.objects.filter(
        group=group,
        user=request.user
    ).delete()

    messages.success(request, f"You left '{group.name}'.")
    return redirect("groups")


@login_required
def delete_group(request, group_id):
    group = get_object_or_404(EcoGroup, id=group_id, owner=request.user)

    group_name = group.name
    group.delete()

    messages.success(request, f"Group '{group_name}' has been deleted.")
    return redirect("groups")


# =========================
# LEADERBOARD
# =========================

@login_required
def leaderboard(request):
    actions_subquery = EcoAction.objects.filter(user=OuterRef("pk")).values("user").annotate(total=Sum("points")).values("total")
    missions_subquery = UserDailyMission.objects.filter(user=OuterRef("pk"), is_completed=True).values("user").annotate(total=Sum("mission__bonus_points")).values("total")

    users = (
        User.objects
        .annotate(
            action_points=Coalesce(Subquery(actions_subquery), Value(0)),
            bonus_points=Coalesce(Subquery(missions_subquery), Value(0)),
            total_actions=Count("eco_actions", distinct=True)
        )
        .annotate(
            total_points=ExpressionWrapper(
                F("action_points") + F("bonus_points"),
                output_field=IntegerField()
            )
        )
        .order_by("-total_points", "-total_actions", "username")
    )

    leaderboard_users = []

    user_rank = None
    user_total_points = 0
    user_total_actions = 0

    for index, ranked_user in enumerate(users, start=1):
        UserProfile.objects.get_or_create(user=ranked_user)

        level_info = get_level_info(ranked_user.total_points)

        item = {
            "rank": index,
            "user": ranked_user,
            "total_points": ranked_user.total_points,
            "total_actions": ranked_user.total_actions,
            "level_info": level_info,
        }

        leaderboard_users.append(item)

        if ranked_user == request.user:
            user_rank = index
            user_total_points = ranked_user.total_points
            user_total_actions = ranked_user.total_actions

    context = {
        "page_title": "Leaderboard",
        "page_subtitle": "See who has the strongest eco impact",

        "leaderboard_users": leaderboard_users,
        "user_rank": user_rank,
        "user_total_points": user_total_points,
        "user_total_actions": user_total_actions,
    }

    return render(request, "pages/leaderboard.html", context)


# =========================
# PROFILE + AVATAR
# =========================

@login_required
def profile(request):
    profile_obj, created = UserProfile.objects.get_or_create(user=request.user)

    actions = EcoAction.objects.filter(user=request.user).order_by("-created_at")

    total_points = get_user_total_points(request.user)
    action_count = actions.count()

    level_info = get_level_info(total_points)
    progress_percent = level_info["progress_percent"]
    impact_level = level_info["name"]

    category_map = dict(EcoAction.CATEGORY_CHOICES)

    top_category_data = (
        actions
        .values("category")
        .annotate(total_actions=Count("id"), total_points=Sum("points"))
        .order_by("-total_actions", "-total_points")
        .first()
    )

    if top_category_data:
        most_common_category = category_map.get(
            top_category_data["category"],
            top_category_data["category"]
        )
        most_common_category_count = top_category_data["total_actions"]
    else:
        most_common_category = "No category yet"
        most_common_category_count = 0

    recent_actions = actions[:4]

    # Fetch Earned and Locked Badges
    create_default_badges()  # Ensure badges exist
    earned_badges = UserBadge.objects.filter(user=request.user).select_related("badge")
    earned_badge_ids = set(earned_badges.values_list("badge_id", flat=True))
    all_badges = Badge.objects.all()

    badges_list = []
    for b in all_badges:
        badges_list.append({
            "badge": b,
            "is_earned": b.id in earned_badge_ids,
            "earned_at": earned_badges.filter(badge=b).first().earned_at if b.id in earned_badge_ids else None
        })

    # Green Habit Analytics
    category_stats = (
        actions
        .values("category")
        .annotate(count=Count("id"))
        .order_by("-count")
    )
    
    habit_analytics = []
    colors = ["#4e8054", "#10b981", "#2e623c", "#f59e0b", "#3b82f6", "#8b5cf6"]
    
    cumulative_percent = 0
    for index, item in enumerate(category_stats):
        pct = int((item["count"] / action_count) * 100) if action_count > 0 else 0
        color = colors[index % len(colors)]
        habit_analytics.append({
            "name": category_map.get(item["category"], item["category"]),
            "count": item["count"],
            "percent": pct,
            "color": color,
            "start_percent": cumulative_percent,
            "end_percent": cumulative_percent + pct
        })
        cumulative_percent += pct

    context = {
        "page_title": "Profile",
        "page_subtitle": "Your personal eco profile and achievements",

        "total_points": total_points,
        "action_count": action_count,

        "progress_percent": progress_percent,
        "impact_level": impact_level,
        "level_info": level_info,

        "most_common_category": most_common_category,
        "most_common_category_count": most_common_category_count,

        "recent_actions": recent_actions,
        "profile": profile_obj,
        "badges": badges_list,
        "habit_analytics": habit_analytics,
    }

    return render(request, "pages/profile.html", context)


@login_required
def update_avatar(request):
    profile_obj, created = UserProfile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        form = AvatarForm(request.POST, request.FILES, instance=profile_obj)

        if form.is_valid():
            form.save()
            messages.success(request, "Avatar updated successfully.")
        else:
            messages.error(request, "Could not update avatar. Please check the file.")

    return redirect("profile")

@login_required
def ai_classify_action(request):
    if request.method != "POST":
        return JsonResponse(
            {"success": False, "error": "Invalid request method."},
            status=405
        )

    image = request.FILES.get("image")
    caption = request.POST.get("caption", "")

    if not image:
        return JsonResponse(
            {"success": False, "error": "No image uploaded."},
            status=400
        )

    try:
        result = classify_eco_image(image, caption=caption)

        return JsonResponse({
            "success": True,
            "category": result["category"],
            "confidence": result["confidence"],
            "reason": result["reason"],
            "is_eco_action": result["is_eco_action"],
        })

    except Exception as error:
        return JsonResponse({
            "success": False,
            "error": str(error),
        }, status=500)


@login_required
def eco_feed(request):
    # Find user's friends (accepted friendships)
    friendships = Friendship.objects.filter(
        Q(sender=request.user) | Q(receiver=request.user),
        status="accepted"
    )
    friend_ids = []
    for f in friendships:
        if f.sender == request.user:
            friend_ids.append(f.receiver.id)
        else:
            friend_ids.append(f.sender.id)
            
    # Find user's group members
    group_member_ids = []
    user_groups = EcoGroup.objects.filter(members=request.user)
    for g in user_groups:
        group_member_ids.extend(g.members.values_list("id", flat=True))
        
    # Combine all visible user IDs: user, friends, group members
    visible_user_ids = list(set([request.user.id] + friend_ids + group_member_ids))
    
    # Fetch recent actions, annotated with likes counts and whether current user liked it
    from django.db.models import Exists, OuterRef
    
    actions = (
        EcoAction.objects
        .filter(user_id__in=visible_user_ids)
        .select_related("user", "user__profile")
        .annotate(
            likes_count=Count("likes", distinct=True),
            liked_by_user=Exists(EcoActionLike.objects.filter(action=OuterRef("pk"), user=request.user))
        )
        .order_by("-created_at")
    )
    
    context = {
        "page_title": "Eco Feed",
        "page_subtitle": "See the environmental impact of your community",
        "actions": actions[:30],
    }
    return render(request, "pages/eco_feed.html", context)


@login_required
def like_action(request, action_id):
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "Invalid method."}, status=405)
        
    action = get_object_or_404(EcoAction, id=action_id)
    like, created = EcoActionLike.objects.get_or_create(user=request.user, action=action)
    
    if not created:
        # Already liked, unlike it
        like.delete()
        liked = False
    else:
        liked = True
        
    likes_count = action.likes.count()
    return JsonResponse({
        "success": True,
        "liked": liked,
        "likes_count": likes_count
    })