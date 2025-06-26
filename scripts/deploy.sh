#!/bin/bash

# Script de déploiement MSPR2-Cofrap
# Usage: ./scripts/deploy.sh [minikube|k3s]

set -e

echo "🚀 Déploiement MSPR2-Cofrap..."

# Vérification des prérequis
check_prerequisites() {
    echo "📋 Vérification des prérequis..."
    
    # Vérifier kubectl
    if ! command -v kubectl &> /dev/null; then
        echo "❌ kubectl n'est pas installé"
        exit 1
    fi
    
    # Vérifier helm
    if ! command -v helm &> /dev/null; then
        echo "❌ helm n'est pas installé"
        exit 1
    fi
    
    # Vérifier faas-cli
    if ! command -v faas-cli &> /dev/null; then
        echo "❌ faas-cli n'est pas installé"
        exit 1
    fi
    
    echo "✅ Prérequis vérifiés"
}

# Démarrage de l'environnement Kubernetes
start_kubernetes() {
    local env=$1
    
    echo "🔧 Démarrage de l'environnement Kubernetes ($env)..."
    
    if [ "$env" = "minikube" ]; then
        minikube start --cpus=4 --memory=8192 --disk-size=20g
        minikube addons enable ingress
        minikube addons enable metrics-server
    elif [ "$env" = "k3s" ]; then
        # K3S devrait déjà être en cours d'exécution
        echo "ℹ️  K3S devrait être en cours d'exécution"
    else
        echo "❌ Environnement non supporté: $env"
        exit 1
    fi
    
    echo "✅ Environnement Kubernetes prêt"
}

# Déploiement d'OpenFaaS
deploy_openfaas() {
    echo "☁️  Déploiement d'OpenFaaS..."
    
    # Ajouter le repository Helm OpenFaaS
    helm repo add openfaas https://openfaas.github.io/faas-netes/
    helm repo update
    
    # Créer le namespace OpenFaaS
    kubectl create namespace openfaas --dry-run=client -o yaml | kubectl apply -f -
    kubectl create namespace openfaas-fn --dry-run=client -o yaml | kubectl apply -f -
    
    # Déployer OpenFaaS
    helm upgrade openfaas --install openfaas/openfaas \
        --namespace openfaas \
        --set functionNamespace=openfaas-fn \
        --set basic_auth=true \
        --set basic_auth_user=admin \
        --set basic_auth_password=admin123 \
        --set gateway.replicas=1 \
        --set queueWorker.replicas=1 \
        --set faasnetes.replicas=1
    
    echo "⏳ Attente du démarrage d'OpenFaaS..."
    kubectl rollout status deployment/gateway -n openfaas --timeout=300s
    
    echo "✅ OpenFaaS déployé"
}

# Déploiement de PostgreSQL
deploy_postgres() {
    echo "🗄️  Déploiement de PostgreSQL..."
    
    kubectl apply -f k8s/postgres.yaml
    
    echo "⏳ Attente du démarrage de PostgreSQL..."
    kubectl rollout status deployment/postgres -n mspr2-cofrap --timeout=300s
    
    echo "✅ PostgreSQL déployé"
}

# Déploiement des fonctions OpenFaaS
deploy_functions() {
    echo "⚡ Déploiement des fonctions serverless..."
    
    # Configuration de faas-cli
    export OPENFAAS_URL=http://127.0.0.1:8080
    
    # Attendre que la gateway soit prête
    echo "⏳ Attente de la disponibilité de la gateway OpenFaaS..."
    until curl -s $OPENFAAS_URL > /dev/null; do
        sleep 5
    done
    
    # Login à OpenFaaS
    echo "admin" | faas-cli login --password-stdin
    
    # Déployer les fonctions
    cd functions
    
    echo "📦 Déploiement de generate-password..."
    faas-cli deploy -f generate_password.yml
    
    echo "📦 Déploiement de generate-2fa..."
    faas-cli deploy -f generate_2fa.yml
    
    echo "📦 Déploiement de authenticate-user..."
    faas-cli deploy -f authenticate_user.yml
    
    cd ..
    
    echo "✅ Fonctions serverless déployées"
}

# Déploiement du frontend Django
deploy_frontend() {
    echo "🌐 Déploiement du frontend Django..."
    
    # Construire l'image Docker
    docker build -t mspr2-cofrap-frontend:latest ./frontend_django
    
    # Créer le manifest de déploiement
    cat > k8s/frontend-deployment.yaml << EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: frontend-django
  namespace: mspr2-cofrap
spec:
  replicas: 1
  selector:
    matchLabels:
      app: frontend-django
  template:
    metadata:
      labels:
        app: frontend-django
    spec:
      containers:
      - name: frontend
        image: mspr2-cofrap-frontend:latest
        ports:
        - containerPort: 8000
        env:
        - name: POSTGRES_HOST
          value: "postgres"
        - name: POSTGRES_DB
          value: "mspr2_cofrap"
        - name: POSTGRES_USER
          value: "postgres"
        - name: POSTGRES_PASSWORD
          value: "password"
        - name: OPENFAAS_GATEWAY_URL
          value: "http://gateway.openfaas:8080"
        - name: DJANGO_DEBUG
          value: "False"
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
EOF
    
    kubectl apply -f k8s/frontend-deployment.yaml
    
    echo "⏳ Attente du démarrage du frontend..."
    kubectl rollout status deployment/frontend-django -n mspr2-cofrap --timeout=300s
    
    echo "✅ Frontend Django déployé"
}

# Configuration de l'ingress
setup_ingress() {
    echo "🌍 Configuration de l'ingress..."
    
    kubectl apply -f k8s/ingress.yaml
    
    echo "✅ Ingress configuré"
}

# Affichage des informations de connexion
show_info() {
    echo ""
    echo "🎉 Déploiement terminé avec succès !"
    echo ""
    echo "📋 Informations de connexion :"
    echo "   Frontend Django: http://localhost:8000"
    echo "   OpenFaaS Gateway: http://localhost:8080"
    echo "   PostgreSQL: localhost:5432"
    echo ""
    echo "🔐 Identifiants OpenFaaS :"
    echo "   Utilisateur: admin"
    echo "   Mot de passe: admin123"
    echo ""
    echo "📝 Commandes utiles :"
    echo "   kubectl get pods -n mspr2-cofrap"
    echo "   kubectl get pods -n openfaas"
    echo "   faas-cli list"
    echo ""
}

# Fonction principale
main() {
    local env=${1:-minikube}
    
    check_prerequisites
    start_kubernetes $env
    deploy_openfaas
    deploy_postgres
    deploy_functions
    deploy_frontend
    setup_ingress
    show_info
}

# Exécution du script
main "$@" 