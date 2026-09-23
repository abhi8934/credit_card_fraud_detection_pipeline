import json
import joblib
import pandas as pd
import traceback
from kafka import KafkaConsumer
from pathlib import Path
import psycopg2
import os
from dotenv import load_dotenv


# --------------------------------------------------
# Paths
# --------------------------------------------------

BASE_DIR = Path(__file__).parent
MODEL_DIR = BASE_DIR / "models"


# --------------------------------------------------
# Load trained XGBoost pipeline
# --------------------------------------------------

model = joblib.load(
    MODEL_DIR / "XGBoost_fraud_model.pkl"
)

print("[INFO] XGBoost model loaded.")


# --------------------------------------------------
# Kafka Consumer
# --------------------------------------------------

consumer = KafkaConsumer(
    "transactions",

    bootstrap_servers="localhost:9092",

    # Convert JSON bytes -> Python dictionary
    value_deserializer=lambda x: json.loads(
        x.decode("utf-8")
    ),

    # Start from the latest messages
    auto_offset_reset="latest",

    # Give this consumer its own group
    group_id="fraud-detection-consumer",

    enable_auto_commit=True
)

print("[INFO] Consumer connected to Kafka.")
print("[INFO] Waiting for transactions...\n")

# --------------------------------------------------
# Database connection
# --------------------------------------------------
load_dotenv()

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

conn = psycopg2.connect(
    host=DB_HOST,
    port=DB_PORT,
    database=DB_NAME,
    user=DB_USER,
    password=DB_PASSWORD
)
cursor = conn.cursor()
# --------------------------------------------------
# Model features
# --------------------------------------------------

model_features = ['category', 'amt', 'state',
            'lat', 'long', 'city_pop', 
            'merch_lat', 'merch_long', 'age', 
            'month_sin', 'month_cos']

# --------------------------------------------------
# Consume transactions
# --------------------------------------------------

for message in consumer:
    transaction = message.value
    try:
        # ------------------------------------------
        # Extract model features
        # ------------------------------------------
    
        features = {
            feature: transaction[feature]
            for feature in model_features
        }

        # Convert to DataFrame
        X = pd.DataFrame(
            [features],
            columns=model_features
        )

        # ------------------------------------------
        # Make prediction
        # ------------------------------------------

        prediction = model.predict(X)[0]

        probability = model.predict_proba(X)[0][1]

        # ------------------------------------------
        # Ground truth
        # ------------------------------------------

        ground_truth = transaction.get(
            "is_fraud"
        )

        prediction_text = (
                    "FRAUD"
                    if prediction == 1
                    else "LEGITIMATE"
        )
        # ------------------------------------------
        # Data in database
        # ------------------------------------------
        try:
            cursor.execute("""
                INSERT INTO transactions 
                (transaction_id, category, amount, 
                state, lat, long,  
                city_pop, merch_lat, merch_long,
                age, month_sin, month_cos,
                is_fraud, fraud_prob, transaction_type)
                VALUES (%s, %s, %s, 
                %s, %s, %s, 
                %s,%s, %s, 
                %s, %s, %s, 
                %s, %s, %s)
                """, ( 
                transaction['transaction_id'],
                transaction['category'],
                transaction['amt'],
                transaction['state'],
                transaction['lat'],
                transaction['long'],
                int(transaction['city_pop']),
                float(transaction['merch_lat']),
                float(transaction['merch_long']),
                int(transaction['age']),
                float(transaction['month_sin']),
                float(transaction['month_cos']),
                bool(prediction),
                float(probability),
                prediction_text
            ))
            conn.commit()
        except Exception as e:
            conn.rollback()
            print(f"[ERROR] Could not process {transaction['transaction_id']}")
            print(e)

        # ------------------------------------------
        # Output
        # ------------------------------------------
        print(
            f"[PREDICTION] "
            f"{transaction['transaction_id']} | "
            f"Amount: {transaction['amt']:.2f} | "
            f"Category: {transaction['category']} | "
            f"Prediction: {prediction_text} | "
            f"Probability: {probability:.4f} | "
            f"Ground Truth: {ground_truth}"
        )
    except Exception as e:
        print(
            f"[ERROR] Could not process "
            f"{transaction.get('transaction_id', 'UNKNOWN')}"
        )
        print(traceback.print_exc())