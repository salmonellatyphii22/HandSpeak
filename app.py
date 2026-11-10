
import os
import sqlite3
from functools import wraps
import cv2
import numpy as np

from flask import (
    Flask, render_template, request,
    redirect, url_for, flash, session,
    Response, jsonify
)
from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

from main import GestureCamera


app = Flask(__name__)

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "handspeak-local-development-key-change-before-deployment"
)

app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax"
)

DATABASE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "users.db"
)

camera = GestureCamera()


# ==========================================
# DATABASE
# ==========================================

def get_db():

    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row

    return connection


def init_db():

    connection = get_db()

    connection.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    connection.commit()
    connection.close()


# ==========================================
# LOGIN PROTECTION
# ==========================================

def login_required(function):

    @wraps(function)
    def wrapper(*args, **kwargs):

        if "user_id" not in session:
            flash("Please log in to continue.", "error")
            return redirect(url_for("login"))

        return function(*args, **kwargs)

    return wrapper


# ==========================================
# HOME
# ==========================================

@app.route("/")
def home():

    if "user_id" in session:
        return redirect(url_for("dashboard"))

    return redirect(url_for("login"))


# ==========================================
# SIGNUP
# ==========================================

@app.route("/signup", methods=["GET", "POST"])
def signup():

    if "user_id" in session:
        return redirect(url_for("dashboard"))

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get(
            "confirm_password", ""
        )

        if not name or not email or not password:
            flash("Please complete all fields.", "error")

        elif len(password) < 8:
            flash(
                "Password must contain at least 8 characters.",
                "error"
            )

        elif password != confirm_password:
            flash("Passwords do not match.", "error")

        else:

            connection = get_db()

            try:

                hashed_password = generate_password_hash(password, method="pbkdf2:sha256")

                connection.execute(
                    """
                    INSERT INTO users (name, email, password)
                    VALUES (?, ?, ?)
                    """,
                    (name, email, hashed_password)
                )

                connection.commit()

                flash(
                    "Account created successfully! Please log in.",
                    "success"
                )

                return redirect(url_for("login"))

            except sqlite3.IntegrityError:

                flash(
                    "An account with this email already exists.",
                    "error"
                )

            finally:
                connection.close()

    return render_template("signup.html")


# ==========================================
# LOGIN
# ==========================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if "user_id" in session:
        return redirect(url_for("dashboard"))

    if request.method == "POST":

        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        connection = get_db()

        user = connection.execute(
            "SELECT * FROM users WHERE email = ?",
            (email,)
        ).fetchone()

        connection.close()

        if user and check_password_hash(
            user["password"],
            password
        ):

            session.clear()

            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            session["user_email"] = user["email"]

            return redirect(url_for("dashboard"))

        flash("Invalid email or password.", "error")

    return render_template("login.html")


# ==========================================
# DASHBOARD
# ==========================================

@app.route("/dashboard")
@login_required
def dashboard():

    return render_template(
        "dashboard.html",
        name=session.get("user_name", "User")
    )


# ==========================================
# CAMERA STREAM
# ==========================================

@app.route("/process_frame", methods=["POST"])
@login_required
def process_frame():

    if "frame" not in request.files:
        return jsonify({
            "error": "No frame received"
        }), 400

    file = request.files["frame"]

    image_bytes = file.read()

    np_array = np.frombuffer(
        image_bytes,
        np.uint8
    )

    frame = cv2.imdecode(
        np_array,
        cv2.IMREAD_COLOR
    )

    if frame is None:
        return jsonify({
            "error": "Invalid image"
        }), 400

    processed_frame = camera.process_frame(
        frame
    )

    if processed_frame is None:
        return jsonify({
            "error": camera.camera_error
            or "Frame processing failed"
        }), 500

    import base64

    image_base64 = base64.b64encode(
        processed_frame
    ).decode("utf-8")

    stats = camera.get_stats()

    return jsonify({
        "image": image_base64,
        "gesture": stats["gesture"],
        "hands": stats["hands"],
        "fps": stats["fps"],
        "active": stats["active"],
        "history": stats["history"]
    })


# ==========================================
# CAMERA STATISTICS
# ==========================================

@app.route("/api/stats")
@login_required
def stats():

    return jsonify(camera.get_stats())


# ==========================================
# LOGOUT
# ==========================================

@app.route("/logout", methods=["POST"])
@login_required
def logout():

    session.clear()

    flash("You have logged out successfully.", "success")

    return redirect(url_for("login"))


# ==========================================
# RUN APPLICATION
# ==========================================

if __name__ == "__main__":

    init_db()

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=False,
        threaded=True
    )
