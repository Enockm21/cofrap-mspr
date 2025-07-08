import json
import requests
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import jwt
import random
import string
import qrcode
import base64
from io import BytesIO

# Données factices pour la démo
FAKE_USERS = {
    'admin': {
        'id': 1,
        'username': 'admin',
        'email': 'admin@mspr2.com',
        'password': 'admin123',
        'two_factor_enabled': True,
        'created_at': '2024-01-15',
        'last_login': '2024-01-20 14:30:00'
    },
    'user1': {
        'id': 2,
        'username': 'user1',
        'email': 'user1@example.com',
        'password': 'password123',
        'two_factor_enabled': False,
        'created_at': '2024-01-16',
        'last_login': '2024-01-20 12:15:00'
    }
}

FAKE_ACTIVITIES = [
    {
        'type': 'login',
        'description': 'Connexion réussie depuis Chrome sur Windows',
        'location': 'Paris, France',
        'timestamp': '2024-01-20 14:30:00',
        'icon': 'fas fa-sign-in-alt',
        'status': 'success'
    },
    {
        'type': 'password_generated',
        'description': 'Nouveau mot de passe généré',
        'timestamp': '2024-01-19 10:15:00',
        'icon': 'fas fa-key',
        'status': 'info'
    },
    {
        'type': '2fa_configured',
        'description': 'Authentification à deux facteurs activée',
        'timestamp': '2024-01-18 16:45:00',
        'icon': 'fas fa-mobile-alt',
        'status': 'warning'
    }
]

def home(request):
    """Page d'accueil"""
    return render(request, 'auth_app/home.html')

def login_view(request):
    """Vue de connexion avec données factices"""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        two_factor_code = request.POST.get('two_factor_code')
        recovery_code = request.POST.get('recovery_code')
        
        # Vérification avec les données factices
        user = None
        for fake_user in FAKE_USERS.values():
            if fake_user['username'] == username and fake_user['password'] == password:
                user = fake_user
                break
        
        if user:
            # Vérification 2FA si activé
            if user['two_factor_enabled']:
                if not two_factor_code and not recovery_code:
                    messages.warning(request, 'Code 2FA requis')
                    return render(request, 'auth_app/login.html', {
                        'username': username,
                        'requires_2fa': True
                    })
                
                # Simulation de vérification 2FA
                if two_factor_code and two_factor_code != '123456':
                    messages.error(request, 'Code 2FA invalide')
                    return render(request, 'auth_app/login.html', {
                        'username': username,
                        'requires_2fa': True
                    })
                
                if recovery_code and recovery_code != 'RECOVERY':
                    messages.error(request, 'Code de récupération invalide')
                    return render(request, 'auth_app/login.html', {
                        'username': username,
                        'requires_2fa': True
                    })
            
            # Connexion réussie
            request.session['user_data'] = user
            request.session['is_authenticated'] = True
            messages.success(request, f'Connexion réussie ! Bienvenue {user["username"]}')
            return redirect('auth_app:dashboard')
        else:
            messages.error(request, 'Nom d\'utilisateur ou mot de passe incorrect')
    
    return render(request, 'auth_app/login.html')

def register_view(request):
    """Vue d'inscription avec données factices"""
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        password_confirm = request.POST.get('password_confirm')
        
        # Validation simple
        if not username or not email or not password:
            messages.error(request, 'Tous les champs sont requis')
            return render(request, 'auth_app/register.html')
        
        if password != password_confirm:
            messages.error(request, 'Les mots de passe ne correspondent pas')
            return render(request, 'auth_app/register.html')
        
        if len(password) < 8:
            messages.error(request, 'Le mot de passe doit contenir au moins 8 caractères')
            return render(request, 'auth_app/register.html')
        
        # Vérifier si l'utilisateur existe déjà
        for fake_user in FAKE_USERS.values():
            if fake_user['username'] == username or fake_user['email'] == email:
                messages.error(request, 'Un utilisateur avec ce nom ou cet email existe déjà')
                return render(request, 'auth_app/register.html')
        
        # Créer un nouvel utilisateur factice
        new_user = {
            'id': len(FAKE_USERS) + 1,
            'username': username,
            'email': email,
            'password': password,
            'two_factor_enabled': False,
            'created_at': '2024-01-20',
            'last_login': None
        }
        
        FAKE_USERS[username] = new_user
        
        messages.success(request, 'Compte créé avec succès ! Vous pouvez maintenant vous connecter.')
        return redirect('auth_app:login')
    
    return render(request, 'auth_app/register.html')

@login_required
def dashboard(request):
    """Tableau de bord utilisateur avec données factices"""
    user_data = request.session.get('user_data', {})
    
    # Données factices pour le tableau de bord
    dashboard_data = {
        'user': user_data,
        'stats': {
            'secure_logins': random.randint(10, 20),
            'passwords_generated': random.randint(2, 8),
            'two_factor_devices': 1 if user_data.get('two_factor_enabled') else 0,
            'security_score': random.randint(85, 100)
        },
        'activities': FAKE_ACTIVITIES,
        'sessions': [
            {
                'device': 'Chrome sur Windows',
                'location': 'Paris, France',
                'last_activity': 'Il y a 2 heures',
                'current': True
            },
            {
                'device': 'Safari sur iPhone',
                'location': 'Paris, France',
                'last_activity': 'Il y a 1 jour',
                'current': False
            }
        ]
    }
    
    return render(request, 'auth_app/dashboard.html', dashboard_data)

