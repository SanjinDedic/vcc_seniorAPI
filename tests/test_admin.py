from fastapi.testclient import TestClient
from fastapi import HTTPException, UploadFile, File
import os,sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from main import app
from main import create_database
from unittest.mock import patch, mock_open
import json

client = TestClient(app)


def test_reset_database():
    try:
        with open('initial.json', 'r') as f:
            initial_data = json.load(f)
        create_database(initial_data)
        assert True
    except Exception as e:
        assert False

def test_team_signup_success():
    response = client.post("/team_signup/", json={
        "team": {"team_name": "NewTeam", "password": "newpass123"},
        "a": {"admin_password": "BOSSMAN"}
    })
    assert response.status_code == 200
    assert response.json() == {"status": "success", "message": "Team has been added"}

def test_team_signup_failed_wrong_admin_password():
    response = client.post("/team_signup/", json={
        "team": {"team_name": "AnotherTeam", "password": "anotherpass123"},
        "a": {"admin_password": "wrongpassword"}
    })
    assert response.status_code == 200
    assert response.json() == {"status": "failed", "message": "Admin credentials are wrong"}

def test_team_signup_failed_existing_team():
    response = client.post("/team_signup/", json={
        "team": {"team_name": "NewTeam", "password": "newpass123"},
        "a": {"admin_password": "BOSSMAN"}
    })
    assert response.status_code == 200
    assert response.json() == {"status": "failed", "message": "Team already exists"}

def test_reset_rankings_specific_team_success():
    response = client.post("/reset_rankings/?team_name=BrunswickSC1", json={
        "a": {"admin_password": "BOSSMAN"}
    })
    assert response.status_code == 200
    assert response.json() == {"status": "success", "message": "Data for team 'BrunswickSC1' has been reset."}

def test_reset_rankings_all_teams_success():
    response = client.post("/reset_rankings/", json={
        "a": {"admin_password": "BOSSMAN"}
    })
    assert response.status_code == 200
    assert response.json() == {"status": "success", "message": "Data for all teams has been reset."}

def test_reset_rankings_failed_wrong_admin_password():
    response = client.post("/reset_rankings/", json={
        "team_name": "BrunswickSC1",
        "a": {"admin_password": "WRONGPASSWORD"}
    })
    assert response.status_code == 200
    assert response.json() == {"status": "failed", "message": "Admin credentials are wrong"}

def test_reset_rankings_failed_no_admin_password():
    response = client.post("/reset_rankings/", json={
        "team_name": "BrunswickSC1",
        "a": {"admin_password": ""}
    })
    assert response.status_code == 200
    assert response.json() == {"status": "failed", "message": "Admin credentials are wrong"}

def test_reset_questions_score_success():
    response = client.post("/reset_questions_score/", json={"admin_password": "BOSSMAN"})
    assert response.status_code == 200
    assert response.json() == {"status": "success", "message": "Questions scores have been reset."}

def test_reset_questions_score_failed_wrong_admin_password():
    response = client.post("/reset_questions_score/", json={"admin_password": "WRONGPASSWORD"})
    assert response.status_code == 200
    assert response.json() == {"status": "failed", "message": "Admin credentials are wrong"}

def test_reset_questions_score_failed_no_admin_password():
    response = client.post("/reset_questions_score/", json={"admin_password": ""})
    assert response.status_code == 200
    assert response.json() == {"status": "failed", "message": "Admin credentials are wrong"}

def test_list_json_files_success():
    response = client.get("/json-files/BOSSMAN")
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    
def test_list_json_files_wrong_password():
    response = client.get("/json-files/WrongPassword")
    assert response.status_code == 200
    assert response.json() == {"status": "failed", "message": "Admin credentials are wrong"}

def test_set_json_success():
    response = client.post("/set_json/?filename=initial.json", json={ "admin_password": "BOSSMAN"})
    assert response.status_code == 200
    assert response.json() == {"status": "success", "message": "Database updated!"}

