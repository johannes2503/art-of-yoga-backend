from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Q, Sum, Avg, Count, Max
from .models import (
    Routine, Exercise, BreathingExercise, MeditationSession,
    CombinedRoutine, MediaAsset, ExerciseProgress, Achievement,
    ClientAchievement, ClientInstructorRelationship, UploadProgress
)
from .serializers import (
    RoutineSerializer, ExerciseSerializer, BreathingExerciseSerializer,
    MeditationSessionSerializer, CombinedRoutineSerializer, MediaAssetSerializer,
    ExerciseProgressSerializer, AchievementSerializer, ClientAchievementSerializer,
    ClientInstructorRelationshipSerializer, UploadProgressSerializer
)
from users.models import UserProfile
from users.permissions import IsInstructorOrAdmin
from django.utils import timezone
from datetime import timedelta
import json
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.core.exceptions import ValidationError
from django.conf import settings
import os
from supabase import create_client

class IsInstructorOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow instructors to create/edit routines.
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_authenticated and request.user.role in ['instructor', 'admin']

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.instructor == request.user

class RoutineViewSet(viewsets.ModelViewSet):
    queryset = Routine.objects.all()
    permission_classes = [IsInstructorOrReadOnly]
    
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return RoutineCreateSerializer
        return RoutineSerializer
    
    def perform_create(self, serializer):
        serializer.save(instructor=self.request.user.userprofile)
    
    def get_queryset(self):
        queryset = Routine.objects.all()
        user = self.request.user
        
        if not user.is_authenticated:
            return queryset.filter(is_active=True)
        
        user_profile = user.userprofile
        
        if user_profile.is_instructor:
            # Instructors see their own routines
            return queryset.filter(instructor=user_profile)
        else:
            # Clients see routines assigned to them
            client_relationships = ClientInstructorRelationship.objects.filter(client=user_profile)
            return queryset.filter(
                assigned_clients__in=client_relationships,
                is_active=True
            ).distinct()

