#!/usr/bin/env python3
"""
Script de test local pour les fonctions V2 de MSPR2 COFRAP
Teste les fonctions directement sans OpenFaaS
"""

import sys
import os
import json
import time
from datetime import datetime

# Ajouter le répertoire des fonctions au path
sys.path.append('functions/generate_password_v2')
sys.path.append('functions/generate_2fa_v2')
sys.path.append('functions/authenticate_user_v2')

def test_generate_password_v2():
    """Test local de la génération de mot de passe v2"""
    print("🧪 Test local de génération de mot de passe v2...")
    
    try:
        from functions.generate_password_v2.handler import handle
        
        # Simuler l'événement OpenFaaS
        event = type('Event', (), {
            'body': json.dumps({'username': 'test.user.v2'})
        })()
        
        # Appeler la fonction
        result = handle(event, None)
        data = json.loads(result)
        
        if data.get('success'):
            print("✅ Génération de mot de passe v2 réussie")
            print(f"   Username: {data['username']}")
            print(f"   Gendate: {data['gendate']}")
            print(f"   QR Code généré: {len(data['qr_code'])} caractères")
            return True
        else:
            print(f"❌ Échec génération mot de passe v2: {data.get('error')}")
            return False
            
    except Exception as e:
        print(f"❌ Erreur lors du test: {e}")
        return False

def test_generate_2fa_v2():
    """Test local de la génération 2FA v2"""
    print("\n🧪 Test local de génération 2FA v2...")
    
    try:
        from functions.generate_2fa_v2.handler import handle
        
        # Simuler l'événement OpenFaaS
        event = type('Event', (), {
            'body': json.dumps({'username': 'test.user.v2'})
        })()
        
        # Appeler la fonction
        result = handle(event, None)
        data = json.loads(result)
        
        if data.get('success'):
            print("✅ Génération 2FA v2 réussie")
            print(f"   Username: {data['username']}")
            print(f"   Issuer: {data['issuer']}")
            print(f"   QR Code généré: {len(data['qr_code'])} caractères")
            return True
        else:
            print(f"❌ Échec génération 2FA v2: {data.get('error')}")
            return False
            
    except Exception as e:
        print(f"❌ Erreur lors du test: {e}")
        return False

def test_authenticate_user_v2():
    """Test local de l'authentification v2"""
    print("\n🧪 Test local d'authentification v2 (utilisateur inexistant)...")
    
    try:
        from functions.authenticate_user_v2.handler import handle
        
        # Simuler l'événement OpenFaaS
        event = type('Event', (), {
            'body': json.dumps({
                'username': 'utilisateur.inexistant',
                'password': 'motdepasse123'
            })
        })()
        
        # Appeler la fonction
        result = handle(event, None)
        data = json.loads(result)
        
        if data.get('error') == 'Utilisateur inexistant':
            print("✅ Test d'authentification v2 échoué correctement (utilisateur inexistant)")
            return True
        else:
            print(f"❌ Réponse inattendue: {data}")
            return False
            
    except Exception as e:
        print(f"❌ Erreur lors du test: {e}")
        return False

def main():
    """Fonction principale de test local"""
    print("🚀 Tests locaux des fonctions V2 MSPR2 COFRAP")
    print("=" * 50)
    
    # Configuration des variables d'environnement pour les tests
    os.environ['POSTGRES_HOST'] = 'localhost'
    os.environ['POSTGRES_DB'] = 'cofrap_db'
    os.environ['POSTGRES_USER'] = 'cofrap'
    os.environ['POSTGRES_PASSWORD'] = 'password'
    os.environ['ENCRYPTION_KEY'] = '92gQrPQ9sdYqUoub4z1OVHhIA_XWF35E9xHKE-QKq5o='
    
    tests = [
        ("Génération de mot de passe v2", test_generate_password_v2),
        ("Génération 2FA v2", test_generate_2fa_v2),
        ("Authentification v2", test_authenticate_user_v2)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        print("-" * 30)
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Erreur lors du test: {e}")
            results.append((test_name, False))
    
    # Résumé des tests
    print("\n" + "=" * 50)
    print("📊 RÉSUMÉ DES TESTS LOCAUX")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print(f"\n🎯 Résultat: {passed}/{total} tests réussis")
    
    if passed == total:
        print("🎉 Toutes les fonctions v2 fonctionnent correctement en local!")
    else:
        print("⚠️ Certains tests ont échoué. Vérifiez la configuration.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1) 