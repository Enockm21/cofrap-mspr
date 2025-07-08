import json
import hashlib
import os
import jwt
import secrets
import asyncio
from datetime import datetime, timedelta
import asyncpg
import pyotp



async def get_db_connection():
    """Connexion à la base de données PostgreSQL locale"""
    try:
        return await asyncpg.connect(
            host=os.getenv('POSTGRES_HOST', 'host.docker.internal'),
            database=os.getenv('POSTGRES_DB', 'cofrap_db'),
            user=os.getenv('POSTGRES_USER', 'cofrap'),
            password=os.getenv('POSTGRES_PASSWORD', 'password'),
            port=os.getenv('POSTGRES_PORT', '5432')
        )
    except Exception as e:
        print(f"Erreur de connexion à la base de données: {e}")
        raise

async def get_user_by_username(conn, username):
    """Récupération d'un utilisateur par son nom d'utilisateur"""
    row = await conn.fetchrow("""
        SELECT id, username, email, is_active, created_at
        FROM users WHERE username = $1 AND is_active = $2
    """, username, True)
    return dict(row) if row else None

async def verify_password(conn, user_id, password):
    """Vérification du mot de passe"""
    row = await conn.fetchrow("""
        SELECT password_hash, salt FROM password_history 
        WHERE user_id = $1 ORDER BY created_at DESC LIMIT 1
    """, user_id)
    
    if not row:
        return False
    
    password_hash, salt = row['password_hash'], row['salt']
    
    # Vérification du hash
    computed_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
    return computed_hash.hex() == password_hash

async def check_2fa_enabled(conn, user_id):
    """Vérification si 2FA est activé pour l'utilisateur"""
    row = await conn.fetchrow("""
        SELECT is_active FROM two_factor_auth 
        WHERE user_id = $1 AND is_active = $2
    """, user_id, True)
    return row is not None

async def verify_2fa_code(conn, user_id, code):
    """Vérification d'un code 2FA"""
    row = await conn.fetchrow("""
        SELECT secret_key FROM two_factor_auth 
        WHERE user_id = $1 AND is_active = $2
    """, user_id, True)
    
    if not row:
        return False
    
    secret_key = row['secret_key']
    totp = pyotp.TOTP(secret_key)
    return totp.verify(code)

async def verify_recovery_code(conn, user_id, code):
    """Vérification d'un code de récupération"""
    row = await conn.fetchrow("""
        SELECT id FROM recovery_codes 
        WHERE user_id = $1 AND code = $2 AND is_used = $3
    """, user_id, code, False)
    
    if row:
        # Marquer le code comme utilisé
        await conn.execute("""
            UPDATE recovery_codes SET is_used = $1, used_at = $2 
            WHERE id = $3
        """, True, datetime.now(), row['id'])
        return True
    
    return False

async def is_password_expired(conn, user_id):
    """Vérification si le mot de passe a expiré"""
    row = await conn.fetchrow("""
        SELECT created_at FROM password_history 
        WHERE user_id = $1 ORDER BY created_at DESC LIMIT 1
    """, user_id)
    
    if not row:
        return True
    
    # Vérifier si le mot de passe a plus de 90 jours
    password_age = datetime.now() - row['created_at']
    return password_age.days > 90

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

async def update_last_login(conn, user_id):
    """Mise à jour de la dernière connexion"""
    try:
        await conn.execute("""
            UPDATE users SET last_login = $1 WHERE id = $2
        """, datetime.now(), user_id)
    except Exception as e:
        print(f"Impossible de mettre à jour last_login: {e}")
        # Continue sans mettre à jour si la colonne n'existe pas

async def log_successful_login(conn, user_id):
    """Log d'une connexion réussie"""
    try:
        await conn.execute("""
            INSERT INTO login_logs (user_id, login_time, success, ip_address)
            VALUES ($1, $2, $3, $4)
        """, user_id, datetime.now(), True, '127.0.0.1')
    except Exception as e:
        print(f"Impossible de logger la connexion réussie: {e}")
        # Continue sans logger si la table n'existe pas

