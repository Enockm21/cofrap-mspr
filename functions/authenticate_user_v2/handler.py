import json
import os
import time
import pyotp
from cryptography.fernet import Fernet
import psycopg2
from psycopg2.extras import RealDictCursor

def handle(event, context):
    """
    Fonction serverless d'authentification utilisateur V2
    Vérifie username, password, 2FA_code et l'expiration du mot de passe
    """
    try:
        # Parsing robuste de l'entrée
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
        two_factor_code = data.get('2FA_code')
        
        if not username or not password:
            return json.dumps({
                'error': 'username et password sont requis'
            })
        
        # Connexion à la base de données
        db_connection = get_db_connection()
        
        # Récupération des données utilisateur
        user_data = get_user_data(db_connection, username)
        
        if not user_data:
            log_authentication_attempt(db_connection, username, False, 'Utilisateur inexistant')
            return json.dumps({
                'error': 'Utilisateur inexistant'
            })
        
        # Vérification du mot de passe
        if not verify_password(db_connection, user_data, password):
            log_authentication_attempt(db_connection, username, False, 'Mot de passe incorrect')
            return json.dumps({
                'error': 'Mot de passe incorrect'
            })
        
        # Vérification du code 2FA si l'utilisateur en a un
        if user_data['mfa']:
            if not two_factor_code:
                log_authentication_attempt(db_connection, username, False, 'Code 2FA requis')
                return json.dumps({
                    'error': 'Code 2FA requis'
                })
            
            if not verify_2fa_code(db_connection, user_data, two_factor_code):
                log_authentication_attempt(db_connection, username, False, 'Code 2FA incorrect')
                return json.dumps({
                    'error': 'Code 2FA incorrect'
                })
        
        # Vérification de l'expiration du mot de passe (6 mois = 15768000 secondes)
        current_time = int(time.time())
        password_age = current_time - user_data['gendate']
        six_months_in_seconds = 6 * 30 * 24 * 60 * 60  # 6 mois approximatifs
        
        if password_age > six_months_in_seconds:
            # Marquer le mot de passe comme expiré
            mark_password_expired(db_connection, username)
            
            log_authentication_attempt(db_connection, username, False, 'Mot de passe expiré')
            return json.dumps({
                'error': 'Mot de passe expiré',
                'password_expired': True,
                'message': 'Le mot de passe a plus de 6 mois. Veuillez relancer le processus de génération.'
            })
        
        # Authentification réussie
        log_authentication_attempt(db_connection, username, True, 'Authentification réussie')
        
        return json.dumps({
            'success': True,
            'username': username,
            'message': 'Authentification réussie',
            'user_id': user_data['id']
        })
        
    except Exception as e:
        # Log de l'erreur
        try:
            db_connection = get_db_connection()
            log_authentication_attempt(db_connection, username, False, f'Erreur interne: {str(e)}')
        except:
            pass
        
        return json.dumps({
            'error': f'Erreur interne: {str(e)}'
        })

def get_encryption_key():
    """Récupération de la clé de chiffrement depuis les variables d'environnement"""
    key = os.getenv('ENCRYPTION_KEY')
    if not key:
        # Génération d'une clé par défaut (à changer en production)
        key = Fernet.generate_key().decode()
        print("⚠️  ATTENTION: Utilisation d'une clé de chiffrement par défaut")
    return key.encode()

def get_db_connection():
    """Connexion à la base de données PostgreSQL"""
    return psycopg2.connect(
        host=os.getenv('POSTGRES_HOST', 'postgres'),
        database=os.getenv('POSTGRES_DB', 'mspr2_cofrap'),
        user=os.getenv('POSTGRES_USER', 'postgres'),
        password=os.getenv('POSTGRES_PASSWORD', 'password')
    )

def get_user_data(conn, username):
    """Récupération des données utilisateur"""
    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute("""
            SELECT id, username, password, mfa, gendate, expired
            FROM users_v2 WHERE username = %s
        """, (username,))
        return cursor.fetchone()

def verify_password(conn, user_data, password):
    """Vérification du mot de passe"""
    try:
        # Déchiffrement du mot de passe stocké
        encryption_key = get_encryption_key()
        fernet = Fernet(encryption_key)
        
        # Utiliser le mot de passe de la table principale
        encrypted_password = user_data['password']
        
        # Déchiffrement et comparaison
        decrypted_password = fernet.decrypt(encrypted_password.encode()).decode()
        return password == decrypted_password
        
    except Exception as e:
        print(f"Erreur lors de la vérification du mot de passe: {e}")
        return False

def verify_2fa_code(conn, user_data, two_factor_code):
    """Vérification du code 2FA"""
    try:
        # Déchiffrement du secret 2FA
        encryption_key = get_encryption_key()
        fernet = Fernet(encryption_key)
        decrypted_mfa = fernet.decrypt(user_data['mfa'].encode()).decode()
        
        # Vérification du code TOTP
        totp = pyotp.TOTP(decrypted_mfa)
        return totp.verify(two_factor_code)
        
    except Exception as e:
        print(f"Erreur lors de la vérification 2FA: {e}")
        return False

def mark_password_expired(conn, username):
    """Marquer le mot de passe comme expiré"""
    with conn.cursor() as cursor:
        cursor.execute("""
            UPDATE users_v2 
            SET expired = TRUE, updated_at = CURRENT_TIMESTAMP
            WHERE username = %s
        """, (username,))
        conn.commit()

def log_authentication_attempt(conn, username, success, details):
    """Log de la tentative d'authentification"""
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO auth_logs_v2 (user_id, action, success, details)
                SELECT id, 'login', %s, %s
                FROM users_v2 WHERE username = %s
            """, (success, json.dumps({'details': details}), username))
            conn.commit()
    except Exception as e:
        print(f"Erreur lors du logging: {e}") 