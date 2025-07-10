-- Script de réinitialisation complète de la base de données MSPR COFRAP
-- Supprime toutes les tables et recrée une structure propre unifiée V1/V2

-- =====================================================
-- ÉTAPE 1: SUPPRESSION DE TOUTES LES TABLES EXISTANTES
-- =====================================================
-- Ce script supprime TOUTES les tables existantes (V1, V2, Kubernetes)
-- et recrée une structure unifiée propre pour les fonctions V1 et V2

-- Suppression des tables dans l'ordre pour éviter les erreurs de contraintes
-- Tables V1
DROP TABLE IF EXISTS recovery_codes CASCADE;
DROP TABLE IF EXISTS two_factor_codes CASCADE;
DROP TABLE IF EXISTS password_rotation_schedule CASCADE;
DROP TABLE IF EXISTS password_history CASCADE;
DROP TABLE IF EXISTS auth_logs CASCADE;
DROP TABLE IF EXISTS user_sessions CASCADE;
DROP TABLE IF EXISTS temp_passwords CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- Tables V2
DROP TABLE IF EXISTS auth_logs_v2 CASCADE;
DROP TABLE IF EXISTS password_history_v2 CASCADE;
DROP TABLE IF EXISTS users_v2 CASCADE;

-- Tables Kubernetes/autres
DROP TABLE IF EXISTS two_factor_auth CASCADE;
DROP TABLE IF EXISTS login_logs CASCADE;

-- =====================================================
-- ÉTAPE 2: CRÉATION DE LA TABLE PRINCIPALE USERS
-- =====================================================

CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(100) UNIQUE,
    password VARCHAR(255), -- Pour V2 (mots de passe chiffrés)
    mfa VARCHAR(255), -- Secret 2FA chiffré
    gendate BIGINT NOT NULL, -- Timestamp UNIX de génération
    expired BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    is_staff BOOLEAN DEFAULT FALSE,
    is_superuser BOOLEAN DEFAULT FALSE,
    date_joined TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =====================================================
-- ÉTAPE 3: TABLES POUR LES MOTS DE PASSE
-- =====================================================

-- Table pour l'historique des mots de passe
CREATE TABLE password_history (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    password VARCHAR(255), -- Pour V2 (chiffré)
    gendate BIGINT, -- Pour V2
    expired BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table pour la planification de rotation des mots de passe
CREATE TABLE password_rotation_schedule (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE UNIQUE,
    rotation_date TIMESTAMP NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =====================================================
-- ÉTAPE 4: TABLES POUR L'AUTHENTIFICATION 2FA
-- =====================================================

-- Table pour les codes de récupération 2FA
CREATE TABLE recovery_codes (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    code VARCHAR(32) NOT NULL,
    created_at TIMESTAMP NOT NULL,
    used BOOLEAN DEFAULT FALSE,
    used_at TIMESTAMP
);

-- =====================================================
-- ÉTAPE 5: TABLES POUR LES SESSIONS ET LOGS
-- =====================================================

-- Table pour les sessions utilisateur
CREATE TABLE user_sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    session_token VARCHAR(255) NOT NULL UNIQUE,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table pour les logs d'authentification
CREATE TABLE auth_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    action VARCHAR(50) NOT NULL, -- login, logout, password_change, 2fa_generated, etc.
    ip_address INET,
    user_agent TEXT,
    success BOOLEAN DEFAULT TRUE,
    details JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =====================================================
-- ÉTAPE 6: CRÉATION DES INDEX POUR LES PERFORMANCES
-- =====================================================

-- Index pour la table users
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_gendate ON users(gendate);
CREATE INDEX idx_users_expired ON users(expired);
CREATE INDEX idx_users_is_active ON users(is_active);

-- Index pour password_history
CREATE INDEX idx_password_history_user_id ON password_history(user_id);
CREATE INDEX idx_password_history_created_at ON password_history(created_at);
CREATE INDEX idx_password_history_gendate ON password_history(gendate);

-- Index pour password_rotation_schedule
CREATE INDEX idx_password_rotation_schedule_user_id ON password_rotation_schedule(user_id);
CREATE INDEX idx_password_rotation_schedule_rotation_date ON password_rotation_schedule(rotation_date);

-- Index pour recovery_codes
CREATE INDEX idx_recovery_codes_user_id ON recovery_codes(user_id);
CREATE INDEX idx_recovery_codes_used ON recovery_codes(used);

-- Index pour user_sessions
CREATE INDEX idx_user_sessions_user_id ON user_sessions(user_id);
CREATE INDEX idx_user_sessions_token ON user_sessions(session_token);
CREATE INDEX idx_user_sessions_expires ON user_sessions(expires_at);

-- Index pour auth_logs
CREATE INDEX idx_auth_logs_user_id ON auth_logs(user_id);
CREATE INDEX idx_auth_logs_created_at ON auth_logs(created_at);
CREATE INDEX idx_auth_logs_action ON auth_logs(action);

-- =====================================================
-- ÉTAPE 7: INSERTION D'UTILISATEURS DE TEST
-- =====================================================

-- Utilisateur admin
INSERT INTO users (username, email, password, gendate, is_staff, is_superuser) 
VALUES (
    'admin',
    'admin@mspr.local',
    'NO_PASSWORD_YET',
    EXTRACT(EPOCH FROM CURRENT_TIMESTAMP)::BIGINT,
    TRUE,
    TRUE
);

-- Utilisateur de test
INSERT INTO users (username, email, password, gendate) 
VALUES (
    'testuser',
    'test@mspr.local',
    'NO_PASSWORD_YET',
    EXTRACT(EPOCH FROM CURRENT_TIMESTAMP)::BIGINT
);

-- Utilisateur demo
INSERT INTO users (username, email, password, gendate, is_staff) 
VALUES (
    'demo',
    'demo@mspr.local',
    'NO_PASSWORD_YET',
    EXTRACT(EPOCH FROM CURRENT_TIMESTAMP)::BIGINT,
    TRUE
);

-- =====================================================
-- ÉTAPE 8: VÉRIFICATION ET AFFICHAGE DES RÉSULTATS
-- =====================================================

-- Message de confirmation
SELECT 'Base de données MSPR COFRAP réinitialisée avec succès!' as message;

-- Affichage du nombre d'utilisateurs créés
SELECT COUNT(*) as nombre_utilisateurs FROM users;

-- Affichage de toutes les tables créées
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public' 
ORDER BY table_name;

-- Affichage de la structure de la table users
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'users' 
ORDER BY ordinal_position; 