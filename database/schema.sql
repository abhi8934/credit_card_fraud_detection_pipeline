DROP TABLE IF EXISTS transactions;
CREATE TABLE transactions(
    id SERIAL PRIMARY KEY,
    transaction_id VARCHAR(50) UNIQUE NOT NULL,
    category VARCHAR(50),
    amount NUMERIC(12, 2) NOT NULL,
    state VARCHAR(50),
    lat DOUBLE PRECISION,
    long DOUBLE PRECISION,
    city_pop DOUBLE PRECISION,
    merch_lat DOUBLE PRECISION,
    merch_long DOUBLE PRECISION,
    age INTEGER,
    month_sin DOUBLE PRECISION,
    month_cos DOUBLE PRECISION,
    transaction_type VARCHAR(50),
    is_fraud BOOLEAN NOT NULL DEFAULT FALSE,
	fraud_prob DOUBLE PRECISION,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);