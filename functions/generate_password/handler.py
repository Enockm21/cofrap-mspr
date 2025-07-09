import json
import secrets
import string
import hashlib
import os
from datetime import datetime, timedelta
import psycopg2
from psycopg2.extras import RealDictCursor
import sys
from cryptography.fernet import Fernet

def handle(event, context):
    """
    Fonction serverless pour générer des mots de passe sécurisés avec rotation
    Compatible OpenFaaS python3-http-debian
    """
    # Gérer les requêtes OPTIONS pour CORS preflight
    if hasattr(event, 'method') and event.method == 'OPTIONS':
        return context.headers({
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization',
            'Access-Control-Max-Age': '3600'
        }).status(200).succeed('')
    
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
        length = data.get('length', 16)
        include_symbols = data.get('include_symbols', True)
        include_numbers = data.get('include_numbers', True)
        include_uppercase = data.get('include_uppercase', True)
        include_lowercase = data.get('include_lowercase', True)
        # Validation des paramètres
        if length < 8 or length > 128:
            return json.dumps({'error': 'La longueur du mot de passe doit être entre 8 et 128 caractères'})
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
            return json.dumps({'error': 'Au moins un type de caractère doit être sélectionné'})
        password = ''.join(secrets.choice(chars) for _ in range(length))
        gendate = int(datetime.now().timestamp())
        
        # Chiffrement du mot de passe
        encryption_key = get_encryption_key()
        fernet = Fernet(encryption_key)
        encrypted_password = fernet.encrypt(password.encode()).decode()
        
        db_connection = get_db_connection()
        username = data.get('username')
        if username:
            store_password_v2(db_connection, username, encrypted_password, gendate)
        if data.get('enable_rotation', False):
            schedule_password_rotation(db_connection, username, data.get('rotation_days', 90))
        return json.dumps({
            'success': True,
            'username': username,
            'password': password,  # Mot de passe en clair pour l'utilisateur
            'gendate': gendate,
            'generated_at': datetime.now().isoformat(),
            'expires_at': (datetime.now() + timedelta(days=data.get('rotation_days', 90))).isoformat() if data.get('enable_rotation') else None
        })
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

def get_encryption_key():
    """Récupération de la clé de chiffrement depuis les variables d'environnement"""
    key = os.getenv('ENCRYPTION_KEY')
    if not key:
        # Génération d'une clé par défaut (à changer en production)
        key = Fernet.generate_key().decode()
        print("⚠️  ATTENTION: Utilisation d'une clé de chiffrement par défaut")
    return key.encode()

def store_password_v2(conn, username, encrypted_password, gendate):
    """Stockage du mot de passe V2 chiffré en base"""
    with conn.cursor() as cursor:
        # Vérifier si l'utilisateur existe
        cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
        user_result = cursor.fetchone()
        if not user_result:
            raise Exception(f"Utilisateur {username} non trouvé")
        
        user_id = user_result[0]
        
        # Mise à jour de l'utilisateur
        cursor.execute("""
            UPDATE users 
            SET password = %s, gendate = %s, expired = FALSE, updated_at = CURRENT_TIMESTAMP
            WHERE username = %s
        """, (encrypted_password, gendate, username))
        
        # Ajout dans l'historique
        cursor.execute("""
            INSERT INTO password_history (user_id, password, gendate, expired)
            VALUES (%s, %s, %s, FALSE)
        """, (user_id, encrypted_password, gendate))
        
        conn.commit()

def schedule_password_rotation(conn, username, rotation_days):
    """Planification de la rotation automatique du mot de passe"""
    with conn.cursor() as cursor:
        # Récupérer l'ID de l'utilisateur
        cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
        user_result = cursor.fetchone()
        if not user_result:
            raise Exception(f"Utilisateur {username} non trouvé")
        
        user_id = user_result[0]
        
        cursor.execute("""
            INSERT INTO password_rotation_schedule (user_id, rotation_date)
            VALUES (%s, %s)
            ON CONFLICT (user_id) DO UPDATE SET rotation_date = EXCLUDED.rotation_date
        """, (user_id, datetime.now() + timedelta(days=rotation_days)))
        conn.commit() 