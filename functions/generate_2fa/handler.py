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

def handle(event, context):
    """
    Fonction serverless pour générer des codes 2FA (TOTP)
    """
    try:
        print(f"DEBUG: Event reçu: {event}")
        print(f"DEBUG: Type de event: {type(event)}")
        
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
        user_id = data.get('user_id')
        user_email = data.get('user_email')
        issuer = data.get('issuer', 'MSPR2-Cofrap')
        
        if not user_id or not user_email:
            return json.dumps({
                'error': 'user_id et user_email sont requis'
            })
        
        # Génération d'une clé secrète pour TOTP
        secret_key = pyotp.random_base32()
        
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
        
        # Connexion à PostgreSQL
        db_connection = get_db_connection()
        
        # Stockage de la clé secrète en base (chiffrée)
        store_2fa_secret(db_connection, user_id, secret_key, user_email)
        
        # Génération d'un code de récupération
        recovery_codes = generate_recovery_codes()
        store_recovery_codes(db_connection, user_id, recovery_codes)
        
        return json.dumps({
            'success': True,
            'secret_key': secret_key,
            'qr_code': qr_code_base64,
            'provisioning_uri': provisioning_uri,
            'recovery_codes': recovery_codes,
            'generated_at': datetime.now().isoformat(),
            'expires_at': (datetime.now() + timedelta(days=365)).isoformat()
        })
        
    except json.JSONDecodeError:
        return json.dumps({'error': 'Format JSON invalide'})
    except Exception as e:
        return json.dumps({'error': f'Erreur interne: {str(e)}'})

def get_db_connection():
    """Connexion à la base de données PostgreSQL"""
    return psycopg2.connect(
        host=os.getenv('POSTGRES_HOST', 'postgres'),
        database=os.getenv('POSTGRES_DB', 'mspr2_cofrap'),
        user=os.getenv('POSTGRES_USER', 'postgres'),
        password=os.getenv('POSTGRES_PASSWORD', 'password')
    )

def store_2fa_secret(conn, user_id, secret_key, user_email):
    """Stockage de la clé secrète 2FA en base"""
    with conn.cursor() as cursor:
        cursor.execute("""
            INSERT INTO two_factor_auth (user_id, secret_key, user_email, created_at, is_active)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (user_id) DO UPDATE SET 
                secret_key = EXCLUDED.secret_key,
                updated_at = %s,
                is_active = %s
        """, (user_id, secret_key, user_email, datetime.now(), True, datetime.now(), True))
        conn.commit()

def generate_recovery_codes():
    """Génération de codes de récupération"""
    codes = []
    for _ in range(10):
        # Génération de codes de 8 caractères
        code = ''.join(secrets.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789') for _ in range(8))
        codes.append(code)
    return codes

def store_recovery_codes(conn, user_id, recovery_codes):
    """Stockage des codes de récupération"""
    with conn.cursor() as cursor:
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