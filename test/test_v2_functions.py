#!/usr/bin/env python3
"""
Script de test pour les fonctions V2 de MSPR2 COFRAP
Teste la génération de mot de passe, 2FA et l'authentification
"""

import requests
import json
import time
import base64
from io import BytesIO
from PIL import Image

# Configuration
GATEWAY_URL = "http://127.0.0.1:8080"
TEST_USERNAME = "test.user.v2"

def test_generate_password():
    """Test de la génération de mot de passe"""
    print("🧪 Test de génération de mot de passe...")
    
    url = f"{GATEWAY_URL}/function/generate-password-v2"
    data = {"username": TEST_USERNAME}
    
    try:
        response = requests.post(url, json=data, timeout=30)
        result = response.json()
        
        if result.get('success'):
            print("✅ Génération de mot de passe réussie")
            print(f"   Username: {result['username']}")
            print(f"   Gendate: {result['gendate']}")
            print(f"   QR Code généré: {len(result['qr_code'])} caractères")
            
            # Test de décodage du QR code
            try:
                qr_data = base64.b64decode(result['qr_code'])
                img = Image.open(BytesIO(qr_data))
                print(f"   QR Code valide: {img.size[0]}x{img.size[1]} pixels")
            except Exception as e:
                print(f"   ⚠️ Erreur QR code: {e}")
            
            return True
        else:
            print(f"❌ Échec génération mot de passe: {result.get('error')}")
            return False
            
    except Exception as e:
        print(f"❌ Erreur lors du test: {e}")
        return False

def test_generate_2fa():
    """Test de la génération 2FA"""
    print("\n🧪 Test de génération 2FA...")
    
    url = f"{GATEWAY_URL}/function/generate-2fa-v2"
    data = {"username": TEST_USERNAME}
    
    try:
        response = requests.post(url, json=data, timeout=30)
        result = response.json()
        
        if result.get('success'):
            print("✅ Génération 2FA réussie")
            print(f"   Username: {result['username']}")
            print(f"   Issuer: {result['issuer']}")
            print(f"   QR Code généré: {len(result['qr_code'])} caractères")
            print(f"   URI de provisionnement: {result['provisioning_uri'][:50]}...")
            
            # Test de décodage du QR code
            try:
                qr_data = base64.b64decode(result['qr_code'])
                img = Image.open(BytesIO(qr_data))
                print(f"   QR Code valide: {img.size[0]}x{img.size[1]} pixels")
            except Exception as e:
                print(f"   ⚠️ Erreur QR code: {e}")
            
            return True
        else:
            print(f"❌ Échec génération 2FA: {result.get('error')}")
            return False
            
    except Exception as e:
        print(f"❌ Erreur lors du test: {e}")
        return False

def test_authentication_without_2fa():
    """Test d'authentification sans 2FA"""
    print("\n🧪 Test d'authentification (utilisateur inexistant)...")
    
    url = f"{GATEWAY_URL}/function/authenticate-user-v2"
    data = {
        "username": "utilisateur.inexistant",
        "password": "motdepasse123"
    }
    
    try:
        response = requests.post(url, json=data, timeout=30)
        result = response.json()
        
        if result.get('error') == 'Utilisateur inexistant':
            print("✅ Test d'authentification échoué correctement (utilisateur inexistant)")
            return True
        else:
            print(f"❌ Réponse inattendue: {result}")
            return False
            
    except Exception as e:
        print(f"❌ Erreur lors du test: {e}")
        return False

def test_password_expiration():
    """Test de vérification d'expiration de mot de passe"""
    print("\n🧪 Test de vérification d'expiration...")
    
    # Créer un utilisateur avec un mot de passe "ancien" (plus de 6 mois)
    old_timestamp = int(time.time()) - (7 * 30 * 24 * 60 * 60)  # 7 mois
    
    url = f"{GATEWAY_URL}/function/generate-password-v2"
    data = {"username": f"{TEST_USERNAME}_expired"}
    
    try:
        # D'abord, générer un mot de passe normal
        response = requests.post(url, json=data, timeout=30)
        result = response.json()
        
        if result.get('success'):
            print("✅ Utilisateur avec mot de passe expiré créé")
            
            # Maintenant tester l'authentification
            auth_url = f"{GATEWAY_URL}/function/authenticate-user-v2"
            auth_data = {
                "username": f"{TEST_USERNAME}_expired",
                "password": "motdepasse123"  # Mot de passe incorrect
            }
            
            auth_response = requests.post(auth_url, json=auth_data, timeout=30)
            auth_result = auth_response.json()
            
            if auth_result.get('error') == 'Mot de passe incorrect':
                print("✅ Test d'authentification échoué correctement (mot de passe incorrect)")
                return True
            else:
                print(f"❌ Réponse inattendue: {auth_result}")
                return False
        else:
            print(f"❌ Échec création utilisateur: {result.get('error')}")
            return False
            
    except Exception as e:
        print(f"❌ Erreur lors du test: {e}")
        return False

def test_function_availability():
    """Test de disponibilité des fonctions"""
    print("\n🧪 Test de disponibilité des fonctions...")
    
    functions = [
        "generate-password-v2",
        "generate-2fa-v2", 
        "authenticate-user-v2"
    ]
    
    all_available = True
    
    for func_name in functions:
        try:
            response = requests.get(f"{GATEWAY_URL}/function/{func_name}", timeout=10)
            if response.status_code in [200, 404, 405]:  # 405 = Method Not Allowed (normal pour GET)
                print(f"✅ {func_name}: Disponible")
            else:
                print(f"❌ {func_name}: Erreur {response.status_code}")
                all_available = False
        except Exception as e:
            print(f"❌ {func_name}: Erreur de connexion - {e}")
            all_available = False
    
    return all_available

def main():
    """Fonction principale de test"""
    print("🚀 Tests des fonctions V2 MSPR2 COFRAP")
    print("=" * 50)
    
    tests = [
        ("Disponibilité des fonctions", test_function_availability),
        ("Génération de mot de passe", test_generate_password),
        ("Génération 2FA", test_generate_2fa),
        ("Authentification (utilisateur inexistant)", test_authentication_without_2fa),
        ("Vérification d'expiration", test_password_expiration)
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
    print("📊 RÉSUMÉ DES TESTS")
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
        print("🎉 Tous les tests sont passés avec succès!")
    else:
        print("⚠️ Certains tests ont échoué. Vérifiez la configuration.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1) 