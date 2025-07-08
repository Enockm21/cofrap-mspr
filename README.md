# MSPR2 COFRAP - Système de Gestion des Mots de Passe et Authentification

## 📋 Description du Projet

MSPR2 COFRAP est une application moderne de gestion des mots de passe et d'authentification sécurisée, construite avec des microservices serverless basés sur OpenFaaS. Le projet intègre des fonctionnalités avancées de sécurité incluant la rotation automatique des mots de passe, l'authentification à deux facteurs (2FA), et la génération sécurisée de mots de passe.

#Deploy app
chmod db

## 🚀 Installation et Déploiement

### Prérequis
- Docker et Docker Compose
- OpenFaaS CLI (`faas-cli`)
- PostgreSQL (local ou conteneurisé)
- Python 3.12+

### 1. Cloner le Repository
```bash
git clone <repository-url>
cd mspr
```

### 2. Configuration de l'Environnement
```bash
# Copier les fichiers de configuration
cp .env.example .env
# Éditer les variables d'environnement selon votre configuration
```

### 3. Initialisation de la Base de Données

#### Option A: Base de Données Locale
```bash
# Rendre le script d'initialisation exécutable
chmod +x db/init_local_database.sh

# Initialiser la base de données
./db/init_local_database.sh
```

#### Option B: Base de Données Conteneurisée
```bash

# Initialiser la base de données
# Connection
psql postgres

CREATE USER XXX WITH PASSWORD '';
CREATE DATABASE XX OWNER "";
## Création de la base de données locale
psql -h localhost -U XX -d XX -f db/init_local_db.sql
```

### 4. Ajout d'Utilisateurs de Test
```bash
# Ajouter des utilisateurs avec des mots de passe connus
psql -h localhost -U XX -d XX -f db/add_test_users.sql
```

**Utilisateurs de test disponibles :**
- `demo` / `password` (Staff)
- `user1` / `test123` (Utilisateur normal)
- `admin2` / `admin123` (Super admin)
- `testuser2` / `secret` (Utilisateur normal)

### 5. Déploiement des Fonctions Serverless
```bash
# Builder et déployer toutes les fonctions
faas-cli build -f stack.yml
docker push enock17/generate-password:latest
docker push enock17/authenticate-user:latest
docker push enock17/generate-2fa:latest
faas-cli deploy -f stack.yml
```

### 6. Démarrage du Frontend Django
```bash
cd frontend_django
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
```

## 🧪 Tests des Fonctions

### Test de la Fonction `generate-password`

#### Génération basique
```bash
curl -X POST http://127.0.0.1:8080/function/generate-password \
  -H 'Content-Type: application/json' \
  -d '{}'
```

#### Génération avec paramètres
```bash
curl -X POST http://127.0.0.1:8080/function/generate-password \
  -H 'Content-Type: application/json' \
  -d '{
    "length": 20,
    "include_symbols": true,
    "include_numbers": true,
    "include_uppercase": true,
    "include_lowercase": true,
    "user_id": 1,
    "enable_rotation": true,
    "rotation_days": 90
  }'
```

### Test de la Fonction `authenticate-user`

#### Authentification simple
```bash
curl -X POST http://127.0.0.1:8080/function/authenticate-user \
  -H 'Content-Type: application/json' \
  -d '{
    "username": "demo",
    "password": "password"
  }'
```

#### Authentification avec 2FA
```bash
curl -X POST http://127.0.0.1:8080/function/authenticate-user \
  -H 'Content-Type: application/json' \
  -d '{
    "username": "demo",
    "password": "password",
    "two_factor_code": "123456"
  }'
```

#### Authentification avec code de récupération
```bash
curl -X POST http://127.0.0.1:8080/function/authenticate-user \
  -H 'Content-Type: application/json' \
  -d '{
    "username": "demo",
    "password": "password",
    "recovery_code": "BACKUP123"
  }'
```

### Test de la Fonction `generate-2fa`

#### Génération de clé 2FA
```bash
curl -X POST http://127.0.0.1:8080/function/generate-2fa \
  -H 'Content-Type: application/json' \
  -d '{
    "user_id": 1,
    "username": "demo"
  }'
```

## 📊 Structure de la Base de Données

