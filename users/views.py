from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import UserProfile
from .serializers import UserProfileSerializer

class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow users to edit their own profile.
    """
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj == request.user.userprofile

class UserProfileViewSet(viewsets.ModelViewSet):
    queryset = UserProfile.objects.all()
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]
    
    def get_queryset(self):
        user = self.request.user.userprofile
        if user.is_instructor:
            # Instructors can see their own profile and their clients' profiles
            return UserProfile.objects.filter(
                client_relationships__instructor=user
            ).distinct() | UserProfile.objects.filter(id=user.id)
        else:
            # Clients can only see their own profile and their instructor's profile
            return UserProfile.objects.filter(
                id__in=[user.id, user.client_relationships.first().instructor.id if user.client_relationships.exists() else None]
            ).exclude(id=None)
    
    @action(detail=False, methods=['get'])
    def me(self, request):
        """Get the current user's profile."""
        serializer = self.get_serializer(request.user.userprofile)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def update_role(self, request, pk=None):
        """Update a user's role (instructor only)."""
        if not request.user.userprofile.is_instructor:
            return Response(
                {'error': 'Only instructors can update roles'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        profile = self.get_object()
        new_role = request.data.get('role')
        
        if new_role not in ['client', 'instructor']:
            return Response(
                {'error': 'Invalid role. Must be either "client" or "instructor"'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        profile.role = new_role
        profile.save()
        return Response(self.get_serializer(profile).data) 