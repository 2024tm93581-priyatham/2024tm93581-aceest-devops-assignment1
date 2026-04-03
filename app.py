import os
import random
import sqlite3
from io import BytesIO
from datetime import datetime

from fpdf import FPDF
from fpdf.enums import XPos, YPos
from flask import Flask, abort, jsonify, render_template, request, send_file, session

app = Flask(__name__)
app.config["DATABASE"] = "aceest_fitness.db"
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-in-production")


# Program list updated to match Aceestver-3.0.1.
# Note: keys are kept ASCII-only to avoid unicode issues in some environments.
PROGRAMS = {
    "Fat Loss (FL) - 3 day": {
        "workout": (
            "Mon: Full Body Squat + AMRAP\n"
            "Wed: Bench Press + EMOM 20min\n"
            "Fri: Deadlift + Active Recovery"
        ),
        "diet": (
            "B: 3 Egg Whites + Oats Idli\n"
            "L: Grilled Chicken + Brown Rice\n"
            "D: Fish Curry + Millet Roti\n"
            "Target: 2,000 kcal"
        ),
        "color": "#e74c3c",
    },
    "Fat Loss (FL) - 5 day": {
        "workout": (
            "Mon: 5x5 Back Squat + AMRAP\n"
            "Tue: EMOM 20min Assault Bike\n"
            "Wed: Bench Press + 21-15-9\n"
            "Thu: 10RFT Deadlifts/Box Jumps\n"
            "Fri: 30min Active Recovery"
        ),
        "diet": (
            "B: 3 Egg Whites + Oats Idli\n"
            "L: Grilled Chicken + Brown Rice\n"
            "D: Fish Curry + Millet Roti\n"
            "Target: 2,000 kcal"
        ),
        "color": "#c0392b",
    },
    "Muscle Gain (MG) - PPL": {
        "workout": (
            "Mon: Push (Bench/Incline) + Accessories\n"
            "Tue: Pull (Rows/Deadlift variations)\n"
            "Wed: Legs (Squat/Front Squat)\n"
            "Thu: Push (Volume)\n"
            "Fri: Pull (Volume)\n"
            "Sat: Legs (Power)"
        ),
        "diet": (
            "B: 4 Eggs + PB Oats\n"
            "L: Chicken Biryani (250g Chicken)\n"
            "D: Mutton Curry + Jeera Rice\n"
            "Target: 3,200 kcal"
        ),
        "color": "#2ecc71",
    },
    "Beginner (BG)": {
        "workout": (
            "Circuit Training: Air Squats, Ring Rows, Push-ups.\n"
            "Focus: Technique Mastery & Form (90% Threshold)"
        ),
        "diet": (
            "Balanced Tamil Meals: Idli-Sambar, Rice-Dal, Chapati.\n"
            "Protein: 120g/day"
        ),
        "color": "#3498db",
    },
}


SITE_METRICS = {
    "capacity": "150 Users",
    "area": "10,000 sq ft",
    "break_even": "250 Members",
}

# Calorie factors per program (Aceestver-3.0.1 setup_data parity)
CALORIE_FACTORS = {
    "Fat Loss (FL) - 3 day": 22,
    "Fat Loss (FL) - 5 day": 24,
    "Muscle Gain (MG) - PPL": 35,
    "Beginner (BG)": 26,
}

# Aceestver-3.2.4 AI-style program generator (random template pick)
PROGRAM_TEMPLATES = {
    "Fat Loss": ["Full Body HIIT", "Circuit Training", "Cardio + Weights"],
    "Muscle Gain": ["Push/Pull/Legs", "Upper/Lower Split", "Full Body Strength"],
    "Beginner": ["Full Body 3x/week", "Light Strength + Mobility"],
}


