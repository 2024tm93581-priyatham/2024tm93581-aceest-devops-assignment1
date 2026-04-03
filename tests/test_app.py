import pytest

from app import CALORIE_FACTORS, PROGRAMS, SITE_METRICS, app, get_db_connection, init_db


@pytest.fixture()
def client(tmp_path):
    app.config["TESTING"] = True
    app.config["DATABASE"] = str(tmp_path / "test_aceest.db")
    app.secret_key = "test-secret"
    init_db()
    with app.test_client() as client:
        yield client


def test_index_get_renders_ok(client):
    response = client.get("/")
    assert response.status_code == 200

    body = response.get_data(as_text=True)
    assert "ACEest FUNCTIONAL FITNESS" in body
    # Site metrics should always be rendered
    assert SITE_METRICS["capacity"] in body
    assert SITE_METRICS["area"] in body
    assert SITE_METRICS["break_even"] in body


@pytest.mark.parametrize("program_key", list(PROGRAMS.keys()))
def test_index_post_displays_selected_program_details(client, program_key):
    response = client.post("/", data={"program": program_key})
    assert response.status_code == 200

    body = response.get_data(as_text=True)
    program = PROGRAMS[program_key]
    # Workout and diet text should be present in the rendered HTML
    assert program["workout"].split("\n")[0] in body
    assert program["diet"].split("\n")[0] in body


def test_index_post_with_invalid_program_shows_placeholder(client):
    response = client.post("/", data={"program": "INVALID_PROGRAM"})
    assert response.status_code == 200

    body = response.get_data(as_text=True)
    # When no valid program is found, the placeholder text should appear
    assert (
        "Select a profile on the left to view the weekly workout schedule." in body
    )
    assert "Select a profile to view the recommended nutrition plan." in body


def test_save_client_api_calculates_and_stores_calories(client):
    payload = {
        "name": "Arun",
        "age": 28,
        "weight": 70,
        "program": "Fat Loss (FL) - 3 day",
    }
    response = client.post("/api/client", json=payload)
    assert response.status_code == 200

    data = response.get_json()
    assert data["status"] == "ok"
    assert data["client"]["calories"] == 1540
    assert data["client"]["membership_status"] == "Active"


def test_load_client_api_returns_saved_client(client):
    client.post(
        "/api/client",
        json={
            "name": "Meena",
            "age": 30,
            "weight": 60,
            "program": "Muscle Gain (MG) - PPL",
        },
    )
    response = client.get("/api/client/Meena")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "ok"
    assert data["client"]["name"] == "Meena"
    assert data["client"]["calories"] == 2100


def test_list_clients_api_returns_saved_clients(client):
    client.post(
        "/api/client",
        json={"name": "Zara", "age": 22, "weight": 55, "program": "Beginner (BG)"},
    )
    client.post(
        "/api/client",
        json={"name": "Arun", "age": 28, "weight": 70, "program": "Fat Loss (FL) - 3 day"},
    )

    r = client.get("/api/clients")
    assert r.status_code == 200
    payload = r.get_json()
    assert payload["status"] == "ok"
    names = [c["name"] for c in payload.get("clients", [])]
    assert "Arun" in names
    assert "Zara" in names


def test_save_progress_api_logs_weekly_adherence(client):
    client.post(
        "/api/client",
        json={"name": "Kavin", "age": 26, "weight": 65, "program": "Beginner (BG)"},
    )
    response = client.post("/api/progress", json={"client_name": "Kavin", "adherence": 87})
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "ok"
    assert payload["progress"]["adherence"] == 87
    assert payload["progress"]["week"].startswith("Week ")

    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT client_name, adherence FROM progress WHERE client_name=?",
            ("Kavin",),
        ).fetchone()
    assert row is not None
    assert row["adherence"] == 87


def test_calorie_factors_match_program_keys():
    assert set(CALORIE_FACTORS.keys()) == set(PROGRAMS.keys())


def test_get_progress_api_empty_series(client):
    response = client.get("/api/client/NonexistentClient/progress")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "ok"
    assert data["client_name"] == "NonexistentClient"
    assert data["series"] == []


def test_get_progress_api_returns_ordered_series(client):
    client.post(
        "/api/client",
        json={
            "name": "ChartUser",
            "age": 31,
            "weight": 72,
            "program": "Fat Loss (FL) - 3 day",
        },
    )
    client.post("/api/progress", json={"client_name": "ChartUser", "adherence": 40})
    client.post("/api/progress", json={"client_name": "ChartUser", "adherence": 88})

    response = client.get("/api/client/ChartUser/progress")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "ok"
    assert len(data["series"]) == 2
    assert data["series"][0]["adherence"] == 40
    assert data["series"][1]["adherence"] == 88
    assert all("week" in p for p in data["series"])


def test_bmi_api_returns_ok_for_valid_client(client):
    client.post(
        "/api/client",
        json={
            "name": "BMIUser",
            "age": 25,
            "height": 170,
            "weight": 70,
            "program": "Beginner (BG)",
        },
    )

    response = client.get("/api/client/BMIUser/bmi")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "ok"
    assert data["client_name"] == "BMIUser"
    assert data["bmi"] == 24.2
    assert data["category"] == "Normal"
    assert "Low risk" in data["risk"]


