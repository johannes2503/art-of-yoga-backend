from django.db import models
from users.models import UserProfile
from typing import Optional

class MediaAsset(models.Model):
    """Media asset (image, video, audio) with metadata and organization."""
    ASSET_TYPE_CHOICES = [
        ('image', 'Image'),
        ('video', 'Video'),
        ('audio', 'Audio'),
        ('animation', 'Animation'),
    ]
    
    name = models.CharField(max_length=128)
    asset_type = models.CharField(max_length=16, choices=ASSET_TYPE_CHOICES)
    url = models.URLField(help_text="URL to the media file in Supabase Storage")
    thumbnail_url = models.URLField(blank=True, help_text="URL to thumbnail for videos")
    file_size = models.PositiveIntegerField(help_text="File size in bytes")
    duration_seconds = models.PositiveIntegerField(null=True, blank=True, help_text="Duration for video/audio in seconds")
    instructor = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name="media_assets")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    def __str__(self) -> str:
        return f"{self.name} ({self.asset_type})"

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