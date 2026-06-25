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
        self.points = POINTS_BY_CATEGORY.get(self.category, 0)
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
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "action")

    def __str__(self):
        return f"{self.user.username} liked action {self.action.id}"


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

    class Meta:
        unique_together = ("user", "mission", "date")

    def __str__(self):
        status = "Completed" if self.is_completed else "Pending"
        return f"{self.user.username} - {self.mission.title} - {status}"