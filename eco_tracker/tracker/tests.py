from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from .models import EcoAction, DailyMission, UserDailyMission, WeeklyMission, UserWeeklyMission, UserProfile
from .utils import (
    get_user_total_points,
    complete_missions_for_action,
    get_points_earned_today,
    award_points_for_completed_mission,
    create_default_daily_missions,
)

class EcoTrackerPointsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="password123")
        self.profile = UserProfile.objects.create(user=self.user)
        
        # Populate and deactivate default missions to avoid interference
        create_default_daily_missions()
        DailyMission.objects.all().update(is_active=False)
        WeeklyMission.objects.all().update(is_active=False)
        
        # Create some default daily and weekly missions for testing
        self.daily_mission = DailyMission.objects.create(
            title="Recycle Daily",
            category="recycling",
            bonus_points=20,
            is_active=True
        )
        self.weekly_mission = WeeklyMission.objects.create(
            title="Recycle Weekly",
            category="recycling",
            bonus_points=50,
            is_active=True
        )
        
    def test_action_upload_awards_zero_points(self):
        action = EcoAction.objects.create(
            user=self.user,
            category="recycling",
            caption="Recycled plastic bottle",
            points=10
        )
        # Verify save sets points to 0
        self.assertEqual(action.points, 0)
        self.assertEqual(get_user_total_points(self.user), 0)

    def test_daily_mission_completion_points_and_cap(self):
        # Generate user daily mission for today
        user_daily, created = UserDailyMission.objects.get_or_create(
            user=self.user,
            mission=self.daily_mission,
            date=timezone.localdate(),
            defaults={"is_completed": False}
        )
        
        action = EcoAction.objects.create(
            user=self.user,
            category="recycling",
            caption="Test recycling"
        )
        
        # Complete missions
        completed = complete_missions_for_action(self.user, action)
        
        # Verify daily mission is completed
        user_daily.refresh_from_db()
        self.assertTrue(user_daily.is_completed)
        self.assertEqual(user_daily.earned_points, 20)
        self.assertEqual(get_user_total_points(self.user), 20)
        
    def test_daily_points_cap_enforcement(self):
        # Populate and deactivate all first
        create_default_daily_missions()
        DailyMission.objects.all().update(is_active=False)
        
        m1 = DailyMission.objects.create(title="M1", category="recycling", bonus_points=60, is_active=True)
        m2 = DailyMission.objects.create(title="M2", category="tree_planting", bonus_points=60, is_active=True)
        
        ud1, created1 = UserDailyMission.objects.get_or_create(
            user=self.user, 
            mission=m1, 
            date=timezone.localdate(),
            defaults={"is_completed": False}
        )
        ud2, created2 = UserDailyMission.objects.get_or_create(
            user=self.user, 
            mission=m2, 
            date=timezone.localdate(),
            defaults={"is_completed": False}
        )
        
        # Complete M1
        a1 = EcoAction.objects.create(user=self.user, category="recycling", caption="A1")
        completed = complete_missions_for_action(self.user, a1)
        
        ud1.refresh_from_db()
        self.assertEqual(ud1.earned_points, 60)
        
        # Complete M2
        a2 = EcoAction.objects.create(user=self.user, category="tree_planting", caption="A2")
        complete_missions_for_action(self.user, a2)
        
        ud2.refresh_from_db()
        # Should be capped at 40 points because 60 + 40 = 100
        self.assertEqual(ud2.earned_points, 40)
        self.assertEqual(get_user_total_points(self.user), 100)

    def test_perfect_day_bonus(self):
        # Populate and deactivate all first
        create_default_daily_missions()
        DailyMission.objects.all().update(is_active=False)
        
        m1 = DailyMission.objects.create(title="M1", category="recycling", bonus_points=20, is_active=True)
        m2 = DailyMission.objects.create(title="M2", category="tree_planting", bonus_points=20, is_active=True)
        m3 = DailyMission.objects.create(title="M3", category="energy_saving", bonus_points=20, is_active=True)
        
        ud1, created1 = UserDailyMission.objects.get_or_create(
            user=self.user, mission=m1, date=timezone.localdate(), defaults={"is_completed": False}
        )
        ud2, created2 = UserDailyMission.objects.get_or_create(
            user=self.user, mission=m2, date=timezone.localdate(), defaults={"is_completed": False}
        )
        ud3, created3 = UserDailyMission.objects.get_or_create(
            user=self.user, mission=m3, date=timezone.localdate(), defaults={"is_completed": False}
        )
        
        # Complete M1
        a1 = EcoAction.objects.create(user=self.user, category="recycling", caption="A1")
        complete_missions_for_action(self.user, a1)
        ud1.refresh_from_db()
        self.assertEqual(ud1.earned_points, 20)
        
        # Complete M2
        a2 = EcoAction.objects.create(user=self.user, category="tree_planting", caption="A2")
        complete_missions_for_action(self.user, a2)
        ud2.refresh_from_db()
        self.assertEqual(ud2.earned_points, 20)
        
        # Complete M3
        a3 = EcoAction.objects.create(user=self.user, category="energy_saving", caption="A3")
        completed = complete_missions_for_action(self.user, a3)
        ud3.refresh_from_db()
        
        # Check that the perfect day bonus was added to the last completed daily mission
        # Since M3 is the last completed, ud3 should have earned_points = 20 + 15 = 35
        self.assertEqual(ud3.earned_points, 35)
        self.assertEqual(get_user_total_points(self.user), 75) # 20 + 20 + 35 = 75


