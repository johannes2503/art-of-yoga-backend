from rest_framework import serializers
from .models import UserProfile

class UserProfileSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source='user.email', read_only=True)
    
    class Meta:
        model = UserProfile
        fields = ['id', 'email', 'is_instructor', 'supabase_id', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at', 'supabase_id'] 