from django.db import models
from users.models import UserProfile
from typing import Optional
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from core.storage import SupabaseStorage
import os
import json
import uuid
from django.utils import timezone

class MediaAsset(models.Model):
    """Model for storing media assets (images, videos, audio, animations)."""
    
    ASSET_TYPES = (
        ('image', 'Image'),
        ('video', 'Video'),
        ('audio', 'Audio'),
        ('animation', 'Animation'),
    )
    
    name = models.CharField(max_length=255)
    asset_type = models.CharField(max_length=20, choices=ASSET_TYPES)
    file_path = models.CharField(max_length=512, null=True, blank=True)  # Made nullable
    url = models.URLField(max_length=1024)
    thumbnail_url = models.URLField(max_length=1024, null=True, blank=True)
    file_size = models.PositiveIntegerField(help_text='File size in bytes')
    duration_seconds = models.PositiveIntegerField(null=True, blank=True)
    instructor = models.ForeignKey(
        'users.UserProfile',
        on_delete=models.CASCADE,
        related_name='media_assets'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['asset_type']),
            models.Index(fields=['instructor', 'asset_type']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.get_asset_type_display()})"
    
    def clean(self):
        """Validate the media asset."""
        # Check file size
        max_size = settings.MAX_FILE_SIZES.get(self.asset_type)
        if max_size and self.file_size > max_size:
            raise ValidationError(
                f'File size exceeds maximum allowed size for {self.asset_type}'
            )
    
    def save(self, *args, **kwargs):
        """Save the media asset and handle storage operations."""
        if not self.pk:  # New instance
            self.clean()
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        """Delete the media asset and its file from storage."""
        storage = SupabaseStorage()
        if self.file_path:
            storage.delete_file(self.file_path)
        super().delete(*args, **kwargs)
    
    def refresh_url(self):
        """Refresh the signed URL for the media asset."""
        storage = SupabaseStorage()
        if self.file_path:
            signed_url = storage._get_signed_url(self.file_path)
            self.url = signed_url
            if self.asset_type in ['image', 'video']:
                self.thumbnail_url = storage._generate_thumbnail_url(self.file_path)
            self.save(update_fields=['url', 'thumbnail_url', 'updated_at'])
    
    @classmethod
    def create_from_upload(cls, file_data: bytes, file_name: str, instructor, asset_type: str) -> 'MediaAsset':
        """Create a media asset from uploaded file data."""
        storage = SupabaseStorage()
        file_path, metadata = storage.upload_file(
            file_data=file_data,
            file_name=file_name,
            instructor_id=instructor.id,
            asset_type=asset_type
        )
        
        return cls.objects.create(
            name=os.path.splitext(os.path.basename(file_name))[0],
            asset_type=asset_type,
            file_path=file_path,
            url=metadata['url'],
            thumbnail_url=metadata['thumbnail_url'],
            file_size=metadata['file_size'],
            instructor=instructor
        )

class Routine(models.Model):
    """Yoga routine created by an instructor and assigned to clients."""
    name = models.CharField(max_length=128)
    description = models.TextField(blank=True)
    instructor = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name="routines")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    def __str__(self) -> str:
        return f"{self.name} (Instructor: {self.instructor.email})"

class Exercise(models.Model):
    """Exercise or pose within a routine."""
    routine = models.ForeignKey(Routine, on_delete=models.CASCADE, related_name="exercises")
    name = models.CharField(max_length=128)
    instructions = models.TextField(blank=True)
    media_assets = models.ManyToManyField(MediaAsset, blank=True, related_name="exercises")
    order = models.PositiveIntegerField(default=0)

    def __str__(self) -> str:
        return f"{self.name} (Routine: {self.routine.name})"

class BreathingExercise(models.Model):
    """Breathing exercise with pattern, timer, and progress tracking."""
    name = models.CharField(max_length=128)
    description = models.TextField(blank=True)
    instructor = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name="breathing_exercises")
    pattern = models.JSONField(help_text="Breath pattern configuration (e.g., [inhale, hold, exhale, hold])")
    timer_seconds = models.PositiveIntegerField(default=60, help_text="Default session duration in seconds")
    media_assets = models.ManyToManyField(MediaAsset, blank=True, related_name="breathing_exercises")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    def __str__(self) -> str:
        return f"{self.name} (Instructor: {self.instructor.email})"

