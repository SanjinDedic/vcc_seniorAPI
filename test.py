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
    response = client.post("/team_signup/",headers={"Password":"BOSSMAN"}, json={"name": "Test Team", "password": "testpassword"})
    assert response.status_code == 200
    assert response.json() == {"status": "success", "message": "Team has been added"}

    # Test team already exists
    response = client.post("/team_signup/",headers={"Password":"BOSSMAN"}, json={"name": "Test Team", "password": "testpassword"})
    assert response.status_code == 200
    assert response.json() == {"status": "failed", "message": "Team already exists"}

    # Test missing team name
    response = client.post("/team_signup/",headers={"Password":"BOSSMAN"}, json={"password": "testpassword"})
    assert response.status_code == 422

    # Test missing team password
    response = client.post("/team_signup/",headers={"Password":"BOSSMAN"}, json={"name": "Test Team"})
    assert response.status_code == 422

    # Test missing headers
    response = client.post("/team_signup/", json={"name": "Test Team", "password": "testpassword"})
    assert response.status_code == 200
    assert response.json() == {"status": "failed", "message": "Admin credentials are wrong"}

    # Test wrong headers
    response = client.post("/team_signup/",headers={"Password":"ABC"}, json={"name": "Test Team", "password": "testpassword"})
    assert response.status_code == 200
    assert response.json() == {"status": "failed", "message": "Admin credentials are wrong"}

def test_team_login_correct():
    # Test missing team name
    response = client.post("/team_login", json={"team_name":"RedWolves","password": "123"})
    assert response.status_code == 200
    assert response.json() == {"status": "success", "message": "Logged in successfully"}

    
def test_team_login_incorrect():
    # Test missing team name
    response = client.post("/team_login", json={"team_name":"RedWolves","password": "testpassword"})
    assert response.status_code == 200
    assert response.json() == {"status": "failed", "message": "No team found with these credentials"}

def test_team_login_error():
   # Test missing team password
    response = client.post("/team_login", json={"team_name": "Test Team"})
    print(response.json())
    assert response.status_code == 422

def test_submit_mcqs_answer_correct():
    # Submit a correct answer with headers
    response = client.post("/submit_mcqs_answer",headers={"Team-Name":"RedWolves","Team-Password":"123"}, json={
        "id": "1",
        "team_name": "Test Team",
        "answer": "b"
    })
    assert response.status_code == 200
    assert response.json() == {"message": "Correct"}

    # Submit a correct answer without headers
    response = client.post("/submit_mcqs_answer", json={
        "id": "1",
        "team_name": "Test Team",
        "answer": "b"
    })
    assert response.status_code == 200
    assert response.json() == {"status": "failed", "message": "Team credentials are wrong"}

    # Submit a correct answer with wrong headers
    response = client.post("/submit_mcqs_answer",headers={"Team-Name":"abc","Team-Password":"testabc"}, json={
        "id": "1",
        "team_name": "Test Team",
        "answer": "b"
    })
    assert response.status_code == 200
    assert response.json() == {"status": "failed", "message": "Team credentials are wrong"}


def test_submit_mcqs_answer_correct_cheat():
    # Submit a correct answer
    response = client.post("/submit_mcqs_answer",headers={"Team-Name":"RedWolves","Team-Password":"123"}, json={
        "id": "1",
        "team_name": "Test Team",
        "answer": "b"
    })
    assert response.status_code == 200
    assert response.json() == {"message": "Correct"}

    #Submit same answer again
    response = client.post("/submit_mcqs_answer",headers={"Team-Name":"RedWolves","Team-Password":"123"}, json={
        "id": "1",
        "team_name": "Test Team",
        "answer": "b"
    })
    assert response.status_code == 200
    assert response.json() == {"message": "Question already attempted"}

    # Submit a correct answer with no headers
    response = client.post("/submit_mcqs_answer", json={
        "id": "1",
        "team_name": "Test Team",
        "answer": "b"
    })
    assert response.status_code == 200
    assert response.json() == {"status": "failed", "message": "Team credentials are wrong"}

    # Submit a correct answer with wrong headers
    response = client.post("/submit_mcqs_answer",headers={"Team-Name":"ABC","Team-Password":"123"}, json={
        "id": "1",
        "team_name": "Test Team",
        "answer": "b"
    })
    assert response.status_code == 200
    assert response.json() == {"status": "failed", "message": "Team credentials are wrong"}


def test_submit_mcqs_answer_incorrect():
    # Submit an incorrect answer
    response = client.post("/submit_mcqs_answer",headers={"Team-Name":"RedWolves","Team-Password":"123"}, json={
        "id": "1",
        "team_name": "Test Team",
        "answer": "c"
    })
    assert response.status_code == 200
    assert response.json() == {"message": "Incorrect"}

    # Submit an incorrect answer with no headers
    response = client.post("/submit_mcqs_answer", json={
        "id": "1",
        "team_name": "Test Team",
        "answer": "c"
    })
    assert response.status_code == 200
    assert response.json() == {"status": "failed", "message": "Team credentials are wrong"}

    # Submit an incorrect answer with wrong headers
    response = client.post("/submit_mcqs_answer",headers={"Team-Name":"RedWolvesdas","Team-Password":"123"}, json={
        "id": "1",
        "team_name": "Test Team",
        "answer": "c"
    })
    assert response.status_code == 200
    assert response.json() == {"status": "failed", "message": "Team credentials are wrong"}

