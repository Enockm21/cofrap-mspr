import json
import secrets
import os
import base64
import qrcode
import io
from datetime import datetime, timedelta
import psycopg2
from psycopg2.extras import RealDictCursor
import pyotp
from cryptography.fernet import Fernet

def handle(event, context):
    """
    Fonction serverless pour générer des codes 2FA (TOTP)
    """
    try:
        print(f"DEBUG: Event reçu: {event}")
        
        # Parser les paramètres depuis le body de la requête
        if hasattr(event, 'body'):
            body = event.body
            if isinstance(body, bytes):
                body = body.decode('utf-8')
        elif isinstance(event, str):
            body = event
        else:
            body = str(event)
            
        print(f"DEBUG: Body reçu: {body}")
        
        try:
            data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            data = {}
            
        print(f"DEBUG: Data parsée: {data}")
        
        # Paramètres de génération
        username = data.get('username')
        email = data.get('email')
        create_account = data.get('create_account', False)
        issuer = data.get('issuer', 'MSPR2-Cofrap')
        
        if not username:
            return {
                "statusCode": 400,
                "body": json.dumps({
                    'error': 'username est requis'
                })
            }
        
        # Génération d'une clé secrète pour TOTP
        secret_key = pyotp.random_base32()
        
        # Déterminer l'email à utiliser
        user_email = None
        if create_account and email:
            # Mode création de compte : utiliser l'email fourni
            user_email = email
        else:
            # Mode normal : récupérer l'email depuis la base de données
            try:
                db_connection = get_db_connection()
                user_email = get_user_email(db_connection, username)
                if not user_email:
                    return {
                        "statusCode": 404,
                        "body": json.dumps({
                            'error': 'Utilisateur non trouvé dans la base de données'
                        })
                    }
            except Exception as e:
                return {
                    "statusCode": 500,
                    "body": json.dumps({
                        'error': f'Erreur de connexion à la base de données: {str(e)}'
                    })
                }
        
        if not user_email:
            return {
                "statusCode": 400,
                "body": json.dumps({
                    'error': 'Email requis pour la génération 2FA'
                })
            }
        
        # Création de l'objet TOTP
        totp = pyotp.TOTP(secret_key)
        
        # Génération du code QR
        provisioning_uri = totp.provisioning_uri(
            name=user_email,
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
        encrypted_secret = fernet.encrypt(secret_key.encode()).decode()
        
        # Stockage des données seulement si l'utilisateur existe en base
        if not create_account:
            try:
                # Stockage de la clé secrète chiffrée en base
                store_2fa_secret(db_connection, username, encrypted_secret, user_email)
                
                # Génération d'un code de récupération
                recovery_codes = generate_recovery_codes()
                store_recovery_codes(db_connection, username, recovery_codes)
            except Exception as e:
                return {
                    "statusCode": 500,
                    "body": json.dumps({
                        'error': f'Erreur lors du stockage en base: {str(e)}'
                    })
                }
        else:
            # Mode création de compte : générer les codes de récupération sans les stocker
            recovery_codes = generate_recovery_codes()
        
        return {
            "statusCode": 200,
            "body": json.dumps({
                'success': True,
                'secret_key': secret_key,
                'qr_code': qr_code_base64,
                'provisioning_uri': provisioning_uri,
                'recovery_codes': recovery_codes,
                'generated_at': datetime.now().isoformat(),
                'expires_at': (datetime.now() + timedelta(days=365)).isoformat()
            })
        }
        
    except json.JSONDecodeError:
        return {
            "statusCode": 400,
            "body": json.dumps({'error': 'Format JSON invalide'})
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({'error': f'Erreur interne: {str(e)}'})
        }

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
        host=os.getenv('POSTGRES_HOST', 'host.docker.internal'),
        database=os.getenv('POSTGRES_DB', 'cofrap_db'),
        user=os.getenv('POSTGRES_USER', 'cofrap'),
        password=os.getenv('POSTGRES_PASSWORD', 'password')
    )

def get_user_email(conn, username):
    """Récupération de l'email de l'utilisateur depuis la table users"""
    with conn.cursor() as cursor:
        cursor.execute("SELECT email FROM users WHERE username = %s", (username,))
        result = cursor.fetchone()
        return result[0] if result else None

def store_2fa_secret(conn, username, encrypted_secret, user_email):
    """Stockage de la clé secrète 2FA chiffrée en base"""
    with conn.cursor() as cursor:
        # Mise à jour directe dans la table users
        cursor.execute("""
            UPDATE users 
            SET mfa = %s, updated_at = CURRENT_TIMESTAMP
            WHERE username = %s
        """, (encrypted_secret, username))
        
        if cursor.rowcount == 0:
            raise Exception(f"Utilisateur {username} non trouvé")
        
        conn.commit()

def generate_recovery_codes():
    """Génération de codes de récupération"""
    codes = []
    for _ in range(10):
        # Génération de codes de 8 caractères
        code = ''.join(secrets.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789') for _ in range(8))
        codes.append(code)
    return codes

def store_recovery_codes(conn, username, recovery_codes):
    """Stockage des codes de récupération"""
    with conn.cursor() as cursor:
        # Récupérer l'ID de l'utilisateur
        cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
        user_result = cursor.fetchone()
        if not user_result:
            raise Exception(f"Utilisateur {username} non trouvé")
        
        user_id = user_result[0]
        
        # Suppression des anciens codes
        cursor.execute("DELETE FROM recovery_codes WHERE user_id = %s", (user_id,))
        
        # Insertion des nouveaux codes
        for code in recovery_codes:
            cursor.execute("""
                INSERT INTO recovery_codes (user_id, code, created_at, used)
                VALUES (%s, %s, %s, %s)
            """, (user_id, code, datetime.now(), False))
        conn.commit()

def verify_2fa_code(secret_key, code):
    """Vérification d'un code 2FA"""
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