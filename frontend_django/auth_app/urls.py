from django.urls import path
from . import views

app_name = 'auth_app'

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('generate-password/', views.generate_password, name='generate_password'),
    path('generate-2fa/', views.generate_2fa, name='generate_2fa'),
    path('logout/', views.logout_view, name='logout'),
] 