def get_db_connection():
    conn = sqlite3.connect(app.config["DATABASE"])
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password TEXT,
                role TEXT
            )
            """
        )
        cur.execute("SELECT 1 FROM users WHERE username='admin'")
        if not cur.fetchone():
            cur.execute(
                "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                ("admin", "admin", "Admin"),
            )

        # If clients schema is older/partial, recreate (Aceestver-3.2.4 adds membership fields).
        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='clients'"
        )
        exists = cur.fetchone() is not None
        if exists:
            cur.execute("PRAGMA table_info(clients)")
            cols = {row[1] for row in cur.fetchall()}
            required = {
                "id",
                "name",
                "age",
                "height",
                "weight",
                "program",
                "calories",
                "target_weight",
                "target_adherence",
                "membership_status",
                "membership_end",
            }
            if not required.issubset(cols):
                cur.execute("DROP TABLE clients")

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS clients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                age INTEGER,
                height REAL,
                weight REAL,
                program TEXT,
                calories INTEGER,
                target_weight REAL,
                target_adherence INTEGER,
                membership_status TEXT,
                membership_end TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_name TEXT,
                week TEXT,
                adherence INTEGER
            )
            """
        )
        # Workouts (session-level) + exercises (per workout)
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS workouts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_name TEXT,
                date TEXT,
                workout_type TEXT,
                duration_min INTEGER,
                notes TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS exercises (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workout_id INTEGER,
                name TEXT,
                sets INTEGER,
                reps INTEGER,
                weight REAL
            )
            """
        )
        # Body metrics (weight, waist, bodyfat)
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_name TEXT,
                date TEXT,
                weight REAL,
                waist REAL,
                bodyfat REAL
            )
            """
        )
        conn.commit()


@app.route("/", methods=["GET", "POST"])
def index():
    """
    Web UI equivalent of the original Tkinter app.

    - Shows a program dropdown (Fat Loss, Muscle Gain, Beginner).
    - On selection, displays the weekly workout and daily nutrition plan.
    """
    selected_key = None

    if request.method == "POST":
        selected_key = request.form.get("program")
    else:
        selected_key = request.args.get("program")

    selected_program = PROGRAMS.get(selected_key)

    return render_template(
        "index.html",
        programs=PROGRAMS,
        selected_key=selected_key,
        selected_program=selected_program,
        site_metrics=SITE_METRICS,
    )


@app.route("/api/client", methods=["POST"])
def save_client():
    data = request.get_json(silent=True) or request.form

    name = (data.get("name") or "").strip()
    program = (data.get("program") or "").strip()

    if not name or program not in PROGRAMS:
        return (
            jsonify(
                {
                    "status": "error",
                    "message": "Valid name and program are required.",
                }
            ),
            400,
        )

    # Optional fields (store NULL when not provided)
    def _pos_int(v):
        try:
            iv = int(v)
        except (TypeError, ValueError):
            return None
        return iv if iv > 0 else None

    def _pos_float(v):
        try:
            fv = float(v)
        except (TypeError, ValueError):
            return None
        return fv if fv > 0 else None

    age = _pos_int(data.get("age", 0))
    height = _pos_float(data.get("height", 0))
    weight = _pos_float(data.get("weight", 0))
    target_weight = _pos_float(data.get("target_weight", 0))
    target_adherence = _pos_int(data.get("target_adherence", 0))

    membership_status = (data.get("membership_status") or "").strip() or "Active"
    membership_end = (data.get("membership_end") or "").strip() or None
    if membership_end == "":
        membership_end = None

    calories = (
        int(weight * CALORIE_FACTORS[program]) if weight is not None else None
    )

    with get_db_connection() as conn:
        conn.execute(
            """
            INSERT INTO clients
                (name, age, height, weight, program, calories, target_weight,
                 target_adherence, membership_status, membership_end)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET
                age=excluded.age,
                height=excluded.height,
                weight=excluded.weight,
                program=excluded.program,
                calories=excluded.calories,
                target_weight=excluded.target_weight,
                target_adherence=excluded.target_adherence,
                membership_status=excluded.membership_status,
                membership_end=excluded.membership_end
            """,
            (
                name,
                age,
                height,
                weight,
                program,
                calories,
                target_weight,
                target_adherence,
                membership_status,
                membership_end,
            ),
        )
        conn.commit()

    return jsonify(
        {
            "status": "ok",
            "client": {
                "name": name,
                "age": age,
                "height": height,
                "weight": weight,
                "program": program,
                "calories": calories,
                "target_weight": target_weight,
                "target_adherence": target_adherence,
                "membership_status": membership_status,
                "membership_end": membership_end,
            },
        }
    )


