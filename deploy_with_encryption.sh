#!/bin/bash

# Script de déploiement avec chiffrement automatique
echo "🔐 Déploiement MSPR COFRAP avec chiffrement..."

# Génération de la clé de chiffrement si elle n'existe pas
if [ -z "$ENCRYPTION_KEY" ]; then
    echo "🔑 Génération d'une nouvelle clé de chiffrement..."
    ENCRYPTION_KEY=$(python3 -c "
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode())
")
    export ENCRYPTION_KEY
    echo "✅ Clé de chiffrement générée: ${ENCRYPTION_KEY:0:20}..."
else
    echo "✅ Clé de chiffrement existante utilisée: ${ENCRYPTION_KEY:0:20}..."
fi

# Test du chiffrement
echo "🧪 Test du chiffrement..."
python3 test_encryption.py

if [ $? -ne 0 ]; then
    echo "❌ Erreur lors du test de chiffrement"
    exit 1
fi

# Déploiement des fonctions V1 avec chiffrement
echo "🚀 Déploiement des fonctions V1 avec chiffrement..."

# Fonction generate-password
echo "📦 Déploiement de generate-password..."
faas-cli deploy -f generate_password.yml --env ENCRYPTION_KEY="$ENCRYPTION_KEY"

# Fonction generate-2fa
echo "📦 Déploiement de generate-2fa..."
faas-cli deploy -f generate_2fa.yml --env ENCRYPTION_KEY="$ENCRYPTION_KEY"

# Fonction authenticate-user
echo "📦 Déploiement de authenticate-user..."
faas-cli deploy -f authenticate_user.yml --env ENCRYPTION_KEY="$ENCRYPTION_KEY"

# Déploiement des fonctions V2
echo "🚀 Déploiement des fonctions V2..."

# Fonction generate-password-v2
echo "📦 Déploiement de generate-password-v2..."
faas-cli deploy -f generate_password_v2.yml --env ENCRYPTION_KEY="$ENCRYPTION_KEY"

# Fonction generate-2fa-v2
echo "📦 Déploiement de generate-2fa-v2..."
faas-cli deploy -f generate_2fa_v2.yml --env ENCRYPTION_KEY="$ENCRYPTION_KEY"

# Fonction authenticate-user-v2
echo "📦 Déploiement de authenticate-user-v2..."
faas-cli deploy -f authenticate_user_v2.yml --env ENCRYPTION_KEY="$ENCRYPTION_KEY"

echo "✅ Déploiement terminé!"
echo ""
echo "🔑 Clé de chiffrement utilisée: ${ENCRYPTION_KEY:0:20}..."
echo "💾 Sauvegardez cette clé pour les futurs déploiements:"
echo "   export ENCRYPTION_KEY='$ENCRYPTION_KEY'"
echo ""
echo "🧪 Pour tester les fonctions:"
echo "   python3 test_migration_v2.py" 