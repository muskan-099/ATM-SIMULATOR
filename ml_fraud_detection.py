
from pathlib import Path
import sqlite3

import pandas as pd
from sklearn.ensemble import IsolationForest


# Main ATM_SIMULATOR folder
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "atm.db"


def get_db_connection():
    """Connect to the existing ATM database."""
    return sqlite3.connect(DB_PATH, timeout=10)


def get_transaction_data():
    """Read historical withdrawal transactions."""
    connection = get_db_connection()

    try:
        query = """
            SELECT account_no, amount
            FROM transactions
            WHERE transaction_type = 'WITHDRAW'
        """

        return pd.read_sql_query(query, connection)

    finally:
        connection.close()


def train_fraud_model():
    """Train an anomaly-detection model on historical withdrawals."""
    df = get_transaction_data()

    # Require at least five historical withdrawals
    if len(df) < 5:
        return None

    # Count historical withdrawals for each account
    df["transaction_frequency"] = (
        df.groupby("account_no")["account_no"]
        .transform("count")
    )

    training_data = df[
        ["amount", "transaction_frequency"]
    ]

    model = IsolationForest(
        contamination=0.2,
        random_state=42
    )

    model.fit(training_data)

    return model


def detect_anomaly(account_no, amount):
    """Return True if a withdrawal is flagged as anomalous."""
    model = train_fraud_model()

    # Not enough historical data to train
    if model is None:
        return False

    connection = get_db_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM transactions
            WHERE account_no = ?
              AND transaction_type = 'WITHDRAW'
            """,
            (account_no,)
        )

        transaction_frequency = cursor.fetchone()[0]

    finally:
        connection.close()

    # Use matching feature names to avoid sklearn warnings
    prediction_data = pd.DataFrame(
        [[float(amount), transaction_frequency]],
        columns=["amount", "transaction_frequency"]
    )

    prediction = model.predict(prediction_data)

    # -1 means anomalous; 1 means not flagged
    return bool(prediction[0] == -1)
