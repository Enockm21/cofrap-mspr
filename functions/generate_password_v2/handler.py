import json
import secrets
import string
import os
import base64
import qrcode
import io
import time
from cryptography.fernet import Fernet
import psycopg2
from psycopg2.extras import RealDictCursor

def handle(event, context):
    """
    Fonction serverless pour générer des mots de passe sécurisés V2
    Prend un username et génère un mot de passe de 24 caractères avec QR code
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
        
        if not username:
            return json.dumps({
                'error': 'Le paramètre username est requis'
            })
        
        # Génération d'un mot de passe de 24 caractères
        chars = (
            string.ascii_uppercase +  # Majuscules
            string.ascii_lowercase +  # Minuscules
            string.digits +           # Chiffres
            '!@#$%^&*()_+-=[]{}|;:,.<>?'  # Caractères spéciaux
        )
        
        password = ''.join(secrets.choice(chars) for _ in range(24))
        
        # Génération du QR code contenant le mot de passe
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(password)
        qr.make(fit=True)
        
        # Conversion en base64 pour transmission
        img = qr.make_image(fill_color="black", back_color="white")
        img_buffer = io.BytesIO()
        img.save(img_buffer, format='PNG')
        qr_code_base64 = base64.b64encode(img_buffer.getvalue()).decode()
        
        # Chiffrement du mot de passe
        encryption_key = get_encryption_key()
        fernet = Fernet(encryption_key)
        encrypted_password = fernet.encrypt(password.encode()).decode()
        
        # Timestamp UNIX de génération
        gendate = int(time.time())
        
        # Connexion à la base de données
        db_connection = get_db_connection()
        
        # Stockage en base de données
        store_password_in_db(db_connection, username, encrypted_password, gendate)
        
        # Log de la génération
        log_password_generation(db_connection, username, True)
        
        return json.dumps({
            'success': True,
            'username': username,
            'qr_code': qr_code_base64,
            'gendate': gendate,
            'message': 'Mot de passe généré avec succès'
        })
        
    except Exception as e:
        # Log de l'erreur
        try:
            db_connection = get_db_connection()
            log_password_generation(db_connection, username, False, str(e))
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

def store_password_in_db(conn, username, encrypted_password, gendate):
    """Stockage du mot de passe chiffré en base"""
    with conn.cursor() as cursor:
        # Vérifier si l'utilisateur existe déjà
        cursor.execute("SELECT id FROM users_v2 WHERE username = %s", (username,))
        existing_user = cursor.fetchone()
        
        if existing_user:
            # Mise à jour de l'utilisateur existant
            cursor.execute("""
                UPDATE users_v2 
                SET password = %s, gendate = %s, expired = FALSE, updated_at = CURRENT_TIMESTAMP
                WHERE username = %s
            """, (encrypted_password, gendate, username))
        else:
            # Création d'un nouvel utilisateur
            cursor.execute("""
                INSERT INTO users_v2 (username, password, gendate, expired)
                VALUES (%s, %s, %s, FALSE)
            """, (username, encrypted_password, gendate))
        
        # Ajout dans l'historique
        user_id = existing_user[0] if existing_user else cursor.fetchone()[0]
        cursor.execute("""
            INSERT INTO password_history_v2 (user_id, password, gendate, expired)
            VALUES (%s, %s, %s, FALSE)
        """, (user_id, encrypted_password, gendate))
        
        conn.commit()

def log_password_generation(conn, username, success, error_details=None):
    """Log de la génération de mot de passe"""
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO auth_logs_v2 (user_id, action, success, details)
                SELECT id, 'password_generated', %s, %s
                FROM users_v2 WHERE username = %s
            """, (success, json.dumps({'error': error_details} if error_details else {}), username))
            conn.commit()
    except Exception as e:
        print(f"Erreur lors du logging: {e}") 