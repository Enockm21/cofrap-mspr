import json
import hashlib
import os
import jwt
import secrets
from datetime import datetime, timedelta
import psycopg2
from psycopg2.extras import RealDictCursor
import pyotp
from cryptography.fernet import Fernet


def get_db_connection():
    """Connexion à la base de données PostgreSQL"""
    return psycopg2.connect(
        host=os.getenv('POSTGRES_HOST', 'host.docker.internal'),
        database=os.getenv('POSTGRES_DB', 'cofrap_db'),
        user=os.getenv('POSTGRES_USER', 'cofrap'),
        password=os.getenv('POSTGRES_PASSWORD', 'password'),
        port=os.getenv('POSTGRES_PORT', '5432')
    )

def get_user_by_username(conn, username):
    """Récupération d'un utilisateur par son nom d'utilisateur"""
    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute("""
            SELECT id, username, email, is_active, created_at
            FROM users WHERE username = %s AND is_active = %s
        """, (username, True))
        row = cursor.fetchone()
        return dict(row) if row else None

def create_user(conn, username, email=None):
    """Création d'un nouvel utilisateur"""
    if not email:
        email = f"{username}@mspr.local"
    
    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        # Vérifier si l'utilisateur existe déjà
        cursor.execute("""
            SELECT id FROM users WHERE username = %s OR email = %s
        """, (username, email))
        
        if cursor.fetchone():
            return None  # Utilisateur existe déjà
        
        # Créer le nouvel utilisateur
        cursor.execute("""
            INSERT INTO users (username, email, is_active, created_at, updated_at, gendate)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id, username, email, created_at
        """, (username, email, True, datetime.now(), datetime.now(), 0))
        
        row = cursor.fetchone()
        conn.commit()
        return dict(row) if row else None

def get_encryption_key():
    """Récupération de la clé de chiffrement depuis les variables d'environnement"""
    key = os.getenv('ENCRYPTION_KEY')
    if not key:
        # Génération d'une clé par défaut (à changer en production)
        key = Fernet.generate_key().decode()
        print("⚠️  ATTENTION: Utilisation d'une clé de chiffrement par défaut")
    return key.encode()

def verify_password(conn, user_id, password):
    """Vérification du mot de passe chiffré"""
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT password FROM users 
            WHERE id = %s
        """, (user_id,))
        
        row = cursor.fetchone()
        if not row:
            return False
        
        stored_encrypted_password = row[0]
        
        try:
            # Déchiffrement du mot de passe stocké
            encryption_key = get_encryption_key()
            fernet = Fernet(encryption_key)
            decrypted_password = fernet.decrypt(stored_encrypted_password.encode()).decode()
            
            # Vérification du mot de passe
            return password == decrypted_password
        except Exception as e:
            print(f"Erreur lors du déchiffrement du mot de passe: {e}")
            return False

def check_2fa_enabled(conn, user_id):
    """Vérification si 2FA est activé pour l'utilisateur"""
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT mfa FROM users 
            WHERE id = %s AND mfa IS NOT NULL
        """, (user_id,))
        return cursor.fetchone() is not None

def verify_2fa_code(conn, user_id, code):
    """Vérification d'un code 2FA avec secret chiffré"""
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT mfa FROM users 
            WHERE id = %s AND mfa IS NOT NULL
        """, (user_id,))
        
        row = cursor.fetchone()
        if not row:
            return False
        
        encrypted_secret = row[0]
        
        try:
            # Déchiffrement du secret 2FA
            encryption_key = get_encryption_key()
            fernet = Fernet(encryption_key)
            secret_key = fernet.decrypt(encrypted_secret.encode()).decode()
            
            totp = pyotp.TOTP(secret_key)
            return totp.verify(code)
        except Exception as e:
            print(f"Erreur lors du déchiffrement du secret 2FA: {e}")
            return False

def verify_recovery_code(conn, user_id, code):
    """Vérification d'un code de récupération"""
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT id FROM recovery_codes 
            WHERE user_id = %s AND code = %s AND is_used = %s
        """, (user_id, code, False))
        
        row = cursor.fetchone()
        if row:
            # Marquer le code comme utilisé
            cursor.execute("""
                UPDATE recovery_codes SET is_used = %s, used_at = %s 
                WHERE id = %s
            """, (True, datetime.now(), row[0]))
            conn.commit()
            return True
        
        return False

def is_password_expired(conn, user_id):
    """Vérification si le mot de passe a expiré"""
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT gendate FROM users 
            WHERE id = %s
        """, (user_id,))
        
        row = cursor.fetchone()
        if not row:
            return True
        
        # Vérifier si le mot de passe a plus de 6 mois (15768000 secondes)
        current_time = int(datetime.now().timestamp())
        password_age = current_time - row[0]
        return password_age > 15768000  # 6 mois en secondes

def generate_jwt_token(user):
    """Génération d'un token JWT"""
    payload = {
        'user_id': user['id'],
        'username': user['username'],
        'exp': datetime.utcnow() + timedelta(hours=24),
        'iat': datetime.utcnow()
    }
    
    secret_key = os.getenv('JWT_SECRET_KEY', 'your-secret-key-change-in-production')
    return jwt.encode(payload, secret_key, algorithm='HS256')

