"""
Configuration module pour charger les variables d'environnement depuis .env
"""
import os
from pathlib import Path

def load_env_file(env_path=None):
    """
    Charge les variables d'environnement depuis un fichier .env
    Alternative native à python-decouple
    """
    if env_path is None:
        # Rechercher le fichier .env dans le répertoire parent (projet Django)
        base_dir = Path(__file__).resolve().parent.parent
        env_path = base_dir / '.env'
    
    if not os.path.exists(env_path):
        return
    
    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            # Ignorer les lignes vides et les commentaires
            if not line or line.startswith('#'):
                continue
            
            # Traiter les variables au format KEY=VALUE
            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
                
                # Supprimer les guillemets si présents
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                elif value.startswith("'") and value.endswith("'"):
                    value = value[1:-1]
                
                # Définir la variable d'environnement si elle n'existe pas déjà
                if key not in os.environ:
                    os.environ[key] = value

def get_env(key, default=None, cast=str):
    """
    Récupère une variable d'environnement avec un type de données spécifique
    """
    value = os.getenv(key, default)
    
    if value is None:
        return default
    
    if cast == bool:
        return value.lower() in ('true', '1', 'yes', 'on')
    elif cast == int:
        try:
            return int(value)
        except ValueError:
            return default
    elif cast == list:
        return [item.strip() for item in value.split(',') if item.strip()]
    
    return cast(value)

# Charger automatiquement le fichier .env
load_env_file() 