class ClientInstructorRelationshipViewSet(viewsets.ModelViewSet):
    serializer_class = ClientInstructorRelationshipSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user_profile = self.request.user.userprofile
        
        if user_profile.is_instructor:
            return ClientInstructorRelationship.objects.filter(instructor=user_profile)
        else:
            return ClientInstructorRelationship.objects.filter(client=user_profile)
    
    @action(detail=True, methods=['post'])
    def assign_routine(self, request, pk=None):
        relationship = self.get_object()
        routine_id = request.data.get('routine_id')
        
        if not routine_id:
            return Response(
                {'error': 'routine_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        routine = get_object_or_404(Routine, id=routine_id)
        
        # Verify the routine belongs to the instructor
        if routine.instructor != relationship.instructor:
            return Response(
                {'error': 'Routine does not belong to the instructor'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        relationship.routines.add(routine)
        return Response(self.get_serializer(relationship).data)
    
    @action(detail=True, methods=['post'])
    def remove_routine(self, request, pk=None):
        relationship = self.get_object()
        routine_id = request.data.get('routine_id')
        
        if not routine_id:
            return Response(
                {'error': 'routine_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        routine = get_object_or_404(Routine, id=routine_id)
        relationship.routines.remove(routine)
        return Response(self.get_serializer(relationship).data)

class MediaAssetViewSet(viewsets.ModelViewSet):
    """ViewSet for managing media assets."""
    serializer_class = MediaAssetSerializer
    permission_classes = [IsInstructorOrAdmin]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    
    def get_queryset(self):
        return MediaAsset.objects.filter(instructor=self.request.user.userprofile)
    
    @action(detail=False, methods=['post'])
    def get_upload_policy(self, request):
        """Get a policy for direct-to-Supabase upload."""
        file_name = request.data.get('file_name')
        asset_type = request.data.get('asset_type')
        content_type = request.data.get('content_type')
        
        if not file_name or not asset_type:
            return Response(
                {'error': 'file_name and asset_type are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate asset type
        if asset_type not in dict(MediaAsset.ASSET_TYPES):
            return Response(
                {'error': f'Invalid asset type. Must be one of: {", ".join(dict(MediaAsset.ASSET_TYPES).keys())}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Generate upload policy
        storage = SupabaseStorage()
        policy = storage.generate_upload_policy(
            file_name=file_name,
            instructor_id=request.user.userprofile.id,
            asset_type=asset_type,
            content_type=content_type
        )
        
        # Create progress tracking
        progress = UploadProgress.create_for_direct_upload(
            policy=policy,
            instructor=request.user.userprofile
        )
        
        # Add progress ID to policy response
        policy['progress_id'] = str(progress.upload_id)
        
        return Response(policy)
    
    @action(detail=False, methods=['post'])
    def update_progress(self, request):
        """Update upload progress for direct uploads."""
        upload_id = request.data.get('upload_id')
        uploaded_size = request.data.get('uploaded_size')
        status = request.data.get('status')
        error_message = request.data.get('error_message')
        
        if not upload_id:
            return Response(
                {'error': 'upload_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            progress = UploadProgress.objects.get(
                upload_id=upload_id,
                instructor=request.user.userprofile
            )
        except UploadProgress.DoesNotExist:
            return Response(
                {'error': 'Upload progress not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Update progress
        progress.update_progress(
            uploaded_size=uploaded_size or progress.uploaded_size,
            status=status,
            error_message=error_message
        )
        
        return Response(UploadProgressSerializer(progress).data)
    
    @action(detail=False, methods=['get'])
    def get_progress(self, request):
        """Get upload progress status."""
        upload_id = request.query_params.get('upload_id')
        
        if not upload_id:
            return Response(
                {'error': 'upload_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            progress = UploadProgress.objects.get(
                upload_id=upload_id,
                instructor=request.user.userprofile
            )
        except UploadProgress.DoesNotExist:
            return Response(
                {'error': 'Upload progress not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        return Response(UploadProgressSerializer(progress).data)
    
    @action(detail=False, methods=['get'])
    def list_progress(self, request):
        """List all upload progress for the instructor."""
        status_filter = request.query_params.get('status')
        asset_type = request.query_params.get('asset_type')
        
        queryset = UploadProgress.objects.filter(
            instructor=request.user.userprofile
        )
        
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if asset_type:
            queryset = queryset.filter(asset_type=asset_type)
        
        serializer = UploadProgressSerializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def verify_upload(self, request):
        """Verify a direct upload and create a MediaAsset."""
        upload_id = request.data.get('upload_id')
        file_path = request.data.get('file_path')
        
        if not upload_id or not file_path:
            return Response(
                {'error': 'upload_id and file_path are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            progress = UploadProgress.objects.get(
                upload_id=upload_id,
                instructor=request.user.userprofile
            )
        except UploadProgress.DoesNotExist:
            return Response(
                {'error': 'Upload progress not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Update progress status
        progress.update_progress(
            status='verifying',
            uploaded_size=progress.total_size
        )
        
        try:
            # Verify upload
            storage = SupabaseStorage()
            success, metadata = storage.verify_upload(
                upload_id=upload_id,
                file_path=file_path,
                instructor_id=request.user.userprofile.id
            )
            
            if not success:
                progress.update_progress(
                    status='failed',
                    error_message='Upload verification failed'
                )
                return Response(
                    {'error': 'Upload verification failed'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Create MediaAsset
            asset = MediaAsset.objects.create(
                name=os.path.splitext(os.path.basename(file_path))[0],
                asset_type=file_path.split('/')[1],  # Get type from path
                file_path=file_path,
                url=metadata['url'],
                thumbnail_url=metadata['thumbnail_url'],
                file_size=metadata.get('size', 0),
                instructor=request.user.userprofile
            )
            
            # Update progress status
            progress.update_progress(
                status='completed',
                file_path=file_path
            )
            
            return Response(MediaAssetSerializer(asset).data)
            
        except Exception as e:
            progress.update_progress(
                status='failed',
                error_message=str(e)
            )
            return Response(
                {'error': f'Error creating media asset: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def perform_create(self, serializer):
        """Handle file upload and create media asset."""
        # Check if this is a direct upload verification
        if self.action == 'verify_upload':
            return
        
        # Handle traditional file upload
        file_obj = self.request.FILES.get('file')
        if not file_obj:
            raise ValidationError('No file provided')
        
        # Validate file type
        content_type = file_obj.content_type
        asset_type = None
        for type_name, allowed_types in settings.MEDIA_ASSET_TYPES.items():
            if content_type in allowed_types:
                asset_type = type_name
                break
        
        if not asset_type:
            raise ValidationError(f'Unsupported file type: {content_type}')
        
        # Validate file size
        max_size = settings.MAX_FILE_SIZES.get(asset_type)
        if max_size and file_obj.size > max_size:
            raise ValidationError(
                f'File size exceeds maximum allowed size for {asset_type}'
            )
        
        # Create progress tracking
        progress = UploadProgress.create_for_traditional_upload(
            file_obj=file_obj,
            instructor=self.request.user.userprofile,
            asset_type=asset_type
        )
        
        try:
            # Read file data
            file_data = file_obj.read()
            
            # Update progress
            progress.update_progress(
                uploaded_size=len(file_data),
                status='uploading'
            )
            
            # Create media asset
            asset = MediaAsset.create_from_upload(
                file_data=file_data,
                file_name=file_obj.name,
                instructor=self.request.user.userprofile,
                asset_type=asset_type
            )
            
            # Update progress
            progress.update_progress(
                status='completed',
                file_path=asset.file_path
            )
            
            serializer.instance = asset
            
        except Exception as e:
            progress.update_progress(
                status='failed',
                error_message=str(e)
            )
            raise
    
    def perform_destroy(self, instance):
        """Delete media asset and its file from storage."""
        instance.delete()
    
    @action(detail=True, methods=['post'])
    def refresh_url(self, request, pk=None):
        """Refresh the signed URL for a media asset."""
        asset = self.get_object()
        asset.refresh_url()
        return Response(self.get_serializer(asset).data)

class BreathingExerciseViewSet(viewsets.ModelViewSet):
    """ViewSet for managing breathing exercises."""
    serializer_class = BreathingExerciseSerializer
    permission_classes = [IsInstructorOrReadOnly]
    
    def get_queryset(self):
        user = self.request.user
        if user.role in ['instructor', 'admin']:
            return BreathingExercise.objects.filter(instructor=user)
        else:
            # Clients see exercises from their instructors
            relationships = ClientInstructorRelationship.objects.filter(client=user)
            instructor_ids = relationships.values_list('instructor_id', flat=True)
            return BreathingExercise.objects.filter(
                instructor_id__in=instructor_ids,
                is_active=True
            )
    
    def perform_create(self, serializer):
        serializer.save(instructor=self.request.user)
    
    @action(detail=True, methods=['post'])
    def add_media(self, request, pk=None):
        exercise = self.get_object()
        media_id = request.data.get('media_id')
        
        if not media_id:
            return Response(
                {'error': 'media_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        media = get_object_or_404(MediaAsset, id=media_id, instructor=request.user)
        exercise.media_assets.add(media)
        return Response(self.get_serializer(exercise).data)

class MeditationSessionViewSet(viewsets.ModelViewSet):
    """ViewSet for managing meditation sessions."""
    serializer_class = MeditationSessionSerializer
    permission_classes = [IsInstructorOrReadOnly]
    
    def get_queryset(self):
        user = self.request.user
        if user.role in ['instructor', 'admin']:
            return MeditationSession.objects.filter(instructor=user)
        else:
            # Clients see sessions from their instructors
            relationships = ClientInstructorRelationship.objects.filter(client=user)
            instructor_ids = relationships.values_list('instructor_id', flat=True)
            return MeditationSession.objects.filter(
                instructor_id__in=instructor_ids,
                is_active=True
            )
    
    def perform_create(self, serializer):
        serializer.save(instructor=self.request.user)
    
    @action(detail=True, methods=['post'])
    def add_audio(self, request, pk=None):
        session = self.get_object()
        media_id = request.data.get('media_id')
        
        if not media_id:
            return Response(
                {'error': 'media_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        media = get_object_or_404(
            MediaAsset,
            id=media_id,
            instructor=request.user,
            asset_type='audio'
        )
        session.audio_assets.add(media)
        return Response(self.get_serializer(session).data)

class CombinedRoutineViewSet(viewsets.ModelViewSet):
    """ViewSet for managing combined routines."""
    serializer_class = CombinedRoutineSerializer
    permission_classes = [IsInstructorOrReadOnly]
    
    def get_queryset(self):
        user = self.request.user
        if user.role in ['instructor', 'admin']:
            return CombinedRoutine.objects.filter(instructor=user)
        else:
            # Clients see routines from their instructors
            relationships = ClientInstructorRelationship.objects.filter(client=user)
            instructor_ids = relationships.values_list('instructor_id', flat=True)
            return CombinedRoutine.objects.filter(
                instructor_id__in=instructor_ids,
                is_active=True
            )
    
    def perform_create(self, serializer):
        serializer.save(instructor=self.request.user)
    
    @action(detail=True, methods=['post'])
    def add_exercise(self, request, pk=None):
        routine = self.get_object()
        exercise_type = request.data.get('exercise_type')
        exercise_id = request.data.get('exercise_id')
        
        if not exercise_type or not exercise_id:
            return Response(
                {'error': 'exercise_type and exercise_id are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if exercise_type == 'routine':
            exercise = get_object_or_404(Routine, id=exercise_id, instructor=request.user)
            routine.routines.add(exercise)
        elif exercise_type == 'breathing':
            exercise = get_object_or_404(BreathingExercise, id=exercise_id, instructor=request.user)
            routine.breathing_exercises.add(exercise)
        elif exercise_type == 'meditation':
            exercise = get_object_or_404(MeditationSession, id=exercise_id, instructor=request.user)
            routine.meditation_sessions.add(exercise)
        else:
            return Response(
                {'error': 'Invalid exercise type'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return Response(self.get_serializer(routine).data)

class ExerciseProgressViewSet(viewsets.ModelViewSet):
    """ViewSet for tracking exercise progress."""
    serializer_class = ExerciseProgressSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.role in ['instructor', 'admin']:
            # Instructors see progress of their clients
            relationships = ClientInstructorRelationship.objects.filter(instructor=user)
            client_ids = relationships.values_list('client_id', flat=True)
            return ExerciseProgress.objects.filter(client_id__in=client_ids)
        else:
            # Clients see their own progress
            return ExerciseProgress.objects.filter(client=user)
    
    def perform_create(self, serializer):
        serializer.save(client=self.request.user)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get exercise statistics for the user."""
        user = request.user
        if user.role in ['instructor', 'admin']:
            # Get stats for instructor's clients
            relationships = ClientInstructorRelationship.objects.filter(instructor=user)
            client_ids = relationships.values_list('client_id', flat=True)
            progress = ExerciseProgress.objects.filter(client_id__in=client_ids)
        else:
            # Get stats for the client
            progress = ExerciseProgress.objects.filter(client=user)
        
        stats = {
            'total_exercises': progress.count(),
            'total_duration': progress.aggregate(total=models.Sum('duration_seconds'))['total'] or 0,
            'average_difficulty': progress.exclude(difficulty_rating__isnull=True)
                .aggregate(avg=models.Avg('difficulty_rating'))['avg'] or 0,
            'by_type': {
                'exercise': progress.filter(exercise__isnull=False).count(),
                'breathing': progress.filter(breathing_exercise__isnull=False).count(),
                'meditation': progress.filter(meditation_session__isnull=False).count(),
            }
        }
        
        return Response(stats)

class AchievementViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing achievements."""
    serializer_class = AchievementSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = Achievement.objects.filter(is_active=True)

class ClientAchievementViewSet(viewsets.ModelViewSet):
    """ViewSet for managing client achievements."""
    serializer_class = ClientAchievementSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.role in ['instructor', 'admin']:
            # Instructors see achievements of their clients
            relationships = ClientInstructorRelationship.objects.filter(instructor=user)
            client_ids = relationships.values_list('client_id', flat=True)
            return ClientAchievement.objects.filter(client_id__in=client_ids)
        else:
            # Clients see their own achievements
            return ClientAchievement.objects.filter(client=user)
    
    @action(detail=False, methods=['get'])
    def check_achievements(self, request):
        """Check and award new achievements for the client."""
        user = request.user
        if user.role not in ['client']:
            return Response(
                {'error': 'Only clients can check achievements'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get client's progress
        progress = ExerciseProgress.objects.filter(client=user)
        
        # Get all active achievements
        achievements = Achievement.objects.filter(is_active=True)
        
        # Check each achievement's criteria
        new_achievements = []
        for achievement in achievements:
            if not ClientAchievement.objects.filter(client=user, achievement=achievement).exists():
                try:
                    criteria = json.loads(achievement.criteria) if isinstance(achievement.criteria, str) else achievement.criteria
                    if self._check_achievement_criteria(progress, criteria):
                        # Award achievement
                        progress_data = self._get_progress_data(progress, criteria)
                        client_achievement = ClientAchievement.objects.create(
                            client=user,
                            achievement=achievement,
                            progress_data=progress_data
                        )
                        new_achievements.append(ClientAchievementSerializer(client_achievement).data)
                except (json.JSONDecodeError, TypeError) as e:
                    # Log error and continue with next achievement
                    print(f"Error processing achievement {achievement.id}: {str(e)}")
                    continue
        
        return Response({
            'new_achievements': new_achievements,
            'total_achievements': ClientAchievement.objects.filter(client=user).count()
        })
    
    def _check_achievement_criteria(self, progress, criteria):
        """Check if progress meets achievement criteria."""
        achievement_type = criteria.get('type')
        
        if not achievement_type:
            return False
            
        check_methods = {
            'exercise_count': self._check_exercise_count,
            'duration': self._check_duration,
            'consistency': self._check_consistency,
            'difficulty': self._check_difficulty,
            'combined_routine': self._check_combined_routine
        }
        
        check_method = check_methods.get(achievement_type)
        if not check_method:
            return False
            
        return check_method(progress, criteria)
    
    def _check_exercise_count(self, progress, criteria):
        """Check if client has completed required number of exercises."""
        required_count = criteria.get('required_count', 0)
        exercise_type = criteria.get('exercise_type', 'all')
        
        if exercise_type == 'all':
            count = progress.count()
        elif exercise_type == 'exercise':
            count = progress.filter(exercise__isnull=False).count()
        elif exercise_type == 'breathing':
            count = progress.filter(breathing_exercise__isnull=False).count()
        elif exercise_type == 'meditation':
            count = progress.filter(meditation_session__isnull=False).count()
        else:
            return False
            
        return count >= required_count
    
    def _check_duration(self, progress, criteria):
        """Check if client has accumulated required duration."""
        required_duration = criteria.get('required_duration', 0)  # in seconds
        time_period = criteria.get('time_period')  # e.g., 'day', 'week', 'month', 'all'
        
        if time_period:
            now = timezone.now()
            if time_period == 'day':
                start_time = now - timedelta(days=1)
            elif time_period == 'week':
                start_time = now - timedelta(weeks=1)
            elif time_period == 'month':
                start_time = now - timedelta(days=30)
            else:
                return False
            progress = progress.filter(completed_at__gte=start_time)
        
        total_duration = progress.aggregate(
            total=Sum('duration_seconds')
        )['total'] or 0
        
        return total_duration >= required_duration
    
    def _check_consistency(self, progress, criteria):
        """Check if client has maintained consistent practice."""
        required_days = criteria.get('required_days', 0)
        consecutive = criteria.get('consecutive', False)
        
        if not progress.exists():
            return False
            
        # Get all unique dates with completed exercises
        dates = progress.dates('completed_at', 'day')
        
        if consecutive:
            # Check for consecutive days
            dates_list = sorted([d.date() for d in dates])
            if not dates_list:
                return False
                
            current_streak = 1
            max_streak = 1
            
            for i in range(1, len(dates_list)):
                if (dates_list[i] - dates_list[i-1]).days == 1:
                    current_streak += 1
                    max_streak = max(max_streak, current_streak)
                else:
                    current_streak = 1
                    
            return max_streak >= required_days
        else:
            # Check for total days
            return len(dates) >= required_days
    
    def _check_difficulty(self, progress, criteria):
        """Check if client has completed exercises at required difficulty level."""
        required_difficulty = criteria.get('required_difficulty', 0)
        required_count = criteria.get('required_count', 1)
        
        return progress.filter(
            difficulty_rating__gte=required_difficulty
        ).count() >= required_count
    
    def _check_combined_routine(self, progress, criteria):
        """Check if client has completed required combined routines."""
        required_count = criteria.get('required_count', 0)
        routine_id = criteria.get('routine_id')
        
        if routine_id:
            # Check specific routine completion
            return progress.filter(
                combined_routine_id=routine_id
            ).count() >= required_count
        else:
            # Check any combined routine completion
            return progress.filter(
                combined_routine__isnull=False
            ).count() >= required_count
    
    def _get_progress_data(self, progress, criteria):
        """Get relevant progress data for achievement."""
        achievement_type = criteria.get('type')
        data = {
            'type': achievement_type,
            'criteria_met_at': timezone.now().isoformat()
        }
        
        if achievement_type == 'exercise_count':
            exercise_type = criteria.get('exercise_type', 'all')
            if exercise_type == 'all':
                data['total_count'] = progress.count()
            else:
                data['total_count'] = progress.filter(
                    **{f'{exercise_type}__isnull': False}
                ).count()
                
        elif achievement_type == 'duration':
            time_period = criteria.get('time_period')
            if time_period:
                now = timezone.now()
                if time_period == 'day':
                    start_time = now - timedelta(days=1)
                elif time_period == 'week':
                    start_time = now - timedelta(weeks=1)
                elif time_period == 'month':
                    start_time = now - timedelta(days=30)
                progress = progress.filter(completed_at__gte=start_time)
            
            data['total_duration'] = progress.aggregate(
                total=Sum('duration_seconds')
            )['total'] or 0
            
        elif achievement_type == 'consistency':
            dates = progress.dates('completed_at', 'day')
            data['total_days'] = len(dates)
            if criteria.get('consecutive'):
                dates_list = sorted([d.date() for d in dates])
                current_streak = 1
                max_streak = 1
                for i in range(1, len(dates_list)):
                    if (dates_list[i] - dates_list[i-1]).days == 1:
                        current_streak += 1
                        max_streak = max(max_streak, current_streak)
                    else:
                        current_streak = 1
                data['max_consecutive_days'] = max_streak
                
        elif achievement_type == 'difficulty':
            data['highest_difficulty'] = progress.aggregate(
                max_difficulty=Max('difficulty_rating')
            )['max_difficulty'] or 0
            data['difficulty_count'] = progress.filter(
                difficulty_rating__gte=criteria.get('required_difficulty', 0)
            ).count()
            
        elif achievement_type == 'combined_routine':
            routine_id = criteria.get('routine_id')
            if routine_id:
                data['routine_completions'] = progress.filter(
                    combined_routine_id=routine_id
                ).count()
            else:
                data['total_completions'] = progress.filter(
                    combined_routine__isnull=False
                ).count()
        
        return data 