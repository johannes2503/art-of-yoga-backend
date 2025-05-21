from rest_framework import serializers
from .models import UserProfile
from django.core.validators import MinLengthValidator

class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration."""
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[MinLengthValidator(8)],
        style={'input_type': 'password'}
    )
    confirm_password = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'}
    )
    
    class Meta:
        model = UserProfile
        fields = ['email', 'password', 'confirm_password', 'full_name', 'role']
        extra_kwargs = {
            'email': {'required': True},
            'full_name': {'required': True},
            'role': {'required': True}
        }
    
    def validate(self, data):
        """Validate that passwords match and role is valid."""
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError("Passwords do not match.")
        
        if data['role'] not in dict(UserProfile.ROLE_CHOICES):
            raise serializers.ValidationError("Invalid role selected.")
        
        return data

class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for user profile management."""
    email = serializers.EmailField(source='user.email', read_only=True)
    
    class Meta:
        model = UserProfile
        fields = ['id', 'email', 'role', 'full_name', 'created_at', 'updated_at']
        read_only_fields = ['id', 'email', 'created_at', 'updated_at', 'supabase_id']

class UserProfileUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating user profile."""
    class Meta:
        model = UserProfile
        fields = ['full_name']
        extra_kwargs = {
            'full_name': {'required': False}
        } 