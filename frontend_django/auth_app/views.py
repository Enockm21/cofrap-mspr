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

def make_api_request(endpoint, data, registration_data=None):
    """
    Fonction utilitaire pour faire des requêtes API avec gestion du paramètre create_account
    """
    # Si on est dans le workflow d'inscription, ajouter les paramètres nécessaires
    if registration_data and registration_data.get('account_created'):
        data['create_account'] = True
        if 'email' not in data and registration_data.get('email'):
            data['email'] = registration_data.get('email')
    
    try:
        response = requests.post(
            f"{settings.OPENFAAS_GATEWAY_URL}/function/{endpoint}",
            json=data,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        return response
    except requests.RequestException as e:
        raise Exception(f'Erreur de connexion au backend: {str(e)}')

def public_home(request):
    """Page d'accueil publique - accessible à tous"""
    return render(request, 'auth_app/public_home.html')

def dashboard_home(request):
    """Page d'accueil du tableau de bord - accessible seulement aux utilisateurs connectés"""
    # Vérifier si l'utilisateur est connecté
    if not request.session.get('is_authenticated'):
        messages.warning(request, 'Vous devez être connecté pour accéder à cette page.')
        return redirect('auth_app:login')
    
    user_data = request.session.get('user_data', {})
    
    context = {
        'user': user_data,
        'welcome_message': f'Bienvenue {user_data.get("username", "Utilisateur")} !'
    }
    
    return render(request, 'auth_app/home.html', context)

def login_view(request):
    """Authentification via fonction OpenFaaS avec code 2FA obligatoire"""
    # Nettoyer les données d'inscription après redirection depuis 2FA
    if request.session.get('registration_data', {}).get('mfa_generated'):
        messages.success(request, 'Inscription terminée ! Connectez-vous avec vos identifiants.')
        request.session.pop('registration_data', None)
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        two_factor_code = request.POST.get('two_factor_code')
        
        if not username or not password:
            messages.error(request, 'Nom d\'utilisateur et mot de passe requis')
            return render(request, 'auth_app/login.html')
        
        if not two_factor_code:
            messages.error(request, 'Code 2FA requis')
            return render(request, 'auth_app/login.html', {
                'username': username,
                'requires_2fa': True
            })
        
        # Appel à la fonction OpenFaaS authenticate-user avec code 2FA obligatoire
        try:
            auth_data = {
                'username': username,
                'password': password,
                'two_factor_code': two_factor_code
            }
            
            # Si c'est un nouveau compte, ajouter le paramètre create_account
            registration_data = request.session.get('registration_data')
            if registration_data and registration_data.get('account_created'):
                auth_data['create_account'] = True
                auth_data['email'] = registration_data.get('email')
            
            response = requests.post(
                f"{settings.OPENFAAS_GATEWAY_URL}/function/authenticate-user",
                json=auth_data,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            # print(response.json(),"response")
            if response.status_code == 200:
                result = response.json()
                
                # Vérifier si la réponse contient un token (connexion réussie)
                if result.get('token') and result.get('user'):
                    # Connexion réussie
                    user_data = {
                        'id': result.get('user', {}).get('id') or result.get('user_id'),
                        'username': username,
                        'email': result.get('user', {}).get('email') or result.get('email', f'{username}@mspr2.com'),
                        'two_factor_enabled': result.get('user', {}).get('two_factor_enabled', True),
                        'token': result.get('token'),
                        'last_login': result.get('last_login')
                    }
                    
                    request.session['user_data'] = user_data
                    request.session['is_authenticated'] = True
                    request.session['auth_token'] = result.get('token')
                    
                    # Nettoyer les données d'inscription après connexion réussie
                    if 'registration_data' in request.session:
                        del request.session['registration_data']
                    
                    # Nettoyer les données de connexion temporaires
                    if 'login_step' in request.session:
                        del request.session['login_step']
                    if 'login_username' in request.session:
                        del request.session['login_username']
                    if 'login_password' in request.session:
                        del request.session['login_password']
                    
                    messages.success(request, f'Connexion réussie ! Bienvenue {username}')
                    return redirect('auth_app:dashboard_home')  # Redirection vers la page d'accueil du tableau de bord
                
                else:
                    error_msg = result.get('error', 'Identifiants ou code 2FA incorrect')
                    messages.error(request, error_msg)
                    return render(request, 'auth_app/login.html', {
                        'username': username,
                        'requires_2fa': True
                    })
            else:
                messages.error(request, f'Erreur serveur: {response.status_code}')
                
        except requests.RequestException as e:
            messages.error(request, f'Erreur de connexion au backend: {str(e)}')
        except Exception as e:
            messages.error(request, f'Erreur inattendue: {str(e)}')
    
    return render(request, 'auth_app/login.html')

def register_view(request):
    """Vue d'inscription - Étape 1: Création utilisateur"""
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        
        # Validation simple
        if not username:
            messages.error(request, 'Le nom d\'utilisateur est requis')
            return render(request, 'auth_app/register.html')
        
        if not email:
            email = f"{username}@mspr2.com"  # Email par défaut si pas fourni
        
        # Appel à l'API pour créer le compte utilisateur
        try:
            response = requests.post(
                f"{settings.OPENFAAS_GATEWAY_URL}/function/authenticate-user",
                json={
                    'username': username,
                    'email': email,
                    'create_account': True
                },
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get('success'):
                    # Stocker les infos utilisateur en session pour le workflow
                    request.session['registration_data'] = {
                        'username': username,
                        'email': email,
                        'user_id': result.get('user_id'),
                        'account_created': True
                    }
                    request.session.modified = True  # Forcer la sauvegarde de la session
                    
                    messages.success(request, f'Utilisateur {username} créé avec succès ! Générons maintenant votre mot de passe sécurisé.')
                    return redirect('auth_app:password_generator')
                else:
                    error_msg = result.get('error', 'Erreur lors de la création du compte')
                    messages.error(request, error_msg)
            else:
                messages.error(request, f'Erreur serveur: {response.status_code}')
                
        except requests.RequestException as e:
            messages.error(request, f'Erreur de connexion au backend: {str(e)}')
        except Exception as e:
            messages.error(request, f'Erreur inattendue: {str(e)}')
    
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
    """Étape 2: Génération de mot de passe via fonction OpenFaaS"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            # Récupérer le nom d'utilisateur
            registration_data = request.session.get('registration_data')
            user_data = request.session.get('user_data', {})
            username = registration_data.get('username') if registration_data else user_data.get('username')
            
            if not username:
                return JsonResponse({
                    'success': False,
                    'error': 'Nom d\'utilisateur non trouvé'
                }, status=400)
            
            # Appel à la fonction OpenFaaS generate-password
            try:
                # Préparer les données pour l'API
                api_data = {
                    'username': username,
                    'return_password': True  # Demander le mot de passe en clair pour l'affichage
                }
                
                # Si on est dans le workflow d'inscription, ajouter le paramètre create_account
                if registration_data and registration_data.get('account_created'):
                    api_data['create_account'] = True
                    api_data['email'] = registration_data.get('email')
                
                response = requests.post(
                    f"{settings.OPENFAAS_GATEWAY_URL}/function/generate-password",
                    json=api_data,
                    headers={'Content-Type': 'application/json'},
                    timeout=30
                )
                
                if response.status_code == 200:
                    result = response.json()
                    
                    if result.get('success'):
                        # Stocker les infos de génération dans la session
                        if registration_data:
                            request.session['registration_data']['password_generated'] = True
                            request.session['registration_data']['gendate'] = result.get('gendate')
                            request.session.modified = True  # Forcer la sauvegarde de la session
                        
                        return JsonResponse({
                            'success': True,
                            'qr_code': result.get('qr_code'),
                            'password': result.get('password'),  # Mot de passe en clair pour affichage
                            'gendate': result.get('gendate'),
                            'message': result.get('message', 'Mot de passe généré avec succès'),
                            'next_url': '/two-factor/' if registration_data else None
                        })
                    else:
                        return JsonResponse({
                            'success': False,
                            'error': result.get('error', 'Erreur lors de la génération')
                        }, status=500)
                        
                else:
                    return JsonResponse({
                        'success': False,
                        'error': f'Erreur serveur: {response.status_code}'
                    }, status=500)
                    
            except requests.RequestException as e:
                return JsonResponse({
                    'success': False,
                    'error': f'Erreur de connexion au backend: {str(e)}'
                }, status=500)
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'Erreur inattendue: {str(e)}'
            }, status=500)
    
    return JsonResponse({'error': 'Méthode non autorisée'}, status=405)

@csrf_exempt
def generate_2fa(request):
    """Étape 3: Génération de 2FA via fonction OpenFaaS"""
 
    if request.method == 'POST':
        
        try:
            # La génération 2FA n'a pas besoin de données du frontend
            # Elle utilise les données de session
            # print("Génération 2FA - Pas de données requises du frontend")
            
            # Récupérer le nom d'utilisateur
            registration_data = request.session.get('registration_data')
            # print(registration_data,"registration_data")
            user_data = request.session.get('user_data', {})
            username = registration_data.get('username') if registration_data else user_data.get('username')
            
            if not username:
                return JsonResponse({
                    'success': False,
                    'error': 'Nom d\'utilisateur non trouvé'
                }, status=400)
            
            # Appel à la fonction OpenFaaS generate-2fa
            try:
                # Préparer les données pour l'API
                api_data = {'username': username}
                
                # Si on est dans le workflow d'inscription, créer l'utilisateur si besoin
                if registration_data and registration_data.get('account_created'):
                    # Créer l'utilisateur (idempotent)
                    try:
                        create_user_response = requests.post(
                            f"{settings.OPENFAAS_GATEWAY_URL}/function/authenticate-user",
                            json={
                                'username': username,
                                'email': registration_data.get('email'),
                                'create_account': True
                            },
                            headers={'Content-Type': 'application/json'},
                            timeout=30
                        )
                        # On ne bloque pas si l'utilisateur existe déjà
                    except requests.RequestException as e:
                        return JsonResponse({
                            'success': False,
                            'error': f'Erreur de connexion lors de la création de l\'utilisateur: {str(e)}'
                        }, status=500)
                    # NE PAS mettre create_account dans l'appel à generate-2fa
                
                response = requests.post(
                    f"{settings.OPENFAAS_GATEWAY_URL}/function/generate-2fa",
                    json=api_data,
                    headers={'Content-Type': 'application/json'},
                    timeout=30
                )
                # print(response.json())
                
                if response.status_code == 200:
                    result = response.json()
                    
                    if result.get('success'):
                        # Stocker les infos de génération 2FA dans la session
                        if registration_data:
                            request.session['registration_data']['mfa_generated'] = True
                            # Note: two_factor_enabled sera mis à True seulement après vérification du code
                            request.session.modified = True  # Forcer la sauvegarde de la session
                        
                        return JsonResponse({
                            'success': True,
                            'qr_code': result.get('qr_code'),
                            'provisioning_uri': result.get('provisioning_uri'),
                            'issuer': result.get('issuer', 'MSPR2-COFRAP'),
                            'message': result.get('message', 'Secret 2FA généré avec succès'),
                            'next_url': '/login/' if registration_data else None
                        })
                    else:
                        return JsonResponse({
                            'success': False,
                            'error': result.get('error', 'Erreur lors de la génération du 2FA')
                        }, status=500)
                        
                else:
                    return JsonResponse({
                        'success': False,
                        'error': f': {response.status_code}'
                    }, status=500)
                    
            except requests.RequestException as e:
                return JsonResponse({
                    'success': False,
                    'error': f'Erreur de connexion au backend: {str(e)}'
                }, status=500)
            
        except Exception as e:
            print(e,"e")
            return JsonResponse({
                'success': False,
                'error': f'Erreur inattendue: {str(e)}'
            }, status=500)
    
    return JsonResponse({'error': 'Méthode non autorisée'}, status=405)

def password_generator_view(request):
    """Étape 2: Génération du mot de passe via OpenFaaS"""
    # Vérifier si on est dans le workflow d'inscription
    registration_data = request.session.get('registration_data')
    if not registration_data and not request.session.get('is_authenticated'):
        messages.error(request, 'Vous devez commencer par créer un compte')
        return redirect('auth_app:register')
    
    # Pour utilisateur connecté ou en cours d'inscription
    user_data = registration_data or request.session.get('user_data', {})
    
    context = {
        'user': user_data,
        'is_registration': bool(registration_data),
        'step': 2,
        'next_step': 'Configuration 2FA'
    }
    
    return render(request, 'auth_app/password_generator.html', context)

def two_factor_view(request):
    """Étape 3: Configuration 2FA via OpenFaaS"""
    # Vérifier si on est dans le workflow d'inscription
    registration_data = request.session.get('registration_data')
    if not registration_data and not request.session.get('is_authenticated'):
        messages.error(request, 'Vous devez commencer par créer un compte')
        return redirect('auth_app:register')
    
    # Vérifier que le mot de passe a été généré
    if registration_data and not registration_data.get('password_generated'):
        messages.error(request, 'Vous devez d\'abord générer un mot de passe')
        return redirect('auth_app:password_generator')
    
    # Pour utilisateur connecté ou en cours d'inscription
    user_data = registration_data or request.session.get('user_data', {})
    
    # Pendant le workflow d'inscription, on ne devrait jamais afficher la gestion mais toujours la configuration
    is_2fa_already_active = False
    if registration_data:
        # En cours d'inscription : toujours afficher la configuration
        is_2fa_already_active = False
    else:
        # Utilisateur connecté : vérifier s'il a déjà activé la 2FA
        is_2fa_already_active = user_data.get('two_factor_enabled', False)
    
    context = {
        'user': user_data,
        'is_registration': bool(registration_data),
        'step': 3,
        'next_step': 'Authentification',
        'user_2fa_enabled': is_2fa_already_active
    }
    
    return render(request, 'auth_app/two_factor.html', context)

@csrf_exempt
def verify_2fa(request):
    """Vérification du code 2FA via OpenFaaS"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            code = data.get('code')
            
            if not code:
                return JsonResponse({'success': False, 'error': 'Code requis'}, status=400)
            
            # Récupérer le username depuis la session
            registration_data = request.session.get('registration_data')
            user_data = request.session.get('user_data', {})
            username = registration_data.get('username') if registration_data else user_data.get('username')
            
            if not username:
                return JsonResponse({
                    'success': False,
                    'error': 'Nom d\'utilisateur non trouvé'
                }, status=400)
            
            # Appel à la fonction OpenFaaS generate-2fa avec verify_2fa=True
            try:
                payload = {
                    'username': username,
                    'code': code,
                    'verify_2fa': True
                }
                
                response = requests.post(
                    f"{settings.OPENFAAS_GATEWAY_URL}/function/generate-2fa",
                    json=payload,
                    headers={'Content-Type': 'application/json'},
                    timeout=30
                )
                print(response.json(),"response")
                if response.status_code == 200:
                    result = response.json()
                    
                    if result.get('success'):
                        # Activer la 2FA pour l'utilisateur
                        if registration_data:
                            # En cours d'inscription : activer la 2FA dans registration_data
                            request.session['registration_data']['two_factor_enabled'] = True
                            request.session.modified = True
                        elif user_data:
                            # Utilisateur connecté : activer la 2FA dans user_data
                            user_data['two_factor_enabled'] = True
                            request.session['user_data'] = user_data
                            request.session.modified = True
                        
                        return JsonResponse({
                            'success': True,
                            'message': '2FA activée avec succès !',
                            'next_url': '/login/' if registration_data else None
                        })
                    else:
                        return JsonResponse({
                            'success': False,
                            'error': result.get('error', 'Code incorrect')
                        })
                        
                else:
                    # print(result,"result")
                    print(response,"response2")
                    return JsonResponse({
                        'success': False,
                        'error': f'Erreur serveur: {response.status_code}'
                    }, status=500)
                    
            except requests.RequestException as e:
                return JsonResponse({
                    'success': False,
                    'error': f'Erreur de connexion au backend: {str(e)}'
                }, status=500)
                
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Données JSON invalides'}, status=400)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'Erreur inattendue: {str(e)}'
            }, status=500)
    
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

def logout_confirm(request):
    """Page de confirmation de déconnexion"""
    # Vérifier si l'utilisateur est connecté
    if not request.session.get('is_authenticated'):
        messages.warning(request, 'Vous n\'êtes pas connecté.')
        return redirect('auth_app:login')
    
    user_data = request.session.get('user_data', {})
    
    context = {
        'user': user_data
    }
    
    return render(request, 'auth_app/logout_confirm.html', context)

def logout_view(request):
    """Déconnexion"""
    # Récupérer le nom d'utilisateur avant de supprimer la session
    username = request.session.get('user_data', {}).get('username', 'Utilisateur')
    
    # Nettoyer complètement la session
    request.session.flush()
    
    # Supprimer le cookie de session si il existe
    if hasattr(request, 'session'):
        request.session.delete()
    
    messages.success(request, f'Déconnexion réussie ! Au revoir {username}')
    return redirect('auth_app:public_home')

# Décorateur personnalisé pour vérifier l'authentification
def login_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.session.get('is_authenticated'):
            messages.error(request, 'Vous devez être connecté pour accéder à cette page.')
            return redirect('auth_app:login')
        return view_func(request, *args, **kwargs)
    return wrapper 