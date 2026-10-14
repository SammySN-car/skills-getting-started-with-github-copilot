from copy import deepcopy

import pytest
from fastapi.testclient import TestClient

from src.app import activities, app


client = TestClient(app)


@pytest.fixture(autouse=True)
def restore_activities():
    original_activities = deepcopy(activities)
    yield
    activities.clear()
    activities.update(original_activities)


def test_root_redirects_to_static_index():
    response = client.get("/", follow_redirects=False)

    assert response.status_code == 307
    assert response.headers["location"] == "/static/index.html"


def test_get_activities_returns_activity_data():
    response = client.get("/activities")

    assert response.status_code == 200
    body = response.json()
    assert "Chess Club" in body
    assert body["Chess Club"]["participants"] == [
        "michael@mergington.edu",
        "daniel@mergington.edu",
    ]


def test_signup_adds_participant():
    email = "new.student@mergington.edu"

    response = client.post("/activities/Basketball Team/signup", params={"email": email})

    assert response.status_code == 200
    assert email in activities["Basketball Team"]["participants"]
    assert response.json() == {
        "message": f"Signed up {email} for Basketball Team"
    }


def test_signup_rejects_unknown_activity():
    response = client.post(
        "/activities/Unknown Club/signup",
        params={"email": "student@mergington.edu"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Activity not found"}


def test_signup_rejects_duplicate_participant():
    email = "new.student@mergington.edu"
    activity = "Basketball Team"
    client.post(f"/activities/{activity}/signup", params={"email": email})

    response = client.post(f"/activities/{activity}/signup", params={"email": email})

    assert response.status_code == 400
    assert response.json() == {
        "detail": "Student is already signed up for this activity"
    }
    assert activities[activity]["participants"].count(email) == 1


def test_unregister_removes_participant():
    email = "new.student@mergington.edu"
    activity = "Basketball Team"
    client.post(f"/activities/{activity}/signup", params={"email": email})

    response = client.delete(f"/activities/{activity}/participants/{email}")

    assert response.status_code == 200
    assert email not in activities[activity]["participants"]
    assert response.json() == {
        "message": f"Unregistered {email} from {activity}"
    }


@pytest.mark.parametrize(
    ("activity", "email", "expected_detail"),
    [
        ("Unknown Club", "student@mergington.edu", "Activity not found"),
        ("Basketball Team", "missing@mergington.edu", "Participant not found"),
    ],
)
def test_unregister_rejects_missing_activity_or_participant(
    activity, email, expected_detail
):
    response = client.delete(f"/activities/{activity}/participants/{email}")

    assert response.status_code == 404
    assert response.json() == {"detail": expected_detail}
