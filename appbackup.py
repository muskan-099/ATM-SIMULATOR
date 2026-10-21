
from pathlib import Path
import sqlite3

from flask import (
    Flask, render_template_string, request,
    redirect, url_for, session, flash
)

app = Flask(__name__)
app.secret_key = "local-demo-change-before-deployment"

# Existing database: ATM_SIMULATOR/atm.db
BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "atm.db"


def get_db_connection():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


LOGIN_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
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
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>ATM Dashboard</title>
        <style>
            body {
                margin: 0; padding: 30px; background: #0b1220;
                color: white; font-family: Arial, sans-serif;
            }
            .card {
                max-width: 650px; margin: 40px auto; padding: 30px;
                border-radius: 18px; background: #172238;
            }
            h1 { color: #60a5fa; }
            .balance { font-size: 32px; font-weight: bold; }
            a { color: #93c5fd; }
        </style>
    </head>
    <body>
        <main class="card">
            <h1>Welcome, {{ user["name"] }}!</h1>
            <p>Your account is connected to the existing ATM database.</p>
            <p>Available balance</p>
            <div class="balance">₹{{ "%.2f"|format(user["balance"]) }}</div>
            <p>Banking features will be added step by step.</p>
            <a href="{{ url_for('logout') }}">Logout</a>
        </main>
    </body>
    </html>
    """, user=user)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


if __name__ == "__main__":
    app.run(debug=True)
