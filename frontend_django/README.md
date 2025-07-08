# Frontend Django - Cofrap Authentification

## Description

Frontend moderne pour l'application d'authentification Cofrap, développé avec Django et un design responsive utilisant des données factices pour la démonstration.

## Fonctionnalités

### 🔐 Authentification
- **Connexion/Inscription** : Interface moderne avec validation en temps réel
- **Authentification à deux facteurs (2FA)** : Support complet avec QR codes et codes de récupération
- **Gestion des sessions** : Suivi des connexions et déconnexion sécurisée

### 🛡️ Sécurité
- **Générateur de mots de passe** : Création de mots de passe forts et sécurisés
- **Indicateur de force** : Évaluation en temps réel de la robustesse des mots de passe
- **Codes de récupération** : Accès de secours en cas de perte du dispositif 2FA

### 📊 Tableau de bord
- **Statistiques de sécurité** : Vue d'ensemble des métriques de sécurité
- **Activité récente** : Historique des actions de sécurité
- **Gestion des sessions** : Contrôle des appareils connectés
- **Paramètres avancés** : Configuration des préférences de sécurité

## Installation

### Prérequis
- Python 3.8+
- PostgreSQL (optionnel, SQLite par défaut)
- pip

### Installation des dépendances
```bash
pip install -r requirements.txt
```

### Configuration
1. Copiez le fichier de configuration :
```bash
cp mspr2_cofrap/settings.py mspr2_cofrap/settings_local.py
```

2. Modifiez les paramètres dans `settings_local.py` :
```python
# Base de données
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Clé secrète
SECRET_KEY = 'votre-cle-secrete-ici'

# Mode debug
DEBUG = True
```

### Migration de la base de données
```bash
python manage.py makemigrations
python manage.py migrate
```

### Création d'un superutilisateur (optionnel)
```bash
python manage.py createsuperuser
```

### Lancement du serveur
```bash
python manage.py runserver
```

L'application sera accessible à l'adresse : http://localhost:8000

## Utilisation

### Comptes de démonstration

#### Administrateur (avec 2FA)
- **Nom d'utilisateur** : `admin`
- **Mot de passe** : `admin123`
- **Code 2FA** : `123456`
- **Code de récupération** : `RECOVERY`

#### Utilisateur standard
- **Nom d'utilisateur** : `user1`
- **Mot de passe** : `password123`

### Fonctionnalités principales

#### 1. Inscription
- Accédez à `/register/`
- Remplissez le formulaire avec vos informations
- Le générateur de mot de passe est disponible
- Validation en temps réel de la force du mot de passe

#### 2. Connexion
- Accédez à `/login/`
- Utilisez vos identifiants
- Si 2FA est activé, entrez le code de votre application d'authentification
- Ou utilisez un code de récupération

#### 3. Tableau de bord
- Vue d'ensemble de votre sécurité
- Statistiques de connexion
- Gestion des paramètres 2FA
- Historique des activités

#### 4. Génération de mots de passe
- Cliquez sur "Générer" dans la section sécurité
- Choisissez les paramètres (longueur, types de caractères)
- Le mot de passe est généré et copié automatiquement

#### 5. Configuration 2FA
- Cliquez sur "Configurer" dans la section 2FA
- Scannez le QR code avec votre application d'authentification
- Sauvegardez les codes de récupération

## Structure du projet

```
frontend_django/
├── auth_app/                 # Application d'authentification
│   ├── views.py             # Logique métier
│   ├── urls.py              # Configuration des URLs
│   └── __init__.py
├── mspr2_cofrap/            # Configuration Django
│   ├── settings.py          # Paramètres
│   ├── urls.py              # URLs principales
│   └── wsgi.py              # Configuration WSGI
├── static/                  # Fichiers statiques
│   ├── css/
│   │   ├── style.css        # Styles principaux
│   │   └── components.css   # Composants spécifiques
│   └── js/
│       └── app.js           # JavaScript principal
├── templates/               # Templates HTML
│   ├── base.html            # Template de base
│   └── auth_app/            # Templates de l'app
│       ├── home.html        # Page d'accueil
│       ├── login.html       # Connexion
│       ├── register.html    # Inscription
│       └── dashboard.html   # Tableau de bord
├── manage.py                # Script de gestion Django
├── requirements.txt         # Dépendances Python
└── README.md               # Ce fichier
```

## Technologies utilisées

### Backend
- **Django 4.2+** : Framework web Python
- **PostgreSQL/SQLite** : Base de données
- **PyJWT** : Gestion des tokens JWT
- **qrcode** : Génération de QR codes pour 2FA

### Frontend
- **HTML5** : Structure sémantique
- **CSS3** : Styles modernes avec variables CSS
- **JavaScript ES6+** : Interactivité et validation
- **Font Awesome** : Icônes
- **Google Fonts** : Typographie (Inter)

### Design
- **Responsive Design** : Compatible mobile/desktop
- **Design System** : Variables CSS pour la cohérence
- **Animations** : Transitions fluides
- **Accessibilité** : Support des standards WCAG

## Fonctionnalités avancées

### Validation en temps réel
- Vérification de la force des mots de passe
- Validation des formulaires côté client
- Messages d'erreur contextuels

### Sécurité
- Protection CSRF
- Validation côté serveur
- Gestion sécurisée des sessions
- Chiffrement des données sensibles

### Performance
- Optimisation des assets statiques
- Lazy loading des composants
- Compression des ressources

## Développement

### Ajout de nouvelles fonctionnalités
1. Créez les vues dans `auth_app/views.py`
2. Ajoutez les URLs dans `auth_app/urls.py`
3. Créez les templates dans `templates/auth_app/`
4. Ajoutez les styles dans `static/css/`
5. Testez la fonctionnalité

### Personnalisation du design
- Modifiez les variables CSS dans `static/css/style.css`
- Ajoutez de nouveaux composants dans `static/css/components.css`
- Personnalisez les icônes avec Font Awesome

### Intégration avec l'API
Le frontend est conçu pour fonctionner avec les fonctions serverless OpenFaaS. Pour activer l'intégration :

1. Configurez l'URL de la passerelle OpenFaaS dans `settings.py`
2. Les appels API sont automatiquement activés
3. Les données factices sont utilisées en mode démo

## Support

Pour toute question ou problème :
1. Consultez la documentation Django
2. Vérifiez les logs du serveur
3. Testez avec les comptes de démonstration

## Licence

Ce projet fait partie de Cofrap (Compagnie Française de Réalisation d'Applicatifs Professionnels) et est destiné à des fins éducatives. 