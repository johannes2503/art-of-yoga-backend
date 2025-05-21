from django.db import models
from django.conf import settings
from typing import Any

class UserProfile(models.Model):
    """Profile for users authenticated via Supabase. Stores role and extra info."""
    supabase_id = models.UUIDField(unique=True, db_index=True, help_text="Supabase user UUID")
    email = models.EmailField(unique=True)
    ROLE_CHOICES = [
        ("admin", "Admin"),
        ("instructor", "Instructor"),
        ("client", "Client"),
    ]
    role = models.CharField(max_length=32, choices=ROLE_CHOICES, default="client")
    full_name = models.CharField(max_length=128, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        """String representation."""
        return f"{self.email} ({self.role})" 