#!/bin/bash

echo "🗄️  Initialisation de la base de données locale pour MSPR..."

# Vérifier que PostgreSQL est en cours d'exécution
echo "📋 Vérification de PostgreSQL..."
if ! pg_isready -h localhost -p 5432 > /dev/null 2>&1; then
    echo "❌ PostgreSQL n'est pas accessible sur localhost:5432"
    echo "💡 Assurez-vous que PostgreSQL est démarré"
    exit 1
fi

echo "✅ PostgreSQL est accessible"

# Exécuter le script SQL
echo "🔧 Exécution du script d'initialisation..."
psql -h localhost -U cofrap -d cofrap_db -f db/init_local_db.sql

if [ $? -eq 0 ]; then
    echo "✅ Base de données initialisée avec succès !"
    
    # Afficher un résumé
    echo ""
    echo "📊 Résumé de la base de données :"
    echo "   Base de données: cofrap_db"
    echo "   Utilisateur: cofrap"
    echo "   Tables créées:"
    psql -h localhost -U cofrap -d cofrap_db -c "\dt" | grep -v "List of relations" | grep -v "----" | grep -v "^$"
    
    echo ""
    echo "👥 Utilisateurs créés:"
    psql -h localhost -U cofrap -d cofrap_db -c "SELECT username, email, is_staff, is_superuser FROM users;"
    
    echo ""
    echo "🧪 Test de la fonction OpenFaaS..."
    sleep 2
    
    # Tester la fonction OpenFaaS
    echo "📊 Test du nombre d'utilisateurs:"
    curl -X POST http://localhost:8080/function/test-function \
      -H "Content-Type: application/json" \
      -d '{"action": "users_count", "name": "Testeur"}' | jq '.'
    
    echo ""
    echo "🔍 Test des informations complètes:"
    curl -X POST http://localhost:8080/function/test-function \
      -H "Content-Type: application/json" \
      -d '{"action": "full_info", "name": "Testeur"}' | jq '.'
    
    echo ""
    echo "🔐 Test de la fonction generate-password..."
    sleep 2
    
    # Construire et déployer generate-password si pas déjà fait
    echo "📦 Vérification du déploiement de generate-password..."
    if ! curl -s http://localhost:8080/function/generate-password > /dev/null 2>&1; then
        echo "🔨 Construction et déploiement de generate-password..."
        faas-cli build -f stack.yml generate-password
        faas-cli deploy -f stack.yml generate-password
        sleep 10
    fi
    
    echo ""
    echo "🔐 Test de la fonction authenticate-user..."
    sleep 2
    
    # Construire et déployer authenticate-user si pas déjà fait
    echo "📦 Vérification du déploiement de authenticate-user..."
    if ! curl -s http://localhost:8080/function/authenticate-user > /dev/null 2>&1; then
        echo "🔨 Construction et déploiement de authenticate-user..."
        faas-cli build -f stack.yml authenticate-user
        faas-cli deploy -f stack.yml authenticate-user
        sleep 10
    fi
    
    # Créer un utilisateur de test avec un mot de passe valide
    echo "👤 Création d'un utilisateur de test pour authenticate-user..."
    psql -h localhost -U cofrap -d cofrap_db -c "
    INSERT INTO users (username, email, is_active, is_staff) 
    VALUES ('testauth', 'testauth@mspr.local', TRUE, FALSE) 
    ON CONFLICT (username) DO NOTHING;
    
    INSERT INTO password_history (user_id, password_hash, salt) 
    SELECT u.id, 
           '5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8', 
           'testsalt123' 
    FROM users u WHERE u.username = 'testauth';
    "
    
    # Test 1: Authentification réussie
    echo "📊 Test 1: Authentification réussie (mot de passe: 'password')"
    curl -X POST http://localhost:8080/function/authenticate-user \
      -H "Content-Type: application/json" \
      -d '{"username": "testauth", "password": "password"}' | jq '.'
    
    # Test 2: Authentification échouée - utilisateur inexistant
    echo ""
    echo "📊 Test 2: Authentification échouée - utilisateur inexistant"
    curl -X POST http://localhost:8080/function/authenticate-user \
      -H "Content-Type: application/json" \
      -d '{"username": "utilisateur_inexistant", "password": "password"}' | jq '.'
    
    # Test 3: Authentification échouée - mot de passe incorrect
    echo ""
    echo "📊 Test 3: Authentification échouée - mot de passe incorrect"
    curl -X POST http://localhost:8080/function/authenticate-user \
      -H "Content-Type: application/json" \
      -d '{"username": "testauth", "password": "mauvais_mot_de_passe"}' | jq '.'
    
    # Test 4: Authentification échouée - paramètres manquants
    echo ""
    echo "📊 Test 4: Authentification échouée - paramètres manquants"
    curl -X POST http://localhost:8080/function/authenticate-user \
      -H "Content-Type: application/json" \
      -d '{"username": "testauth"}' | jq '.'
    
    # Tester generate-password
    echo "📊 Test 1: Génération de mot de passe simple"
    curl -X POST http://localhost:8080/function/generate-password \
      -H "Content-Type: application/json" \
      -d '{"length": 12, "include_symbols": true, "include_numbers": true}' | jq '.'
    
    # echo -e "\n\n📊 Test 2: Génération avec stockage en base (user_id=1)"
    # curl -X POST http://localhost:8080/function/generate-password \
    #   -H "Content-Type: application/json" \
    #   -d '{"length": 16, "user_id": 1, "enable_rotation": true, "rotation_days": 30}' | jq '.'
    
    # echo -e "\n\n📊 Test 3: Génération de mot de passe complexe"
    # curl -X POST http://localhost:8080/function/generate-password \
    #   -H "Content-Type: application/json" \
    #   -d '{"length": 20, "include_symbols": true, "include_numbers": true, "include_uppercase": true, "include_lowercase": true}' | jq '.'
    
    echo -e "\n\n📊 Vérification des données en base:"
    echo "   - Historique des mots de passe:"
    psql -h localhost -U cofrap -d cofrap_db -c "SELECT COUNT(*) as password_history_count FROM password_history;"
    echo "   - Planification de rotation:"
    psql -h localhost -U cofrap -d cofrap_db -c "SELECT COUNT(*) as rotation_schedule_count FROM password_rotation_schedule;"
    echo "   - Logs d'authentification:"
    psql -h localhost -U cofrap -d cofrap_db -c "SELECT COUNT(*) as auth_logs_count FROM auth_logs;"
    echo "   - Derniers logs d'authentification:"
    psql -h localhost -U cofrap -d cofrap_db -c "SELECT username, success, reason, created_at FROM auth_logs ORDER BY created_at DESC LIMIT 5;"
    
else
    echo "❌ Erreur lors de l'initialisation de la base de données"
    exit 1
fi

echo ""
echo "🎉 Initialisation terminée !"
echo "🌐 Interface OpenFaaS: http://localhost:8080"
echo "🗄️  Base de données: cofrap_db (utilisateur: cofrap)"
echo "🔐 Fonction generate-password: http://localhost:8080/function/generate-password"
echo "🔐 Fonction authenticate-user: http://localhost:8080/function/authenticate-user"
echo "📊 Tables créées: users, temp_passwords, two_factor_codes, user_sessions, auth_logs, password_history, password_rotation_schedule" 