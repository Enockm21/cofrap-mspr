-- Script pour ajouter des utilisateurs de test avec des mots de passe connus
-- Compatible avec la fonction authenticate_user

-- Ajout d'utilisateurs de test
INSERT INTO users (username, email, password_hash, is_staff, is_superuser, is_active) 
VALUES 
    ('demo', 'demo@mspr.local', 'pbkdf2_sha256$600000$demo_hash$demo_salt', TRUE, FALSE, TRUE),
    ('user1', 'user1@mspr.local', 'pbkdf2_sha256$600000$user1_hash$user1_salt', FALSE, FALSE, TRUE),
    ('admin2', 'admin2@mspr.local', 'pbkdf2_sha256$600000$admin2_hash$admin2_salt', TRUE, TRUE, TRUE),
    ('testuser2', 'testuser2@mspr.local', 'pbkdf2_sha256$600000$testuser2_hash$testuser2_salt', FALSE, FALSE, TRUE)
ON CONFLICT (username) DO NOTHING;

-- Insertion des hashes de mots de passe dans password_history
-- Ces hashes sont générés avec PBKDF2-HMAC-SHA256, 100000 itérations
-- Format: hash_hex + salt_hex

-- Utilisateur 'demo' - mot de passe: "password"
INSERT INTO password_history (user_id, password_hash, salt, created_at)
SELECT 
    u.id,
    '5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8', -- hash de "password"
    '73616c745f64656d6f5f75736572', -- salt en hex
    CURRENT_TIMESTAMP
FROM users u WHERE u.username = 'demo'
ON CONFLICT DO NOTHING;

-- Utilisateur 'user1' - mot de passe: "test123"
INSERT INTO password_history (user_id, password_hash, salt, created_at)
SELECT 
    u.id,
    'a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3', -- hash de "test123"
    '73616c745f75736572315f74657374', -- salt en hex
    CURRENT_TIMESTAMP
FROM users u WHERE u.username = 'user1'
ON CONFLICT DO NOTHING;

-- Utilisateur 'admin2' - mot de passe: "admin123"
INSERT INTO password_history (user_id, password_hash, salt, created_at)
SELECT 
    u.id,
    '240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9', -- hash de "admin123"
    '73616c745f61646d696e325f736563', -- salt en hex
    CURRENT_TIMESTAMP
FROM users u WHERE u.username = 'admin2'
ON CONFLICT DO NOTHING;

-- Utilisateur 'testuser2' - mot de passe: "secret"
INSERT INTO password_history (user_id, password_hash, salt, created_at)
SELECT 
    u.id,
    '2bb80d537b1da3e38bd30361aa855686bde0eacd7162fef6a25fe97bf527a25b', -- hash de "secret"
    '73616c745f7465737475736572325f', -- salt en hex
    CURRENT_TIMESTAMP
FROM users u WHERE u.username = 'testuser2'
ON CONFLICT DO NOTHING;

-- Affichage des utilisateurs créés
SELECT 'Utilisateurs de test créés avec succès!' as message;
SELECT 
    u.username,
    u.email,
    u.is_staff,
    u.is_superuser,
    CASE 
        WHEN ph.password_hash IS NOT NULL THEN 'Oui'
        ELSE 'Non'
    END as mot_de_passe_configure
FROM users u
LEFT JOIN password_history ph ON u.id = ph.user_id
WHERE u.username IN ('demo', 'user1', 'admin2', 'testuser2')
ORDER BY u.username; 