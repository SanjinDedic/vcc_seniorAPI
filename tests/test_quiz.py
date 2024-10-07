from fastapi.testclient import TestClient
import os,sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from main import app

client = TestClient(app)



def test_get_token():
    global VALID_TOKEN
    login_response = client.post("/team_login", json={"team_name": "SanjinX", "password": "652093"})
    assert login_response.status_code == 200
    token = login_response.json()["data"]
    VALID_TOKEN = token



def test_get_comp_table():
    
    response = client.get("/get_comp_table")
    assert response.status_code == 200


def test_get_questions():
    
    response = client.get("/questions", headers={"Authorization": f"Bearer {VALID_TOKEN}"})
    assert response.status_code == 200

def test_get_questions_wrong_token():
    
    response = client.get("/questions", headers={"Authorization": "Bearer VALID_TOKEN"})
    assert response.status_code == 401

def test_submit_answer_mcqs_correct():
    
    response = client.post("/submit_mcqs_answer", json={"id": "1", "answer": "b"}, headers={"Authorization": f"Bearer {VALID_TOKEN}"})
    assert response.status_code == 200
    assert response.json() == {"status":"success", "message":"Submission was successful", "data":"Correct"}

def test_submit_answer_mcqs_incorrect():
    response = client.post("/submit_mcqs_answer", json={"id": "2", "answer": "c"}, headers={"Authorization": f"Bearer {VALID_TOKEN}"})
    assert response.status_code == 200
    assert response.json() == {"status":"success", "message":"Submission was successful", "data":"Incorrect"}

def test_submit_answer_mcqs_already_attempted():
    
    response = client.post("/submit_mcqs_answer", json={"id": "1", "answer": "b"}, headers={"Authorization": f"Bearer {VALID_TOKEN}"})
    assert response.status_code == 200
    assert response.json() == {"status":"failed", "message":"Question already attempted","data": None}

def test_submit_sa_answer_correct():
    
    response = client.post("/submit_sa_answer", json={"id": "13", "answer": "157"}, headers={"Authorization": f"Bearer {VALID_TOKEN}"})
    assert response.status_code == 200
    assert response.json() == {"status":"success", "message":"Submission was successful", "data":"Correct"}

def test_submit_sa_answer_mcqs_tryagain():

    response = client.post("/submit_sa_answer", json={"id": "22", "answer": "b"}, headers={"Authorization": f"Bearer {VALID_TOKEN}"})
    assert response.status_code == 200
    assert response.json() == {"status":"success", "message":"Submission was successful", "data":"Try again"}

def test_submit_sa_answer_mcqs_incorrect():

    response_again = client.post("/submit_sa_answer", json={"id": "22", "answer": "b"}, headers={"Authorization": f"Bearer {VALID_TOKEN}"})
    response_inc = client.post("/submit_sa_answer", json={"id": "22", "answer": "b"}, headers={"Authorization": f"Bearer {VALID_TOKEN}"})
    
    assert response_again.status_code == 200
    assert response_again.json() == {"status":"success", "message":"Submission was successful", "data":"Try again"}

    assert response_inc.status_code == 200
    assert response_inc.json() == {"status":"success", "message":"Submission was successful", "data":"Incorrect"}