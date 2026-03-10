from flask import Flask, render_template, request

app = Flask(__name__)


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


if __name__ == "__main__":
    # For local development / assignment demo purposes.
    app.run(host="0.0.0.0", port=5000, debug=True)

