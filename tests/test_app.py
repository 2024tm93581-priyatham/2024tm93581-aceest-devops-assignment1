import pytest

from app import PROGRAMS, SITE_METRICS, app, get_db_connection, init_db


@pytest.fixture()
def client(tmp_path):
    app.config["TESTING"] = True
    app.config["DATABASE"] = str(tmp_path / "test_aceest.db")
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
        "program": "Fat Loss (FL)",
    }
    response = client.post("/api/client", json=payload)
    assert response.status_code == 200

    data = response.get_json()
    assert data["status"] == "ok"
    assert data["client"]["calories"] == 1540


def test_load_client_api_returns_saved_client(client):
    client.post(
        "/api/client",
        json={"name": "Meena", "age": 30, "weight": 60, "program": "Muscle Gain (MG)"},
    )
    response = client.get("/api/client/Meena")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "ok"
    assert data["client"]["name"] == "Meena"
    assert data["client"]["calories"] == 2100


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