### Tables Principales
- **`users`** - Informations des utilisateurs
- **`password_history`** - Historique des mots de passe avec rotation
- **`password_rotation_schedule`** - Planification de la rotation
- **`two_factor_auth`** - Configuration 2FA
- **`recovery_codes`** - Codes de récupération 2FA
- **`login_logs`** - Logs d'authentification
- **`auth_logs`** - Logs d'actions d'authentification

## 🔧 Configuration

### Variables d'Environnement
```bash
# Base de données
POSTGRES_HOST=host.docker.internal
POSTGRES_DB=cofrap_db
POSTGRES_USER=cofrap
POSTGRES_PASSWORD=password
POSTGRES_PORT=5432


# OpenFaaS
OPENFAAS_GATEWAY=http://127.0.0.1:8080
```

### Configuration OpenFaaS
Le fichier `stack.yml` définit la configuration des fonctions serverless avec :
- Limites de ressources (CPU/Mémoire)
- Variables d'environnement
- Labels et annotations
- Images Docker

## 🛠️ Développement

### Structure du Projet
```
mspr/
├── functions/                 # Fonctions serverless
│   ├── generate_password/     # Génération de mots de passe
│   ├── authenticate_user/     # Authentification
│   └── generate_2fa/         # Génération 2FA
├── frontend_django/          # Interface utilisateur
├── db/                       # Scripts de base de données
├── k8s/                      # Configuration Kubernetes
├── scripts/                  # Scripts de déploiement
└── docs/                     # Documentation
```

### Ajout d'une Nouvelle Fonction
1. Créer le dossier dans `functions/`
2. Implémenter `handler.py`
3. Configurer `requirements.txt`
4. Ajouter la configuration dans `stack.yml`
5. Builder et déployer

### Tests Locaux
```bash
# Test d'une fonction spécifique
faas-cli build -f functions/generate_password.yml
faas-cli deploy -f functions/generate_password.yml

# Test avec curl
curl -X POST http://127.0.0.1:8080/function/generate-password \
  -H 'Content-Type: application/json' \
  -d '{"length": 16}'
```

## 🔒 Sécurité

### Fonctionnalités de Sécurité
- **Hachage PBKDF2** avec 100 000 itérations
- **Rotation automatique** des mots de passe
- **Authentification à deux facteurs** (TOTP)
- **Codes de récupération** pour 2FA
- **Logs d'audit** complets
- **Expiration des sessions** JWT
- **Validation des entrées** robuste

### Bonnes Pratiques
- Changer les clés secrètes en production
- Utiliser HTTPS en production
- Configurer des limites de taux
- Surveiller les logs d'authentification
- Sauvegarder régulièrement la base de données

## 📈 Monitoring et Logs

### Prometheus
```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'openfaas'
    static_configs:
      - targets: ['gateway:8080']
```

### AlertManager
```yaml
# alertmanager.yml
global:
  smtp_smarthost: 'localhost:587'
  smtp_from: 'alertmanager@example.com'

route:
  group_by: ['alertname']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 1h
  receiver: 'web.hook'
```

## 🚀 Déploiement en Production

### Docker Compose
```bash
# Démarrage complet
docker-compose up -d

# Vérification des services
docker-compose ps
```

### Kubernetes
```bash
# Déploiement sur K8s
kubectl apply -f k8s/

# Vérification
kubectl get pods
kubectl get services
```

## 🤝 Contribution

### Workflow de Développement
1. Fork du repository
2. Création d'une branche feature
3. Développement et tests
4. Pull Request avec description détaillée
5. Review et merge

### Standards de Code
- Respecter PEP 8 pour Python
- Commentaires en français
- Tests unitaires pour les nouvelles fonctionnalités
- Documentation des API

## 📞 Support

### Problèmes Courants
1. **Erreur de connexion à la base de données**
   - Vérifier les variables d'environnement
   - S'assurer que PostgreSQL est démarré

2. **Fonction ne répond pas**
   - Vérifier les logs OpenFaaS
   - Contrôler la configuration dans `stack.yml`

3. **Erreur d'authentification**
   - Vérifier la présence des utilisateurs dans `password_history`
   - Contrôler les logs d'authentification

### Contacts
- **Développeur**: Enock Mukokom
- **Email**: enock.mukokom@gmail.com
- **Projet**: MSPR2 COFRAP

## 📄 Licence

Ce projet est développé dans le cadre du MSPR (Mise en Situation Professionnelle Réelle) à l'EPSI.

---

**Version**: 2.0  
**Dernière mise à jour**: Juillet 2025  
**Statut**: En développement