from django.contrib import admin
from .models import UserProfile

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("email", "role", "supabase_id", "created_at")
    search_fields = ("email", "role", "supabase_id")
    list_filter = ("role",) 