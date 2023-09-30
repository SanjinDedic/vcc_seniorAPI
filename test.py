import pytest
from fastapi.testclient import TestClient
from main import app  # Make sure to import the FastAPI app from your main.py
from main import create_database
import random
import string
import json


client = TestClient(app)


# recreate the database before each test
@pytest.fixture(autouse=True)
def recreate_database():
    with open('initial.json', 'r') as f:
        initial_data = json.load(f)
    create_database(initial_data)



def random_string(length=10):
    """Generate a random string of letters and digits."""
    letters_and_digits = string.ascii_letters + string.digits
    return ''.join(random.choice(letters_and_digits) for i in range(length))


def test_quick_signup():
    # Test successful team signup
    response = client.post("/team_signup/", json={"name": "Test Team", "password": "testpassword"})
    assert response.status_code == 200
    assert response.json() == {"status": "success", "message": "Team has been added"}

    # Test team already exists
    response = client.post("/team_signup/", json={"name": "Test Team", "password": "testpassword"})
    assert response.status_code == 200
    assert response.json() == {"status": "failed", "message": "Team already exists"}

    # Test missing team name
    response = client.post("/team_signup/", json={"password": "testpassword"})
    assert response.status_code == 422

    # Test missing team password
    response = client.post("/team_signup/", json={"name": "Test Team"})
    assert response.status_code == 422


def test_submit_mcqs_answer_correct():
    # Submit a correct answer
    response = client.post("/submit_mcqs_answer", json={
        "id": "1",
        "team_name": "Test Team",
        "answer": "b"
    })
    assert response.status_code == 200
    assert response.json() == {"message": "Correct"}

def test_submit_mcqs_answer_incorrect():
    # Submit an incorrect answer
    response = client.post("/submit_mcqs_answer", json={
        "id": "1",
        "team_name": "Test Team",
        "answer": "c"
    })
    assert response.status_code == 200
    assert response.json() == {"message": "Incorrect"}

def test_submit_mcqs_answer_error():
    # Submit an answer with an invalid question ID
    response = client.post("/submit_mcqs_answer", json={
        "id": "999",
        "team_name": "Test Team",
        "answer": "a"
    })
    assert response.status_code == 500
    assert response.json() == {"detail": "An error occurred when submitting the answer."}


def test_submit_sa_answer_correct():
    # Submit a correct answer
    response = client.post("/submit_sa_answer", json={
        "id": 2,
        "team_name": "Test Team",
        "answer": "plus"
    })
    assert response.status_code == 200
    assert response.json() == {"message": "Correct"}

def test_submit_sa_answer_incorrect():
    # Submit an incorrect answer
    response = client.post("/submit_sa_answer", json={
        "id": 2,
        "team_name": "Test Team",
        "answer": "banana"
    })
    assert response.status_code == 200
    assert response.json() == {"message": "Try again"}

def test_submit_sa_answer_out_of_tries():
    # Submit an incorrect answer 3 times
    for i in range(2):
        response = client.post("/submit_sa_answer", json={
            "id": 6,
            "team_name": "Test Team",
            "answer": "b"
        })
        assert response.status_code == 200
        assert response.json() == {"message": "Try again"}
    response = client.post("/submit_sa_answer", json={
        "id": 6,
        "team_name": "Test Team",
        "answer": "b"
    })
    assert response.status_code == 200
    assert response.json() == {"message": "Incorrect"}

