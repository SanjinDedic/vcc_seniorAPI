from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_get_token():
    login_response = client.post("/team_login", json={"team_name": "BrunswickSC1", "password": "ighEMkOP"})
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    return token

VALID_TOKEN = test_get_token()

def test_get_questions():
    
    response = client.get("/questions", headers={"Authorization": f"Bearer {VALID_TOKEN}"})
    assert response.status_code == 200

def test_submit_answer_mcqs_correct():
    
    response = client.post("/submit_mcqs_answer", json={"id": "1", "answer": "a"}, headers={"Authorization": f"Bearer {VALID_TOKEN}"})
    assert response.status_code == 200
    assert response.json() == {"message": "Correct"}

def test_submit_answer_mcqs_incorrect():
    response = client.post("/submit_mcqs_answer", json={"id": "2", "answer": "b"}, headers={"Authorization": f"Bearer {VALID_TOKEN}"})
    assert response.status_code == 200
    assert response.json() == {"message": "Incorrect"}

def test_submit_sa_answer_correct():
    
    response = client.post("/submit_sa_answer", json={"id": "22", "answer": "Bicyle"}, headers={"Authorization": f"Bearer {VALID_TOKEN}"})
    assert response.status_code == 200
    assert response.json() == {"message": "Correct"}

def test_submit_sa_answer_mcqs_incorrect():

    response = client.post("/submit_sa_answer", json={"id": "23", "answer": "b"}, headers={"Authorization": f"Bearer {VALID_TOKEN}"})
    assert response.status_code == 200
    assert response.json() == {"message": "Incorrect"}