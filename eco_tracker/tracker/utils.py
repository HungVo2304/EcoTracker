ECO_LEVELS = [
    {
        "name": "Eco Beginner",
        "icon": "🌱",
        "min_points": 0,
        "max_points": 100,
        "description": "You are starting your eco journey.",
    },
    {
        "name": "Green Starter",
        "icon": "🍃",
        "min_points": 100,
        "max_points": 300,
        "description": "You are building consistent green habits.",
    },
    {
        "name": "Eco Warrior",
        "icon": "🌿",
        "min_points": 300,
        "max_points": 600,
        "description": "Your actions are creating visible positive impact.",
    },
    {
        "name": "Planet Protector",
        "icon": "🌍",
        "min_points": 600,
        "max_points": 1000,
        "description": "You are strongly contributing to the planet.",
    },
    {
        "name": "Climate Champion",
        "icon": "🏆",
        "min_points": 1000,
        "max_points": 1500,
        "description": "You are leading by example.",
    },
    {
        "name": "Earth Guardian",
        "icon": "🛡️",
        "min_points": 1500,
        "max_points": None,
        "description": "You have reached the highest eco level.",
    },
]


def get_level_info(total_points):
    total_points = total_points or 0

    for level in ECO_LEVELS:
        min_points = level["min_points"]
        max_points = level["max_points"]

        if max_points is None or min_points <= total_points < max_points:
            if max_points is None:
                progress_percent = 100
                points_to_next = 0
                next_level = None
            else:
                points_in_level = total_points - min_points
                points_needed_for_level = max_points - min_points
                progress_percent = int((points_in_level / points_needed_for_level) * 100)
                points_to_next = max_points - total_points

                next_level = None
                current_index = ECO_LEVELS.index(level)
                if current_index + 1 < len(ECO_LEVELS):
                    next_level = ECO_LEVELS[current_index + 1]["name"]

            return {
                "name": level["name"],
                "icon": level["icon"],
                "description": level["description"],
                "min_points": min_points,
                "max_points": max_points,
                "progress_percent": progress_percent,
                "points_to_next": points_to_next,
                "next_level": next_level,
            }

    return ECO_LEVELS[0]


from django.utils import timezone
from django.db.models import Sum

from .models import DailyMission, UserDailyMission, EcoAction


def get_user_total_points(user):
    action_points = EcoAction.objects.filter(user=user).aggregate(total=Sum("points"))["total"] or 0
    bonus_points = UserDailyMission.objects.filter(user=user, is_completed=True).aggregate(total=Sum("mission__bonus_points"))["total"] or 0
    return action_points + bonus_points



DEFAULT_DAILY_MISSIONS = [
    {
        "title": "Recycle something today",
        "description": "Upload a recycling action such as plastic, paper, or cans.",
        "category": "recycling",
        "bonus_points": 10,
    },
    {
        "title": "Use green transport",
        "description": "Walk, cycle, or use public transport.",
        "category": "green_transport",
        "bonus_points": 15,
    },
    {
        "title": "Save energy",
        "description": "Reduce electricity use or save energy at home.",
        "category": "saving_energy",
        "bonus_points": 10,
    },
    {
        "title": "Use a reusable item",
        "description": "Use a reusable bottle, bag, cup, or container.",
        "category": "reusable_item",
        "bonus_points": 10,
    },
    {
        "title": "Clean up your area",
        "description": "Pick up litter or clean a shared space.",
        "category": "clean_up",
        "bonus_points": 15,
    },
    {
        "title": "Plant or care for a tree",
        "description": "Plant a tree or take care of plants.",
        "category": "tree_planting",
        "bonus_points": 20,
    },
]


def create_default_daily_missions():
    for mission_data in DEFAULT_DAILY_MISSIONS:
        DailyMission.objects.get_or_create(
            title=mission_data["title"],
            defaults={
                "description": mission_data["description"],
                "category": mission_data["category"],
                "bonus_points": mission_data["bonus_points"],
                "is_active": True,
            }
        )


def get_today_missions_for_user(user):
    create_default_daily_missions()

    today = timezone.localdate()

    active_missions = list(
        DailyMission.objects
        .filter(is_active=True)
        .order_by("id")
    )

    if not active_missions:
        return []

    mission_count = min(3, len(active_missions))
    start_index = today.toordinal() % len(active_missions)

    selected_missions = []

    for i in range(mission_count):
        selected_missions.append(
            active_missions[(start_index + i) % len(active_missions)]
        )

    user_missions = []

    for mission in selected_missions:
        user_mission, created = UserDailyMission.objects.get_or_create(
            user=user,
            mission=mission,
            date=today
        )

        user_missions.append(user_mission)

    return user_missions


def complete_missions_for_action(user, eco_action):
    today_missions = get_today_missions_for_user(user)
    completed_missions = []

    for user_mission in today_missions:
        if (
            not user_mission.is_completed
            and user_mission.mission.category == eco_action.category
        ):
            user_mission.is_completed = True
            user_mission.completed_at = timezone.now()
            user_mission.completed_action = eco_action
            user_mission.save()

            completed_missions.append(user_mission)

    return completed_missions


