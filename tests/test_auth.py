# tests/test_auth.py
import pytest
from fastapi.testclient import TestClient
from fastapi import HTTPException
from main import app
from auth import create_access_token, get_current_user, verify_password

client = TestClient(app)

def test_verify_password():
    hashed_password = "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW"  # Password: "secret"
    assert verify_password("secret", hashed_password) == True
    assert verify_password("wrong_password", hashed_password) == False

def test_create_access_token():
    data = {"sub": "test_team", "role": "student"}
    token = create_access_token(data=data)
    assert token is not None
    assert isinstance(token, str)

def test_get_current_user_valid_token(mocker):
    data = {"sub": "BrunswickSC1", "role": "student"}
    token = create_access_token(data=data)
    mocker.patch("auth.oauth2_scheme", return_value=token)
    
    user = get_current_user(token)
    assert user == {"team_name": "BrunswickSC1", "role": "student"}

def test_get_current_user_invalid_token(mocker):
    invalid_token = "invalid_token"
    mocker.patch("auth.oauth2_scheme", return_value=invalid_token)
    
    with pytest.raises(HTTPException) as exc_info:
        get_current_user(invalid_token)
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Invalid token"

def test_team_login_valid_credentials():
    response = client.post("/team_login", json={"team_name": "BrunswickSC1", "password": "ighEMkOP"})
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert "token_type" in response.json()

def test_team_login_invalid_credentials():
    response = client.post("/team_login", json={"team_name": "invalid_team", "password": "invalid_password"})
    assert response.status_code == 200
    assert response.json() == {"status": "failed", "message": "No team found with these credentials"}