from django.db import models
from django.contrib.auth.models import User


POINTS_BY_CATEGORY = {
    "recycling": 20,
    "tree_planting": 50,
    "green_transport": 30,
    "clean_up": 40,
    "saving_energy": 15,
    "reusable_item": 25,
}


class EcoAction(models.Model):
    CATEGORY_CHOICES = [
        ("recycling", "Recycling"),
        ("tree_planting", "Tree Planting"),
        ("green_transport", "Green Transport"),
        ("clean_up", "Clean Up"),
        ("saving_energy", "Saving Energy"),
        ("reusable_item", "Reusable Item"),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="eco_actions"
    )
    image = models.ImageField(upload_to="eco_actions/")
    caption = models.CharField(max_length=255)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    points = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        self.points = 0
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.username} - {self.get_category_display()} - {self.points} pts"


class Friendship(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("accepted", "Accepted"),
    ]

    sender = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="sent_friend_requests"
    )
    receiver = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="received_friend_requests"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("sender", "receiver")

    def __str__(self):
        return f"{self.sender.username} → {self.receiver.username} ({self.status})"


class EcoGroup(models.Model):
    name = models.CharField(max_length=100)
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="owned_groups"
    )
    members = models.ManyToManyField(
        User,
        through="GroupMember",
        related_name="eco_groups"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def member_count(self):
        return self.members.count()

    def can_add_member(self):
        return self.member_count() < 5

    def __str__(self):
        return self.name


class GroupMember(models.Model):
    group = models.ForeignKey(EcoGroup, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("group", "user")

    def __str__(self):
        return f"{self.user.username} in {self.group.name}"
    

class UserProfile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile"
    )
    avatar = models.ImageField(
        upload_to="avatars/",
        blank=True,
        null=True
    )
    streak_count = models.PositiveIntegerField(default=0)
    last_action_date = models.DateField(null=True, blank=True)
    last_level = models.CharField(max_length=100, default="Eco Novice")
    last_perfect_day_date = models.DateField(null=True, blank=True)
    points_spent = models.PositiveIntegerField(default=0)
    active_frame = models.ForeignKey(
        "AvatarFrame",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="active_users"
    )

    def __str__(self):
        return f"{self.user.username}'s Profile"
    

class Badge(models.Model):
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField()
    icon = models.CharField(max_length=10) # Emoji
    requirement_category = models.CharField(max_length=50, choices=EcoAction.CATEGORY_CHOICES)
    requirement_count = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.icon} {self.name}"


class UserBadge(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="badges"
    )
    badge = models.ForeignKey(
        Badge,
        on_delete=models.CASCADE,
        related_name="earned_by"
    )
    earned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "badge")

    def __str__(self):
        return f"{self.user.username} earned {self.badge.name}"


class EcoActionLike(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="likes"
    )
    action = models.ForeignKey(
        EcoAction,
        on_delete=models.CASCADE,
        related_name="likes"
    )
    reaction_type = models.CharField(max_length=20, default="like")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "action", "reaction_type")

    def __str__(self):
        return f"{self.user.username} - {self.reaction_type} on action {self.action.id}"


class GroupWeeklyQuest(models.Model):
    group = models.OneToOneField(
        EcoGroup,
        on_delete=models.CASCADE,
        related_name="weekly_quest"
    )
    category = models.CharField(max_length=50, choices=EcoAction.CATEGORY_CHOICES)
    target_count = models.PositiveIntegerField(default=10)
    start_date = models.DateField()
    is_completed = models.BooleanField(default=False)

    def __str__(self):
        return f"Quest for {self.group.name}: {self.category} ({self.target_count})"


class GroupInvite(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("accepted", "Accepted"),
        ("rejected", "Rejected"),
    ]

    group = models.ForeignKey(
        EcoGroup,
        on_delete=models.CASCADE,
        related_name="invites"
    )
    sender = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="sent_group_invites"
    )
    receiver = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="received_group_invites"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("group", "receiver")

    def __str__(self):
        return f"{self.sender.username} invited {self.receiver.username} to {self.group.name}"
    

class DailyMission(models.Model):
    title = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=50, choices=EcoAction.CATEGORY_CHOICES)
    bonus_points = models.PositiveIntegerField(default=10)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.title} (+{self.bonus_points} pts)"


class UserDailyMission(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="daily_missions"
    )
    mission = models.ForeignKey(
        DailyMission,
        on_delete=models.CASCADE,
        related_name="user_missions"
    )
    date = models.DateField()
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(blank=True, null=True)
    completed_action = models.ForeignKey(
        EcoAction,
        on_delete=models.SET_NULL,
        blank=True,
        null=True
    )
    earned_points = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ("user", "mission", "date")

    def __str__(self):
        status = "Completed" if self.is_completed else "Pending"
        return f"{self.user.username} - {self.mission.title} - {status}"


class WeeklyMission(models.Model):
    title = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=50, choices=EcoAction.CATEGORY_CHOICES)
    bonus_points = models.PositiveIntegerField(default=50)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.title} (+{self.bonus_points} pts)"


class UserWeeklyMission(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="weekly_missions"
    )
    mission = models.ForeignKey(
        WeeklyMission,
        on_delete=models.CASCADE,
        related_name="user_missions"
    )
    start_date = models.DateField()
    completed_count = models.PositiveIntegerField(default=0)
    required_count = models.PositiveIntegerField(default=3)
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(blank=True, null=True)
    earned_points = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ("user", "mission", "start_date")

    def __str__(self):
        status = "Completed" if self.is_completed else f"{self.completed_count}/{self.required_count}"
        return f"{self.user.username} - {self.mission.title} - {status}"


class AvatarFrame(models.Model):
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    cost = models.PositiveIntegerField(default=100)
    css_style = models.TextField(help_text="CSS border style rules for frame")
    preview_emoji = models.CharField(max_length=10, default="✨")

    def __str__(self):
        return f"{self.preview_emoji} {self.name} ({self.cost} pts)"


class UserAvatarFrame(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="owned_frames")
    frame = models.ForeignKey(AvatarFrame, on_delete=models.CASCADE)
    purchased_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "frame")

    def __str__(self):
        return f"{self.user.username} owned {self.frame.name}"


class UserGroupQuestReward(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="group_quest_rewards")
    quest = models.ForeignKey(GroupWeeklyQuest, on_delete=models.CASCADE, related_name="rewards")
    earned_points = models.PositiveIntegerField(default=30)
    awarded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "quest")

    def __str__(self):
        return f"{self.user.username} earned +{self.earned_points} pts on Quest {self.quest.id}"


class TriviaQuestion(models.Model):
    question_text = models.CharField(max_length=255)
    option_a = models.CharField(max_length=100)
    option_b = models.CharField(max_length=100)
    option_c = models.CharField(max_length=100)
    option_d = models.CharField(max_length=100)
    correct_option = models.CharField(max_length=1, choices=[('A', 'A'), ('B', 'B'), ('C', 'C'), ('D', 'D')])
    explanation = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.question_text


class UserTriviaSubmission(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="trivia_submissions")
    date = models.DateField()
    questions_answered = models.PositiveIntegerField(default=0)
    correct_answers = models.PositiveIntegerField(default=0)
    earned_points = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ("user", "date")

    def __str__(self):
        return f"{self.user.username} - Trivia {self.date} - {self.correct_answers}/3 correct"


class AICoachSuggestion(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="ai_suggestions")
    date = models.DateField()
    suggestion_text = models.TextField()
    suggested_category = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        unique_together = ("user", "date")

    def __str__(self):
        return f"AI Suggestion for {self.user.username} on {self.date}"