@app.route("/api/client/<name>", methods=["GET"])
def load_client(name):
    with get_db_connection() as conn:
        row = conn.execute(
            """
            SELECT
                name, age, height, weight, program, calories, target_weight,
                target_adherence, membership_status, membership_end
            FROM clients
            WHERE name=?
            """,
            (name,),
        ).fetchone()

    if not row:
        return jsonify({"status": "error", "message": "Client not found."}), 404

    return jsonify({"status": "ok", "client": dict(row)})


@app.route("/api/clients", methods=["GET"])
def list_clients():
    """
    List saved clients for populating a dropdown in the UI.
    """
    with get_db_connection() as conn:
        rows = conn.execute(
            """
            SELECT name, program, membership_status, membership_end
            FROM clients
            ORDER BY name COLLATE NOCASE ASC
            """
        ).fetchall()

    clients = [
        {
            "name": r["name"],
            "program": r["program"],
            "membership_status": r["membership_status"],
            "membership_end": r["membership_end"],
        }
        for r in rows
    ]
    return jsonify({"status": "ok", "clients": clients})


@app.route("/api/progress", methods=["POST"])
def save_progress():
    data = request.get_json(silent=True) or request.form
    client_name = (data.get("client_name") or "").strip()
    adherence = int(data.get("adherence", 0))

    if not client_name:
        return jsonify({"status": "error", "message": "client_name is required."}), 400

    week = datetime.now().strftime("Week %U - %Y")
    with get_db_connection() as conn:
        conn.execute(
            "INSERT INTO progress (client_name, week, adherence) VALUES (?, ?, ?)",
            (client_name, week, adherence),
        )
        conn.commit()

    return jsonify(
        {
            "status": "ok",
            "progress": {
                "client_name": client_name,
                "week": week,
                "adherence": adherence,
            },
        }
    )


@app.route("/api/client/<name>/progress", methods=["GET"])
def get_client_progress(name):
    """
    Weekly adherence series for charting (Aceestver-2.2.1 show_progress_chart parity).
    Rows ordered by id, matching Tkinter ORDER BY id.
    """
    with get_db_connection() as conn:
        rows = conn.execute(
            """
            SELECT week, adherence
            FROM progress
            WHERE client_name = ?
            ORDER BY id
            """,
            (name,),
        ).fetchall()

    series = [{"week": r["week"], "adherence": r["adherence"]} for r in rows]
    return jsonify(
        {
            "status": "ok",
            "client_name": name,
            "series": series,
        }
    )

@app.route("/api/client/<name>/bmi", methods=["GET"])
def get_client_bmi(name):
    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT height, weight FROM clients WHERE name=?",
            (name,),
        ).fetchone()

    if not row:
        return jsonify({"status": "error", "message": "Client not found."}), 404

    height = row["height"]
    weight = row["weight"]
    if height is None or weight is None or height <= 0 or weight <= 0:
        return (
            jsonify({"status": "error", "message": "Missing valid height and weight."}),
            400,
        )

    h_m = height / 100.0
    bmi = round(weight / (h_m * h_m), 1)

    if bmi < 18.5:
        category = "Underweight"
        risk = "Potential nutrient deficiency, low energy."
    elif bmi < 25:
        category = "Normal"
        risk = "Low risk if active and strong."
    elif bmi < 30:
        category = "Overweight"
        risk = "Moderate risk; focus on adherence and progressive activity."
    else:
        category = "Obese"
        risk = "Higher risk; prioritize fat loss, consistency, and supervision."

    return jsonify(
        {
            "status": "ok",
            "client_name": name,
            "bmi": bmi,
            "category": category,
            "risk": risk,
        }
    )


