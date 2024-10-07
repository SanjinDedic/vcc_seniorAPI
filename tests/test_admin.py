from fastapi.testclient import TestClient
from fastapi import HTTPException, UploadFile, File
import os,sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from main import app
from main import create_database
from unittest.mock import patch, mock_open
import json
from database import create_database
from config import CURRENT_DIR

client = TestClient(app)


def test_reset_database():
    try:
        with open(os.path.join(CURRENT_DIR, "initial.json"), 'r') as f:
            initial_data = json.load(f)
        teams_json_path = os.path.join(CURRENT_DIR, "teams.json")
        colors_json_path = os.path.join(CURRENT_DIR, "colors.json")
        create_database(initial_data, teams_json_path, colors_json_path)
        assert True
    except Exception as e:
        assert False

def test_get_token():
    global VALID_TOKEN
    login_response = client.post("/admin_login", json={"name": "Administrator", "password": "BOSSMAN"})
    assert login_response.status_code == 200
    token = login_response.json()["data"]
    VALID_TOKEN = token

def test_team_signup_success():
    response = client.post("/team_signup", json={"team_name": "NewTeam", "password": "newpass123"})
    assert response.status_code == 200
    assert response.json() == {"status": "success", "message": "Team has been added", "data": None}

def test_team_signup_failed_wrong_password():
    response = client.post("/team_signup", json={"team_name": "AnotherTeam", "password": ""})
    assert response.status_code == 200
    assert response.json() == {"status": "failed", "message": "Team credentials are empty", "data": None}

def test_team_signup_failed_existing_team():
    response = client.post("/team_signup", json={"team_name": "NewTeam", "password": "newpass123"})
    assert response.status_code == 200
    assert response.json() == {"status": "failed", "message": "Team already exists", "data": None}

def test_reset_rankings_specific_team_success():
    response = client.post("/reset_rankings/?team_name=SanjinX", headers={"Authorization": f"Bearer {VALID_TOKEN}"})
    assert response.status_code == 200
    assert response.json() == {"status": "success", "message": "Data for team 'SanjinX' has been reset.", "data": None}

def test_reset_rankings_all_teams_success():
    response = client.post("/reset_rankings/", headers={"Authorization": f"Bearer {VALID_TOKEN}"})
    assert response.status_code == 200
    assert response.json() == {"status": "success", "message": "Data for all teams has been reset.", "data": None}

def test_reset_rankings_failed_wrong_admin_password():
    response = client.post("/reset_rankings/", json={
        "team_name": "SanjinX"}, headers={"Authorization": "Bearer WRONG_TOKEN"})
    assert response.status_code == 401

def test_reset_rankings_failed_no_admin_password():
    response = client.post("/reset_rankings/", json={
        "team_name": "SanjinX"}, headers={"Authorization": "Bearer "})
    assert response.status_code == 401

def test_reset_questions_score_success():
    response = client.post("/reset_questions_score", headers={"Authorization": f"Bearer {VALID_TOKEN}"})
    assert response.status_code == 200
    assert response.json() == {"status": "success", "message": "Questions scores have been reset", "data": None}

def test_reset_questions_score_failed_wrong_admin_password():
    response = client.post("/reset_questions_score", headers={"Authorization": "Bearer WRONG_TOKEN"})
    assert response.status_code == 401

def test_reset_questions_score_failed_no_admin_password():
    response = client.post("/reset_questions_score", headers={"Authorization": "Bearer "})
    assert response.status_code == 401

def test_list_json_files_success():
    response = client.get("/json-files", headers={"Authorization": f"Bearer {VALID_TOKEN}"})
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    
def test_list_json_files_wrong_password():
    response = client.get("/json-files", headers={"Authorization": "Bearer WRONG_TOKEN"})
    assert response.status_code == 401

def test_set_json_success():
    response = client.post("/set_json/?filename=initial.json", headers={"Authorization": f"Bearer {VALID_TOKEN}"})
    assert response.status_code == 200
    assert response.json() == {"status": "success", "message": "File set successfully", "data": None}

