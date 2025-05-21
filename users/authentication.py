from rest_framework.authentication import BaseAuthentication
from rest_framework import exceptions
from django.conf import settings
from users.models import UserProfile
from typing import Optional, Tuple
import requests
import jwt

class SupabaseJWTAuthentication(BaseAuthentication):
    """Authenticate requests using Supabase JWT tokens."""
    def authenticate(self, request) -> Optional[Tuple[UserProfile, None]]:
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return None
        token = auth_header.split(" ", 1)[1]
        try:
            # Get JWKS from Supabase
            jwks_url = f"{settings.SUPABASE_URL}/auth/v1/keys"
            jwks = requests.get(jwks_url).json()["keys"]
            unverified_header = jwt.get_unverified_header(token)
            key = next((k for k in jwks if k["kid"] == unverified_header["kid"]), None)
            if not key:
                raise exceptions.AuthenticationFailed("Invalid token header.")
            public_key = jwt.algorithms.RSAAlgorithm.from_jwk(key)
            payload = jwt.decode(
                token,
                public_key,
                algorithms=[unverified_header["alg"]],
                audience=None,  # Optionally set audience
                options={"verify_aud": False},
            )
        except Exception as e:
            raise exceptions.AuthenticationFailed(f"Invalid Supabase JWT: {str(e)}")
        # Get or create user profile
        supabase_id = payload.get("sub")
        email = payload.get("email")
        if not supabase_id or not email:
            raise exceptions.AuthenticationFailed("Invalid token payload.")
        user, _ = UserProfile.objects.get_or_create(
            supabase_id=supabase_id,
            defaults={"email": email}
        )
        return (user, None) 