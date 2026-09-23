import pandas as pd
from kafka import KafkaProducer
import json
import numpy as np
from pathlib import Path
import time

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / 'data'

producer = KafkaProducer(
    bootstrap_servers='localhost:9092',
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)


df = pd.read_csv(DATA_DIR/"credit_card_transactions.csv")

def generate_transaction(df):
    # --------------------------------
    # Adding extra columns
    # --------------------------------
    df['trans_date_trans_time'] = pd.to_datetime(df['trans_date_trans_time'])
    df['dob'] = pd.to_datetime(df['dob'])

    df['age'] = ((df['trans_date_trans_time'] - df['dob']).dt.days / 365.25).astype(int)

    df['month'] = df['trans_date_trans_time'].dt.month

    df['month_sin'] = np.sin(2 * np.pi * df['month'] / 12)
    df['month_cos'] = np.cos(2 * np.pi * df['month'] / 12)

    # --------------------------------
    # Decide whether transaction is fraud
    # --------------------------------
    is_fraud = np.random.random() < 0.02

    # Start from realistic transaction
    row = df.sample(1).iloc[0].copy()

    # --------------------------------
    # Normal variation
    # --------------------------------

    row["amt"] *= np.random.normal(1.0, 0.15)
    row["amt"] = max(1, row["amt"])

    row["age"] += np.random.randint(-2, 3)
    row["age"] = np.clip(row["age"], 18, 100)

    row["city_pop"] *= np.random.normal(1.0, 0.05)
    row["city_pop"] = max(1, int(row["city_pop"]))

    # --------------------------------
    # Month
    # --------------------------------

    month = np.random.randint(1, 13)

    row["month_sin"] = np.sin(
        2 * np.pi * month / 12
    )

    row["month_cos"] = np.cos(
        2 * np.pi * month / 12
    )

    # --------------------------------
    # FRAUD MODIFICATIONS
    # --------------------------------

    if is_fraud:
        # 70% chance of unusually high amount
        if np.random.random() < 0.70:
            row["amt"] *= np.random.uniform(1.5, 3.0)

        # 60% chance of unusual merchant location
        if np.random.random() < 0.60:
            row["merch_lat"] = (
                row["lat"] +
                np.random.uniform(-2, 2)
            )

            row["merch_long"] = (
                row["long"] +
                np.random.uniform(-2, 2)
            )

        # 30% chance of changing category
        if np.random.random() < 0.30:
            row["category"] = np.random.choice(
                df["category"].unique()
            )

    # --------------------------------
    # Return
    # --------------------------------
    features = ['category', 'amt', 'state',
                 'lat', 'long', 'city_pop', 
                 'merch_lat', 'merch_long', 'age', 
                 'month_sin', 'month_cos']
    row = row[features]
    return row, is_fraud

tx_id = 100000
while True:
    row, is_fraud = generate_transaction(df)

    transaction = {
        "transaction_id": f"TX{tx_id}",
        # Model Features
        "amt": float(row["amt"]),
        "lat" : float(row["lat"]),
        "long" : float(row["long"]),
        "city_pop" : float(row["city_pop"]),
        "merch_lat" : float(row["merch_lat"]),
        "merch_long" : float(row["merch_long"]),
        "age" : int(row["age"]),
        "month_sin" : float(row["month_sin"]),
        "month_cos" : float(row["month_cos"]),

        #Catagorical_Features
        "state": row['state'],
        'category': row["category"],

        # Ground truth
        'is_fraud': int(is_fraud)
    }

    producer.send(
        "transactions",
        value=transaction
    )

    print(
        f"[SENT] {transaction['transaction_id']} | "
        f"Amount: {transaction['amt']:.2f} | "
        f"Category: {transaction['category']} | "
        f"Fraud: {is_fraud}"
    )

    tx_id += 1
    time.sleep(1)