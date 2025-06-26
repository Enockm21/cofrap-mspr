# Guide d'Installation - MSPR2-Cofrap

## 📋 Prérequis

### Outils requis
- **Docker** (version 20.10+)
- **Docker Compose** (version 2.0+)
- **kubectl** (version 1.25+)
- **Helm** (version 3.10+)
- **faas-cli** (version 0.14+)
- **minikube** ou **K3S**

### Ressources système recommandées
- **CPU**: 4 cœurs minimum
- **RAM**: 8 GB minimum
- **Espace disque**: 20 GB minimum

## 🚀 Installation

### 1. Installation des outils

#### macOS
```bash
# Homebrew
brew install docker docker-compose kubectl helm minikube

# faas-cli
curl -sL https://cli.openfaas.com | sudo sh
```

#### Ubuntu/Debian
```bash
# Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# kubectl
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl

# Helm
curl https://baltocdn.com/helm/signing.asc | gpg --dearmor | sudo tee /usr/share/keyrings/helm.gpg > /dev/null
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/helm.gpg] https://baltocdn.com/helm/stable/debian/ all main" | sudo tee /etc/apt/sources.list.d/helm-stable-debian.list
sudo apt-get update && sudo apt-get install helm

# faas-cli
curl -sL https://cli.openfaas.com | sudo sh

# minikube
curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64
sudo install minikube-linux-amd64 /usr/local/bin/minikube
```

### 2. Clonage du repository
```bash
git clone <repository-url>
cd MSPR2-Cofrap
```

### 3. Déploiement automatique

#### Option A: Déploiement complet avec Kubernetes
```bash
# Rendre le script exécutable
chmod +x scripts/deploy.sh

# Déploiement avec minikube
./scripts/deploy.sh minikube

# Ou avec K3S
./scripts/deploy.sh k3s
```

#### Option B: Développement local avec Docker Compose
```bash
# Démarrage de l'environnement de développement
docker-compose up -d

# Vérification des services
docker-compose ps
```

### 4. Vérification du déploiement

#### Vérifier les pods Kubernetes
```bash
kubectl get pods -n mspr2-cofrap
kubectl get pods -n openfaas
```

#### Vérifier les fonctions OpenFaaS
```bash
faas-cli list
```

#### Vérifier les services
```bash
kubectl get services -n mspr2-cofrap
```

## 🌐 Accès aux services

### URLs de développement
- **Frontend Django**: http://localhost:8000
- **OpenFaaS Gateway**: http://localhost:8080
- **PostgreSQL**: localhost:5432

### Identifiants par défaut
- **OpenFaaS**:
  - Utilisateur: `admin`
  - Mot de passe: `admin123`

- **PostgreSQL**:
  - Base de données: `mspr2_cofrap`
  - Utilisateur: `postgres`
  - Mot de passe: `password`

## 🔧 Configuration

### Variables d'environnement

#### Frontend Django
```bash
POSTGRES_HOST=postgres
POSTGRES_DB=mspr2_cofrap
POSTGRES_USER=postgres
POSTGRES_PASSWORD=password
OPENFAAS_GATEWAY_URL=http://gateway:8080
DJANGO_DEBUG=True
JWT_SECRET_KEY=your-secret-key-change-in-production
```

#### Fonctions OpenFaaS
```bash
POSTGRES_HOST=postgres.mspr2-cofrap.svc.cluster.local
POSTGRES_DB=mspr2_cofrap
POSTGRES_USER=postgres
POSTGRES_PASSWORD=password
JWT_SECRET_KEY=your-secret-key-change-in-production
```

### Sécurité en production

⚠️ **IMPORTANT**: Pour un déploiement en production, modifiez obligatoirement :

1. **Mots de passe par défaut**
2. **Clés secrètes JWT**
3. **Configuration SSL/TLS**
4. **Politiques de sécurité réseau**

## 🐛 Dépannage

### Problèmes courants

#### Minikube ne démarre pas
```bash
# Vérifier les prérequis
minikube start --driver=docker

# Si problème de mémoire
minikube start --memory=8192 --cpus=4
```

#### OpenFaaS ne répond pas
```bash
# Vérifier les pods
kubectl get pods -n openfaas

# Vérifier les logs
kubectl logs -n openfaas deployment/gateway
```

#### PostgreSQL ne démarre pas
```bash
# Vérifier les logs
kubectl logs -n mspr2-cofrap deployment/postgres

# Vérifier le PVC
kubectl get pvc -n mspr2-cofrap
```

#### Fonctions OpenFaaS non déployées
```bash
# Vérifier la connexion
faas-cli login --username admin --password admin123

# Redéployer les fonctions
cd functions
faas-cli deploy -f generate_password.yml
faas-cli deploy -f generate_2fa.yml
faas-cli deploy -f authenticate_user.yml
```

## 📚 Commandes utiles

### Kubernetes
```bash
# Voir tous les pods
kubectl get pods --all-namespaces

# Voir les services
kubectl get services --all-namespaces

# Voir les logs d'un pod
kubectl logs -n mspr2-cofrap <pod-name>

# Accéder à un pod
kubectl exec -it -n mspr2-cofrap <pod-name> -- /bin/bash
```

### OpenFaaS
```bash
# Lister les fonctions
faas-cli list

# Voir les logs d'une fonction
faas-cli logs generate-password

# Tester une fonction
echo '{"length": 16}' | faas-cli invoke generate-password
```

### Docker Compose
```bash
# Voir les logs
docker-compose logs -f

# Redémarrer un service
docker-compose restart frontend

# Arrêter l'environnement
docker-compose down
```

## 🔄 Mise à jour

### Mise à jour des fonctions
```bash
cd functions
faas-cli deploy -f generate_password.yml
faas-cli deploy -f generate_2fa.yml
faas-cli deploy -f authenticate_user.yml
```

### Mise à jour du frontend
```bash
# Reconstruire l'image
docker build -t mspr2-cofrap-frontend:latest ./frontend_django

# Redéployer
kubectl rollout restart deployment/frontend-django -n mspr2-cofrap
```

## 🗑️ Nettoyage

### Arrêt complet
```bash
# Kubernetes
kubectl delete namespace mspr2-cofrap
kubectl delete namespace openfaas
kubectl delete namespace openfaas-fn

# Docker Compose
docker-compose down -v

# Minikube
minikube stop
minikube delete
``` 