class MeditationSession(models.Model):
    """Meditation session with audio, script, and progress tracking."""
    name = models.CharField(max_length=128)
    description = models.TextField(blank=True)
    instructor = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name="meditation_sessions")
    audio_assets = models.ManyToManyField(MediaAsset, blank=True, related_name="meditation_audio_sessions", limit_choices_to={'asset_type': 'audio'})
    script = models.TextField(blank=True, help_text="Guided meditation script")
    duration_seconds = models.PositiveIntegerField(default=600, help_text="Session duration in seconds")
    media_assets = models.ManyToManyField(MediaAsset, blank=True, related_name="meditation_visual_sessions", limit_choices_to={'asset_type__in': ['image', 'video']})
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    def __str__(self) -> str:
        return f"{self.name} (Instructor: {self.instructor.email})"

class CombinedRoutine(models.Model):
    """Routine that integrates yoga, breathing, and meditation exercises."""
    name = models.CharField(max_length=128)
    description = models.TextField(blank=True)
    instructor = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name="combined_routines")
    routines = models.ManyToManyField(Routine, blank=True, related_name="combined_routines")
    breathing_exercises = models.ManyToManyField(BreathingExercise, blank=True, related_name="combined_routines")
    meditation_sessions = models.ManyToManyField(MeditationSession, blank=True, related_name="combined_routines")
    transition_notes = models.TextField(blank=True, help_text="Instructions for transitions between exercise types")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    def __str__(self) -> str:
        return f"{self.name} (Instructor: {self.instructor.email})"

class ClientInstructorRelationship(models.Model):
    """Relationship between a client and an instructor for routine assignments."""
    client = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name="client_relationships")
    instructor = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name="instructor_relationships")
    routines = models.ManyToManyField(Routine, related_name="assigned_clients", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("client", "instructor")

    def __str__(self) -> str:
        return f"Client: {self.client.email} - Instructor: {self.instructor.email}"

class ExerciseProgress(models.Model):
    """Tracks client progress for any type of exercise."""
    client = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name="exercise_progress")
    exercise = models.ForeignKey(Exercise, on_delete=models.CASCADE, related_name="progress_tracking", null=True, blank=True)
    breathing_exercise = models.ForeignKey(BreathingExercise, on_delete=models.CASCADE, related_name="progress_tracking", null=True, blank=True)
    meditation_session = models.ForeignKey(MeditationSession, on_delete=models.CASCADE, related_name="progress_tracking", null=True, blank=True)
    completed_at = models.DateTimeField(auto_now_add=True)
    duration_seconds = models.PositiveIntegerField(help_text="Time spent on exercise in seconds")
    notes = models.TextField(blank=True)
    difficulty_rating = models.PositiveSmallIntegerField(null=True, blank=True, choices=[(i, i) for i in range(1, 6)])
    feedback = models.TextField(blank=True)

    class Meta:
        unique_together = [
            ('client', 'exercise', 'completed_at'),
            ('client', 'breathing_exercise', 'completed_at'),
            ('client', 'meditation_session', 'completed_at'),
        ]

    def __str__(self) -> str:
        exercise_name = (
            self.exercise.name if self.exercise else
            self.breathing_exercise.name if self.breathing_exercise else
            self.meditation_session.name if self.meditation_session else
            "Unknown Exercise"
        )
        return f"{self.client.email} - {exercise_name} ({self.completed_at})"

class Achievement(models.Model):
    """Achievement system for tracking client milestones."""
    ACHIEVEMENT_TYPE_CHOICES = [
        ('consistency', 'Consistency'),
        ('mastery', 'Mastery'),
        ('milestone', 'Milestone'),
        ('special', 'Special'),
    ]
    
    name = models.CharField(max_length=128)
    description = models.TextField()
    achievement_type = models.CharField(max_length=16, choices=ACHIEVEMENT_TYPE_CHOICES)
    icon_url = models.URLField(blank=True)
    criteria = models.JSONField(help_text="Achievement criteria (e.g., {'exercise_count': 10, 'days_streak': 7})")
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self) -> str:
        return f"{self.name} ({self.achievement_type})"

