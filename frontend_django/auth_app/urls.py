from django.urls import path
from . import views

app_name = 'auth_app'

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('password-generator/', views.password_generator_view, name='password_generator'),
    path('two-factor/', views.two_factor_view, name='two_factor'),
    path('generate-password/', views.generate_password, name='generate_password'),
    path('generate-2fa/', views.generate_2fa, name='generate_2fa'),
    path('verify-2fa/', views.verify_2fa, name='verify_2fa'),
    path('get-recovery-codes/', views.get_recovery_codes, name='get_recovery_codes'),
    path('disable-2fa/', views.disable_2fa, name='disable_2fa'),
    path('logout/', views.logout_view, name='logout'),
] 