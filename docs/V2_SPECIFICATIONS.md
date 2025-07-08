# MSPR2 COFRAP - Spécifications V2

## 🎯 Vue d'ensemble

La version 2 du POC MSPR2 COFRAP introduit un système d'authentification sécurisé avec génération automatique de mots de passe, authentification à deux facteurs (2FA) et gestion de l'expiration des mots de passe.

## 🏗️ Architecture

### Structure de base de données

```sql
-- Table principale des utilisateurs
CREATE TABLE users_v2 (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL, -- Mot de passe chiffré
    mfa VARCHAR(255), -- Secret 2FA chiffré
    gendate BIGINT NOT NULL, -- Timestamp UNIX de génération
    expired BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Workflow des fonctions

1. **Génération de mot de passe** → **Génération 2FA** → **Authentification**
2. **Vérification d'expiration** → **Renouvellement si nécessaire**

## 🔐 Fonction 1: Génération de mot de passe sécurisé

### Endpoint
```
POST /function/generate-password-v2
```

### Paramètres d'entrée
```json
{
    "username": "michel.ranu"
}
```

### Paramètres de sortie
```json
{
    "success": true,
    "username": "michel.ranu",
    "qr_code": "iVBORw0KGgoAAAANSUhEUgAA...",
    "gendate": 1721916574,
    "message": "Mot de passe généré avec succès"
}
```

### Spécifications techniques

- **Longueur du mot de passe**: 24 caractères
- **Caractères inclus**:
  - Majuscules (A-Z)
  - Minuscules (a-z)
  - Chiffres (0-9)
  - Caractères spéciaux (!@#$%^&*()_+-=[]{}|;:,.<>?)
- **Chiffrement**: Fernet (AES-128)
- **QR Code**: PNG encodé en base64
- **Stockage**: Base de données PostgreSQL

### Exemple d'utilisation

```bash
curl -X POST http://127.0.0.1:8080/function/generate-password-v2 \
  -H 'Content-Type: application/json' \
  -d '{"username": "michel.ranu"}'
```

## 🔐 Fonction 2: Génération du secret 2FA

### Endpoint
```
POST /function/generate-2fa-v2
```

### Paramètres d'entrée
```json
{
    "username": "michel.ranu",
    "issuer": "MSPR2-COFRAP"
}
```

### Paramètres de sortie
```json
{
    "success": true,
    "username": "michel.ranu",
    "qr_code": "iVBORw0KGgoAAAANSUhEUgAA...",
    "provisioning_uri": "otpauth://totp/MSPR2-COFRAP:michel.ranu?secret=JBSWY3DPEHPK3PXP&issuer=MSPR2-COFRAP",
    "issuer": "MSPR2-COFRAP",
    "message": "Secret 2FA généré avec succès"
}
```

### Spécifications techniques

- **Algorithme**: TOTP (Time-based One-Time Password)
- **Secret**: 32 caractères base32
- **Période**: 30 secondes
- **Chiffrement**: Fernet (AES-128)
- **QR Code**: Compatible Google Authenticator, Authy, etc.

### Exemple d'utilisation

```bash
curl -X POST http://127.0.0.1:8080/function/generate-2fa-v2 \
  -H 'Content-Type: application/json' \
  -d '{"username": "michel.ranu"}'
```

## ✅ Fonction 3: Authentification utilisateur

### Endpoint
```
POST /function/authenticate-user-v2
```

### Paramètres d'entrée
```json
{
    "username": "michel.ranu",
    "password": "motdepasse123",
    "2FA_code": "123456"
}
```

### Paramètres de sortie

#### Authentification réussie
```json
{
    "success": true,
    "username": "michel.ranu",
    "message": "Authentification réussie",
    "user_id": 1
}
```

#### Mot de passe expiré
```json
{
    "error": "Mot de passe expiré",
    "password_expired": true,
    "message": "Le mot de passe a plus de 6 mois. Veuillez relancer le processus de génération."
}
```

#### Erreur d'authentification
```json
{
    "error": "Mot de passe incorrect"
}
```

### Spécifications techniques

- **Vérification mot de passe**: Déchiffrement et comparaison
- **Vérification 2FA**: Validation TOTP
- **Expiration**: 6 mois (15768000 secondes)
- **Logging**: Toutes les tentatives d'authentification

### Exemple d'utilisation

```bash
curl -X POST http://127.0.0.1:8080/function/authenticate-user-v2 \
  -H 'Content-Type: application/json' \
  -d '{
    "username": "michel.ranu",
    "password": "motdepasse123",
    "2FA_code": "123456"
  }'
