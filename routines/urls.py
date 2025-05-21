from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'routines', views.RoutineViewSet, basename='routine')
router.register(r'relationships', views.ClientInstructorRelationshipViewSet, basename='relationship')
router.register(r'media', views.MediaAssetViewSet, basename='media')
router.register(r'breathing-exercises', views.BreathingExerciseViewSet, basename='breathing-exercise')
router.register(r'meditation-sessions', views.MeditationSessionViewSet, basename='meditation-session')
router.register(r'combined-routines', views.CombinedRoutineViewSet, basename='combined-routine')
router.register(r'progress', views.ExerciseProgressViewSet, basename='progress')
router.register(r'achievements', views.AchievementViewSet, basename='achievement')
router.register(r'client-achievements', views.ClientAchievementViewSet, basename='client-achievement')

urlpatterns = [
    path('', include(router.urls)),
] 