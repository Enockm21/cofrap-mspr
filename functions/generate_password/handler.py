import json
import secrets
import string
import hashlib
import os
from datetime import datetime, timedelta
import psycopg2
from psycopg2.extras import RealDictCursor
import sys

def handle(event, context):
    """
    Fonction serverless pour générer des mots de passe sécurisés avec rotation
    Compatible OpenFaaS python3-http-debian
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
        salt = secrets.token_hex(16)
        password_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
        password_hash_hex = password_hash.hex()
        db_connection = get_db_connection()
        user_id = data.get('user_id')
        if user_id:
            store_password_hash(db_connection, user_id, password_hash_hex, salt)
        if data.get('enable_rotation', False):
            schedule_password_rotation(db_connection, user_id, data.get('rotation_days', 90))
        return json.dumps({
            'password': password,
            'hash': password_hash_hex,
            'salt': salt,
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

def store_password_hash(conn, user_id, password_hash, salt):
    """Stockage du hash du mot de passe en base"""
    with conn.cursor() as cursor:
        cursor.execute("""
            INSERT INTO password_history (user_id, password_hash, salt, created_at)
            VALUES (%s, %s, %s, %s)
        """, (user_id, password_hash, salt, datetime.now()))
        conn.commit()

def schedule_password_rotation(conn, user_id, rotation_days):
    """Planification de la rotation automatique du mot de passe"""
    with conn.cursor() as cursor:
        cursor.execute("""
            INSERT INTO password_rotation_schedule (user_id, rotation_date)
            VALUES (%s, %s)
            ON CONFLICT (user_id) DO UPDATE SET rotation_date = EXCLUDED.rotation_date
        """, (user_id, datetime.now() + timedelta(days=rotation_days)))
        conn.commit() 