def update_last_login(conn, user_id):
    """Mise à jour de la dernière connexion"""
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                UPDATE users SET last_login = %s WHERE id = %s
            """, (datetime.now(), user_id))
            conn.commit()
    except Exception as e:
        print(f"Impossible de mettre à jour last_login: {e}")
        # Continue sans mettre à jour si la colonne n'existe pas

def log_successful_login(conn, user_id):
    """Log d'une connexion réussie"""
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO login_logs (user_id, login_time, success, ip_address)
                VALUES (%s, %s, %s, %s)
            """, (user_id, datetime.now(), True, '127.0.0.1'))
            conn.commit()
    except Exception as e:
        print(f"Impossible de logger la connexion réussie: {e}")
        # Continue sans logger si la table n'existe pas

def log_failed_attempt(conn, username, reason):
    """Log d'une tentative de connexion échouée"""
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO login_logs (username, login_time, success, reason, ip_address)
                VALUES (%s, %s, %s, %s, %s)
            """, (username, datetime.now(), False, reason, '127.0.0.1'))
            conn.commit()
    except Exception as e:
        print(f"Impossible de logger la tentative échouée: {e}")
        # Continue sans logger si la table n'existe pas

def handle(event, context):
    """Handler principal pour OpenFaaS avec support CORS"""
    try:
        # Parser les paramètres depuis le body de la requête
        if hasattr(event, 'body'):
            body = event.body
            if isinstance(body, bytes):
                body = body.decode('utf-8')
            if body:
                try:
                    data = json.loads(body)
                except Exception:
                    data = {}
            else:
                data = {}
        elif isinstance(event, str):
            try:
                data = json.loads(event)
            except Exception:
                data = {}
        else:
            data = {}
        
        # Paramètres d'authentification
        username = data.get('username')
        password = data.get('password')
        two_factor_code = data.get('two_factor_code')
        recovery_code = data.get('recovery_code')
        create_account = data.get('create_account', False)
        email = data.get('email')
        
        if not username:
            return json.dumps({
                'error': 'username est requis'
            })
        
        # Connexion à PostgreSQL
        try:
            db_connection = get_db_connection()
        except Exception as db_error:
            print(f"Erreur de connexion à la base de données: {db_error}")
            return json.dumps({
                'error': 'Erreur de connexion à la base de données',
                'details': str(db_error)
            })
        
        try:
            # Vérification de l'utilisateur
            user = get_user_by_username(db_connection, username)
            
            # Si l'utilisateur n'existe pas et qu'on veut créer un compte
            if not user and create_account:
                new_user = create_user(db_connection, username, email)
                if new_user:
                    return json.dumps({
                        'success': True,
                        'message': 'Utilisateur créé avec succès',
                        'user': {
                            'id': new_user['id'],
                            'username': new_user['username'],
                            'email': new_user['email'],
                            'created_at': new_user['created_at'].isoformat()
                        }
                    })
                else:
                    return json.dumps({
                        'error': 'Un utilisateur avec ce nom ou email existe déjà'
                    })
            
            # Si l'utilisateur n'existe pas et qu'on ne crée pas de compte
            if not user:
                log_failed_attempt(db_connection, username, 'Utilisateur non trouvé')
                return json.dumps({
                    'error': 'Identifiants invalides'
                })
            
            # Pour l'authentification normale, le mot de passe est requis
            if not password:
                return json.dumps({
                    'error': 'password est requis pour l\'authentification'
                })
            
            # Vérification du mot de passe
            if not verify_password(db_connection, user['id'], password):
                log_failed_attempt(db_connection, username, 'Mot de passe incorrect')
                return json.dumps({
                    'error': 'Identifiants invalides'
                })
            
            # Vérification si l'utilisateur a 2FA activé
            two_factor_enabled = check_2fa_enabled(db_connection, user['id'])
            
            if two_factor_enabled:
                if not two_factor_code and not recovery_code:
                    return json.dumps({
                        'error': 'Code 2FA requis',
                        'requires_2fa': True
                    })
                
                # Vérification du code 2FA ou du code de récupération
                if two_factor_code:
                    if not verify_2fa_code(db_connection, user['id'], two_factor_code):
                        log_failed_attempt(db_connection, username, 'Code 2FA incorrect')
                        return json.dumps({
                            'error': 'Code 2FA incorrect'
                        })
                elif recovery_code:
                    if not verify_recovery_code(db_connection, user['id'], recovery_code):
                        log_failed_attempt(db_connection, username, 'Code de récupération incorrect')
                        return json.dumps({
                            'error': 'Code de récupération incorrect'
                        })
            
            # Vérification de l'expiration du mot de passe
            if is_password_expired(db_connection, user['id']):
                return json.dumps({
                    'error': 'Mot de passe expiré',
                    'requires_password_change': True
                })
            
            # Génération du token JWT
            token = generate_jwt_token(user)
            
            # Mise à jour de la dernière connexion
            update_last_login(db_connection, user['id'])
            
            # Log de la connexion réussie
            log_successful_login(db_connection, user['id'])
            
            response_data = {
                'token': token,
                'user': {
                    'id': user['id'],
                    'username': user['username'],
                    'email': user['email'],
                    'two_factor_enabled': two_factor_enabled
                },
                'expires_at': (datetime.now() + timedelta(hours=24)).isoformat()
            }
            
            return json.dumps(response_data)
            
        finally:
            db_connection.close()
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"Erreur dans authenticate_user: {e}")
        print(f"Traceback: {error_trace}")
        
        return json.dumps({
            'error': f'Erreur interne: {str(e)}',
            'details': error_trace
        }) 