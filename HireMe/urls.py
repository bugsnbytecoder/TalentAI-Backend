from rest_framework import routers
from django.urls import path, include
from .views import DeveloperViewSet

router = routers.DefaultRouter()
router.register(r'developers', DeveloperViewSet, basename='developers')

urlpatterns = [
    path('', include(router.urls)),  
]