class ClientAchievement(models.Model):
    """Links achievements to clients and tracks when they were earned."""
    client = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name="achievements")
    achievement = models.ForeignKey(Achievement, on_delete=models.CASCADE, related_name="client_achievements")
    earned_at = models.DateTimeField(auto_now_add=True)
    progress_data = models.JSONField(default=dict, help_text="Data about how the achievement was earned")

    class Meta:
        unique_together = ('client', 'achievement')

    def __str__(self) -> str:
        return f"{self.client.email} - {self.achievement.name} ({self.earned_at})"

class UploadProgress(models.Model):
    """Model for tracking file upload progress."""
    
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('uploading', 'Uploading'),
        ('verifying', 'Verifying'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    )
    
    upload_id = models.UUIDField(unique=True)
    instructor = models.ForeignKey(
        'users.UserProfile',
        on_delete=models.CASCADE,
        related_name='upload_progress'
    )
    file_name = models.CharField(max_length=255)
    file_path = models.CharField(max_length=512, null=True, blank=True)
    asset_type = models.CharField(max_length=20, choices=MediaAsset.ASSET_TYPES)
    total_size = models.PositiveIntegerField(help_text='Total file size in bytes')
    uploaded_size = models.PositiveIntegerField(default=0, help_text='Uploaded bytes so far')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    error_message = models.TextField(null=True, blank=True)
    metadata = models.JSONField(default=dict, help_text='Additional upload metadata')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['upload_id']),
            models.Index(fields=['status']),
            models.Index(fields=['instructor', 'status']),
        ]
    
    def __str__(self):
        return f"{self.file_name} ({self.status})"
    
    @property
    def progress_percentage(self):
        """Calculate upload progress percentage."""
        if self.total_size == 0:
            return 0
        return min(100, int((self.uploaded_size / self.total_size) * 100))
    
    def update_progress(self, uploaded_size: int, status: str = None, error_message: str = None):
        """Update upload progress."""
        self.uploaded_size = uploaded_size
        if status:
            self.status = status
        if error_message:
            self.error_message = error_message
        if status == 'completed':
            self.completed_at = timezone.now()
        self.save(update_fields=[
            'uploaded_size', 'status', 'error_message',
            'completed_at', 'updated_at'
        ])
    
    def to_dict(self):
        """Convert progress to dictionary."""
        return {
            'upload_id': str(self.upload_id),
            'file_name': self.file_name,
            'file_path': self.file_path,
            'asset_type': self.asset_type,
            'total_size': self.total_size,
            'uploaded_size': self.uploaded_size,
            'progress_percentage': self.progress_percentage,
            'status': self.status,
            'error_message': self.error_message,
            'metadata': self.metadata,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }
    
    @classmethod
    def create_for_direct_upload(cls, policy: dict, instructor) -> 'UploadProgress':
        """Create progress tracking for direct upload."""
        return cls.objects.create(
            upload_id=policy['upload_id'],
            instructor=instructor,
            file_name=os.path.basename(policy['file_path']),
            file_path=policy['file_path'],
            asset_type=policy['asset_type'],
            total_size=policy['max_size_bytes'],
            metadata={
                'content_type': policy['content_type'],
                'bucket': policy['bucket'],
                'expires_at': policy['expires_at']
            }
        )
    
    @classmethod
    def create_for_traditional_upload(cls, file_obj, instructor, asset_type: str) -> 'UploadProgress':
        """Create progress tracking for traditional upload."""
        return cls.objects.create(
            upload_id=uuid.uuid4(),
            instructor=instructor,
            file_name=file_obj.name,
            asset_type=asset_type,
            total_size=file_obj.size,
            metadata={
                'content_type': file_obj.content_type,
                'upload_method': 'traditional'
            }
        ) 