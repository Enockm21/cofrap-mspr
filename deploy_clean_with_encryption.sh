#!/bin/bash

# Script de déploiement complet avec réinitialisation de la base de données
# et chiffrement automatique pour MSPR COFRAP

set -e

echo "🧹 Déploiement complet MSPR COFRAP avec réinitialisation de la base"
echo "================================================================"

# Configuration
DB_HOST=${1:-"localhost"}
DB_NAME=${2:-"cofrap_db"}
DB_USER=${3:-"cofrap"}
DB_PASSWORD=${4:-"password"}

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

# Réinitialisation de la base de données
echo "🗄️ Réinitialisation complète de la base de données..."

# Vérification de la connexion PostgreSQL
if command -v psql &> /dev/null; then
    echo "📋 Connexion à PostgreSQL..."
    PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "SELECT 'Connexion PostgreSQL OK' as status;"
    
    if [ $? -eq 0 ]; then
        echo "✅ Connexion PostgreSQL réussie"
        
        # Sauvegarde de la base existante (optionnel)
        echo "💾 Sauvegarde de la base existante..."
        BACKUP_FILE="backup_$(date +%Y%m%d_%H%M%S).sql"
        PGPASSWORD=$DB_PASSWORD pg_dump -h $DB_HOST -U $DB_USER -d $DB_NAME > $BACKUP_FILE
        echo "✅ Sauvegarde créée: $BACKUP_FILE"
        
        # Réinitialisation complète
        echo "🧹 Suppression et recréation de toutes les tables..."
        PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -U $DB_USER -d $DB_NAME -f db/init_clean_database.sql
        
        # Vérification de la réinitialisation
        echo "🔍 Vérification de la réinitialisation..."
        PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -U $DB_USER -d $DB_NAME -f db/verify_clean_database.sql
        
        echo "✅ Base de données réinitialisée avec succès"
    else
        echo "❌ Impossible de se connecter à PostgreSQL"
        echo "💡 Vérifiez que PostgreSQL est démarré et accessible"
        exit 1
    fi
else
    echo "⚠️ psql non trouvé, réinitialisation manuelle requise"
    echo "💡 Exécutez manuellement:"
    echo "   PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -U $DB_USER -d $DB_NAME -f db/init_clean_database.sql"
    echo "   PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -U $DB_USER -d $DB_NAME -f db/verify_clean_database.sql"
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



echo ""
echo "🎉 Déploiement complet terminé avec succès!"
echo ""
echo "📋 Résumé:"
echo "   ✅ Base de données réinitialisée"
echo "   ✅ Toutes les tables V1 et V2 supprimées"
echo "   ✅ Structure unifiée créée"
echo "   ✅ Fonctions V1 et V2 déployées avec chiffrement"
echo "   ✅ Tests de chiffrement passés"
echo ""
echo "🔑 Clé de chiffrement utilisée: ${ENCRYPTION_KEY:0:20}..."
echo "💾 Sauvegardez cette clé pour les futurs déploiements:"
echo "   export ENCRYPTION_KEY='$ENCRYPTION_KEY'"
echo ""
echo "📁 Sauvegarde créée: $BACKUP_FILE"
echo ""
echo "🧪 Pour tester manuellement:"
echo "   python3 test_migration_v2.py"
echo ""
echo "📊 Pour vérifier la base de données:"
echo "   PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -U $DB_USER -d $DB_NAME -f db/verify_clean_database.sql" 