class EcoTrackerPremiumFeaturesTests(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(username="user1", password="password123")
        self.user2 = User.objects.create_user(username="user2", password="password123")
        
        self.profile1 = UserProfile.objects.create(user=self.user1)
        self.profile2 = UserProfile.objects.create(user=self.user2)
        
        # Seed default frames
        from .models import AvatarFrame
        self.frame_emerald = AvatarFrame.objects.create(
            code="emerald_glow",
            name="Emerald Glow",
            cost=100,
            css_style="border: 3.5px solid var(--emerald);",
            preview_emoji="💚"
        )
        self.frame_solar = AvatarFrame.objects.create(
            code="solar_neon",
            name="Neon Solar",
            cost=150,
            css_style="border: 3.5px solid var(--warning);",
            preview_emoji="⚡"
        )
        
        # Seed trivia questions
        from .models import TriviaQuestion
        self.trivia_q1 = TriviaQuestion.objects.create(
            question_text="Q1?", option_a="A", option_b="B", option_c="C", option_d="D",
            correct_option="A", explanation="Exp 1"
        )
        self.trivia_q2 = TriviaQuestion.objects.create(
            question_text="Q2?", option_a="A", option_b="B", option_c="C", option_d="D",
            correct_option="B", explanation="Exp 2"
        )
        self.trivia_q3 = TriviaQuestion.objects.create(
            question_text="Q3?", option_a="A", option_b="B", option_c="C", option_d="D",
            correct_option="C", explanation="Exp 3"
        )

    def test_frame_shop_purchase_and_equip(self):
        # Initial points are 0
        self.assertEqual(get_user_total_points(self.user1), 0)
        
        # Give user1 some points (by creating a mock eco action with points)
        # Wait, points field gets cleared on EcoAction.save() due to the overridden save method setting self.points = 0!
        # Oh, let's verify that. Yes! models.py line 37: self.points = 0. So EcoActions don't award points directly; points come from daily/weekly missions or trivia/group quests!
        # That is correct: "cái khúc này bỏ point system được hong mà để người chơi lấy điểm thông qua làm nhiệm vụ hoi" (can we remove the point system here and let players get points via missions only?).
        # So EcoAction.points is always 0. Points come from missions/trivia/group quests!
        # Let's award points to user1 by creating a UserDailyMission completed with earned_points
        from .models import DailyMission, UserDailyMission
        mission = DailyMission.objects.create(title="Mock Mission", category="recycling", bonus_points=120)
        UserDailyMission.objects.create(
            user=self.user1,
            mission=mission,
            date=timezone.localdate(),
            is_completed=True,
            earned_points=120
        )
        
        self.assertEqual(get_user_total_points(self.user1), 120)
        
        # Try to buy frame
        self.client.login(username="user1", password="password123")
        
        # 1. Purchase frame
        response = self.client.post("/shop/", {"action": "purchase", "frame_code": "emerald_glow"})
        self.assertEqual(response.status_code, 302) # Redirects back to frame_shop
        
        self.profile1.refresh_from_db()
        self.assertEqual(self.profile1.points_spent, 100)
        
        # Available points should be total_points - points_spent = 120 - 100 = 20
        available_points = get_user_total_points(self.user1) - self.profile1.points_spent
        self.assertEqual(available_points, 20)
        
        # Verify ownership in UserAvatarFrame
        from .models import UserAvatarFrame
        self.assertTrue(UserAvatarFrame.objects.filter(user=self.user1, frame=self.frame_emerald).exists())
        
        # 2. Equip frame
        response = self.client.post("/shop/", {"action": "equip", "frame_code": "emerald_glow"})
        self.assertEqual(response.status_code, 302)
        
        self.profile1.refresh_from_db()
        self.assertEqual(self.profile1.active_frame, self.frame_emerald)
        
        # 3. Unequip frame
        response = self.client.post("/shop/", {"action": "unequip", "frame_code": "emerald_glow"})
        self.assertEqual(response.status_code, 302)
        
        self.profile1.refresh_from_db()
        self.assertIsNone(self.profile1.active_frame)

    def test_daily_trivia_ajax_submission(self):
        self.client.login(username="user1", password="password123")
        
        # Submit trivia answers: 2 correct (Q1: A, Q2: B) and 1 incorrect (Q3: A, correct is C)
        payload = {
            "answers": {
                str(self.trivia_q1.id): "A", # correct
                str(self.trivia_q2.id): "B", # correct
                str(self.trivia_q3.id): "A"  # incorrect
            }
        }
        
        import json
        response = self.client.post(
            "/trivia/submit/",
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        
        res_data = response.json()
        self.assertTrue(res_data["success"])
        self.assertEqual(res_data["correct_count"], 2)
        self.assertEqual(res_data["points_earned"], 10) # 2 * 5 = 10 points
        
        # Verify in database
        from .models import UserTriviaSubmission
        sub = UserTriviaSubmission.objects.filter(user=self.user1, date=timezone.localdate()).first()
        self.assertIsNotNone(sub)
        self.assertEqual(sub.questions_answered, 3)
        self.assertEqual(sub.correct_answers, 2)
        self.assertEqual(sub.earned_points, 10)
        
        # Check total points
        self.assertEqual(get_user_total_points(self.user1), 10)

    def test_coop_group_quest_rewards(self):
        # Create group and add members
        from .models import EcoGroup, GroupMember
        group = EcoGroup.objects.create(name="Eco Team", owner=self.user1)
        GroupMember.objects.create(group=group, user=self.user1)
        GroupMember.objects.create(group=group, user=self.user2)
        
        # Generate weekly quest
        from .utils import get_or_create_weekly_quest
        quest, count, percent = get_or_create_weekly_quest(group)
        
        # Complete the quest by uploading 10 actions matching quest.category
        # Wait, get_or_create_weekly_quest evaluates actions uploaded during the quest week
        # Let's upload 10 actions
        for _ in range(10):
            EcoAction.objects.create(
                user=self.user1,
                category=quest.category,
                caption="Quest action"
            )
            
        # Call get_or_create_weekly_quest again to trigger completion check and reward distribution
        quest, count, percent = get_or_create_weekly_quest(group)
        
        self.assertTrue(quest.is_completed)
        
        # Both members should receive the +30 points reward
        from .models import UserGroupQuestReward
        self.assertTrue(UserGroupQuestReward.objects.filter(user=self.user1, quest=quest).exists())
        self.assertTrue(UserGroupQuestReward.objects.filter(user=self.user2, quest=quest).exists())
        
        self.assertEqual(get_user_total_points(self.user1), 30)
        self.assertEqual(get_user_total_points(self.user2), 30)

    def test_ai_coach_suggestion_generation(self):
        # Verify daily AI suggestion generates correctly
        from .utils import generate_ai_coach_suggestion
        suggestion = generate_ai_coach_suggestion(self.user1)
        
        self.assertIsNotNone(suggestion)
        self.assertEqual(suggestion.user, self.user1)
        self.assertEqual(suggestion.date, timezone.localdate())
        self.assertTrue(len(suggestion.suggestion_text) > 10)


