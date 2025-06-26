# MSPR2-Cofrap - Application Serverless Sécurisée

## 🎯 Objectif
Application serverless sécurisée pour la création, l'authentification et la gestion de comptes utilisateurs avec rotation de mots de passe et 2FA.

## 🔧 Stack Technique
- **Python** (fonctions serverless OpenFaaS)
- **OpenFaaS** (via faas-cli)
- **Kubernetes** (via minikube ou K3S local)
- **PostgreSQL** (chart Helm ou manifest YAML)
- **Django** (frontend simple pour appel des fonctions)
- **Docker** (pour packager chaque composant)
- **Helm** (déploiement OpenFaaS)

## 📂 Structure du Projet
```
MSPR2-Cofrap/
├── frontend_django/          # Interface utilisateur Django
├── functions/                # Fonctions serverless OpenFaaS
│   ├── generate_password/    # Génération de mots de passe sécurisés
│   ├── generate_2fa/         # Génération de codes 2FA
│   └── authenticate_user/    # Authentification utilisateur
├── k8s/                     # Manifests Kubernetes
│   ├── postgres.yaml
│   ├── ingress.yaml
│   └── deployments.yaml
├── docs/                    # Documentation
├── docker-compose.yml       # Développement local
└── README.md
```

## 🚀 Installation et Démarrage

### Prérequis
- Docker et Docker Compose
- kubectl
- minikube ou K3S
- faas-cli
- helm

### Étapes d'installation
1. Cloner le repository
2. Démarrer l'environnement Kubernetes local
3. Déployer PostgreSQL
4. Déployer OpenFaaS
5. Déployer les fonctions serverless
6. Lancer le frontend Django

## 🔐 Sécurité
- Rotation automatique des mots de passe
- Authentification à deux facteurs (2FA)
- Chiffrement des données sensibles
- Validation des entrées utilisateur
- Logs d'audit

## 📝 Documentation
Consultez le dossier `docs/` pour la documentation détaillée de chaque composant. 