from rest_framework import serializers
from .models import (
    Routine, Exercise, ClientInstructorRelationship, MediaAsset, BreathingExercise, MeditationSession, CombinedRoutine, ExerciseProgress, Achievement, ClientAchievement
)
from users.serializers import UserProfileSerializer

class MediaAssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = MediaAsset
        fields = [
            'id', 'name', 'asset_type', 'url', 'thumbnail_url', 'file_size', 'duration_seconds',
            'instructor', 'created_at', 'updated_at', 'is_active'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'instructor']

class ExerciseSerializer(serializers.ModelSerializer):
    media_assets = MediaAssetSerializer(many=True, read_only=True)
    class Meta:
        model = Exercise
        fields = ['id', 'name', 'instructions', 'media_assets', 'order']
        read_only_fields = ['id']

class BreathingExerciseSerializer(serializers.ModelSerializer):
    instructor = UserProfileSerializer(read_only=True)
    media_assets = MediaAssetSerializer(many=True, read_only=True)
    class Meta:
        model = BreathingExercise
        fields = [
            'id', 'name', 'description', 'instructor', 'pattern', 'timer_seconds',
            'media_assets', 'created_at', 'updated_at', 'is_active'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'instructor']

class MeditationSessionSerializer(serializers.ModelSerializer):
    instructor = UserProfileSerializer(read_only=True)
    audio_assets = MediaAssetSerializer(many=True, read_only=True)
    media_assets = MediaAssetSerializer(many=True, read_only=True)
    class Meta:
        model = MeditationSession
        fields = [
            'id', 'name', 'description', 'instructor', 'audio_assets', 'script',
            'duration_seconds', 'media_assets', 'created_at', 'updated_at', 'is_active'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'instructor']

class RoutineSerializer(serializers.ModelSerializer):
    exercises = ExerciseSerializer(many=True, read_only=True)
    instructor = UserProfileSerializer(read_only=True)
    
    class Meta:
        model = Routine
        fields = ['id', 'name', 'description', 'instructor', 'exercises', 
                 'created_at', 'updated_at', 'is_active']
        read_only_fields = ['id', 'created_at', 'updated_at', 'instructor']

class CombinedRoutineSerializer(serializers.ModelSerializer):
    instructor = UserProfileSerializer(read_only=True)
    routines = RoutineSerializer(many=True, read_only=True)
    breathing_exercises = BreathingExerciseSerializer(many=True, read_only=True)
    meditation_sessions = MeditationSessionSerializer(many=True, read_only=True)
    class Meta:
        model = CombinedRoutine
        fields = [
            'id', 'name', 'description', 'instructor', 'routines', 'breathing_exercises',
            'meditation_sessions', 'transition_notes', 'created_at', 'updated_at', 'is_active'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'instructor']

class ClientInstructorRelationshipSerializer(serializers.ModelSerializer):
    client = UserProfileSerializer(read_only=True)
    instructor = UserProfileSerializer(read_only=True)
    routines = RoutineSerializer(many=True, read_only=True)
    
    class Meta:
        model = ClientInstructorRelationship
        fields = ['id', 'client', 'instructor', 'routines', 'created_at']
        read_only_fields = ['id', 'created_at']

class RoutineCreateSerializer(serializers.ModelSerializer):
    exercises = ExerciseSerializer(many=True, required=False)
    
    class Meta:
        model = Routine
        fields = ['id', 'name', 'description', 'exercises', 'is_active']
        read_only_fields = ['id']

    def create(self, validated_data):
        exercises_data = validated_data.pop('exercises', [])
        routine = Routine.objects.create(**validated_data)
        
        for exercise_data in exercises_data:
            Exercise.objects.create(routine=routine, **exercise_data)
        
        return routine

    def update(self, instance, validated_data):
        exercises_data = validated_data.pop('exercises', None)
        
        # Update routine fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update exercises if provided
        if exercises_data is not None:
            # Delete existing exercises
            instance.exercises.all().delete()
            # Create new exercises
            for exercise_data in exercises_data:
                Exercise.objects.create(routine=instance, **exercise_data)
        
        return instance

class ExerciseProgressSerializer(serializers.ModelSerializer):
    client = UserProfileSerializer(read_only=True)
    exercise = ExerciseSerializer(read_only=True)
    breathing_exercise = BreathingExerciseSerializer(read_only=True)
    meditation_session = MeditationSessionSerializer(read_only=True)
    class Meta:
        model = ExerciseProgress
        fields = [
            'id', 'client', 'exercise', 'breathing_exercise', 'meditation_session',
            'completed_at', 'duration_seconds', 'notes', 'difficulty_rating', 'feedback'
        ]
        read_only_fields = ['id', 'completed_at', 'client']

class AchievementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Achievement
        fields = [
            'id', 'name', 'description', 'achievement_type', 'icon_url', 'criteria', 'created_at', 'is_active'
        ]
        read_only_fields = ['id', 'created_at']

class ClientAchievementSerializer(serializers.ModelSerializer):
    client = UserProfileSerializer(read_only=True)
    achievement = AchievementSerializer(read_only=True)
    class Meta:
        model = ClientAchievement
        fields = [
            'id', 'client', 'achievement', 'earned_at', 'progress_data'
        ]
        read_only_fields = ['id', 'earned_at', 'client', 'achievement'] 