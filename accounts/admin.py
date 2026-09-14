from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'role', 'curso', 'is_active')
    list_filter = ('role', 'curso', 'is_active')
    fieldsets = BaseUserAdmin.fieldsets + (
        ('ACTUVa', {'fields': ('role', 'curso')}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('ACTUVa', {'fields': ('role', 'curso')}),
    )