def test_set_json_wrong_password():
    response = client.post("/set_json/?filename=initial.json", json={"admin_password": "WrongPassword"})
    assert response.status_code == 200
    assert response.json() == {"status": "failed", "message": "Admin credentials are wrong"}

def test_set_json_no_filename():
    response = client.post("/set_json/?filename=", json={"admin_password": "BOSSMAN"})
    assert response.status_code == 200
    assert response.json() == {"status": "failed", "message": "Wrong file selected!"}

def test_manual_questions_success():
    
        response = client.get("/manual_questions/BOSSMAN")
        assert response.status_code == 200
        assert "team_name" in response.json()[0]
    

def test_manual_questions_wrong_password():
    response = client.get("/manual_questions/WrongPassword")
    assert response.status_code == 200
    assert response.json() == {"status": "failed", "message": "Admin credentials are wrong"}

def test_manual_questions_no_password():
    response = client.get("/manual_questions/")
    assert response.status_code == 404
    

def test_update_manual_score_success():
        response = client.post("/update_manual_score/", json={
            "data":{"teams": [
            {"team_name": "BrunswickSC1", "scores": {"q1_score": 100, "q2_score": 200, "q3_score": 300, "q4_score": 400}}
        ]},
        "a":{"admin_password": "BOSSMAN"}
        })
        assert response.status_code == 200
        assert response.json() == {"status": "success"}

def test_update_manual_score_failed_wrong_admin_password():
    response = client.post("/update_manual_score/", json={
        "data":{"teams": [
            {"team_name": "BrunswickSC1", "scores": {"q1_score": 100, "q2_score": 200, "q3_score": 300, "q4_score": 400}}
        ]},
        "a":{"admin_password": "Wrongpass"}
    })
    assert response.status_code == 200
    assert response.json() == {"status": "failed", "message": "Admin credentials are wrong"}

def test_update_manual_score_score_out_of_range():
    response = client.post("/update_manual_score/", json={
        "data":{"teams": [
            {"team_name": "BrunswickSC1", "scores": {"q1_score": 700, "q2_score": 200, "q3_score": 300, "q4_score": 400}}
        ]},
        "a":{"admin_password": "BOSSMAN"}
    })
    assert response.status_code == 200
    assert "out of range" in response.json()["message"]

def test_upload_database_success():
    file_path = os.path.join(os.path.dirname(__file__), 'initial_test.json')
    with open(file_path, 'rb') as f:
        response = client.post(
            "/upload/BOSSMAN",
            files={"file": (os.path.basename(file_path), f, "application/json")}
        )
    assert response.status_code == 200
    assert response.json() == {"status": "success", "message": f"Database {os.path.basename(file_path)}.db created successfully!"}

def test_upload_database_wrong_password():
    response = client.post("/upload/WrongPassword", files={"file": ("dummy.json", "dummy content", "application/json")})
    assert response.status_code == 200
    assert response.json() == {"status": "failed", "message": "Admin credentials are wrong"}

def test_upload_database_wrong_file_format():
    response = client.post(
        "/upload/BOSSMAN",
        files={"file": ("dummy.txt", "dummy content", "text/plain")}
    )
    assert response.status_code == 200
    assert response.json() == {"status": "error", "message": "Wrong json format or file uploaded!"}

def test_upload_database_file_already_exists():
    file_path = 'initial.json'
    # Patch os.path.exists to always return True
    with patch('os.path.exists', return_value=True):
        with open(file_path, 'rb') as f:
            response = client.post(
                "/upload/BOSSMAN",
                files={"file": (file_path, f, "application/json")}
            )
    assert response.status_code == 200
    assert "already uploaded" in response.json()["message"]

def test_upload_database_no_file():
    response = client.post("/upload/BOSSMAN")
    assert response.status_code == 200
    assert response.json() == {"status": "failed", "message": "File Not uploaded"}