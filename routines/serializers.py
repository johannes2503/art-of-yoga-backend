from rest_framework import serializers
from .models import (
    Routine, Exercise, ClientInstructorRelationship, MediaAsset, BreathingExercise, MeditationSession, CombinedRoutine, ExerciseProgress, Achievement, ClientAchievement, UploadProgress
)
from users.serializers import UserProfileSerializer

class MediaAssetSerializer(serializers.ModelSerializer):
    """Serializer for media assets."""
    class Meta:
        model = MediaAsset
        fields = ['id', 'name', 'asset_type', 'url', 'thumbnail_url', 
                 'file_size', 'duration_seconds', 'created_at', 'is_active']
        read_only_fields = ['id', 'created_at']

class ExerciseSerializer(serializers.ModelSerializer):
    """Serializer for basic exercises."""
    media_assets = MediaAssetSerializer(many=True, read_only=True)
    
    class Meta:
        model = Exercise
        fields = ['id', 'routine', 'name', 'instructions', 'media_assets', 'order']
        read_only_fields = ['id']

class BreathingExerciseSerializer(serializers.ModelSerializer):
    """Serializer for breathing exercises."""
    media_assets = MediaAssetSerializer(many=True, read_only=True)
    instructor_email = serializers.EmailField(source='instructor.email', read_only=True)
    
    class Meta:
        model = BreathingExercise
        fields = ['id', 'name', 'description', 'instructor', 'instructor_email',
                 'pattern', 'timer_seconds', 'media_assets', 'created_at',
                 'updated_at', 'is_active']
        read_only_fields = ['id', 'created_at', 'updated_at', 'instructor']

class MeditationSessionSerializer(serializers.ModelSerializer):
    """Serializer for meditation sessions."""
    audio_assets = MediaAssetSerializer(many=True, read_only=True)
    media_assets = MediaAssetSerializer(many=True, read_only=True)
    instructor_email = serializers.EmailField(source='instructor.email', read_only=True)
    
    class Meta:
        model = MeditationSession
        fields = ['id', 'name', 'description', 'instructor', 'instructor_email',
                 'audio_assets', 'script', 'duration_seconds', 'media_assets',
                 'created_at', 'updated_at', 'is_active']
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
    """Serializer for combined routines."""
    routines = ExerciseSerializer(many=True, read_only=True)
    breathing_exercises = BreathingExerciseSerializer(many=True, read_only=True)
    meditation_sessions = MeditationSessionSerializer(many=True, read_only=True)
    instructor_email = serializers.EmailField(source='instructor.email', read_only=True)
    
    class Meta:
        model = CombinedRoutine
        fields = ['id', 'name', 'description', 'instructor', 'instructor_email',
                 'routines', 'breathing_exercises', 'meditation_sessions',
                 'transition_notes', 'created_at', 'updated_at', 'is_active']
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
    """Serializer for exercise progress tracking."""
    exercise_name = serializers.SerializerMethodField()
    exercise_type = serializers.SerializerMethodField()
    
    class Meta:
        model = ExerciseProgress
        fields = ['id', 'client', 'exercise', 'breathing_exercise', 'meditation_session',
                 'exercise_name', 'exercise_type', 'completed_at', 'duration_seconds',
                 'notes', 'difficulty_rating', 'feedback']
        read_only_fields = ['id', 'completed_at']
    
    def get_exercise_name(self, obj):
        if obj.exercise:
            return obj.exercise.name
        elif obj.breathing_exercise:
            return obj.breathing_exercise.name
        elif obj.meditation_session:
            return obj.meditation_session.name
        return None
    
    def get_exercise_type(self, obj):
        if obj.exercise:
            return 'exercise'
        elif obj.breathing_exercise:
            return 'breathing'
        elif obj.meditation_session:
            return 'meditation'
        return None

class AchievementSerializer(serializers.ModelSerializer):
    """Serializer for achievements."""
    class Meta:
        model = Achievement
        fields = ['id', 'name', 'description', 'achievement_type', 'icon_url',
                 'criteria', 'created_at', 'is_active']
        read_only_fields = ['id', 'created_at']

class ClientAchievementSerializer(serializers.ModelSerializer):
    """Serializer for client achievements."""
    achievement_details = AchievementSerializer(source='achievement', read_only=True)
    
    class Meta:
        model = ClientAchievement
        fields = ['id', 'client', 'achievement', 'achievement_details',
                 'earned_at', 'progress_data']
        read_only_fields = ['id', 'earned_at']

class UploadProgressSerializer(serializers.ModelSerializer):
    """Serializer for upload progress tracking."""
    
    progress_percentage = serializers.IntegerField(read_only=True)
    upload_id = serializers.UUIDField(read_only=True)
    instructor_email = serializers.EmailField(source='instructor.user.email', read_only=True)
    
    class Meta:
        model = UploadProgress
        fields = [
            'upload_id', 'instructor_email', 'file_name', 'file_path',
            'asset_type', 'total_size', 'uploaded_size', 'progress_percentage',
            'status', 'error_message', 'metadata', 'created_at', 'updated_at',
            'completed_at'
        ]
        read_only_fields = [
            'upload_id', 'instructor_email', 'file_path', 'total_size',
            'uploaded_size', 'progress_percentage', 'status', 'error_message',
            'metadata', 'created_at', 'updated_at', 'completed_at'
        ] 