from django.contrib import admin
from .models import Role, User


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ['name', 'name_en', 'is_system', 'is_active', 'created_at']
    list_filter = ['is_active', 'is_system']
    search_fields = ['name', 'name_en']


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['username', 'full_name', 'phone', 'is_active', 'is_staff', 'is_superuser']
    list_filter = ['is_active', 'is_staff', 'is_superuser']
    search_fields = ['username', 'full_name', 'phone']
    filter_horizontal = ['roles']
