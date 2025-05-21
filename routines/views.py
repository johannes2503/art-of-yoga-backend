from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import Routine, Exercise, ClientInstructorRelationship
from .serializers import (
    RoutineSerializer, RoutineCreateSerializer,
    ExerciseSerializer, ClientInstructorRelationshipSerializer
)
from users.models import UserProfile

class IsInstructorOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow instructors to create/edit routines.
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_authenticated and request.user.userprofile.is_instructor

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.instructor == request.user.userprofile

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

class ExerciseViewSet(viewsets.ModelViewSet):
    queryset = Exercise.objects.all()
    serializer_class = ExerciseSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        queryset = Exercise.objects.all()
        user = self.request.user.userprofile
        
        if user.is_instructor:
            # Instructors see exercises they've created
            return queryset.filter(created_by=user)
        else:
            # Clients see exercises from routines assigned to them
            client_relationships = ClientInstructorRelationship.objects.filter(client=user)
            return queryset.filter(
                routine__assigned_clients__in=client_relationships,
                routine__is_active=True
            ).distinct()
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user.userprofile) 