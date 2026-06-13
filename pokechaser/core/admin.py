from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from pokechaser.core.models import User


@admin.register(User)
class UserAdmin(UserAdmin):
    list_display = ("username", "email", "first_name", "last_name", "is_staff")
