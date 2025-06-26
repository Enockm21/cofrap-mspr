"""
URL configuration for mspr2_cofrap project.
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('auth_app.urls')),
] 