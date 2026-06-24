from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Sum, Q
from django.contrib.auth import login
from .forms import RegisterForm
from .models import EcoAction, Friendship, EcoGroup, GroupMember
from .forms import EcoActionForm, EcoGroupForm
from django.contrib import messages


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
    progress_percent, impact_level = calculate_progress(total_points)

    active_group = EcoGroup.objects.filter(members=request.user).first()

    context = {
        "page_title": "Dashboard",
        "page_subtitle": "Upload actions, earn points, and grow your eco impact",
        "total_points": total_points,
        "action_count": action_count,
        "progress_percent": progress_percent,
        "impact_level": impact_level,
        "recent_actions": recent_actions,
        "active_group": active_group,
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
            return redirect("dashboard")
    else:
        form = EcoActionForm()

    context = {
        "page_title": "Upload Action",
        "page_subtitle": "Upload your eco-friendly action and earn points",
        "form": form,
    }

    return render(request, "pages/upload_action.html", context)


@login_required
def my_progress(request):
    actions = EcoAction.objects.filter(user=request.user).order_by("-created_at")

    total_points = actions.aggregate(total=Sum("points"))["total"] or 0
    action_count = actions.count()
    progress_percent, impact_level = calculate_progress(total_points)

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
    }

    return render(request, "pages/my_progress.html", context)


@login_required
def friends(request):
    if request.method == "POST":
        username = request.POST.get("username")

        target_user = (
            User.objects
            .filter(username=username)
            .exclude(id=request.user.id)
            .first()
        )

        if target_user:
            existing = Friendship.objects.filter(
                Q(sender=request.user, receiver=target_user) |
                Q(sender=target_user, receiver=request.user)
            ).first()

            if not existing:
                Friendship.objects.create(
                    sender=request.user,
                    receiver=target_user
                )
                messages.success(request, f"Friend request sent to {target_user.username}.")
            else:
                messages.warning(request, "You already sent a request or are already friends with this user.")
        else:
            messages.error(request, "User not found.")

        return redirect("friends")

    friend_requests = Friendship.objects.filter(
        receiver=request.user,
        status="pending"
    )

    accepted_friendships = Friendship.objects.filter(
        Q(sender=request.user) | Q(receiver=request.user),
        status="accepted"
    )

    context = {
        "page_title": "Friends",
        "page_subtitle": "Add friends and compare your eco progress",
        "friend_requests": friend_requests,
        "accepted_friendships": accepted_friendships,
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
        action = request.POST.get("action")

        if action == "create_group":
            form = EcoGroupForm(request.POST)

            if form.is_valid():
                group = form.save(commit=False)
                group.owner = request.user
                group.save()

                GroupMember.objects.create(
                    group=group,
                    user=request.user
                )

        elif action == "add_member":
            group_id = request.POST.get("group_id")
            username = request.POST.get("username")

            group = get_object_or_404(EcoGroup, id=group_id, owner=request.user)
            target_user = User.objects.filter(username=username).first()

            if target_user and group.can_add_member():
                GroupMember.objects.get_or_create(
                    group=group,
                    user=target_user
                )

        return redirect("groups")

    form = EcoGroupForm()
    user_groups = EcoGroup.objects.filter(members=request.user)

    context = {
        "page_title": "Groups",
        "page_subtitle": "Create small eco groups from 2 to 5 members",
        "form": form,
        "user_groups": user_groups,
    }

    return render(request, "pages/groups.html", context)


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
    actions = EcoAction.objects.filter(user=request.user)

    total_points = actions.aggregate(total=Sum("points"))["total"] or 0
    action_count = actions.count()
    progress_percent, impact_level = calculate_progress(total_points)

    context = {
        "page_title": "Profile",
        "page_subtitle": "Your personal eco profile",
        "total_points": total_points,
        "action_count": action_count,
        "progress_percent": progress_percent,
        "impact_level": impact_level,
    }

    return render(request, "pages/profile.html", context)

def register(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        form = RegisterForm(request.POST)

        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("dashboard")
    else:
        form = RegisterForm()

    context = {
        "form": form,
    }

    return render(request, "pages/register.html", context)