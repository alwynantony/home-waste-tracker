
import sqlite3
from pathlib import Path

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    jsonify
)
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

# Use an absolute path for the database
BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "database.db"

# Development secret key (replace with a private key before deployment)
app.secret_key = "change-this-to-a-random-secret-key"


# ---------------- DATABASE ----------------

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_db_connection()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS waste_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            waste_type TEXT NOT NULL,
            quantity REAL NOT NULL CHECK (quantity > 0),
            date TEXT NOT NULL DEFAULT (date('now')),
            FOREIGN KEY (user_id)
                REFERENCES users(id)
                ON DELETE CASCADE
        )
    """)

    conn.commit()
    conn.close()
    init_db()

# ---------------- HOME ----------------

@app.route("/")
def home():
    return render_template("index.html")


# ---------------- REGISTRATION ----------------

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not username or not email or not password:
            flash("All fields are required.")
            return redirect(url_for("register"))

        if len(password) < 8:
            flash("Password must contain at least 8 characters.")
            return redirect(url_for("register"))

        # Hash the password before storing it
        hashed_password = generate_password_hash(password)

        conn = get_db_connection()

        try:
            conn.execute("""
                INSERT INTO users (username, email, password)
                VALUES (?, ?, ?)
            """, (username, email, hashed_password))

            conn.commit()

            flash("Registration successful! Please log in.")
            return redirect(url_for("login"))

        except sqlite3.IntegrityError:
            flash("Username or email already exists.")
            return redirect(url_for("register"))

        finally:
            conn.close()

    return render_template("register.html")


# ---------------- LOGIN ----------------

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        conn = get_db_connection()

        user = conn.execute("""
            SELECT * FROM users
            WHERE username = ?
        """, (username,)).fetchone()

        conn.close()

        if user and check_password_hash(user["password"], password):

            session.clear()
            session["user_id"] = user["id"]
            session["username"] = user["username"]

            flash("Login successful!")
            return redirect(url_for("dashboard"))

        flash("Invalid username or password.")
        return redirect(url_for("login"))

    return render_template("login.html")


# ---------------- DASHBOARD ----------------

@app.route("/dashboard")
def dashboard():

    if "user_id" not in session:
        flash("Please log in first.")
        return redirect(url_for("login"))

    return render_template("dashboard.html")


# ---------------- LOGOUT ----------------

@app.route("/logout")
def logout():

    session.clear()

    flash("You have been logged out.")
    return redirect(url_for("login"))


# ---------------- LOG WASTE ----------------

@app.route("/submit_waste", methods=["POST"])
def submit_waste():

    # Check whether user is logged in
    if "user_id" not in session:
        flash("Please log in first.")
        return redirect(url_for("login"))

    waste_type = request.form.get("waste_type", "").strip()
    quantity = request.form.get("quantity", "").strip()

    # Allowed waste categories
    allowed_types = [
        "Food Waste",
        "Plastic",
        "Paper",
        "Metal",
        "E-Waste"
    ]

    if waste_type not in allowed_types:
        flash("Invalid waste type.")
        return redirect(url_for("log_waste"))

    # Validate quantity
    try:
        quantity = float(quantity)

        if quantity <= 0:
            flash("Quantity must be greater than zero.")
            return redirect(url_for("log_waste"))

    except (ValueError, TypeError):
        flash("Please enter a valid quantity.")
        return redirect(url_for("log_waste"))

    # Save waste record to SQLite
    conn = get_db_connection()

    conn.execute("""
        INSERT INTO waste_records
        (user_id, waste_type, quantity)
        VALUES (?, ?, ?)
    """, (
        session["user_id"],
        waste_type,
        quantity
    ))

    conn.commit()
    conn.close()

    flash("Waste record saved successfully!")

    return redirect(url_for("dashboard"))


# ---------------- LOG WASTE PAGE ----------------

@app.route("/log_waste")
def log_waste():

    if "user_id" not in session:
        flash("Please log in first.")
        return redirect(url_for("login"))

    return render_template("log_waste.html")

# ---------------- RUN APPLICATION ----------------



# ---------------- WASTE DATA API ----------------

@app.route("/api/waste-data")
def waste_data():

    # Only logged-in users can access their data
    if "user_id" not in session:
        return jsonify({"error": "Please log in first"}), 401

    conn = get_db_connection()

    records = conn.execute("""
        SELECT waste_type, SUM(quantity) AS total
        FROM waste_records
        WHERE user_id = ?
        GROUP BY waste_type
    """, (session["user_id"],)).fetchall()

    conn.close()

    # Convert database results into JSON
    data = {
        "Food Waste": 0,
        "Plastic": 0,
        "Paper": 0,
        "Metal": 0,
        "E-Waste": 0
    }

    for record in records:
        data[record["waste_type"]] = record["total"]

    return jsonify(data)



@app.route("/api/waste-history")
def waste_history():

    if "user_id" not in session:
        return jsonify({"error": "Please log in"}), 401

    conn = get_db_connection()

    records = conn.execute("""
        SELECT id, waste_type, quantity, date
        FROM waste_records
        WHERE user_id = ?
        ORDER BY id DESC
    """, (session["user_id"],)).fetchall()

    conn.close()

    return jsonify([
        {
            "id": row["id"],
            "waste_type": row["waste_type"],
            "quantity": row["quantity"],
            "date": row["date"]
        }
        for row in records
    ])

if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5001)