@csrf_exempt
def generate_password(request):
    """Génération de mot de passe via fonction serverless (simulation)"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            length = data.get('length', 16)
            include_uppercase = data.get('include_uppercase', True)
            include_lowercase = data.get('include_lowercase', True)
            include_numbers = data.get('include_numbers', True)
            include_symbols = data.get('include_symbols', True)
            
            # Génération du mot de passe
            chars = ''
            if include_lowercase:
                chars += string.ascii_lowercase
            if include_uppercase:
                chars += string.ascii_uppercase
            if include_numbers:
                chars += string.digits
            if include_symbols:
                chars += '!@#$%^&*()_+-=[]{}|;:,.<>?'
            
            if not chars:
                return JsonResponse({'error': 'Aucun type de caractère sélectionné'}, status=400)
            
            password = ''.join(random.choice(chars) for _ in range(length))
            
            # Simuler un appel API
            if settings.OPENFAAS_GATEWAY_URL != 'http://gateway:8080':
                try:
                    response = requests.post(
                        f"{settings.OPENFAAS_GATEWAY_URL}/function/generate-password",
                        json=data,
                        headers={'Content-Type': 'application/json'},
                        timeout=5
                    )
                    if response.status_code == 200:
                        return JsonResponse(response.json())
                except:
                    pass
            
            return JsonResponse({
                'password': password,
                'strength': 'strong',
                'length': length
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Méthode non autorisée'}, status=405)

@csrf_exempt
def generate_2fa(request):
    """Génération de 2FA via fonction serverless (simulation)"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_data = request.session.get('user_data', {})
            
            # Générer un secret factice
            secret = ''.join(random.choices(string.ascii_uppercase + string.digits, k=32))
            
            # Générer des codes de récupération
            recovery_codes = [''.join(random.choices(string.ascii_uppercase + string.digits, k=8)) for _ in range(8)]
            
            # Créer un QR code factice
            qr_data = f"otpauth://totp/Cofrap:{user_data.get('username', 'user')}?secret={secret}&issuer=Cofrap"
            
            # Générer un QR code simple (en base64 pour la démo)
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(qr_data)
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            buffer = BytesIO()
            img.save(buffer, format='PNG')
            qr_code_base64 = base64.b64encode(buffer.getvalue()).decode()
            
            # Simuler un appel API
            if settings.OPENFAAS_GATEWAY_URL != 'http://gateway:8080':
                try:
                    response = requests.post(
                        f"{settings.OPENFAAS_GATEWAY_URL}/function/generate-2fa",
                        json=data,
                        headers={'Content-Type': 'application/json'},
                        timeout=5
                    )
                    if response.status_code == 200:
                        return JsonResponse(response.json())
                except:
                    pass
            
            return JsonResponse({
                'secret': secret,
                'qr_code_url': f"data:image/png;base64,{qr_code_base64}",
                'recovery_codes': recovery_codes,
                'setup_url': qr_data
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Méthode non autorisée'}, status=405)

def password_generator_view(request):
    """Page du générateur de mots de passe"""
    if not request.session.get('is_authenticated'):
        messages.error(request, 'Vous devez être connecté pour accéder à cette page')
        return redirect('auth_app:login')
    
    return render(request, 'auth_app/password_generator.html', {
        'user': request.session.get('user_data', {})
    })

def two_factor_view(request):
    """Page de configuration 2FA"""
    if not request.session.get('is_authenticated'):
        messages.error(request, 'Vous devez être connecté pour accéder à cette page')
        return redirect('auth_app:login')
    
    user_data = request.session.get('user_data', {})
    return render(request, 'auth_app/two_factor.html', {
        'user': user_data,
        'user_2fa_enabled': user_data.get('two_factor_enabled', False),
        'recovery_codes_count': 10  # Nombre factice
    })

@csrf_exempt
def verify_2fa(request):
    """Vérification du code 2FA"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            code = data.get('code')
            
            # Simulation de vérification (code factice: 123456)
            if code == '123456':
                # Activer la 2FA pour l'utilisateur
                user_data = request.session.get('user_data', {})
                if user_data:
                    user_data['two_factor_enabled'] = True
                    request.session['user_data'] = user_data
                
                return JsonResponse({'success': True})
            else:
                return JsonResponse({'success': False, 'error': 'Code incorrect'})
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Données JSON invalides'}, status=400)
    
    return JsonResponse({'error': 'Méthode non autorisée'}, status=405)

@csrf_exempt
def get_recovery_codes(request):
    """Récupération des codes de récupération"""
    if request.method == 'GET':
        user_data = request.session.get('user_data', {})
        if user_data:
            # Générer de nouveaux codes de récupération
            recovery_codes = [''.join(random.choices(string.ascii_uppercase + string.digits, k=8)) for _ in range(10)]
            return JsonResponse({'recovery_codes': recovery_codes})
    
    return JsonResponse({'error': 'Méthode non autorisée'}, status=405)

@csrf_exempt
def disable_2fa(request):
    """Désactivation de la 2FA"""
    if request.method == 'POST':
        user_data = request.session.get('user_data', {})
        if user_data:
            user_data['two_factor_enabled'] = False
            request.session['user_data'] = user_data
            return JsonResponse({'success': True})
    
    return JsonResponse({'error': 'Méthode non autorisée'}, status=405)

def logout_view(request):
    """Déconnexion"""
    request.session.flush()
    messages.success(request, 'Déconnexion réussie !')
    return redirect('auth_app:home')

# Décorateur personnalisé pour vérifier l'authentification
def login_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.session.get('is_authenticated'):
            messages.error(request, 'Vous devez être connecté pour accéder à cette page.')
            return redirect('auth_app:login')
        return view_func(request, *args, **kwargs)
    return wrapper 