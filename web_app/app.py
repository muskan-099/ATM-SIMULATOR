
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from ml_fraud_detection import detect_anomaly

from pathlib import Path
import sqlite3
from datetime import datetime


from flask import (
    Flask, render_template_string, request,
    redirect, url_for, session, flash
)

app = Flask(__name__)
app.secret_key = "local-demo-change-before-deployment"

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "atm.db"


def get_db_connection():
    connection = sqlite3.connect(DB_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    return connection


def calculate_notes(amount, inventory):
    """Return a possible note combination, or None."""
    result = {}
    remaining = amount

    for denomination, available in sorted(
        inventory, key=lambda item: item[0], reverse=True
    ):
        count = min(remaining // denomination, available)

        if count > 0:
            result[denomination] = count
            remaining -= denomination * count

    return result if remaining == 0 else None


LOGIN_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>ATM Simulator | Login</title>
    <style>
        * { box-sizing: border-box; }
        body {
            margin: 0; min-height: 100vh; display: grid;
            place-items: center; background: #0b1220;
            color: white; font-family: Arial, sans-serif;
        }
        .card {
            width: min(90%, 390px); padding: 34px;
            border-radius: 18px; background: #172238;
            box-shadow: 0 15px 40px #0005;
        }
        h1 { color: #60a5fa; text-align: center; }
        p { color: #cbd5e1; text-align: center; }
        label { display: block; margin-top: 18px; }
        input {
            width: 100%; padding: 12px; margin-top: 8px;
            border: 1px solid #475569; border-radius: 8px;
            background: #0b1220; color: white;
        }
        button {
            width: 100%; padding: 12px; margin-top: 24px;
            border: 0; border-radius: 8px;
            background: #2563eb; color: white;
            font-size: 16px; cursor: pointer;
        }
        .message { color: #fca5a5; text-align: center; }
    </style>
</head>
<body>
    <main class="card">
        <h1>ATM Simulator</h1>
        <p>Secure Banking · ML Fraud Detection</p>

        {% for message in get_flashed_messages() %}
            <div class="message">{{ message }}</div>
        {% endfor %}

        <form method="POST">
            <label for="account_no">Account Number</label>
            <input id="account_no" name="account_no"
                   inputmode="numeric" required>

            <label for="pin">ATM PIN</label>
            <input id="pin" name="pin" type="password"
                   inputmode="numeric" required>

            <button type="submit">Login Securely</button>
        </form>
    </main>
</body>
</html>
"""


@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        account_no = request.form.get("account_no", "").strip()
        pin = request.form.get("pin", "").strip()

        if not account_no.isdigit() or not pin:
            flash("Enter a valid account number and PIN.")
            return redirect(url_for("login"))

        connection = get_db_connection()
        try:
            user = connection.execute(
                """
                SELECT account_no, name, account_locked
                FROM users
                WHERE account_no = ? AND pin = ?
                """,
                (int(account_no), pin),
            ).fetchone()
        finally:
            connection.close()

        if user is None:
            flash("Invalid account number or PIN.")
        elif user["account_locked"]:
            flash("Your account is locked. Contact the administrator.")
        else:
            session.clear()
            session["account_no"] = user["account_no"]
            session["name"] = user["name"]
            return redirect(url_for("dashboard"))

        return redirect(url_for("login"))

    return render_template_string(LOGIN_PAGE)


@app.route("/dashboard")
def dashboard():
    if "account_no" not in session:
        return redirect(url_for("login"))

    connection = get_db_connection()
    try:
        user = connection.execute(
            "SELECT name, balance FROM users WHERE account_no = ?",
            (session["account_no"],),
        ).fetchone()
    finally:
        connection.close()

    if user is None:
        session.clear()
        return redirect(url_for("login"))

    return render_template_string("""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>ATM Simulator | Dashboard</title>
        <style>
            * { box-sizing: border-box; }
            body {
                margin: 0; padding: 24px; background: #0b1220;
                color: white; font-family: Arial, sans-serif;
            }
            .container { max-width: 760px; margin: 25px auto; }
            .card {
                padding: 24px; margin-bottom: 20px;
                border-radius: 16px; background: #172238;
            }
            h1, h2 { color: #60a5fa; }
            .balance { font-size: 32px; font-weight: bold; }
            .actions {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
                gap: 16px;
            }
            input, button {
                width: 100%; padding: 12px; margin-top: 12px;
                border-radius: 8px; font-size: 15px;
            }
            input {
                border: 1px solid #475569;
                background: #0b1220; color: white;
            }
            button {
                border: 0; background: #2563eb;
                color: white; cursor: pointer;
            }
            .withdraw button { background: #dc2626; }
            .message { color: #fcd34d; margin-bottom: 10px; }
            a { color: #93c5fd; }
            .note { color: #cbd5e1; font-size: 13px; }
        </style>
    </head>
    <body>
        <main class="container">
            <section class="card">
                <h1>Welcome, {{ user["name"] }}!</h1>
                <p>ATM Simulator Web Banking</p>

                {% for message in get_flashed_messages() %}
                    <p class="message">{{ message }}</p>
                {% endfor %}

                <p>Available balance</p>
                <div class="balance">
                    ₹{{ "%.2f"|format(user["balance"]) }}
                </div>
                <p><a href="{{ url_for('dashboard') }}">Refresh balance</a></p>
            </section>

            <div class="actions">
                <section class="card">
                    <h2>Deposit</h2>
                    <form method="POST"
                          action="{{ url_for('deposit') }}">
                        <label for="deposit_amount">Amount (₹)</label>
                        <input id="deposit_amount" name="amount"
                               type="number" min="1" step="1"
                               placeholder="Enter amount" required>
                        <button type="submit">Deposit Money</button>
                    </form>
                </section>

                <section class="card withdraw">
                    <h2>Withdraw</h2>
                    <form method="POST"
                          action="{{ url_for('withdraw') }}">
                        <label for="withdraw_amount">Amount (₹)</label>
                        <input id="withdraw_amount" name="amount"
                               type="number" min="50" step="50"
                               placeholder="Multiple of ₹50" required>
                        <button type="submit">Withdraw Money</button>
                    </form>
                    <p class="note">
                        Withdrawal amounts must be multiples of ₹50.
                        Available ATM notes are checked before dispensing.
                    </p>
                </section>
            </div>

            <section class="card">
                <h2>Banking options</h2>
                <p>Balance is retrieved from your existing SQLite database.</p>
                <p><a href="{{ url_for('statement') }}">View Mini Statement</a></p>
                <a href="{{ url_for('logout') }}">Logout</a>
            </section>
        </main>
    </body>
    </html>
    """, user=user)


def parse_amount():
    raw_amount = request.form.get("amount", "").strip()

    try:
        amount = int(raw_amount)
    except (ValueError, TypeError):
        return None

    if amount <= 0:
        return None

    return amount


@app.route("/deposit", methods=["POST"])
def deposit():
    if "account_no" not in session:
        return redirect(url_for("login"))

    amount = parse_amount()
    if amount is None:
        flash("Enter a valid positive whole-number amount.")
        return redirect(url_for("dashboard"))

    connection = get_db_connection()

    try:
        connection.execute("BEGIN IMMEDIATE")

        user = connection.execute(
            "SELECT balance FROM users WHERE account_no = ?",
            (session["account_no"],),
        ).fetchone()

        if user is None:
            connection.rollback()
            session.clear()
            return redirect(url_for("login"))

        new_balance = round(float(user["balance"]) + amount, 2)
        now = datetime.now()

        connection.execute(
            "UPDATE users SET balance = ? WHERE account_no = ?",
            (new_balance, session["account_no"]),
        )

        connection.execute(
            """
            INSERT INTO transactions
                (account_no, transaction_type, amount,
                 balance_after, date, time)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                session["account_no"], "DEPOSIT", amount,
                new_balance, now.strftime("%Y-%m-%d"),
                now.strftime("%H:%M:%S"),
            ),
        )

        connection.commit()
        flash(f"₹{amount} deposited successfully.")

    except sqlite3.Error:
        connection.rollback()
        flash("Deposit failed because of a database error.")
    finally:
        connection.close()

    return redirect(url_for("dashboard"))


@app.route("/withdraw", methods=["POST"])
def withdraw():
    if "account_no" not in session:
        return redirect(url_for("login"))

    amount = parse_amount()
    if amount is None or amount % 50 != 0:
        flash("Enter a withdrawal amount that is a multiple of ₹50.")
        return redirect(url_for("dashboard"))

    connection = get_db_connection()

    try:
        connection.execute("BEGIN IMMEDIATE")

        user = connection.execute(
            "SELECT balance FROM users WHERE account_no = ?",
            (session["account_no"],),
        ).fetchone()

        if user is None:
            connection.rollback()
            session.clear()
            return redirect(url_for("login"))

        if float(user["balance"]) < amount:
            connection.rollback()
            flash("Insufficient account balance.")
            return redirect(url_for("dashboard"))

        inventory_rows = connection.execute(
            """
            SELECT denomination, note_count
            FROM atm_cash
            ORDER BY denomination DESC
            """
        ).fetchall()

        inventory = [
            (int(row["denomination"]), int(row["note_count"]))
            for row in inventory_rows
        ]

        notes = calculate_notes(amount, inventory)

        if notes is None:
            connection.rollback()
            flash("ATM does not have a suitable combination of notes.")
            return redirect(url_for("dashboard"))

        new_balance = round(float(user["balance"]) - amount, 2)
        now = datetime.now()

        connection.execute(
            "UPDATE users SET balance = ? WHERE account_no = ?",
            (new_balance, session["account_no"]),
        )

        for denomination, count in notes.items():
            cursor = connection.execute(
                """
                UPDATE atm_cash
                SET note_count = note_count - ?
                WHERE denomination = ? AND note_count >= ?
                """,
                (count, denomination, count),
            )

            if cursor.rowcount != 1:
                raise sqlite3.IntegrityError(
                    "ATM cash inventory changed during withdrawal."
                )

        connection.execute(
            """
            INSERT INTO transactions
                (account_no, transaction_type, amount,
                 balance_after, date, time)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                session["account_no"], "WITHDRAW", amount,
                new_balance, now.strftime("%Y-%m-%d"),
                now.strftime("%H:%M:%S"),
            ),
        )

        connection.commit()

        note_summary = ", ".join(
            f"₹{denomination} × {count}"
            for denomination, count in notes.items()
        )
        flash(f"₹{amount} withdrawn successfully. Notes: {note_summary}")

    except sqlite3.Error:
        connection.rollback()
        flash("Withdrawal failed because of a database error.")
    finally:
        connection.close()

    return redirect(url_for("dashboard"))
    if amount is None or amount % 50 != 0:
        flash("Enter a withdrawal amount that is a multiple of ₹50.")
        return redirect(url_for("dashboard"))
    
    try:
        is_suspicious = detect_anomaly(
            session["account_no"],
            amount
        )
    except Exception:
        app.logger.exception("ML anomaly detection failed")
        flash("Withdrawal could not be verified. Please try again.")
        return redirect(url_for("dashboard"))

    if is_suspicious:
        flash(
            "Suspicious withdrawal detected by ML. "
            "Transaction was not processed."
        )
        return redirect(url_for("dashboard"))
    connection = get_db_connection()



@app.route("/statement")
def statement():
    if "account_no" not in session:
        return redirect(url_for("login"))

    
    # ML-based anomaly detection
    try:
        is_suspicious = detect_anomaly(
            session["account_no"],
            amount
        )
    except Exception:
        app.logger.exception("ML anomaly detection failed")
        flash("Withdrawal could not be verified. Please try again.")
        return redirect(url_for("dashboard"))

    if is_suspicious:
        flash(
            "Suspicious withdrawal detected by ML. "
            "Transaction was not processed."
        )
        return redirect(url_for("dashboard"))


    connection = get_db_connection()
    try:
        transactions = connection.execute(
            """
            SELECT transaction_type, amount, balance_after, date, time
            FROM transactions
            WHERE account_no = ?
            ORDER BY transaction_id DESC
            LIMIT 20
            """,
            (session["account_no"],),
        ).fetchall()
    finally:
        connection.close()

    return render_template_string("""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Mini Statement</title>
        <style>
            body {
                margin: 0; padding: 24px;
                background: #0b1220; color: white;
                font-family: Arial, sans-serif;
            }
            .card {
                max-width: 900px; margin: 20px auto;
                padding: 24px; background: #172238;
                border-radius: 16px; overflow-x: auto;
            }
            h1 { color: #60a5fa; }
            table { width: 100%; border-collapse: collapse; }
            th, td {
                padding: 12px; text-align: left;
                border-bottom: 1px solid #334155;
                white-space: nowrap;
            }
            th { color: #93c5fd; }
            a { color: #93c5fd; }
            .empty { color: #cbd5e1; }
        </style>
    </head>
    <body>
        <main class="card">
            <h1>Mini Statement</h1>
            <p>Showing your latest 20 transactions.</p>

            {% if transactions %}
            <table>
                <thead>
                    <tr>
                        <th>Type</th>
                        <th>Amount</th>
                        <th>Balance After</th>
                        <th>Date</th>
                        <th>Time</th>
                    </tr>
                </thead>
                <tbody>
                    {% for tx in transactions %}
                    <tr>
                        <td>{{ tx["transaction_type"] }}</td>
                        <td>₹{{ "%.2f"|format(tx["amount"]) }}</td>
                        <td>₹{{ "%.2f"|format(tx["balance_after"]) }}</td>
                        <td>{{ tx["date"] }}</td>
                        <td>{{ tx["time"] }}</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
            {% else %}
                <p class="empty">No transactions found yet.</p>
            {% endif %}

            <p><a href="{{ url_for('dashboard') }}">Back to Dashboard</a></p>
        </main>
    </body>
    </html>
    """, transactions=transactions)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


if __name__ == "__main__":
    app.run(debug=True)
