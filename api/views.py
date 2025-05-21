from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from users.models import UserProfile
from typing import Any

class AuthTestView(APIView):
    """A simple view to test Supabase JWT authentication."""
    permission_classes = [IsAuthenticated]

    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        user: UserProfile = request.user
        return Response({
            "message": "Authenticated!",
            "user": {
                "email": user.email,
                "role": user.role,
                "supabase_id": str(user.supabase_id),
            }
        }) 