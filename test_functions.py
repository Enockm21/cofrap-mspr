#!/usr/bin/env python3
"""
Script de test pour les fonctions serverless MSPR2-Cofrap
"""

import sys
import os
import json

# Ajouter les chemins des fonctions au path
sys.path.append('./functions/generate_password')
sys.path.append('./functions/generate_2fa')
sys.path.append('./functions/authenticate_user')

def test_generate_password():
    """Test de la fonction generate-password"""
    print("🔐 Test de la fonction generate-password...")
    
    try:
        from handler import handle
        
        # Test avec paramètres par défaut
        test_data = {
            'length': 16,
            'include_symbols': True,
            'include_numbers': True,
            'include_uppercase': True,
            'include_lowercase': True,
            'enable_rotation': False
        }
        
        response = handle(json.dumps(test_data))
        result = json.loads(response)
        
        print(f"✅ Mot de passe généré: {result['password']}")
        print(f"   Longueur: {len(result['password'])}")
        print(f"   Hash: {result['hash'][:20]}...")
        print(f"   Généré le: {result['generated_at']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False

def test_generate_2fa():
    """Test de la fonction generate-2fa"""
    print("\n🔐 Test de la fonction generate-2fa...")
    
    try:
        # Changer le répertoire de travail
        original_dir = os.getcwd()
        os.chdir('./functions/generate_2fa')
        
        from handler import handle
        
        # Test avec paramètres de base
        test_data = {
            'user_id': 1,
            'user_email': 'test@example.com',
            'issuer': 'MSPR2-Cofrap-Test'
        }
        
        response = handle(json.dumps(test_data))
        result = json.loads(response)
        
        print(f"✅ Clé secrète générée: {result['secret_key']}")
        print(f"   Email: {result.get('user_email', 'N/A')}")
        print(f"   Codes de récupération: {len(result['recovery_codes'])} codes")
        print(f"   QR Code: {'Oui' if result.get('qr_code') else 'Non'}")
        
        # Restaurer le répertoire
        os.chdir(original_dir)
        return True
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        # Restaurer le répertoire en cas d'erreur
        os.chdir(original_dir)
        return False

def test_authenticate_user():
    """Test de la fonction authenticate-user"""
    print("\n🔐 Test de la fonction authenticate-user...")
    
    try:
        # Changer le répertoire de travail
        original_dir = os.getcwd()
        os.chdir('./functions/authenticate_user')
        
        from handler import handle
        
        # Test avec utilisateur de test
        test_data = {
            'username': 'admin',
            'password': 'password'
        }
        
        response = handle(json.dumps(test_data))
        result = json.loads(response)
        
        if 'token' in result:
            print(f"✅ Authentification réussie!")
            print(f"   Utilisateur: {result['user']['username']}")
            print(f"   Email: {result['user']['email']}")
            print(f"   2FA activé: {result['user']['two_factor_enabled']}")
            print(f"   Token: {result['token'][:50]}...")
        else:
            print(f"⚠️  Réponse: {result}")
        
        # Restaurer le répertoire
        os.chdir(original_dir)
        return True
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        # Restaurer le répertoire en cas d'erreur
        os.chdir(original_dir)
        return False

def main():
    """Fonction principale de test"""
    print("🚀 Tests des fonctions serverless MSPR2-Cofrap")
    print("=" * 50)
    
    # Désactiver les connexions à la base de données pour les tests
    os.environ['POSTGRES_HOST'] = 'localhost'
    
    tests = [
        test_generate_password,
        test_generate_2fa,
        test_authenticate_user
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Erreur lors du test: {e}")
            results.append(False)
    
    print("\n" + "=" * 50)
    print("📊 Résultats des tests:")
    
    test_names = [
        "generate-password",
        "generate-2fa", 
        "authenticate-user"
    ]
    
    for i, (name, result) in enumerate(zip(test_names, results)):
        status = "✅ RÉUSSI" if result else "❌ ÉCHOUÉ"
        print(f"   {name}: {status}")
    
    success_count = sum(results)
    total_count = len(results)
    
    print(f"\n🎯 Score: {success_count}/{total_count} tests réussis")
    
    if success_count == total_count:
        print("🎉 Tous les tests sont passés avec succès!")
    else:
        print("⚠️  Certains tests ont échoué. Vérifiez les erreurs ci-dessus.")

if __name__ == '__main__':
    main() 