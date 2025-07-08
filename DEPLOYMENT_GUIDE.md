# Guide de Déploiement OpenFaaS - MSPR2 COFRAP

## 📋 Résumé du Projet

Ce projet implémente un système de gestion d'authentification sécurisée avec :
- **Génération de mots de passe sécurisés** avec rotation automatique
- **Authentification à deux facteurs (2FA)** avec codes TOTP
- **Authentification d'utilisateurs** avec vérification 2FA
- **Interface web Django** pour la gestion

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Frontend       │    │  Functions      │    │  Database       │
│  Django         │───▶│  OpenFaaS       │───▶│  PostgreSQL     │
│  Port: 8000     │    │  Ports: 8081-83 │    │  Port: 5432     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🚀 Déploiement Actuel (Docker Compose)

### ✅ État des Services

```bash
# Vérifier l'état des containers
docker ps

# Services actifs :
# - mspr2-cofrap-frontend (8000)
# - mspr2-cofrap-generate-password (8081)
# - mspr2-cofrap-generate-2fa (8082) 
# - mspr2-cofrap-authenticate-user (8083)
# - mspr2-cofrap-postgres (5432)
```

### 🔧 Commandes de Gestion

```bash
# Démarrer tous les services
docker-compose up -d

# Arrêter tous les services
docker-compose down

# Voir les logs
docker-compose logs -f [service-name]

# Redémarrer un service
docker-compose restart [service-name]
```

## 🧪 Tests des Fonctions

### 1. Génération de Mot de Passe

```bash
# Test basique
curl -X POST http://localhost:8081/function \
  -H "Content-Type: application/json" \
  -d '{"length": 16, "include_symbols": true}'

# Test avec utilisateur (sauvegarde en BDD)
curl -X POST http://localhost:8081/function \
  -H "Content-Type: application/json" \
  -d '{"length": 12, "include_symbols": true, "user_id": 1}'
```

**Réponse attendue :**
```json
{
  "password": "@u@LxwTtr@LZ",
  "hash": "124686471c9e5a785b53ee08ce42d4cb6c7645f6da215de2ef901d2e496c4e5c",
  "salt": "d94355707c4a4119a65184b71991cdd2",
  "generated_at": "2025-06-26T15:37:02.364409",
  "expires_at": null
}
```

### 2. Génération 2FA

```bash
# Générer une clé 2FA pour un utilisateur
curl -X POST http://localhost:8082/function \
  -H "Content-Type: application/json" \
  -d '{"user_id": 1, "user_email": "admin@mspr2-cofrap.local"}'
```

**Réponse attendue :**
```json
{
  "secret_key": "3LPBYEVAN6CW54HUYLZFD4TNMHPRO5NY",
  "qr_code": "iVBORw0KGgo...[base64]",
  "provisioning_uri": "otpauth://totp/MSPR2-Cofrap:admin%40mspr2-cofrap.local?secret=...",
  "recovery_codes": ["PU7VJH3K", "8UKLO85U", ...],
  "generated_at": "2025-06-26T15:38:10.662628",
  "expires_at": "2026-06-26T15:38:10.662631"
}
```

### 3. Authentification

```bash
# Test d'authentification sans 2FA
curl -X POST http://localhost:8083/function \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "mot_de_passe_généré"}'

# Test avec code 2FA
curl -X POST http://localhost:8083/function \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "mot_de_passe", "two_factor_code": "123456"}'
```

## 🔄 Migration vers OpenFaaS (Option Avancée)

Pour déployer sur un cluster OpenFaaS Kubernetes :

### 1. Prérequis

```bash
# Installer OpenFaaS CLI
curl -sL https://cli.openfaas.com | sudo sh

# Vérifier l'installation
faas-cli version
```

### 2. Fichiers de Configuration

Les fichiers `stack.yml` et templates sont prêts dans le dossier :
- `stack.yml` : Configuration des 3 fonctions
- `functions/*/handler.py` : Code adapté au format HTTP
- `deploy_functions.sh` : Script de déploiement automatisé

### 3. Déploiement OpenFaaS

```bash
# Construire les images
faas-cli build -f stack.yml

# Déployer les fonctions
faas-cli deploy -f stack.yml

# Vérifier le déploiement
faas-cli list
```

## 🗄️ Base de Données

### Structure

- **users** : Utilisateurs du système
- **password_history** : Historique des mots de passe
- **two_factor_auth** : Configuration 2FA
- **recovery_codes** : Codes de récupération
- **login_logs** : Logs d'authentification

### Initialisation

```bash
# Exécuter le script d'initialisation
docker exec -i mspr2-cofrap-postgres psql -U postgres < k8s/postgres-init.sql

# Se connecter à la base
docker exec -it mspr2-cofrap-postgres psql -U postgres -d mspr2_cofrap
```

## 🌐 Interface Web

Accéder à l'interface Django :
- **URL** : http://localhost:8000
- **Admin** : Créer un superuser Django si nécessaire

```bash
# Créer un superuser Django
docker exec -it mspr2-cofrap-frontend python manage.py createsuperuser
```

## 🔧 Surveillance et Monitoring

### Logs

```bash
# Voir les logs de toutes les fonctions
docker-compose logs -f

# Logs spécifiques
docker-compose logs -f mspr2-cofrap-generate-password
docker-compose logs -f mspr2-cofrap-authenticate-user
docker-compose logs -f mspr2-cofrap-generate-2fa
```

### Health Checks

```bash
# Script de vérification automatique
#!/bin/bash
echo "🔍 Vérification des services MSPR2-COFRAP..."

services=("8081" "8082" "8083" "8000")
names=("generate-password" "generate-2fa" "authenticate-user" "frontend")

for i in ${!services[@]}; do
    if curl -s http://localhost:${services[$i]} > /dev/null; then
        echo "✅ ${names[$i]} (${services[$i]}) : OK"
    else
        echo "❌ ${names[$i]} (${services[$i]}) : ERREUR"
    fi
done
```

## 🚨 Dépannage

### Problèmes Courants

1. **Base de données non initialisée**
   ```bash
   docker exec -i mspr2-cofrap-postgres psql -U postgres < k8s/postgres-init.sql
   ```

2. **Port déjà utilisé**
   ```bash
   # Trouver le processus utilisant le port
   lsof -i :8081
   # Arrêter Docker Compose et redémarrer
   docker-compose down && docker-compose up -d
   ```

3. **Problème de connexion DB**
   ```bash
   # Vérifier l'état du container PostgreSQL
   docker logs mspr2-cofrap-postgres
   ```

### Variables d'Environnement

```bash
# Configuration PostgreSQL
POSTGRES_HOST=postgres
POSTGRES_DB=mspr2_cofrap
POSTGRES_USER=postgres
POSTGRES_PASSWORD=password

# Configuration JWT
JWT_SECRET_KEY=your-secret-key-change-in-production
```

## 🎯 Prochaines Étapes

1. **Sécurisation** :
   - Changer les mots de passe par défaut
   - Configurer HTTPS
   - Implémenter rate limiting

2. **Optimisation** :
   - Mise en cache Redis
   - Load balancing
   - Monitoring avec Prometheus

3. **CI/CD** :
   - Pipeline GitHub Actions
   - Tests automatisés
   - Déploiement automatique

## 📞 Support

Pour toute question ou problème :
- Consulter les logs : `docker-compose logs -f`
- Vérifier l'état : `docker ps`
- Tests : Utiliser les commandes curl ci-dessus

---

**Équipe COFRAP - MSPR2 2025** 🔐

