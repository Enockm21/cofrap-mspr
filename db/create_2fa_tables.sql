CREATE TABLE IF NOT EXISTS two_factor_auth (
    user_id VARCHAR(255) PRIMARY KEY,
    secret_key VARCHAR(255) NOT NULL,
    user_email VARCHAR(255) NOT NULL,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS recovery_codes (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    code VARCHAR(32) NOT NULL,
    created_at TIMESTAMP NOT NULL,
    used BOOLEAN DEFAULT FALSE,
    used_at TIMESTAMP
); 