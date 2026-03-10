import pytest

from app import app, PROGRAMS, SITE_METRICS


@pytest.fixture()
def client():
    app.config["TESTING"] = True
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

