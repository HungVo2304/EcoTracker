from django.contrib import admin
from .models import EcoAction, Friendship, EcoGroup, GroupMember, UserProfile

admin.site.register(UserProfile)
admin.site.register(EcoAction)
admin.site.register(Friendship)
admin.site.register(EcoGroup)
admin.site.register(GroupMember)