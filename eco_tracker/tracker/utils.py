ECO_LEVELS = [
    {
        "name": "Eco Novice",
        "icon": "🌱",
        "min_points": 0,
        "max_points": 100,
        "description": "Start your green journey.",
    },
    {
        "name": "Green Starter",
        "icon": "🍃",
        "min_points": 100,
        "max_points": 250,
        "description": "Build eco-friendly habits.",
    },
    {
        "name": "Eco Activist",
        "icon": "🌿",
        "min_points": 250,
        "max_points": 500,
        "description": "Consistently choose green actions.",
    },
    {
        "name": "Sustainability Seeker",
        "icon": "🍀",
        "min_points": 500,
        "max_points": 800,
        "description": "Create small changes in daily life.",
    },
    {
        "name": "Waste Warrior",
        "icon": "🧹",
        "min_points": 800,
        "max_points": 1200,
        "description": "Actively reduce waste and clean the environment.",
    },
    {
        "name": "Planet Protector",
        "icon": "🌍",
        "min_points": 1200,
        "max_points": 1800,
        "description": "Actively contribute and protect the green planet.",
    },
    {
        "name": "Forest Guardian",
        "icon": "🌳",
        "min_points": 1800,
        "max_points": 2500,
        "description": "Committed to planting trees and caring for nature.",
    },
    {
        "name": "Energy Innovator",
        "icon": "⚡",
        "min_points": 2500,
        "max_points": 3500,
        "description": "Pioneer in clean energy and reducing emissions.",
    },
    {
        "name": "Climate Champion",
        "icon": "🏆",
        "min_points": 3500,
        "max_points": 5000,
        "description": "Inspire and lead green lifestyles in the community.",
    },
    {
        "name": "Earth Guardian",
        "icon": "🛡️",
        "min_points": 5000,
        "max_points": None,
        "description": "The supreme guardian of the Earth's future.",
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
from .models import DailyMission, UserDailyMission, EcoAction, WeeklyMission, UserWeeklyMission


def get_user_total_points(user):
    from .models import UserGroupQuestReward, UserTriviaSubmission
    action_points = EcoAction.objects.filter(user=user).aggregate(total=Sum("points"))["total"] or 0
    daily_points = UserDailyMission.objects.filter(user=user, is_completed=True).aggregate(total=Sum("earned_points"))["total"] or 0
    weekly_points = UserWeeklyMission.objects.filter(user=user, is_completed=True).aggregate(total=Sum("earned_points"))["total"] or 0
    group_points = UserGroupQuestReward.objects.filter(user=user).aggregate(total=Sum("earned_points"))["total"] or 0
    trivia_points = UserTriviaSubmission.objects.filter(user=user).aggregate(total=Sum("earned_points"))["total"] or 0
    return action_points + daily_points + weekly_points + group_points + trivia_points



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


from django.conf import settings
from datetime import timedelta

def complete_missions_for_action(user, eco_action):
    """
    Checks and progresses both daily and weekly missions when an action is uploaded.
    Returns a list of all progressed/completed UserDailyMission/UserWeeklyMission objects.
    """
    # 1. Process Daily Missions
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
            
            # Award points and enforce daily cap
            award_points_for_completed_mission(user, user_mission, user_mission.mission.bonus_points)
            completed_missions.append(user_mission)

    # Check for Perfect Day Bonus (+15 pts)
    all_completed = all(m.is_completed for m in today_missions)
    if all_completed and len(today_missions) >= 3:
        profile, created = UserProfile.objects.get_or_create(user=user)
        today = timezone.localdate()
        if profile.last_perfect_day_date != today:
            profile.last_perfect_day_date = today
            profile.save()
            
            # Find the daily mission that was just completed in this request (or any daily mission completed today)
            daily_completed_in_req = [m for m in completed_missions if not hasattr(m, 'required_count')]
            if daily_completed_in_req:
                last_mission = daily_completed_in_req[-1]
                
                # Check remaining daily cap
                daily_cap = getattr(settings, "DAILY_POINTS_CAP", 100)
                earned_today = get_points_earned_today(user)
                remaining_cap = max(0, daily_cap - earned_today)
                bonus_awarded = min(15, remaining_cap)
                
                if bonus_awarded > 0:
                    last_mission.earned_points += bonus_awarded
                    last_mission.save()
                    # Tag the mission so the view knows a perfect day bonus was awarded
                    last_mission.perfect_day_bonus = bonus_awarded

    # 2. Process Weekly Missions
    weekly_missions = get_weekly_missions_for_user(user)

    for user_weekly_mission in weekly_missions:
        if (
            not user_weekly_mission.is_completed
            and user_weekly_mission.mission.category == eco_action.category
        ):
            user_weekly_mission.completed_count += 1
            if user_weekly_mission.completed_count >= user_weekly_mission.required_count:
                user_weekly_mission.is_completed = True
                user_weekly_mission.completed_at = timezone.now()
                # Award points and enforce daily cap
                award_points_for_completed_mission(user, user_weekly_mission, user_weekly_mission.mission.bonus_points)
            else:
                user_weekly_mission.save()
            completed_missions.append(user_weekly_mission)

    return completed_missions


def get_today_mission_summary(user):
    missions = get_today_missions_for_user(user)

    total = len(missions)
    completed = sum(1 for mission in missions if mission.is_completed)

    bonus_points = sum(
        mission.earned_points
        for mission in missions
        if mission.is_completed
    )

    return {
        "missions": missions,
        "total": total,
        "completed": completed,
        "bonus_points": bonus_points,
    }


DEFAULT_WEEKLY_MISSIONS = [
    {
        "title": "Weekly Recycling Expert",
        "description": "Complete 5 waste sorting or recycling actions.",
        "category": "recycling",
        "bonus_points": 50,
        "required_count": 5,
    },
    {
        "title": "Green Transport Warrior",
        "description": "Walk, cycle, or use public transit 5 times.",
        "category": "green_transport",
        "bonus_points": 60,
        "required_count": 5,
    },
    {
        "title": "Energy Protection Ambassador",
        "description": "Save energy or turn off unused electrical appliances 5 times.",
        "category": "saving_energy",
        "bonus_points": 40,
        "required_count": 5,
    },
    {
        "title": "Neighborhood Clean Up Knight",
        "description": "Clean up or pick up litter 3 times.",
        "category": "clean_up",
        "bonus_points": 50,
        "required_count": 3,
    },
    {
        "title": "Green Tree Savior",
        "description": "Plant new trees or care for/water plants 3 times.",
        "category": "tree_planting",
        "bonus_points": 70,
        "required_count": 3,
    },
    {
        "title": "Smart Consumer Ambassador",
        "description": "Use reusable water bottles, cloth bags, or containers 5 times.",
        "category": "reusable_item",
        "bonus_points": 45,
        "required_count": 5,
    },
]


def create_default_weekly_missions():
    for mission_data in DEFAULT_WEEKLY_MISSIONS:
        WeeklyMission.objects.get_or_create(
            title=mission_data["title"],
            defaults={
                "description": mission_data["description"],
                "category": mission_data["category"],
                "bonus_points": mission_data["bonus_points"],
                "is_active": True,
            }
        )


def get_weekly_missions_for_user(user):
    create_default_weekly_missions()
    today = timezone.localdate()
    monday = today - timedelta(days=today.weekday())

    active_missions = list(
        WeeklyMission.objects
        .filter(is_active=True)
        .order_by("id")
    )

    if not active_missions:
        return []

    # Deterministically select 2 weekly missions per user per week
    week_number = monday.isocalendar()[1]
    start_index = (week_number + user.id) % len(active_missions)

    selected_missions = []
    mission_count = min(2, len(active_missions))
    for i in range(mission_count):
        selected_missions.append(
            active_missions[(start_index + i) % len(active_missions)]
        )

    user_missions = []
    for mission in selected_missions:
        # Match with default required count
        req_count = 3
        for default_m in DEFAULT_WEEKLY_MISSIONS:
            if default_m["title"] == mission.title:
                req_count = default_m["required_count"]
                break

        user_mission, created = UserWeeklyMission.objects.get_or_create(
            user=user,
            mission=mission,
            start_date=monday,
            defaults={
                "required_count": req_count,
                "completed_count": 0,
                "is_completed": False,
                "earned_points": 0,
            }
        )
        user_missions.append(user_mission)

    return user_missions


def get_weekly_mission_summary(user):
    missions = get_weekly_missions_for_user(user)

    total = len(missions)
    completed = sum(1 for mission in missions if mission.is_completed)
    bonus_points = sum(mission.earned_points for mission in missions if mission.is_completed)

    return {
        "missions": missions,
        "total": total,
        "completed": completed,
        "bonus_points": bonus_points,
    }


def get_user_streak_multiplier(user):
    """
    Helper to get the current streak multiplier based on UserProfile without updating the streak date.
    """
    profile, created = UserProfile.objects.get_or_create(user=user)
    if profile.streak_count >= 7:
        return 1.3
    elif profile.streak_count >= 3:
        return 1.1
    return 1.0


def get_points_earned_today(user):
    """
    Calculates total points earned today from daily and weekly missions.
    """
    today = timezone.localdate()
    daily_points = UserDailyMission.objects.filter(
        user=user,
        is_completed=True,
        date=today
    ).aggregate(total=Sum("earned_points"))["total"] or 0

    weekly_points = UserWeeklyMission.objects.filter(
        user=user,
        is_completed=True,
        completed_at__date=today
    ).aggregate(total=Sum("earned_points"))["total"] or 0

    return daily_points + weekly_points


def award_points_for_completed_mission(user, user_mission, base_points):
    """
    Calculates and awards points for a completed mission, enforcing the daily cap.
    """
    today = timezone.localdate()
    daily_cap = getattr(settings, "DAILY_POINTS_CAP", 100)

    # 1. Apply streak multiplier
    multiplier = get_user_streak_multiplier(user)
    potential_points = int(base_points * multiplier)

    # 2. Get points earned today
    earned_today = get_points_earned_today(user)

    # 3. Enforce cap
    remaining_cap = max(0, daily_cap - earned_today)
    points_awarded = min(potential_points, remaining_cap)

    user_mission.earned_points = points_awarded
    user_mission.save()

    return points_awarded


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
        
        # Award +30 points co-op reward to all members of the group
        from .models import UserGroupQuestReward
        for member in group.members.all():
            UserGroupQuestReward.objects.get_or_create(
                user=member,
                quest=quest,
                defaults={"earned_points": 30}
            )
        
    progress_percent = min(100, int((progress_count / quest.target_count) * 100))
    
    return quest, progress_count, progress_percent


def create_default_trivia_questions():
    from .models import TriviaQuestion
    DEFAULT_QUESTIONS = [
        {
            "question_text": "Which of these materials takes the longest time to decompose in nature?",
            "option_a": "Paper cup",
            "option_b": "Plastic bottle",
            "option_c": "Glass bottle",
            "option_d": "Tin can",
            "correct_option": "C",
            "explanation": "Glass bottles can take up to 1 million years to decompose! While plastic bottles take 450 years, glass is virtually indestructible in landfills."
        },
        {
            "question_text": "How does recycling paper help the environment?",
            "option_a": "It saves trees and reduces energy & water usage",
            "option_b": "It eliminates carbon emissions entirely",
            "option_c": "It prevents global warming instantly",
            "option_d": "It creates clean drinking water",
            "correct_option": "A",
            "explanation": "Recycling 1 ton of paper saves 17 trees, 7,000 gallons of water, and 4,000 kilowatts of energy!"
        },
        {
            "question_text": "What is the most effective way to reduce plastic waste in daily life?",
            "option_a": "Burning all plastic waste at home",
            "option_b": "Throwing plastics in regular bins",
            "option_c": "Using reusable canvas bags and water bottles",
            "option_d": "Buying single-use items",
            "correct_option": "C",
            "explanation": "Using reusable bags and bottles prevents single-use plastics from entering landfills and oceans, which is the most effective reduction strategy."
        },
        {
            "question_text": "Which action contributes most to saving household electricity?",
            "option_a": "Leaving chargers plugged in when not in use",
            "option_b": "Using traditional incandescent light bulbs",
            "option_c": "Switching to LED bulbs and unplugging idle appliances",
            "option_d": "Running the washing machine with half loads",
            "correct_option": "C",
            "explanation": "LED bulbs use up to 80% less energy than traditional ones. Unplugging appliances prevents 'vampire power' draw."
        },
        {
            "question_text": "What percentage of global greenhouse gas emissions comes from transportation?",
            "option_a": "Around 5%",
            "option_b": "Around 14-16%",
            "option_c": "Around 50%",
            "option_d": "Around 80%",
            "correct_option": "B",
            "explanation": "Transportation accounts for approximately 14-16% of global greenhouse gas emissions. Walking, cycling, or transit makes a huge impact!"
        },
        {
            "question_text": "Why are forests referred to as the 'lungs of the Earth'?",
            "option_a": "They absorb carbon dioxide and release oxygen",
            "option_b": "They prevent rain from falling",
            "option_c": "They warm up the atmosphere",
            "option_d": "They create wind currents",
            "correct_option": "A",
            "explanation": "Trees absorb huge amounts of CO2 (a greenhouse gas) during photosynthesis and release oxygen, helping regulate the climate."
        }
    ]
    
    for q_data in DEFAULT_QUESTIONS:
        TriviaQuestion.objects.get_or_create(
            question_text=q_data["question_text"],
            defaults={
                "option_a": q_data["option_a"],
                "option_b": q_data["option_b"],
                "option_c": q_data["option_c"],
                "option_d": q_data["option_d"],
                "correct_option": q_data["correct_option"],
                "explanation": q_data["explanation"]
            }
        )


def generate_ai_coach_suggestion(user):
    """
    Generates a personalized eco coach tip for the user.
    Analyses user's recent uploads, calls Gemini AI, or falls back to smart local rules.
    """
    import os
    import httpx
    import json
    from django.conf import settings
    from .models import AICoachSuggestion, EcoAction
    
    today = timezone.localdate()
    
    # Check if we already generated a suggestion for today
    existing = AICoachSuggestion.objects.filter(user=user, date=today).first()
    if existing:
        return existing

    # Gather user context
    last_7_days = today - timedelta(days=7)
    recent_actions = EcoAction.objects.filter(user=user, created_at__date__gte=last_7_days)
    
    completed_categories = list(recent_actions.values_list("category", flat=True).distinct())
    
    all_categories = [cat[0] for cat in EcoAction.CATEGORY_CHOICES]
    missing_categories = [cat for cat in all_categories if cat not in completed_categories]
    
    # Attempt to call Gemini if API Key is configured and mock mode is disabled
    api_key = getattr(settings, "GEMINI_API_KEY", None) or os.environ.get("GEMINI_API_KEY")
    use_mock = getattr(settings, "USE_MOCK_AI", True)
    
    suggestion_text = ""
    suggested_category = random.choice(missing_categories) if missing_categories else random.choice(all_categories)
    
    if api_key and not use_mock:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
            prompt = f"""
            You are an expert personal sustainability AI Coach for the EcoTracker app.
            The user "{user.username}" is trying to live a green lifestyle.
            Here is their eco activity over the last 7 days:
            - Completed action categories: {completed_categories}
            - Categories they haven't done recently: {missing_categories}
            
            Write a highly personalized, inspiring eco coaching suggestion (exactly 2 to 3 sentences) in English motivating them.
            Recommend they try a green action today, preferably focusing on one of these missing categories: {missing_categories}.
            Be extremely encouraging, positive, and direct. Do not include introductory filler. Write in English.
            """
            
            payload = {
                "contents": [{"parts": [{"text": prompt}]}]
            }
            response = httpx.post(url, json=payload, timeout=15.0)
            response.raise_for_status()
            res = response.json()
            suggestion_text = res["candidates"][0]["content"]["parts"][0]["text"].strip()
        except Exception as e:
            # Fall back to local generator below
            pass

    if not suggestion_text:
        # Smart rule-based local generator (Fallback / Mock mode)
        coach_tips = {
            "recycling": [
                f"Hey {user.username}, you haven't uploaded any recycling actions lately! Grab a few plastic bottles or tin cans, toss them in the recycling bin today, and upload it to earn your daily points.",
                f"Did you know recycling paper saves 70% energy compared to making it from scratch? Sort your waste today, {user.username}, and complete your active Daily Missions!"
            ],
            "tree_planting": [
                f"A touch of green does wonders! Grab a watering can and care for a houseplant or garden bed today, {user.username}. Caring for plants is a great way to stay connected to nature.",
                f"Plants and trees are the lungs of our planet, {user.username}. Take a moment today to water your garden or plant a seedling, and share your eco action with the community!"
            ],
            "green_transport": [
                f"The weather is perfect for a walk or bike ride today, {user.username}! Leave the car behind and walk or cycle to your destination to reduce your carbon footprint.",
                f"Every kilometer you cycle instead of drive saves 150g of CO2! Try taking public transit or walking today, {user.username}, to keep our air clean."
            ],
            "clean_up": [
                f"A clean neighborhood starts with small acts! Take a short walk today, {user.username}, and pick up three pieces of litter. Your community will thank you!",
                f"Small cleanup actions make a massive impact on local wildlife, {user.username}. Spend five minutes cleaning up a local park or street corner today!"
            ],
            "saving_energy": [
                f"Let's save some power today, {user.username}! Try unplugging your laptop charger when full and turning off lights in empty rooms to practice green energy habits.",
                f"Practicing energy efficiency is highly impactful, {user.username}. Turn off standby appliances and switch to natural sunlight today to reduce emissions!"
            ],
            "reusable_item": [
                f"Ready for a coffee or grocery run, {user.username}? Don't forget your reusable shopping bag and water bottle today to dodge single-use plastics!",
                f"Using a reusable mug or water flask saves hundreds of single-use cups every year. Carry yours today, {user.username}, and show your sustainability pride!"
            ]
        }
        
        tips_list = coach_tips.get(suggested_category, coach_tips["recycling"])
        suggestion_text = random.choice(tips_list)

    # Save to database
    suggestion = AICoachSuggestion.objects.create(
        user=user,
        date=today,
        suggestion_text=suggestion_text,
        suggested_category=suggested_category
    )
    
    return suggestion