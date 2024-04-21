import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient
from main import app
import requests
import json
base_url="https://vccfinal.net"

with open('teams.json', 'r') as file:
    data = json.load(file)
    teams_list = data['teams']


def test_get_comp_table():
    response = requests.get(f"{base_url}/get_comp_table")
    assert response.status_code == 200


def test_get_manual_questions():
    response = requests.get(f"{base_url}/manual_questions/BOSSMAN")
    assert response.status_code == 200


def test_get_team_questions():
    response = requests.get(f"{base_url}/questions/{teams_list[0]['name']}/{teams_list[0]['password']}")
    assert response.status_code == 200


def test_get_any_team_questions():
    response = requests.get(f"{base_url}/questions/anything/123")
    assert response.status_code == 200
    assert response.json() == {"status": "failed", "message": "Team credentials are wrong"}

def test_submit_mcqs_answer_correct():
    payload = {
    "id": "2",
    "answer": "b",
    "team_name": teams_list[0]['name'],
    "team_password": teams_list[0]['password']
    }
    response = requests.post(f"{base_url}/submit_mcqs_answer",json=payload)
    assert response.status_code == 200
    assert response.json() == {"message":"Correct"}

def test_submit_mcqs_answer_incorrect():
    payload = {
    "id": "4",
    "answer": "a",
    "team_name": teams_list[0]['name'],
    "team_password": teams_list[0]['password']
    }
    response = requests.post(f"{base_url}/submit_mcqs_answer",json=payload)
    assert response.status_code == 200
    assert response.json() == {"message":"Incorrect"}

def test_submit_mcqs_answer_already_attempted():

    payload = {
    "id": "2",
    "answer": "b",
    "team_name": teams_list[0]['name'],
    "team_password": teams_list[0]['password']
    }
    response = requests.post(f"{base_url}/submit_mcqs_answer",json=payload)
    assert response.status_code == 200
    assert response.json() == {"message":"Question already attempted"}

def test_submit_mcqs_answer_error():
    payload = {
    "id": "999",
    "answer": "66",
    "team_name": teams_list[0]['name'],
    "team_password": teams_list[0]['password']
    }
    response = requests.post(f"{base_url}/submit_mcqs_answer",json=payload)
    assert response.status_code == 200
    assert response.json() == {"message":"An error occurred when submitting the answer."}

def test_submit_sa_answer_correct():
    payload = {
    "id": "1",
    "answer": "mississippi",
    "team_name": teams_list[0]['name'],
    "team_password": teams_list[0]['password']
    }
    response = requests.post(f"{base_url}/submit_sa_answer",json=payload)
    assert response.status_code == 200
    assert response.json() == {"message":"Correct"}

def test_submit_sa_answer_incorrect():
    payload = {
    "id": "11",
    "answer": "dsa",
    "team_name": teams_list[0]['name'],
    "team_password": teams_list[0]['password']
    }
    for i in range(2):
        response = requests.post(f"{base_url}/submit_sa_answer",json=payload)
    assert response.status_code == 200
    assert response.json() == {"message":"Incorrect"}

def test_submit_sa_answer_try_again():

    payload = {
    "id": "4",
    "answer": "banana",
    "team_name": teams_list[0]['name'],
    "team_password": teams_list[0]['password']
    }
    response = requests.post(f"{base_url}/submit_sa_answer",json=payload)
    assert response.status_code == 200
    assert response.json() == {"message":"Try again"}

def test_submit_sa_answer_full_attempts():

    payload = {
    "id": "1",
    "answer": "pl",
    "team_name": teams_list[0]['name'],
    "team_password": teams_list[0]['password']
    }
    response = requests.post(f"{base_url}/submit_sa_answer",json=payload)
    assert response.status_code == 200
    assert response.json() == {"message":"No attempts left"}


