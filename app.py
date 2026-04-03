import sqlite3
from datetime import datetime

from flask import Flask, jsonify, render_template, request

app = Flask(__name__)
app.config["DATABASE"] = "aceest_fitness.db"


# Core program specification reused from the Tkinter version
PROGRAMS = {
    "Fat Loss (FL)": {
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
        "color": "#e74c3c",
    },
    "Muscle Gain (MG)": {
        "workout": (
            "Mon: Squat 5x5\n"
            "Tue: Bench 5x5\n"
            "Wed: Deadlift 4x6\n"
            "Thu: Front Squat 4x8\n"
            "Fri: Incline Press 4x10\n"
            "Sat: Barbell Rows 4x10"
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


def get_db_connection():
    conn = sqlite3.connect(app.config["DATABASE"])
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS clients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                age INTEGER,
                weight REAL,
                program TEXT,
                calories INTEGER
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
    age = int(data.get("age", 0))
    weight = float(data.get("weight", 0))
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

    factors = {"Fat Loss (FL)": 22, "Muscle Gain (MG)": 35, "Beginner (BG)": 26}
    calories = int(weight * factors[program])

    with get_db_connection() as conn:
        conn.execute(
            """
            INSERT INTO clients (name, age, weight, program, calories)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET
                age=excluded.age,
                weight=excluded.weight,
                program=excluded.program,
                calories=excluded.calories
            """,
            (name, age, weight, program, calories),
        )
        conn.commit()

    return jsonify(
        {
            "status": "ok",
            "client": {
                "name": name,
                "age": age,
                "weight": weight,
                "program": program,
                "calories": calories,
            },
        }
    )


@app.route("/api/client/<name>", methods=["GET"])
def load_client(name):
    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT name, age, weight, program, calories FROM clients WHERE name=?",
            (name,),
        ).fetchone()

    if not row:
        return jsonify({"status": "error", "message": "Client not found."}), 404

    return jsonify({"status": "ok", "client": dict(row)})


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


init_db()


if __name__ == "__main__":
    # For local development / assignment demo purposes.
    app.run(host="0.0.0.0", port=5000, debug=True)

