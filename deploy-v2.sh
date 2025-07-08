#!/bin/bash

# Script de déploiement V2 pour MSPR2 COFRAP
# Usage: ./deploy-v2.sh [serveur-db] [db-password] [jwt-secret] [encryption-key]

set -e

# Configuration
DB_HOST=${1:-"localhost"}
DB_PASSWORD=${2:-"password"}
JWT_SECRET=${3:-"votre-cle-secrete-jwt-super-securisee"}
ENCRYPTION_KEY=${4:-$(openssl rand -base64 32)}

echo "🚀 Déploiement V2 MSPR2 COFRAP"
echo "📍 Serveur DB: $DB_HOST"
echo "🔐 Mot de passe DB: ${DB_PASSWORD:0:3}***"
echo "🔑 JWT Secret: ${JWT_SECRET:0:3}***"
echo "🔐 Encryption Key: ${ENCRYPTION_KEY:0:3}***"

# 1. Vérifier que OpenFaaS est installé
echo "📋 Vérification d'OpenFaaS..."
if ! command -v faas-cli &> /dev/null; then
    echo "❌ OpenFaaS CLI non trouvé. Installation..."
    curl -sL https://cli.openfaas.com | sh
fi

# 2. Vérifier la connexion à la gateway OpenFaaS
echo "🔗 Test de connexion à OpenFaaS Gateway..."
if ! faas-cli list &> /dev/null; then
    echo "❌ Impossible de se connecter à OpenFaaS Gateway"
    echo "💡 Assurez-vous qu'OpenFaaS est démarré sur http://127.0.0.1:8080"
    exit 1
fi

# 3. Initialiser la base de données V2
echo "🗄️ Initialisation de la base de données V2..."
if command -v psql &> /dev/null; then
    PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -U postgres -d mspr2_cofrap -f db/init_v2_database.sql
    echo "✅ Base de données V2 initialisée"
else
    echo "⚠️ psql non trouvé, initialisation de la base de données manuelle requise"
    echo "💡 Exécutez: PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -U postgres -d mspr2_cofrap -f db/init_v2_database.sql"
fi

# 4. Créer le fichier stack V2
echo "⚙️ Configuration de l'environnement V2..."
cat > stack-v2.yml << EOF
version: 1.0
provider:
  name: openfaas
  gateway: http://127.0.0.1:8080

functions:
  generate-password-v2:
    lang: python3-http-debian
    handler: ./functions/generate_password_v2
    image: generate-password-v2:latest
    environment:
      POSTGRES_HOST: $DB_HOST
      POSTGRES_DB: cofrap
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: $DB_PASSWORD
      ENCRYPTION_KEY: $ENCRYPTION_KEY
    labels:
      - "com.openfaas.scale.min=1"
      - "com.openfaas.scale.max=10"
    annotations:
      topic: "password-generation"
    secrets:
      - postgres-password
    limits:
      memory: 256Mi
      cpu: 200m
    requests:
      memory: 128Mi
      cpu: 100m

  generate-2fa-v2:
    lang: python3-http-debian
    handler: ./functions/generate_2fa_v2
    image: generate-2fa-v2:latest
    environment:
      POSTGRES_HOST: $DB_HOST
      POSTGRES_DB: mspr2_cofrap
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: $DB_PASSWORD
      ENCRYPTION_KEY: $ENCRYPTION_KEY
    labels:
      - "com.openfaas.scale.min=1"
      - "com.openfaas.scale.max=10"
    annotations:
      topic: "2fa-generation"
    secrets:
      - postgres-password
    limits:
      memory: 256Mi
      cpu: 200m
    requests:
      memory: 128Mi
      cpu: 100m

  authenticate-user-v2:
    lang: python3-http-debian
    handler: ./functions/authenticate_user_v2
    image: authenticate-user-v2:latest
    environment:
      POSTGRES_HOST: $DB_HOST
      POSTGRES_DB: mspr2_cofrap
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: $DB_PASSWORD
      ENCRYPTION_KEY: $ENCRYPTION_KEY
    labels:
      - "com.openfaas.scale.min=1"
      - "com.openfaas.scale.max=10"
    annotations:
      topic: "user-authentication"
    secrets:
      - postgres-password
    limits:
      memory: 256Mi
      cpu: 200m
    requests:
      memory: 128Mi
      cpu: 100m
EOF

# 5. Déployer les fonctions V2
echo "📦 Déploiement des fonctions V2..."
faas-cli deploy -f stack-v2.yml

# 6. Vérifier le déploiement
echo "✅ Vérification du déploiement V2..."
faas-cli list

# 7. Test rapide des fonctions V2
echo "🧪 Tests rapides des fonctions V2..."

echo "Test generate-password-v2:"
curl -s -X POST http://127.0.0.1:8080/function/generate-password-v2 \
  -H 'Content-Type: application/json' \
  -d '{"username": "test.user"}' | jq '.success' 2>/dev/null || echo "Fonction accessible"

echo "Test generate-2fa-v2:"
curl -s -X POST http://127.0.0.1:8080/function/generate-2fa-v2 \
  -H 'Content-Type: application/json' \
  -d '{"username": "test.user"}' | jq '.success' 2>/dev/null || echo "Fonction accessible"

echo "Test authenticate-user-v2 (utilisateur inexistant):"
curl -s -X POST http://127.0.0.1:8080/function/authenticate-user-v2 \
  -H 'Content-Type: application/json' \
  -d '{"username": "test", "password": "test"}' | jq '.error' 2>/dev/null || echo "Fonction accessible"

# 8. Nettoyer les fichiers temporaires
rm -f stack-v2.yml

echo ""
echo "🎉 Déploiement V2 terminé avec succès!"
echo ""
echo "📊 URLs des fonctions V2:"
echo "  - generate-password-v2: http://127.0.0.1:8080/function/generate-password-v2"
echo "  - generate-2fa-v2: http://127.0.0.1:8080/function/generate-2fa-v2"
echo "  - authenticate-user-v2: http://127.0.0.1:8080/function/authenticate-user-v2"
echo ""
echo "🔧 Commandes utiles:"
echo "  - Voir les logs: faas-cli logs generate-password-v2"
echo "  - Redémarrer: faas-cli deploy -f stack-v2.yml"
echo "  - Supprimer: faas-cli remove generate-password-v2"
echo ""
echo "📋 Exemples d'utilisation:"
echo "  # Générer un mot de passe"
echo "  curl -X POST http://127.0.0.1:8080/function/generate-password-v2 \\"
echo "    -H 'Content-Type: application/json' \\"
echo "    -d '{\"username\": \"michel.ranu\"}'"
echo ""
echo "  # Générer un secret 2FA"
echo "  curl -X POST http://127.0.0.1:8080/function/generate-2fa-v2 \\"
echo "    -H 'Content-Type: application/json' \\"
echo "    -d '{\"username\": \"michel.ranu\"}'"
echo ""
echo "  # Authentifier un utilisateur"
echo "  curl -X POST http://127.0.0.1:8080/function/authenticate-user-v2 \\"
echo "    -H 'Content-Type: application/json' \\"
echo "    -d '{\"username\": \"michel.ranu\", \"password\": \"motdepasse\", \"2FA_code\": \"123456\"}'"
echo ""
echo "⚠️  N'oubliez pas de:"
echo "  - Configurer HTTPS en production"
echo "  - Sauvegarder la base de données"
echo "  - Surveiller les logs"
echo "  - Changer la clé de chiffrement en production" 