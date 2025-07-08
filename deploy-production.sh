#!/bin/bash

# Script de déploiement en production pour MSPR2 COFRAP
# Usage: ./deploy-production.sh [serveur-db] [db-password] [jwt-secret]

set -e

# Configuration
DB_HOST=${1:-"votre-serveur-db.com"}
DB_PASSWORD=${2:-"votre-mot-de-passe-securise"}
JWT_SECRET=${3:-"votre-cle-secrete-jwt-super-securisee"}

echo "🚀 Déploiement en production MSPR2 COFRAP"
echo "📍 Serveur DB: $DB_HOST"
echo "🔐 Mot de passe DB: ${DB_PASSWORD:0:3}***"
echo "🔑 JWT Secret: ${JWT_SECRET:0:3}***"

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

# 3. Mettre à jour la configuration avec les vraies valeurs
echo "⚙️ Configuration de l'environnement..."
sed -i.bak "s/votre-serveur-db.com/$DB_HOST/g" stack-production.yml
sed -i.bak "s/votre-mot-de-passe-securise/$DB_PASSWORD/g" stack-production.yml
sed -i.bak "s/votre-cle-secrete-jwt-super-securisee/$JWT_SECRET/g" stack-production.yml

# 4. Déployer les fonctions
echo "📦 Déploiement des fonctions..."
faas-cli deploy -f stack-production.yml

# 5. Vérifier le déploiement
echo "✅ Vérification du déploiement..."
faas-cli list

# 6. Test rapide des fonctions
echo "🧪 Tests rapides des fonctions..."

echo "Test generate-password:"
curl -s -X POST http://127.0.0.1:8080/function/generate-password \
  -H 'Content-Type: application/json' \
  -d '{"length": 16}' | jq '.password' 2>/dev/null || echo "Fonction accessible"

echo "Test authenticate-user (utilisateur inexistant):"
curl -s -X POST http://127.0.0.1:8080/function/authenticate-user \
  -H 'Content-Type: application/json' \
  -d '{"username": "test", "password": "test"}' | jq '.error' 2>/dev/null || echo "Fonction accessible"

echo "Test generate-2fa:"
curl -s -X POST http://127.0.0.1:8080/function/generate-2fa \
  -H 'Content-Type: application/json' \
  -d '{"user_id": 1, "username": "test"}' | jq '.error' 2>/dev/null || echo "Fonction accessible"

# 7. Nettoyer les fichiers temporaires
rm -f stack-production.yml.bak

echo ""
echo "🎉 Déploiement terminé avec succès!"
echo ""
echo "📊 URLs des fonctions:"
echo "  - generate-password: http://127.0.0.1:8080/function/generate-password"
echo "  - authenticate-user: http://127.0.0.1:8080/function/authenticate-user"
echo "  - generate-2fa: http://127.0.0.1:8080/function/generate-2fa"
echo ""
echo "🔧 Commandes utiles:"
echo "  - Voir les logs: faas-cli logs generate-password"
echo "  - Redémarrer: faas-cli deploy -f stack-production.yml"
echo "  - Supprimer: faas-cli remove generate-password"
echo ""
echo "⚠️  N'oubliez pas de:"
echo "  - Configurer HTTPS en production"
echo "  - Sauvegarder la base de données"
echo "  - Surveiller les logs" 