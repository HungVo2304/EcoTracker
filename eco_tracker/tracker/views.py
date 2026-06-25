from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Sum, Q, Value, IntegerField, Count
from datetime import timedelta
from django.contrib.auth import login
from django.utils import timezone
from django.db.models.functions import Coalesce
from .models import EcoAction, Friendship, EcoGroup, GroupMember, UserProfile
from .forms import EcoActionForm, EcoGroupForm, RegisterForm, AvatarForm
from .utils import get_level_info


def register(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        form = RegisterForm(request.POST)

        if form.is_valid():
            user = form.save()
            UserProfile.objects.get_or_create(user=user)
            login(request, user)
            messages.success(request, "Account created successfully. Welcome to Eco Tracker!")
            return redirect("dashboard")
        else:
            messages.error(request, "Please check your information and try again.")
    else:
        form = RegisterForm()

    return render(request, "pages/register.html", {"form": form})

def calculate_progress(total_points):
    progress = min(int((total_points / 500) * 100), 100)

    if progress < 25:
        level = "Eco Beginner"
    elif progress < 50:
        level = "Green Starter"
    elif progress < 75:
        level = "Eco Warrior"
    else:
        level = "Planet Protector"

    return progress, level


@login_required
def dashboard(request):
    actions = EcoAction.objects.filter(user=request.user).order_by("-created_at")
    recent_actions = actions[:5]

    total_points = actions.aggregate(total=Sum("points"))["total"] or 0
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
        item["percent"] = int((item["points"] / max_day_points) * 100) if max_day_points else 0

    active_group = EcoGroup.objects.filter(members=request.user).first()

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
    }

    return render(request, "pages/dashboard.html", context)


@login_required
def upload_action(request):
    if request.method == "POST":
        form = EcoActionForm(request.POST, request.FILES)

        if form.is_valid():
            eco_action = form.save(commit=False)
            eco_action.user = request.user
            eco_action.save()

            messages.success(
                request,
                f"Eco action uploaded successfully! +{eco_action.points} points added."
            )

            return redirect("dashboard")
        else:
            messages.error(request, "Upload failed. Please check your image and information.")
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
            updated_action = form.save()

            messages.success(
                request,
                f"Eco action updated successfully. New score: +{updated_action.points} pts."
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



@login_required
def my_progress(request):
    actions = EcoAction.objects.filter(user=request.user).order_by("-created_at")

    total_points = actions.aggregate(total=Sum("points"))["total"] or 0
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
        "category_stats": category_stats,
        "actions": actions,
        "level_info": level_info,
    }

    return render(request, "pages/my_progress.html", context)


@login_required
def friends(request):
    user_total_points = (
        EcoAction.objects
        .filter(user=request.user)
        .aggregate(total=Sum("points"))["total"] or 0
    )

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

        friend_total_points = (
            EcoAction.objects
            .filter(user=friend)
            .aggregate(total=Sum("points"))["total"] or 0
        )

        difference = user_total_points - friend_total_points

        friends_data.append({
            "friendship": friendship,
            "friend": friend,
            "friend_total_points": friend_total_points,
            "difference": difference,
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

    messages.success(request, f"You are now friends with {friendship.sender.username}.")
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

    return redirect("friends")


@login_required
def remove_friend(request, friendship_id):
    friendship = get_object_or_404(
        Friendship,
        Q(sender=request.user) | Q(receiver=request.user),
        id=friendship_id
    )

    friendship.delete()

    return redirect("friends")


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

    context = {
        "page_title": "Groups",
        "page_subtitle": "Create eco groups and compete with friends",
        "form": form,
        "user_groups": user_groups,
    }

    return render(request, "pages/groups.html", context)


@login_required
def group_detail(request, group_id):
    group = get_object_or_404(
        EcoGroup,
        id=group_id,
        members=request.user
    )

    members = (
        group.members
        .annotate(
            total_points=Coalesce(
                Sum("eco_actions__points"),
                Value(0),
                output_field=IntegerField()
            )
        )
        .order_by("-total_points", "username")
    )

    group_total_points = (
        EcoAction.objects
        .filter(user__in=group.members.all())
        .aggregate(total=Sum("points"))["total"] or 0
    )

    context = {
        "page_title": group.name,
        "page_subtitle": "Group challenge and leaderboard",
        "group": group,
        "members": members,
        "group_total_points": group_total_points,
    }

    return render(request, "pages/group_detail.html", context)


@login_required
def add_group_member(request, group_id):
    group = get_object_or_404(EcoGroup, id=group_id)

    if group.owner != request.user:
        messages.error(request, "Only the group owner can add members.")
        return redirect("group_detail", group_id=group.id)

    if request.method == "POST":
        username = request.POST.get("username", "").strip()

        target_user = User.objects.filter(username=username).first()

        if not target_user:
            messages.error(request, "User not found.")
            return redirect("group_detail", group_id=group.id)

        if group.members.filter(id=target_user.id).exists():
            messages.warning(request, "This user is already in the group.")
            return redirect("group_detail", group_id=group.id)

        if group.member_count() >= 5:
            messages.error(request, "This group already has the maximum of 5 members.")
            return redirect("group_detail", group_id=group.id)

        GroupMember.objects.create(
            group=group,
            user=target_user
        )

        messages.success(request, f"{target_user.username} has been added to the group.")

    return redirect("group_detail", group_id=group.id)


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


@login_required
def leaderboard(request):
    users = (
        User.objects
        .annotate(total_points=Sum("eco_actions__points"))
        .order_by("-total_points")
    )

    context = {
        "page_title": "Leaderboard",
        "page_subtitle": "See who has the highest eco impact",
        "users": users,
    }

    return render(request, "pages/leaderboard.html", context)


@login_required
def profile(request):
    UserProfile.objects.get_or_create(user=request.user)

    actions = EcoAction.objects.filter(user=request.user).order_by("-created_at")

    total_points = actions.aggregate(total=Sum("points"))["total"] or 0
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
    }

    return render(request, "pages/profile.html", context)

@login_required
def update_avatar(request):
    profile, created = UserProfile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        form = AvatarForm(request.POST, request.FILES, instance=profile)

        if form.is_valid():
            form.save()
            messages.success(request, "Avatar updated successfully.")
        else:
            messages.error(request, "Could not update avatar. Please check the file.")

    return redirect("profile")