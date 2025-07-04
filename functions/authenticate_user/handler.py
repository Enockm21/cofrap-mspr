import json
import hashlib
import os
import jwt
import secrets
from datetime import datetime, timedelta
import psycopg2
from psycopg2.extras import RealDictCursor
import pyotp

def handle(event, context):
    """
    Fonction serverless pour l'authentification utilisateur avec 2FA
    """
    try:
        # Parser les paramètres depuis le body de la requête
        body = event.get('body', '{}')
        data = json.loads(body) if body else {}
        
        # Paramètres d'authentification
        username = data.get('username')
        password = data.get('password')
        two_factor_code = data.get('two_factor_code')
        recovery_code = data.get('recovery_code')
        
        if not username or not password:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'error': 'username et password sont requis'
                })
            }
        
        # Connexion à PostgreSQL
        db_connection = get_db_connection()
        
        # Vérification de l'utilisateur
        user = get_user_by_username(db_connection, username)
        if not user:
            log_failed_attempt(db_connection, username, 'Utilisateur non trouvé')
            return {
                'statusCode': 401,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'error': 'Identifiants invalides'
                })
            }
        
        # Vérification du mot de passe
        if not verify_password(db_connection, user['id'], password):
            log_failed_attempt(db_connection, username, 'Mot de passe incorrect')
            return {
                'statusCode': 401,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'error': 'Identifiants invalides'
                })
            }
        
        # Vérification si l'utilisateur a 2FA activé
        two_factor_enabled = check_2fa_enabled(db_connection, user['id'])
        
        if two_factor_enabled:
            if not two_factor_code and not recovery_code:
                return {
                    'statusCode': 401,
                    'headers': {'Content-Type': 'application/json'},
                    'body': json.dumps({
                        'error': 'Code 2FA requis',
                        'requires_2fa': True
                    })
                }
            
            # Vérification du code 2FA ou du code de récupération
            if two_factor_code:
                if not verify_2fa_code(db_connection, user['id'], two_factor_code):
                    log_failed_attempt(db_connection, username, 'Code 2FA incorrect')
                    return {
                        'statusCode': 401,
                        'headers': {'Content-Type': 'application/json'},
                        'body': json.dumps({
                            'error': 'Code 2FA incorrect'
                        })
                    }
            elif recovery_code:
                if not verify_recovery_code(db_connection, user['id'], recovery_code):
                    log_failed_attempt(db_connection, username, 'Code de récupération incorrect')
                    return {
                        'statusCode': 401,
                        'headers': {'Content-Type': 'application/json'},
                        'body': json.dumps({
                            'error': 'Code de récupération incorrect'
                        })
                    }
        
        # Vérification de l'expiration du mot de passe
        if is_password_expired(db_connection, user['id']):
            return {
                'statusCode': 401,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'error': 'Mot de passe expiré',
                    'requires_password_change': True
                })
            }
        
        # Génération du token JWT
        token = generate_jwt_token(user)
        
        # Mise à jour de la dernière connexion
        update_last_login(db_connection, user['id'])
        
        # Log de la connexion réussie
        log_successful_login(db_connection, user['id'])
        
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'token': token,
                'user': {
                    'id': user['id'],
                    'username': user['username'],
                    'email': user['email'],
                    'two_factor_enabled': two_factor_enabled
                },
                'expires_at': (datetime.now() + timedelta(hours=24)).isoformat()
            })
        }
        
    except json.JSONDecodeError:
        return {
            'statusCode': 400,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': 'Format JSON invalide'})
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': f'Erreur interne: {str(e)}'})
        }

def get_db_connection():
    """Connexion à la base de données PostgreSQL"""
    return psycopg2.connect(
        host=os.getenv('POSTGRES_HOST', 'postgres'),
        database=os.getenv('POSTGRES_DB', 'mspr2_cofrap'),
        user=os.getenv('POSTGRES_USER', 'postgres'),
        password=os.getenv('POSTGRES_PASSWORD', 'password')
    )

def get_user_by_username(conn, username):
    """Récupération d'un utilisateur par son nom d'utilisateur"""
    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute("""
            SELECT id, username, email, is_active, created_at
            FROM users WHERE username = %s AND is_active = %s
        """, (username, True))
        return cursor.fetchone()

def verify_password(conn, user_id, password):
    """Vérification du mot de passe"""
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT password_hash, salt FROM password_history 
            WHERE user_id = %s ORDER BY created_at DESC LIMIT 1
        """, (user_id,))
        result = cursor.fetchone()
        
        if not result:
            return False
        
        password_hash, salt = result
        
        # Vérification du hash
        computed_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
        return computed_hash.hex() == password_hash

def check_2fa_enabled(conn, user_id):
    """Vérification si 2FA est activé pour l'utilisateur"""
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT is_active FROM two_factor_auth 
            WHERE user_id = %s AND is_active = %s
        """, (user_id, True))
        return cursor.fetchone() is not None

def verify_2fa_code(conn, user_id, code):
    """Vérification d'un code 2FA"""
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT secret_key FROM two_factor_auth 
            WHERE user_id = %s AND is_active = %s
        """, (user_id, True))
        result = cursor.fetchone()
        
        if not result:
            return False
        
        secret_key = result[0]
        totp = pyotp.TOTP(secret_key)
        return totp.verify(code)

def verify_recovery_code(conn, user_id, code):
    """Vérification d'un code de récupération"""
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT id FROM recovery_codes 
            WHERE user_id = %s AND code = %s AND used = %s
        """, (user_id, code, False))
        
        result = cursor.fetchone()
        if result:
            # Marquer le code comme utilisé
            cursor.execute("""
                UPDATE recovery_codes SET used = %s, used_at = %s
                WHERE user_id = %s AND code = %s
            """, (True, datetime.now(), user_id, code))
            conn.commit()
            return True
        return False

def is_password_expired(conn, user_id):
    """Vérification si le mot de passe a expiré"""
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT created_at FROM password_rotation_schedule 
            WHERE user_id = %s AND rotation_date <= %s
        """, (user_id, datetime.now()))
        return cursor.fetchone() is not None

def generate_jwt_token(user):
    """Génération d'un token JWT"""
    secret_key = os.getenv('JWT_SECRET_KEY', 'your-secret-key-change-in-production')
    
    payload = {
        'user_id': user['id'],
        'username': user['username'],
        'email': user['email'],
        'exp': datetime.now() + timedelta(hours=24),
        'iat': datetime.now()
    }
    
    return jwt.encode(payload, secret_key, algorithm='HS256')

def update_last_login(conn, user_id):
    """Mise à jour de la dernière connexion"""
    with conn.cursor() as cursor:
        cursor.execute("""
            UPDATE users SET last_login = %s WHERE id = %s
        """, (datetime.now(), user_id))
        conn.commit()

def log_successful_login(conn, user_id):
    """Log de connexion réussie"""
    with conn.cursor() as cursor:
        cursor.execute("""
            INSERT INTO login_logs (user_id, status, ip_address, user_agent, created_at)
            VALUES (%s, %s, %s, %s, %s)
        """, (user_id, 'SUCCESS', 'unknown', 'unknown', datetime.now()))
        conn.commit()

def log_failed_attempt(conn, username, reason):
    """Log de tentative échouée"""
    with conn.cursor() as cursor:
        cursor.execute("""
            INSERT INTO login_logs (username, status, reason, ip_address, user_agent, created_at)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (username, 'FAILED', reason, 'unknown', 'unknown', datetime.now()))
        conn.commit() 