@app.route("/api/workout", methods=["POST"])
def log_workout():
    data = request.get_json(silent=True) or request.form

    client_name = (data.get("client_name") or "").strip()
    w_date = (data.get("date") or "").strip()
    workout_type = (data.get("workout_type") or "").strip()
    duration_min = data.get("duration_min", 0)
    notes = (data.get("notes") or "").strip()

    try:
        duration_min = int(duration_min)
    except (TypeError, ValueError):
        duration_min = 0

    if not client_name or not w_date or not workout_type or duration_min <= 0:
        return (
            jsonify(
                {
                    "status": "error",
                    "message": "client_name, date, workout_type, and duration_min are required.",
                }
            ),
            400,
        )

    ex = data.get("exercise") or {}
    ex_name = (ex.get("name") or "").strip() if isinstance(ex, dict) else ""

    def _pos_int(v):
        try:
            iv = int(v)
        except (TypeError, ValueError):
            return None
        return iv if iv > 0 else None

    def _pos_float(v):
        try:
            fv = float(v)
        except (TypeError, ValueError):
            return None
        return fv if fv > 0 else None

    ex_sets = _pos_int(ex.get("sets")) if isinstance(ex, dict) else None
    ex_reps = _pos_int(ex.get("reps")) if isinstance(ex, dict) else None
    ex_weight = _pos_float(ex.get("weight")) if isinstance(ex, dict) else None

    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO workouts (client_name, date, workout_type, duration_min, notes)
            VALUES (?, ?, ?, ?, ?)
            """,
            (client_name, w_date, workout_type, duration_min, notes),
        )
        workout_id = cur.lastrowid

        if ex_name:
            conn.execute(
                """
                INSERT INTO exercises (workout_id, name, sets, reps, weight)
                VALUES (?, ?, ?, ?, ?)
                """,
                (workout_id, ex_name, ex_sets, ex_reps, ex_weight),
            )
        conn.commit()

    return jsonify(
        {
            "status": "ok",
            "workout": {
                "workout_id": workout_id,
                "client_name": client_name,
                "date": w_date,
                "workout_type": workout_type,
                "duration_min": duration_min,
                "notes": notes,
            },
        }
    )


@app.route("/api/metrics", methods=["POST"])
def log_metrics():
    data = request.get_json(silent=True) or request.form

    client_name = (data.get("client_name") or "").strip()
    m_date = (data.get("date") or "").strip()
    notes = (data.get("notes") or "").strip()

    def _pos_float(v):
        try:
            fv = float(v)
        except (TypeError, ValueError):
            return None
        return fv if fv > 0 else None

    weight = _pos_float(data.get("weight", 0))
    waist = _pos_float(data.get("waist", 0))
    bodyfat = _pos_float(data.get("bodyfat", 0))

    if not client_name or not m_date:
        return (
            jsonify({"status": "error", "message": "client_name and date are required."}),
            400,
        )

    with get_db_connection() as conn:
        conn.execute(
            """
            INSERT INTO metrics (client_name, date, weight, waist, bodyfat)
            VALUES (?, ?, ?, ?, ?)
            """,
            (client_name, m_date, weight, waist, bodyfat),
        )
        conn.commit()

    return jsonify(
        {
            "status": "ok",
            "metrics": {
                "client_name": client_name,
                "date": m_date,
                "weight": weight,
                "waist": waist,
                "bodyfat": bodyfat,
                "notes": notes,
            },
        }
    )


@app.route("/api/client/<name>/workouts", methods=["GET"])
def get_workout_history(name):
    with get_db_connection() as conn:
        rows = conn.execute(
            """
            SELECT date, workout_type, duration_min, notes
            FROM workouts
            WHERE client_name=?
            ORDER BY date DESC, id DESC
            """,
            (name,),
        ).fetchall()

    workouts = [
        {
            "date": r["date"],
            "workout_type": r["workout_type"],
            "duration_min": r["duration_min"],
            "notes": r["notes"],
        }
        for r in rows
    ]

    return jsonify({"status": "ok", "client_name": name, "workouts": workouts})


@app.route("/api/client/<name>/weight-trend", methods=["GET"])
def get_weight_trend(name):
    with get_db_connection() as conn:
        rows = conn.execute(
            """
            SELECT date, weight
            FROM metrics
            WHERE client_name=? AND weight IS NOT NULL
            ORDER BY date
            """,
            (name,),
        ).fetchall()

    series = [{"date": r["date"], "weight": r["weight"]} for r in rows]
    return jsonify({"status": "ok", "client_name": name, "series": series})


@app.route("/api/auth/login", methods=["POST"])
def auth_login():
    data = request.get_json(silent=True) or request.form
    username = (data.get("username") or "").strip()
    password = (data.get("password") or "").strip()
    if not username or not password:
        return jsonify({"status": "error", "message": "username and password required."}), 400

    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT role FROM users WHERE username=? AND password=?",
            (username, password),
        ).fetchone()

    if not row:
        return jsonify({"status": "error", "message": "Invalid credentials."}), 401

    session["username"] = username
    session["role"] = row["role"]
    return jsonify(
        {
            "status": "ok",
            "user": {"username": username, "role": row["role"]},
        }
    )


@app.route("/api/auth/logout", methods=["POST"])
def auth_logout():
    session.clear()
    return jsonify({"status": "ok"})


@app.route("/api/auth/me", methods=["GET"])
def auth_me():
    if "username" not in session:
        return jsonify({"status": "error", "message": "Not logged in."}), 401
    return jsonify(
        {
            "status": "ok",
            "user": {"username": session["username"], "role": session.get("role")},
        }
    )


@app.route("/api/client/bootstrap", methods=["POST"])
def bootstrap_client():
    """Minimal client row (Aceestver-3.2.4 add/save client parity)."""
    data = request.get_json(silent=True) or request.form
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"status": "error", "message": "name is required."}), 400

    with get_db_connection() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO clients (name, membership_status) VALUES (?, ?)",
            (name, "Active"),
        )
        conn.commit()

    return jsonify({"status": "ok", "name": name})


@app.route("/api/client/<name>/generate-program", methods=["POST"])
def generate_client_program(name):
    prog_type = random.choice(list(PROGRAM_TEMPLATES.keys()))
    detail = random.choice(PROGRAM_TEMPLATES[prog_type])

    with get_db_connection() as conn:
        row = conn.execute("SELECT name FROM clients WHERE name=?", (name,)).fetchone()
        if not row:
            return jsonify({"status": "error", "message": "Client not found."}), 404
        conn.execute(
            "UPDATE clients SET program=? WHERE name=?",
            (detail, name),
        )
        conn.commit()

    return jsonify(
        {
            "status": "ok",
            "program_type": prog_type,
            "program": detail,
        }
    )


@app.route("/api/client/<name>/membership", methods=["GET"])
def get_client_membership(name):
    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT membership_status, membership_end FROM clients WHERE name=?",
            (name,),
        ).fetchone()

    if not row:
        return jsonify({"status": "error", "message": "Client not found."}), 404

    return jsonify(
        {
            "status": "ok",
            "client_name": name,
            "membership_status": row["membership_status"],
            "membership_end": row["membership_end"],
        }
    )


@app.route("/api/client/<name>/report.pdf", methods=["GET"])
def client_report_pdf(name):
    with get_db_connection() as conn:
        row = conn.execute("SELECT * FROM clients WHERE name=?", (name,)).fetchone()

    if not row:
        abort(404)

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", style="B", size=16)
    pdf.cell(
        0,
        10,
        text=f"ACEest Client Report - {row['name']}",
        new_x=XPos.LMARGIN,
        new_y=YPos.NEXT,
    )
    pdf.set_font("Helvetica", size=12)

    fields = [
        ("id", "ID"),
        ("name", "Name"),
        ("age", "Age"),
        ("height", "Height (cm)"),
        ("weight", "Weight (kg)"),
        ("program", "Program"),
        ("calories", "Calories"),
        ("target_weight", "Target Weight"),
        ("target_adherence", "Target Adherence"),
        ("membership_status", "Membership"),
        ("membership_end", "End"),
    ]
    for key, label in fields:
        if key not in row.keys():
            continue
        val = row[key]
        if val is None:
            val = ""
        pdf.cell(
            0,
            10,
            text=f"{label}: {val}",
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
        )

    out = pdf.output()
    if isinstance(out, str):
        out = out.encode("latin-1")
    elif isinstance(out, bytearray):
        out = bytes(out)

    filename = f"{name}_report.pdf".replace(" ", "_")
    return send_file(
        BytesIO(out),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=filename,
        max_age=0,
    )


init_db()


if __name__ == "__main__":
    # For local development / assignment demo purposes.
    app.run(host="0.0.0.0", port=5000, debug=True)

