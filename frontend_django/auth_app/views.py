import json
import requests
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import jwt

def home(request):
    """Page d'accueil"""
    return render(request, 'auth_app/home.html')

def login_view(request):
    """Vue de connexion"""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        two_factor_code = request.POST.get('two_factor_code')
        recovery_code = request.POST.get('recovery_code')
        
        # Appel de la fonction serverless d'authentification
        auth_data = {
            'username': username,
            'password': password
        }
        
        if two_factor_code:
            auth_data['two_factor_code'] = two_factor_code
        elif recovery_code:
            auth_data['recovery_code'] = recovery_code
        
        try:
            response = requests.post(
                f"{settings.OPENFAAS_GATEWAY_URL}/function/authenticate-user",
                json=auth_data,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                data = response.json()
                # Stockage du token en session
                request.session['auth_token'] = data['token']
                request.session['user_data'] = data['user']
                messages.success(request, 'Connexion réussie !')
                return redirect('auth_app:dashboard')
            else:
                error_data = response.json()
                if error_data.get('requires_2fa'):
                    messages.warning(request, 'Code 2FA requis')
                    return render(request, 'auth_app/login.html', {
                        'username': username,
                        'requires_2fa': True
                    })
                else:
                    messages.error(request, error_data.get('error', 'Erreur de connexion'))
        except Exception as e:
            messages.error(request, f'Erreur de connexion: {str(e)}')
    
    return render(request, 'auth_app/login.html')

def register_view(request):
    """Vue d'inscription"""
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        # Ici, vous pourriez appeler une fonction serverless pour créer l'utilisateur
        # Pour l'instant, on simule la création
        messages.success(request, 'Compte créé avec succès ! Vous pouvez maintenant vous connecter.')
        return redirect('auth_app:login')
    
    return render(request, 'auth_app/register.html')

@login_required
def dashboard(request):
    """Tableau de bord utilisateur"""
    user_data = request.session.get('user_data', {})
    return render(request, 'auth_app/dashboard.html', {'user': user_data})

@csrf_exempt
def generate_password(request):
    """Génération de mot de passe via fonction serverless"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_id = request.session.get('user_data', {}).get('id')
            
            if user_id:
                data['user_id'] = user_id
            
            response = requests.post(
                f"{settings.OPENFAAS_GATEWAY_URL}/function/generate-password",
                json=data,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                return JsonResponse(response.json())
            else:
                return JsonResponse(response.json(), status=response.status_code)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Méthode non autorisée'}, status=405)

@csrf_exempt
def generate_2fa(request):
    """Génération de 2FA via fonction serverless"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_data = request.session.get('user_data', {})
            
            data['user_id'] = user_data.get('id')
            data['user_email'] = user_data.get('email')
            
            response = requests.post(
                f"{settings.OPENFAAS_GATEWAY_URL}/function/generate-2fa",
                json=data,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                return JsonResponse(response.json())
            else:
                return JsonResponse(response.json(), status=response.status_code)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Méthode non autorisée'}, status=405)

def logout_view(request):
    """Déconnexion"""
    request.session.flush()
    messages.success(request, 'Déconnexion réussie !')
    return redirect('auth_app:home') 