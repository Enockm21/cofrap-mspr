import json
import secrets
import os
import base64
import qrcode
import io
import pyotp
import time
from cryptography.fernet import Fernet
import psycopg2
from psycopg2.extras import RealDictCursor

def handle(event, context):
    """
    Fonction serverless pour générer des secrets 2FA V2
    Prend un username et génère un secret 2FA avec QR code pour les apps
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
        
        # Paramètres de génération
        username = data.get('username')
        issuer = data.get('issuer', 'MSPR2-COFRAP')
        
        if not username:
            return json.dumps({
                'error': 'Le paramètre username est requis'
            })
        
        # Génération d'un secret 2FA (TOTP)
        secret_key = pyotp.random_base32()
        
        # Création de l'objet TOTP
        totp = pyotp.TOTP(secret_key)
        
        # Génération du QR code pour les apps 2FA (Google Authenticator, etc.)
        provisioning_uri = totp.provisioning_uri(
            name=username,
            issuer_name=issuer
        )
        
        # Création du QR code
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(provisioning_uri)
        qr.make(fit=True)
        
        # Conversion en base64 pour transmission
        img = qr.make_image(fill_color="black", back_color="white")
        img_buffer = io.BytesIO()
        img.save(img_buffer, format='PNG')
        qr_code_base64 = base64.b64encode(img_buffer.getvalue()).decode()
        
        # Chiffrement du secret 2FA
        encryption_key = get_encryption_key()
        fernet = Fernet(encryption_key)
        encrypted_mfa = fernet.encrypt(secret_key.encode()).decode()
        
        # Connexion à la base de données
        db_connection = get_db_connection()
        
        # Stockage en base de données
        store_mfa_in_db(db_connection, username, encrypted_mfa)
        
        # Log de la génération
        log_2fa_generation(db_connection, username, True)
        
        return json.dumps({
            'success': True,
            'username': username,
            'qr_code': qr_code_base64,
            'provisioning_uri': provisioning_uri,
            'issuer': issuer,
            'message': 'Secret 2FA généré avec succès'
        })
        
    except Exception as e:
        # Log de l'erreur
        try:
            db_connection = get_db_connection()
            log_2fa_generation(db_connection, username, False, str(e))
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

def store_mfa_in_db(conn, username, encrypted_mfa):
    """Stockage du secret 2FA chiffré en base"""
    with conn.cursor() as cursor:
        # Vérifier si l'utilisateur existe
        cursor.execute("SELECT id FROM users_v2 WHERE username = %s", (username,))
        existing_user = cursor.fetchone()
        
        if existing_user:
            # Mise à jour du secret 2FA
            cursor.execute("""
                UPDATE users_v2 
                SET mfa = %s, updated_at = CURRENT_TIMESTAMP
                WHERE username = %s
            """, (encrypted_mfa, username))
        else:
            # Création d'un nouvel utilisateur avec secret 2FA
            cursor.execute("""
                INSERT INTO users_v2 (username, password, mfa, gendate, expired)
                VALUES (%s, %s, %s, %s, FALSE)
            """, (username, 'NO_PASSWORD_YET', encrypted_mfa, int(time.time())))
        
        conn.commit()

def log_2fa_generation(conn, username, success, error_details=None):
    """Log de la génération 2FA"""
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO auth_logs_v2 (user_id, action, success, details)
                SELECT id, '2fa_generated', %s, %s
                FROM users_v2 WHERE username = %s
            """, (success, json.dumps({'error': error_details} if error_details else {}), username))
            conn.commit()
    except Exception as e:
        print(f"Erreur lors du logging: {e}") 