def test_submit_sa_answer_error():
    payload = {
    "id": "96",
    "answer": "6gf",
    "team_name": teams_list[0]['name'],
    "team_password": teams_list[0]['password']
    }
    response = requests.post(f"{base_url}/submit_sa_answer",json=payload)
    assert response.status_code == 200
    assert response.json() == {"message":"An error occurred when submitting the answer."}

def test_team_signup():
    payload = {"team":{
    "name": "NewTeam",
    "password": "123"
    },"a":{
        "admin_password":"BOSSMAN"
    }
    }
    response = requests.post(f"{base_url}/team_signup/",json=payload)
    assert response.status_code == 200
    assert response.json() == {"status": "success", "message": "Team has been added"}

def test_team_signup_exists():
    payload = {"team":{
    "name": "NewTeam",
    "password": "123"
    },"a":{
        "admin_password":"BOSSMAN"
    }
    }
    response = requests.post(f"{base_url}/team_signup/",json=payload)
    assert response.status_code == 200
    assert response.json() == {"status":"failed", "message": "Team already exists"}

def json_files():
   
    response = requests.post(f"{base_url}/json-files/BOSSMAN")
    assert response.status_code == 200
    
def set_json():
    payload = {
    "filename": "initial.json","a":{"admin_password": "BOSSMAN"}
    }
    response = requests.post(f"{base_url}/set_json/",json=payload)
    assert response.status_code == 200
    assert response.json() == {"status": "failed", "message": "Wrong file selected!"}

def reset_rankings_all():
    response = requests.post(f"{base_url}/reset_rankings/",json={"a":{"admin_password":"BOSSMAN"}})
    assert response.status_code == 200
    assert response.json() == {"status": "success", "message": "Data for all teams has been reset."}

def reset_rankings_one():
    response = requests.post(f"{base_url}/reset_rankings/?team_name={teams_list[0]['name']}",json={"a":{"admin_password":"BOSSMAN"}})
    assert response.status_code == 200
    assert response.json() == {"status": "success", "message": f"Data for team '{teams_list[0]['name']}' has been reset."}


def reset_question_score():
    
    response = requests.post(f"{base_url}/reset_questions_score/",json={"admin_password": "BOSSMAN"})
    assert response.status_code == 200
    assert response.json() == {"status": "success", "message": "Questions scores have been reset. "}

def team_login_correct():
    payload = {
    "team_name": teams_list[0]['name'],
    "team_password": teams_list[0]['password']
    }
    response = requests.post(f"{base_url}/team_login",json=payload)
    assert response.status_code == 200
    assert response.json() == {"status": "success", "message": "Logged in successfully"}

def team_login_incorrect():
    payload = {
    "team_name": "fRedWdolves",
    "password": "123"
    }
    response = requests.post(f"{base_url}/team_login",json=payload)
    assert response.status_code == 200
    assert response.json() == {"status": "failed", "message": "No team found with these credentials"}

def admin_login_correct():
    payload = {
    "team_name": "fRedWdolves",
    "password": "123"
    }
    response = requests.post(f"{base_url}/admin_login",json=payload)
    assert response.status_code == 200
    assert response.json() == {"status": "success"}

def admin_login_incorrect():
    payload = {
    "admin_password": "fRedWdolves"
    }
    response = requests.post(f"{base_url}/admin_login",json=payload)
    assert response.status_code == 200
    assert response.json() == {"status": "failed", "message": "Admin credentials are wrong"}
    
"""
def update_manual_score():
    payload = {
    "id": "9",
    "answer": "6",
    "team_name": "RedWdolves"
    }
    response = requests.post(f"{base_url}/submit_sa_answer",json=payload)
    assert response.status_code == 200
    assert response.json() == {"message":"An error occurred when submitting the answer."}

def file_upload():
    payload = {
    "id": "9",
    "answer": "6",
    "team_name": "RedWdolves"
    }
    response = requests.post(f"{base_url}/submit_sa_answer",json=payload)
    assert response.status_code == 200
    assert response.json() == {"message":"An error occurred when submitting the answer."}
"""