def test_submit_mcqs_answer_error():
    # Submit an answer with an invalid question ID
    response = client.post("/submit_mcqs_answer",headers={"Team-Name":"RedWolves","Team-Password":"123"}, json={
        "id": "999",
        "team_name": "Test Team",
        "answer": "a"
    })
    assert response.status_code == 200
    assert response.json() == {"message":"An error occurred when submitting the answer."}

    # Submit an answer with an invalid question ID with no headers
    response = client.post("/submit_mcqs_answer", json={
        "id": "999",
        "team_name": "Test Team",
        "answer": "a"
    })
    assert response.status_code == 200
    assert response.json() == {"status": "failed", "message": "Team credentials are wrong"}

    # Submit an answer with an invalid question ID with wrong headers
    response = client.post("/submit_mcqs_answer",headers={"Team-Name":"RedWolves","Team-Password":"12345"}, json={
        "id": "999",
        "team_name": "Test Team",
        "answer": "a"
    })
    assert response.status_code == 200
    assert response.json() == {"status": "failed", "message": "Team credentials are wrong"}


def test_submit_sa_answer_correct():
    # Submit a correct answer
    response = client.post("/submit_sa_answer",headers={"Team-Name":"RedWolves","Team-Password":"123"}, json={
        "id": 2,
        "team_name": "Test Team",
        "answer": "plus"
    })
    assert response.status_code == 200
    assert response.json() == {"message": "Correct"}

    # Submit a correct answer with no headers
    response = client.post("/submit_sa_answer", json={
        "id": 2,
        "team_name": "Test Team",
        "answer": "plus"
    })
    assert response.status_code == 200
    assert response.json() == {"status": "failed", "message": "Team credentials are wrong"}

    # Submit a correct answer with wrong headers
    response = client.post("/submit_sa_answer",headers={"Team-Name":"Red","Team-Password":"123"}, json={
        "id": 2,
        "team_name": "Test Team",
        "answer": "plus"
    })
    assert response.status_code == 200
    assert response.json() == {"status": "failed", "message": "Team credentials are wrong"}

def test_submit_sa_answer_incorrect():
    # Submit an incorrect answer
    response = client.post("/submit_sa_answer",headers={"Team-Name":"RedWolves","Team-Password":"123"}, json={
        "id": 2,
        "team_name": "Test Team",
        "answer": "banana"
    })
    assert response.status_code == 200
    assert response.json() == {"message": "Try again"}

    # Submit an incorrect answer with no headers
    response = client.post("/submit_sa_answer", json={
        "id": 2,
        "team_name": "Test Team",
        "answer": "banana"
    })
    assert response.status_code == 200
    assert response.json() == {"status": "failed", "message": "Team credentials are wrong"}

    # Submit an incorrect answer with wrong headers
    response = client.post("/submit_sa_answer",headers={"Team-Name":"Team","Team-Password":"123"}, json={
        "id": 2,
        "team_name": "Test Team",
        "answer": "banana"
    })
    assert response.status_code == 200
    assert response.json() == {"status": "failed", "message": "Team credentials are wrong"}

def test_submit_sa_answer_out_of_tries():
    for i in range(2):
        response = client.post("/submit_sa_answer",headers={"Team-Name":"RedWolves","Team-Password":"123"}, json={
            "id": 7,
            "team_name": "RedWolves",
            "answer": "b"
        })
        assert response.status_code == 200
        assert response.json() == {"message": "Try again"}

    response = client.post("/submit_sa_answer",headers={"Team-Name":"RedWolves","Team-Password":"123"}, json={
        "id": 7,
        "team_name": "RedWolves",
        "answer": "b"
    })
    assert response.status_code == 200
    assert response.json() == {"message": "Incorrect"}

    response = client.post("/submit_sa_answer",headers={"Team-Name":"RedWolves","Team-Password":"123"}, json={
        "id": 7,
        "team_name": "RedWolves",
        "answer": "b"
    })
    assert response.status_code == 200
    assert response.json() == {"message": "No attempts left"}

    #sumbit answer with no headers
    response = client.post("/submit_sa_answer", json={
        "id": 7,
        "team_name": "Test Team",
        "answer": "b"
    })
    assert response.status_code == 200
    assert response.json() == {"status": "failed", "message": "Team credentials are wrong"}

    #sumbit answer with wrong headers
    response = client.post("/submit_sa_answer",headers={"Team-Name":"123","Team-Password":"RedWolves"}, json={
        "id": 7,
        "team_name": "Test Team",
        "answer": "b"
    })
    assert response.status_code == 200
    assert response.json() == {"status": "failed", "message": "Team credentials are wrong"}

def test_submit_sa_answer_error():
    # Submit an answer with an invalid question ID
    response = client.post("/submit_sa_answer",headers={"Team-Name":"RedWolves","Team-Password":"123"}, json={
        "id": "999",
        "team_name": "Test Team",
        "answer": "a"
    })
    print(response)
    assert response.status_code == 200
    assert response.json() == {"message":"An error occurred when submitting the answer."}

    # Submit an answer with an invalid question ID with no headers
    response = client.post("/submit_sa_answer", json={
        "id": "999",
        "team_name": "Test Team",
        "answer": "a"
    })
    assert response.status_code == 200
    assert response.json() == {"status": "failed", "message": "Team credentials are wrong"}

    # Submit an answer with an invalid question ID with wrong headers
    response = client.post("/submit_sa_answer",headers={"Team-Name":"RedWolves","Team-Password":"12345"}, json={
        "id": "999",
        "team_name": "Test Team",
        "answer": "a"
    })
    assert response.status_code == 200
    assert response.json() == {"status": "failed", "message": "Team credentials are wrong"}