# 🚀 Guide de Déploiement en Production - MSPR2 COFRAP

## 📋 Prérequis sur Votre Serveur

### 1. Installation d'OpenFaaS
```bash
# Installation d'OpenFaaS
curl -sL https://cli.openfaas.com | sh

# Ou avec Docker
docker run -d --name openfaas \
  --restart=always \
  -p 8080:8080 \
  -p 9090:9090 \
  openfaas/gateway:latest
```

### 2. Installation de Docker (si pas déjà fait)
```bash
# Ubuntu/Debian
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# CentOS/RHEL
sudo yum install -y docker
sudo systemctl start docker
sudo systemctl enable docker
```

### 3. Configuration de la Base de Données Distante
```bash
# Sur votre serveur de base de données
sudo -u postgres psql

# Créer l'utilisateur et la base
CREATE USER cofrap WITH PASSWORD 'votre-mot-de-passe-securise';
CREATE DATABASE cofrap_db OWNER cofrap;
GRANT ALL PRIVILEGES ON DATABASE cofrap_db TO cofrap;
\q

# Initialiser la base de données
psql -h localhost -U cofrap -d cofrap_db -f init_local_db.sql
psql -h localhost -U cofrap -d cofrap_db -f add_test_users.sql
```

## 🔧 Étapes de Déploiement

### Étape 1: Préparer les Images Docker
```bash
# Sur votre machine de développement
docker tag enock17/generate-password:latest enock17/generate-password:v1.0
docker tag enock17/authenticate-user:latest enock17/authenticate-user:v1.0
docker tag enock17/generate-2fa:latest enock17/generate-2fa:v1.0

# Pousser sur Docker Hub
docker push enock17/generate-password:v1.0
docker push enock17/authenticate-user:v1.0
docker push enock17/generate-2fa:v1.0
```

### Étape 2: Transférer les Fichiers sur le Serveur
```bash
# Copier les fichiers nécessaires
scp stack-production.yml user@votre-serveur.com:/home/user/
scp deploy-production.sh user@votre-serveur.com:/home/user/
scp db/init_local_db.sql user@votre-serveur.com:/home/user/
scp db/add_test_users.sql user@votre-serveur.com:/home/user/
```

### Étape 3: Déployer sur le Serveur
```bash
# Se connecter au serveur
ssh user@votre-serveur.com

# Rendre le script exécutable
chmod +x deploy-production.sh

# Déployer avec vos paramètres
./deploy-production.sh "votre-serveur-db.com" "votre-mot-de-passe-securise" "votre-cle-secrete-jwt"
```

## 🔒 Configuration de Sécurité

### 1. Variables d'Environnement Sécurisées
```bash
# Créer un fichier .env sécurisé
cat > .env << EOF
POSTGRES_HOST=votre-serveur-db.com
POSTGRES_DB=cofrap_db
POSTGRES_USER=cofrap
POSTGRES_PASSWORD=votre-mot-de-passe-securise
POSTGRES_PORT=5432
JWT_SECRET_KEY=votre-cle-secrete-jwt-super-securisee
EOF

# Protéger le fichier
chmod 600 .env
```

### 2. Configuration du Firewall
```bash
# Ouvrir uniquement les ports nécessaires
sudo ufw allow 8080/tcp  # OpenFaaS Gateway
sudo ufw allow 5432/tcp  # PostgreSQL (si sur le même serveur)
sudo ufw enable
```

### 3. Configuration SSL/HTTPS
```bash
# Installer Certbot
sudo apt install certbot

# Obtenir un certificat SSL
sudo certbot certonly --standalone -d votre-domaine.com

# Configurer Nginx avec SSL
sudo nano /etc/nginx/sites-available/openfaas
```

## 📊 Monitoring et Logs

### 1. Surveillance des Fonctions
```bash
# Voir les logs en temps réel
faas-cli logs generate-password --follow

# Voir les statistiques
faas-cli list --verbose

# Surveiller les ressources
docker stats
```

### 2. Configuration de Prometheus
```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'openfaas'
    static_configs:
      - targets: ['gateway:8080']
    metrics_path: /metrics
```

### 3. Alertes
```yaml
# alertmanager.yml
global:
  smtp_smarthost: 'smtp.gmail.com:587'
  smtp_from: 'alertmanager@votre-domaine.com'

route:
  group_by: ['alertname']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 1h
  receiver: 'email-notifications'

receivers:
  - name: 'email-notifications'
    email_configs:
      - to: 'admin@votre-domaine.com'
```

## 🔄 Mise à Jour et Maintenance

### 1. Mise à Jour des Fonctions
```bash
# Créer une nouvelle version
docker tag enock17/generate-password:latest enock17/generate-password:v1.1
docker push enock17/generate-password:v1.1

# Mettre à jour le fichier de configuration
sed -i 's/v1.0/v1.1/g' stack-production.yml

# Redéployer
faas-cli deploy -f stack-production.yml
```

### 2. Sauvegarde de la Base de Données
```bash
# Script de sauvegarde automatique
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
pg_dump -h votre-serveur-db.com -U cofrap cofrap_db > backup_$DATE.sql
gzip backup_$DATE.sql

# Ajouter au crontab pour une sauvegarde quotidienne
# 0 2 * * * /path/to/backup-script.sh
```

### 3. Rollback en Cas de Problème
```bash
# Revenir à la version précédente
sed -i 's/v1.1/v1.0/g' stack-production.yml
faas-cli deploy -f stack-production.yml
```

## 🧪 Tests de Validation

### 1. Tests Fonctionnels
```bash
# Test de génération de mot de passe
curl -X POST https://votre-domaine.com/function/generate-password \
  -H 'Content-Type: application/json' \
  -d '{"length": 16}'

# Test d'authentification
curl -X POST https://votre-domaine.com/function/authenticate-user \
  -H 'Content-Type: application/json' \
  -d '{"username": "demo", "password": "password"}'

# Test de génération 2FA
curl -X POST https://votre-domaine.com/function/generate-2fa \
  -H 'Content-Type: application/json' \
  -d '{"user_id": 1, "username": "demo"}'
```

### 2. Tests de Performance
```bash
# Test de charge avec Apache Bench
ab -n 1000 -c 10 -H "Content-Type: application/json" \
  -p test-data.json \
  https://votre-domaine.com/function/generate-password
```

## 🆘 Dépannage

### Problèmes Courants

1. **Fonction ne répond pas**
   ```bash
   # Vérifier les logs
   faas-cli logs generate-password
   
   # Vérifier la configuration
   faas-cli describe generate-password
   ```

2. **Erreur de connexion à la base de données**
   ```bash
   # Tester la connexion
   psql -h votre-serveur-db.com -U cofrap -d cofrap_db
   
   # Vérifier les variables d'environnement
   faas-cli describe generate-password --env
   ```

3. **Problème de mémoire**
   ```bash
   # Augmenter les limites
   # Modifier stack-production.yml
   limits:
     memory: 512Mi
     cpu: 300m
   ```

## 📞 Support

- **Logs OpenFaaS**: `faas-cli logs [function-name]`
- **Statut des services**: `faas-cli list`
- **Documentation OpenFaaS**: https://docs.openfaas.com/
- **Support technique**: enock.mukokom@gmail.com

---

**Version**: 1.0  
**Dernière mise à jour**: Juillet 2025  
**Auteur**: Enock Mukokom

