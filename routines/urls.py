from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'routines', views.RoutineViewSet, basename='routine')
router.register(r'relationships', views.ClientInstructorRelationshipViewSet, basename='relationship')
router.register(r'exercises', views.ExerciseViewSet, basename='exercise')

urlpatterns = [
    path('', include(router.urls)),
] 