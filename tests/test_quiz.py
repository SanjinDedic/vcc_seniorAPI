from fastapi.testclient import TestClient
from main import app
from auth import verify_password

client = TestClient(app)

def get_token():
    login_response = client.post("/team_login", json={"team_name": "BrunswickSC1", "password": "ighEMkOP"})
    print("Login response status code:", login_response.status_code)
    print("Login response content:", login_response.content)
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    return token

VALID_TOKEN = get_token()

def test_get_comp_table():
    response = client.get("/get_comp_table")
    assert response.status_code == 200

def test_get_questions():
    response = client.get("/questions", headers={"Authorization": f"Bearer {VALID_TOKEN}"})
    assert response.status_code == 200

def test_get_questions_wrong_token():
    response = client.get("/questions", headers={"Authorization": "Bearer invalid_token"})
    assert response.status_code == 401

def test_submit_answer_mcqs_correct():
    response = client.post("/submit_mcqs_answer", json={"id": "1", "answer": "a"}, headers={"Authorization": f"Bearer {VALID_TOKEN}"})
    assert response.status_code == 200
    assert response.json() == {"message": "Correct"}

def test_submit_answer_mcqs_incorrect():
    response = client.post("/submit_mcqs_answer", json={"id": "2", "answer": "b"}, headers={"Authorization": f"Bearer {VALID_TOKEN}"})
    assert response.status_code == 200
    assert response.json() == {"message": "Incorrect"}

def test_submit_answer_mcqs_already_attempted():
    client.post("/submit_mcqs_answer", json={"id": "1", "answer": "a"}, headers={"Authorization": f"Bearer {VALID_TOKEN}"})
    response = client.post("/submit_mcqs_answer", json={"id": "1", "answer": "a"}, headers={"Authorization": f"Bearer {VALID_TOKEN}"})
    assert response.status_code == 200
    assert response.json() == {"message": "Question already attempted"}

def test_submit_sa_answer_correct():
    response = client.post("/submit_sa_answer", json={"id": "18", "answer": "yesvcc"}, headers={"Authorization": f"Bearer {VALID_TOKEN}"})
    assert response.status_code == 200
    assert response.json() == {"message": "Correct"}

def test_submit_sa_answer_mcqs_tryagain():
    response = client.post("/submit_sa_answer", json={"id": "22", "answer": "b"}, headers={"Authorization": f"Bearer {VALID_TOKEN}"})
    assert response.status_code == 200
    assert response.json() == {"message": "Try again"}

def test_submit_sa_answer_no_more_attempts():
    client.post("/submit_sa_answer", json={"id": "22", "answer": "b"}, headers={"Authorization": f"Bearer {VALID_TOKEN}"})
    client.post("/submit_sa_answer", json={"id": "22", "answer": "b"}, headers={"Authorization": f"Bearer {VALID_TOKEN}"})
    response_inc = client.post("/submit_sa_answer", json={"id": "22", "answer": "b"}, headers={"Authorization": f"Bearer {VALID_TOKEN}"})
    assert response_inc.status_code == 200
    assert response_inc.json() == {"message": "No attempts left"}