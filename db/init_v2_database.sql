-- Script d'initialisation de la base de données V2 pour MSPR COFRAP
-- Base de données: mspr2_cofrap
-- Utilisateur: postgres

-- Création de la table principale pour les utilisateurs avec mots de passe chiffrés
CREATE TABLE IF NOT EXISTS users_v2 (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL, -- Mot de passe chiffré
    mfa VARCHAR(255), -- Secret 2FA chiffré
    gendate BIGINT NOT NULL, -- Timestamp UNIX de génération
    expired BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table pour l'historique des mots de passe (optionnel)
CREATE TABLE IF NOT EXISTS password_history_v2 (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users_v2(id) ON DELETE CASCADE,
    password VARCHAR(255) NOT NULL, -- Mot de passe chiffré
    gendate BIGINT NOT NULL, -- Timestamp UNIX de génération
    expired BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table pour les logs d'authentification
CREATE TABLE IF NOT EXISTS auth_logs_v2 (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users_v2(id) ON DELETE SET NULL,
    action VARCHAR(50) NOT NULL, -- login, password_generated, 2fa_generated, password_expired
    ip_address INET,
    user_agent TEXT,
    success BOOLEAN DEFAULT TRUE,
    details JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insertion d'utilisateurs de test
INSERT INTO users_v2 (username, password, gendate, expired) 
VALUES (
    'michel.ranu',
    'AAAA...GGGG==', -- Mot de passe chiffré de test
    1721916574, -- Timestamp UNIX
    FALSE
) ON CONFLICT (username) DO NOTHING;

-- Création d'index pour améliorer les performances
CREATE INDEX IF NOT EXISTS idx_users_v2_username ON users_v2(username);
CREATE INDEX IF NOT EXISTS idx_users_v2_gendate ON users_v2(gendate);
CREATE INDEX IF NOT EXISTS idx_users_v2_expired ON users_v2(expired);
CREATE INDEX IF NOT EXISTS idx_password_history_v2_user_id ON password_history_v2(user_id);
CREATE INDEX IF NOT EXISTS idx_auth_logs_v2_user_id ON auth_logs_v2(user_id);
CREATE INDEX IF NOT EXISTS idx_auth_logs_v2_created_at ON auth_logs_v2(created_at);

-- Affichage des informations de la base de données
SELECT 'Base de données V2 initialisée avec succès!' as message;
SELECT COUNT(*) as nombre_utilisateurs FROM users_v2;
SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_name LIKE '%v2%' ORDER BY table_name; 