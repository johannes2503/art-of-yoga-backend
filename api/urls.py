from django.urls import path, include
from .views import AuthTestView

urlpatterns = [
    path("auth-test/", AuthTestView.as_view(), name="auth-test"),
    path("routines/", include("routines.urls")),
    path("users/", include("users.urls")),
] 