def get_today_mission_summary(user):
    missions = get_today_missions_for_user(user)

    total = len(missions)
    completed = sum(1 for mission in missions if mission.is_completed)

    bonus_points = sum(
        mission.mission.bonus_points
        for mission in missions
        if mission.is_completed
    )

    return {
        "missions": missions,
        "total": total,
        "completed": completed,
        "bonus_points": bonus_points,
    }


from django.db.models import Count
from .models import UserProfile, Badge, UserBadge, EcoActionLike, GroupWeeklyQuest
import random

DEFAULT_BADGES = [
    {
        "code": "recycling_master",
        "name": "Recycling Master",
        "description": "Upload 5 recycling actions to earn this badge.",
        "icon": "♻️",
        "requirement_category": "recycling",
        "requirement_count": 5
    },
    {
        "code": "green_commuter",
        "name": "Green Commuter",
        "description": "Upload 5 green transport actions to earn this badge.",
        "icon": "🚲",
        "requirement_category": "green_transport",
        "requirement_count": 5
    },
    {
        "code": "tree_ambassador",
        "name": "Tree Ambassador",
        "description": "Upload 3 tree planting actions to earn this badge.",
        "icon": "🌳",
        "requirement_category": "tree_planting",
        "requirement_count": 3
    },
    {
        "code": "area_hero",
        "name": "Area Hero",
        "description": "Upload 5 clean up actions to earn this badge.",
        "icon": "🧹",
        "requirement_category": "clean_up",
        "requirement_count": 5
    },
    {
        "code": "energy_saver",
        "name": "Energy Saver",
        "description": "Upload 5 saving energy actions to earn this badge.",
        "icon": "💡",
        "requirement_category": "saving_energy",
        "requirement_count": 5
    },
    {
        "code": "eco_consumer",
        "name": "Eco Consumer",
        "description": "Upload 5 reusable item actions to earn this badge.",
        "icon": "🛍️",
        "requirement_category": "reusable_item",
        "requirement_count": 5
    }
]


def create_default_badges():
    for badge_data in DEFAULT_BADGES:
        Badge.objects.get_or_create(
            code=badge_data["code"],
            defaults={
                "name": badge_data["name"],
                "description": badge_data["description"],
                "icon": badge_data["icon"],
                "requirement_category": badge_data["requirement_category"],
                "requirement_count": badge_data["requirement_count"]
            }
        )


def update_user_streak(user):
    """
    Updates the user's eco streak based on their action upload dates.
    Returns (streak_count, points_multiplier).
    - Streak 3-6 days: 1.1x multiplier
    - Streak 7+ days: 1.3x multiplier
    """
    profile, created = UserProfile.objects.get_or_create(user=user)
    today = timezone.localdate()
    
    if profile.last_action_date is None:
        profile.streak_count = 1
    else:
        delta = today - profile.last_action_date
        if delta.days == 1:
            profile.streak_count += 1
        elif delta.days > 1:
            profile.streak_count = 1
        # If delta.days == 0, keep current streak count
        
    profile.last_action_date = today
    profile.save()
    
    if profile.streak_count >= 7:
        multiplier = 1.3
    elif profile.streak_count >= 3:
        multiplier = 1.1
    else:
        multiplier = 1.0
        
    return profile.streak_count, multiplier


def check_and_award_badges(user):
    """
    Evaluates the user's action counts and awards newly earned badges.
    Returns a list of newly unlocked Badge objects.
    """
    create_default_badges()
    newly_earned = []
    
    earned_badge_ids = UserBadge.objects.filter(user=user).values_list("badge_id", flat=True)
    unearned_badges = Badge.objects.exclude(id__in=earned_badge_ids)
    
    for badge in unearned_badges:
        count = EcoAction.objects.filter(user=user, category=badge.requirement_category).count()
        if count >= badge.requirement_count:
            UserBadge.objects.create(user=user, badge=badge)
            newly_earned.append(badge)
            
    return newly_earned


def get_or_create_weekly_quest(group):
    """
    Fetches the active weekly quest for the group. 
    If none exists or it is older than 7 days, generates a new one.
    Returns (quest, progress_count, progress_percent).
    """
    today = timezone.localdate()
    quest = GroupWeeklyQuest.objects.filter(group=group).first()
    
    if quest:
        delta = today - quest.start_date
        if delta.days >= 7:
            quest.delete()
            quest = None
            
    if not quest:
        categories = [cat[0] for cat in EcoAction.CATEGORY_CHOICES]
        selected_cat = random.choice(categories)
        quest = GroupWeeklyQuest.objects.create(
            group=group,
            category=selected_cat,
            target_count=10,
            start_date=today,
            is_completed=False
        )
        
    members = group.members.all()
    progress_count = EcoAction.objects.filter(
        user__in=members,
        category=quest.category,
        created_at__date__gte=quest.start_date
    ).count()
    
    if progress_count >= quest.target_count and not quest.is_completed:
        quest.is_completed = True
        quest.save()
        
    progress_percent = min(100, int((progress_count / quest.target_count) * 100))
    
    return quest, progress_count, progress_percent