def test_bmi_api_errors_when_height_or_weight_missing(client):
    client.post(
        "/api/client",
        json={"name": "NoDataUser", "age": 25, "height": 0, "weight": 0, "program": "Beginner (BG)"},
    )

    response = client.get("/api/client/NoDataUser/bmi")
    assert response.status_code == 400
    data = response.get_json()
    assert data["status"] == "error"


def test_log_workout_and_get_workout_history(client):
    client.post(
        "/api/client",
        json={
            "name": "WorkoutUser",
            "age": 28,
            "height": 175,
            "weight": 80,
            "program": "Fat Loss (FL) - 5 day",
        },
    )

    client.post(
        "/api/workout",
        json={
            "client_name": "WorkoutUser",
            "date": "2026-04-01",
            "workout_type": "Strength",
            "duration_min": 60,
            "notes": "Leg day focused",
            "exercise": {"name": "Squat", "sets": 3, "reps": 5, "weight": 80},
        },
    )
    client.post(
        "/api/workout",
        json={
            "client_name": "WorkoutUser",
            "date": "2026-04-03",
            "workout_type": "Conditioning",
            "duration_min": 35,
            "notes": "Intervals",
        },
    )

    response = client.get("/api/client/WorkoutUser/workouts")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "ok"
    assert len(data["workouts"]) == 2
    # Ordered by date DESC, then id DESC
    assert data["workouts"][0]["date"] == "2026-04-03"
    assert data["workouts"][0]["workout_type"] == "Conditioning"


def test_log_metrics_and_get_weight_trend(client):
    client.post(
        "/api/client",
        json={"name": "MetricsUser", "age": 30, "height": 165, "weight": 68, "program": "Muscle Gain (MG) - PPL"},
    )

    client.post(
        "/api/metrics",
        json={
            "client_name": "MetricsUser",
            "date": "2026-04-01",
            "weight": 68,
            "waist": 80,
            "bodyfat": 18,
        },
    )
    client.post(
        "/api/metrics",
        json={
            "client_name": "MetricsUser",
            "date": "2026-04-05",
            "weight": 67,
            "waist": 79,
            "bodyfat": 17.5,
        },
    )

    response = client.get("/api/client/MetricsUser/weight-trend")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "ok"
    assert len(data["series"]) == 2
    # Ordered by date ASC
    assert data["series"][0]["date"] == "2026-04-01"
    assert data["series"][1]["date"] == "2026-04-05"


def test_auth_login_admin_and_me(client):
    r = client.post("/api/auth/login", json={"username": "admin", "password": "admin"})
    assert r.status_code == 200
    assert r.get_json()["status"] == "ok"
    assert r.get_json()["user"]["role"] == "Admin"

    me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.get_json()["user"]["username"] == "admin"

    client.post("/api/auth/logout")
    assert client.get("/api/auth/me").status_code == 401


def test_auth_login_invalid(client):
    r = client.post("/api/auth/login", json={"username": "admin", "password": "wrong"})
    assert r.status_code == 401


def test_bootstrap_client_minimal(client):
    r = client.post("/api/client/bootstrap", json={"name": "QuickClient"})
    assert r.status_code == 200
    assert r.get_json()["status"] == "ok"

    m = client.get("/api/client/QuickClient/membership")
    assert m.status_code == 200
    assert m.get_json()["membership_status"] == "Active"


def test_generate_program_updates_client(monkeypatch, client):
    client.post("/api/client/bootstrap", json={"name": "GenUser"})

    from app import PROGRAM_TEMPLATES as PT

    def fake_choice(seq):
        if seq == list(PT.keys()):
            return "Fat Loss"
        return "Full Body HIIT"

    monkeypatch.setattr("app.random.choice", fake_choice)

    r = client.post("/api/client/GenUser/generate-program")
    assert r.status_code == 200
    data = r.get_json()
    assert data["status"] == "ok"
    assert data["program"] == "Full Body HIIT"
    assert data["program_type"] == "Fat Loss"

    row = client.get("/api/client/GenUser").get_json()
    assert row["client"]["program"] == "Full Body HIIT"


def test_membership_get_for_saved_client(client):
    client.post(
        "/api/client",
        json={
            "name": "MemUser",
            "age": 40,
            "weight": 75,
            "program": "Beginner (BG)",
            "membership_status": "Active",
            "membership_end": "2027-12-31",
        },
    )
    r = client.get("/api/client/MemUser/membership")
    assert r.status_code == 200
    d = r.get_json()
    assert d["membership_status"] == "Active"
    assert d["membership_end"] == "2027-12-31"


def test_client_pdf_report_bytes(client):
    client.post(
        "/api/client",
        json={"name": "PdfUser", "age": 29, "weight": 72, "program": "Fat Loss (FL) - 3 day"},
    )
    r = client.get("/api/client/PdfUser/report.pdf")
    assert r.status_code == 200
    assert r.mimetype == "application/pdf"
    assert r.data[:4] == b"%PDF"