async def log_failed_attempt(conn, username, reason):
    """Log d'une tentative de connexion échouée"""
    try:
        await conn.execute("""
            INSERT INTO login_logs (username, login_time, success, reason, ip_address)
            VALUES ($1, $2, $3, $4, $5)
        """, username, datetime.now(), False, reason, '127.0.0.1')
    except Exception as e:
        print(f"Impossible de logger la tentative échouée: {e}")
        # Continue sans logger si la table n'existe pas

# Wrapper pour OpenFaaS (non-async)
def handle(event, context):
    """Wrapper pour rendre la fonction compatible avec OpenFaaS"""
    return asyncio.run(handle_async(event, context))

async def handle_async(event, context):
    """Version asynchrone du handler"""
    return await handle_async_impl(event, context)

async def handle_async_impl(event, context):
    """Version asynchrone du handler"""
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
        
        if not username or not password:
            return json.dumps({
                'error': 'username et password sont requis'
            })
        
        # Connexion à PostgreSQL
        try:
            db_connection = await get_db_connection()
        except Exception as db_error:
            print(f"Erreur de connexion à la base de données: {db_error}")
            return json.dumps({
                'error': 'Erreur de connexion à la base de données',
                'details': str(db_error)
            })
        
        try:
            # Vérification de l'utilisateur
            user = await get_user_by_username(db_connection, username)
            if not user:
                await log_failed_attempt(db_connection, username, 'Utilisateur non trouvé')
                return json.dumps({
                    'error': 'Identifiants invalides'
                })
            
            # Vérification du mot de passe
            if not await verify_password(db_connection, user['id'], password):
                await log_failed_attempt(db_connection, username, 'Mot de passe incorrect')
                return json.dumps({
                    'error': 'Identifiants invalides'
                })
            
            # Vérification si l'utilisateur a 2FA activé
            two_factor_enabled = await check_2fa_enabled(db_connection, user['id'])
            
            if two_factor_enabled:
                if not two_factor_code and not recovery_code:
                    return json.dumps({
                        'error': 'Code 2FA requis',
                        'requires_2fa': True
                    })
                
                # Vérification du code 2FA ou du code de récupération
                if two_factor_code:
                    if not await verify_2fa_code(db_connection, user['id'], two_factor_code):
                        await log_failed_attempt(db_connection, username, 'Code 2FA incorrect')
                        return json.dumps({
                            'error': 'Code 2FA incorrect'
                        })
                elif recovery_code:
                    if not await verify_recovery_code(db_connection, user['id'], recovery_code):
                        await log_failed_attempt(db_connection, username, 'Code de récupération incorrect')
                        return json.dumps({
                            'error': 'Code de récupération incorrect'
                        })
            
            # Vérification de l'expiration du mot de passe
            if await is_password_expired(db_connection, user['id']):
                return json.dumps({
                    'error': 'Mot de passe expiré',
                    'requires_password_change': True
                })
            
            # Génération du token JWT
            token = generate_jwt_token(user)
            
            # Mise à jour de la dernière connexion
            await update_last_login(db_connection, user['id'])
            
            # Log de la connexion réussie
            await log_successful_login(db_connection, user['id'])
            
            return json.dumps({
                'token': token,
                'user': {
                    'id': user['id'],
                    'username': user['username'],
                    'email': user['email'],
                    'two_factor_enabled': two_factor_enabled
                },
                'expires_at': (datetime.now() + timedelta(hours=24)).isoformat()
            })
            
        finally:
            await db_connection.close()
        
    except json.JSONDecodeError:
        return json.dumps({'error': 'Format JSON invalide'})
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"Erreur dans authenticate_user: {e}")
        print(f"Traceback: {error_trace}")
        return json.dumps({
            'error': f'Erreur interne: {str(e)}',
            'details': error_trace
        }) 