```

## 🔄 Workflow complet

### 1. Création d'un nouvel utilisateur

```bash
# 1. Générer le mot de passe
curl -X POST http://127.0.0.1:8080/function/generate-password-v2 \
  -H 'Content-Type: application/json' \
  -d '{"username": "michel.ranu"}'

# 2. Générer le secret 2FA
curl -X POST http://127.0.0.1:8080/function/generate-2fa-v2 \
  -H 'Content-Type: application/json' \
  -d '{"username": "michel.ranu"}'
```

### 2. Authentification quotidienne

```bash
# Authentifier l'utilisateur
curl -X POST http://127.0.0.1:8080/function/authenticate-user-v2 \
  -H 'Content-Type: application/json' \
  -d '{
    "username": "michel.ranu",
    "password": "motdepasse123",
    "2FA_code": "123456"
  }'
```

### 3. Gestion de l'expiration

Si le mot de passe a plus de 6 mois, le système retourne une erreur d'expiration et l'utilisateur doit relancer le processus de génération.

## 🔧 Configuration

### Variables d'environnement

```bash
POSTGRES_HOST=postgres
POSTGRES_DB=mspr2_cofrap
POSTGRES_USER=postgres
POSTGRES_PASSWORD=password
ENCRYPTION_KEY=votre-cle-secrete-jwt-super-securisee
```

### Déploiement

```bash
# Déploiement complet V2
./deploy-v2.sh [serveur-db] [db-password] [jwt-secret] [encryption-key]

# Exemple
./deploy-v2.sh postgres password secret123 $(openssl rand -base64 32)
```

## 🧪 Tests

### Script de test automatique

```bash
python3 test/test_v2_functions.py
```

### Tests manuels

```bash
# Test de génération de mot de passe
curl -X POST http://127.0.0.1:8080/function/generate-password-v2 \
  -H 'Content-Type: application/json' \
  -d '{"username": "test.user"}'

# Test de génération 2FA
curl -X POST http://127.0.0.1:8080/function/generate-2fa-v2 \
  -H 'Content-Type: application/json' \
  -d '{"username": "test.user"}'

# Test d'authentification
curl -X POST http://127.0.0.1:8080/function/authenticate-user-v2 \
  -H 'Content-Type: application/json' \
  -d '{"username": "test.user", "password": "test", "2FA_code": "123456"}'
```

## 📊 Monitoring et logs

### Tables de logs

```sql
-- Logs d'authentification
SELECT * FROM auth_logs_v2 ORDER BY created_at DESC LIMIT 10;

-- Historique des mots de passe
SELECT * FROM password_history_v2 WHERE user_id = 1 ORDER BY created_at DESC;
```

### Commandes de monitoring

```bash
# Voir les logs d'une fonction
faas-cli logs generate-password-v2

# Statut des fonctions
faas-cli list

# Métriques
faas-cli describe generate-password-v2
```

## 🔒 Sécurité

### Chiffrement

- **Mots de passe**: Chiffrement Fernet (AES-128)
- **Secrets 2FA**: Chiffrement Fernet (AES-128)
- **Clé de chiffrement**: Variable d'environnement ENCRYPTION_KEY

### Bonnes pratiques

1. **Changer la clé de chiffrement** en production
2. **Configurer HTTPS** pour les communications
3. **Sauvegarder régulièrement** la base de données
4. **Surveiller les logs** d'authentification
5. **Limiter les tentatives** d'authentification

## 🚀 Prochaines étapes

1. **Frontend**: Interface utilisateur pour la gestion des mots de passe
2. **API Gateway**: Gestion centralisée des requêtes
3. **Monitoring**: Tableaux de bord et alertes
4. **Backup**: Système de sauvegarde automatique
5. **Audit**: Logs détaillés pour la conformité

## 📝 Notes de version

### V2.0.0
- ✅ Génération de mots de passe sécurisés (24 caractères)
- ✅ Génération de secrets 2FA avec QR codes
- ✅ Authentification avec vérification d'expiration
- ✅ Chiffrement des données sensibles
- ✅ Logging complet des opérations
- ✅ Tests automatisés
- ✅ Documentation complète 