def test_set_json_wrong_password():
    response = client.post("/set_json/?filename=initial.json", headers={"Authorization": "Bearer WRONG_TOKEN"})
    assert response.status_code == 401

def test_set_json_no_filename():
    response = client.post("/set_json/?filename=", headers={"Authorization": f"Bearer {VALID_TOKEN}"})
    assert response.status_code == 200
    assert response.json() == {"status": "failed", "message": "No filename provided", "data": None}

def test_manual_questions_success():
    
        response = client.get("/manual_questions", headers={"Authorization": f"Bearer {VALID_TOKEN}"})
        assert response.status_code == 200
        assert "team_name" in response.json()["data"][0]
    

def test_manual_questions_wrong_password():
    response = client.get("/manual_questions", headers={"Authorization": "Bearer WRONG_TOKEN"})
    assert response.status_code == 401

def test_manual_questions_no_password():
    response = client.get("/manual_questions")
    assert response.status_code == 401
    

def test_update_manual_score_success():
        response = client.post("/update_manual_score", json={"teams": [
            {"team_name": "SanjinX", "scores": {"q1_score": 100, "q2_score": 200, "q3_score": 300, "q4_score": 400}}
        ]}, headers={"Authorization": f"Bearer {VALID_TOKEN}"})
        assert response.status_code == 200
        assert response.json() == {"status": "success", "message":"Manual scores have been updated.", "data": None}

def test_update_manual_score_failed_wrong_admin_password():
    response = client.post("/update_manual_score", json={"teams": [
            {"team_name": "SanjinX", "scores": {"q1_score": 100, "q2_score": 200, "q3_score": 300, "q4_score": 400}}
        ]}, headers={"Authorization": "Bearer WRONG_TOKEN"})
    assert response.status_code == 401

def test_update_manual_score_score_out_of_range():
    response = client.post("/update_manual_score", json={"teams": [
            {"team_name": "SanjinX", "scores": {"q1_score": 700, "q2_score": 200, "q3_score": 300, "q4_score": 400}}
        ]}, headers={"Authorization": f"Bearer {VALID_TOKEN}"})
    assert response.status_code == 200
    assert "out of range" in response.json()["message"]

def test_upload_database_success():
    file_path = os.path.join(os.path.dirname(__file__), 'initial_test.json')
    with open(file_path, 'rb') as f:
        response = client.post(
            "/upload",
            files={"file": (os.path.basename(file_path), f, "application/json")},
            headers={"Authorization": f"Bearer {VALID_TOKEN}"})
    assert response.status_code == 200
    assert response.json() == {"status": "success"}

def test_upload_database_wrong_password():
    response = client.post("/upload", files={"file": ("dummy.json", "dummy content", "application/json")}, headers={"Authorization": "Bearer WRONG_TOKEN"})
    assert response.status_code == 401

def test_upload_database_wrong_file_format():
    response = client.post(
        "/upload",
        files={"file": ("dummy.txt", "dummy content", "text/plain")},
        headers={"Authorization": f"Bearer {VALID_TOKEN}"}
    )
    assert response.status_code == 200
    assert response.json() == {"status": "failed", "message": "Wrong file type", "data": None}

def test_upload_database_file_already_exists():
    file_path = 'initial.json'
    # Patch os.path.exists to always return True
    with patch('os.path.exists', return_value=True):
        with open(file_path, 'rb') as f:
            response = client.post(
                "/upload",
                files={"file": (file_path, f, "application/json")},
                headers={"Authorization": f"Bearer {VALID_TOKEN}"}
            )
    assert response.status_code == 200
    assert "already uploaded" in response.json()["message"]

def test_upload_database_no_file():
    response = client.post("/upload",headers={"Authorization": f"Bearer {VALID_TOKEN}"})
    assert response.status_code == 200
    assert response.json() == {"status": "failed", "message": "No file provided", "data": None}