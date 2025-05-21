from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.conf import settings
from .models import UserProfile
from .serializers import (
    UserRegistrationSerializer,
    UserProfileSerializer,
    UserProfileUpdateSerializer
)
from .authentication import SupabaseJWTAuthentication
import requests

class IsAdminUser(permissions.BasePermission):
    """Custom permission to only allow admin users."""
    def has_permission(self, request, view):
        return request.user and request.user.role == 'admin'

class IsInstructorOrAdmin(permissions.BasePermission):
    """Custom permission to only allow instructors and admins."""
    def has_permission(self, request, view):
        return request.user and request.user.role in ['instructor', 'admin']

class UserViewSet(viewsets.ModelViewSet):
    """ViewSet for user registration and profile management."""
    authentication_classes = [SupabaseJWTAuthentication]
    queryset = UserProfile.objects.all()
    
    def get_permissions(self):
        """Set permissions based on action."""
        if self.action == 'create':
            permission_classes = [permissions.AllowAny]
        elif self.action in ['update', 'partial_update', 'destroy']:
            permission_classes = [IsAdminUser]
        else:
            permission_classes = [permissions.IsAuthenticated]
        return [permission() for permission in permission_classes]
    
    def get_serializer_class(self):
        """Return appropriate serializer class."""
        if self.action == 'create':
            return UserRegistrationSerializer
        elif self.action in ['update', 'partial_update']:
            return UserProfileUpdateSerializer
        return UserProfileSerializer
    
    def create(self, request, *args, **kwargs):
        """Handle user registration."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Create user in Supabase
        supabase_data = {
            'email': serializer.validated_data['email'],
            'password': serializer.validated_data['password'],
            'user_metadata': {
                'full_name': serializer.validated_data['full_name'],
                'role': serializer.validated_data['role']
            }
        }
        
        try:
            response = requests.post(
                f"{settings.SUPABASE_URL}/auth/v1/signup",
                json=supabase_data,
                headers={'apikey': settings.SUPABASE_KEY}
            )
            response.raise_for_status()
            supabase_user = response.json()
            
            # Create user profile in Django
            user_profile = UserProfile.objects.create(
                supabase_id=supabase_user['id'],
                email=serializer.validated_data['email'],
                full_name=serializer.validated_data['full_name'],
                role=serializer.validated_data['role']
            )
            
            return Response(
                UserProfileSerializer(user_profile).data,
                status=status.HTTP_201_CREATED
            )
            
        except requests.exceptions.RequestException as e:
            return Response(
                {'error': f'Failed to create user in Supabase: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['get'])
    def me(self, request):
        """Get current user's profile."""
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def change_password(self, request):
        """Change user's password."""
        if not request.user.is_authenticated:
            return Response(
                {'error': 'Authentication required'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        old_password = request.data.get('old_password')
        new_password = request.data.get('new_password')
        
        if not old_password or not new_password:
            return Response(
                {'error': 'Both old and new passwords are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Update password in Supabase
            response = requests.post(
                f"{settings.SUPABASE_URL}/auth/v1/user/password",
                json={
                    'old_password': old_password,
                    'new_password': new_password
                },
                headers={
                    'apikey': settings.SUPABASE_KEY,
                    'Authorization': f"Bearer {request.auth}"
                }
            )
            response.raise_for_status()
            return Response({'message': 'Password updated successfully'})
            
        except requests.exceptions.RequestException as e:
            return Response(
                {'error': f'Failed to update password: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            ) 