from flask import Flask, render_template, request, redirect, flash
import sqlite3
import time

app = Flask(__name__)
app.secret_key = "secret123"

MAX_ATTEMPTS = 5
BLOCK_TIME = 120  # seconds


# ---------------- DATABASE ---------------- #

def init_db():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS attempts (
        ip TEXT,
        attempts INTEGER,
        last_attempt REAL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS blocked (
        ip TEXT,
        unblock_time REAL
    )
    """)

    conn.commit()
    conn.close()


init_db()


# ---------------- FUNCTIONS ---------------- #

def is_blocked(ip):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("SELECT unblock_time FROM blocked WHERE ip=?", (ip,))
    result = cursor.fetchone()

    if result:
        if time.time() < result[0]:
            conn.close()
            return True
        else:
            cursor.execute("DELETE FROM blocked WHERE ip=?", (ip,))
            conn.commit()

    conn.close()
    return False


def record_attempt(ip):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("SELECT attempts FROM attempts WHERE ip=?", (ip,))
    result = cursor.fetchone()

    if result:
        attempts = result[0] + 1
        cursor.execute("UPDATE attempts SET attempts=?, last_attempt=? WHERE ip=?",
                       (attempts, time.time(), ip))
    else:
        attempts = 1
        cursor.execute("INSERT INTO attempts VALUES (?, ?, ?)",
                       (ip, attempts, time.time()))

    if attempts >= MAX_ATTEMPTS:
        unblock_time = time.time() + BLOCK_TIME
        cursor.execute("INSERT INTO blocked VALUES (?, ?)", (ip, unblock_time))
        cursor.execute("DELETE FROM attempts WHERE ip=?", (ip,))
        conn.commit()
        conn.close()
        return True

    conn.commit()
    conn.close()
    return False


def reset_attempts(ip):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("DELETE FROM attempts WHERE ip=?", (ip,))
    conn.commit()
    conn.close()


# ---------------- ROUTES ---------------- #

@app.route("/", methods=["GET", "POST"])
def login():

    ip = request.remote_addr

    if is_blocked(ip):
        return "<h2>Your IP is temporarily BLOCKED due to multiple failed login attempts.</h2>"

    if request.method == "POST":

        username = request.form.get("username")
        password = request.form.get("password")

        # Dummy credentials
        if username == "admin" and password == "admin123":
            reset_attempts(ip)
            return "<h2>Login Successful ✅</h2>"

        else:
            blocked = record_attempt(ip)

            if blocked:
                return "<h2>Too many failed attempts! Brute force attack is been detected.. IP BLOCKED.</h2>"

            flash("Invalid credentials!")

    return render_template("login.html")


if __name__ == "__main__":
    app.run(debug=True)
