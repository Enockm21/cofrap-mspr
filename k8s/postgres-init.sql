-- Script d'initialisation pour la base de données MSPR2-Cofrap

-- Création de la base de données
CREATE DATABASE mspr2_cofrap;
\c mspr2_cofrap;

-- Table des utilisateurs
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);

-- Table de l'historique des mots de passe
CREATE TABLE password_history (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    password_hash VARCHAR(255) NOT NULL,
    salt VARCHAR(32) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table de planification de rotation des mots de passe
CREATE TABLE password_rotation_schedule (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE UNIQUE,
    rotation_date TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table d'authentification à deux facteurs
CREATE TABLE two_factor_auth (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE UNIQUE,
    secret_key VARCHAR(32) NOT NULL,
    user_email VARCHAR(100) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table des codes de récupération
CREATE TABLE recovery_codes (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    code VARCHAR(8) NOT NULL,
    used BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    used_at TIMESTAMP
);

-- Table des logs de connexion
CREATE TABLE login_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    username VARCHAR(50),
    status VARCHAR(20) NOT NULL,
    reason TEXT,
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index pour optimiser les performances
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_password_history_user_id ON password_history(user_id);
CREATE INDEX idx_two_factor_auth_user_id ON two_factor_auth(user_id);
CREATE INDEX idx_recovery_codes_user_id ON recovery_codes(user_id);
CREATE INDEX idx_login_logs_user_id ON login_logs(user_id);
CREATE INDEX idx_login_logs_created_at ON login_logs(created_at);

-- Insertion d'un utilisateur de test avec mot de passe hashé
-- Mot de passe: "password" avec salt "testsalt"
INSERT INTO users (username, email) VALUES ('admin', 'admin@mspr2-cofrap.local');

-- Insertion d'un hash de mot de passe de test
-- Ceci est un exemple, en production les mots de passe seraient générés par les fonctions
INSERT INTO password_history (user_id, password_hash, salt) 
VALUES (1, '5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8', 'testsalt');

-- Message de confirmation
SELECT 'Base de données MSPR2-Cofrap initialisée avec succès !' as message; 