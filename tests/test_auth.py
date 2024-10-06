from fastapi.testclient import TestClient
import os,sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from main import app

client = TestClient(app)


def test_admin_login():
    response = client.post("/admin_login", json={"name": "Administrator", "password": "BOSSMAN"})
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert "data" in response.json()

    response = client.post("/admin_login", json={"name": "Administrator", "password": "WRONGPASS"})
    assert response.status_code == 200
    assert response.json() == {"status": "failed", "message": "Admin credentials are wrong","data": None}

    response = client.post("/admin_login", json={"name": "Administrator", "adminpassword": "WRONGPASS"})
    assert response.status_code == 422
    

def test_team_login():
    response = client.post("/team_login", json={"team_name": "SanjinX", "password": "652093"})
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert "data" in response.json()

    response = client.post("/team_login", json={"team_name": "SanjinX", "password": "wrongpass"})
    assert response.status_code == 200
    assert response.json() == {"status": "failed", "message": "No team found with these credentials","data": None}

    response = client.post("/team_login", json={"team": "SanjinX", "password": "wrongpass"})
    assert response.status_code == 422

    response = client.post("/team_login", json={"team_name": "SanjinX", "password": ""})
    assert response.status_code == 200
    assert response.json() == {"status": "failed", "message": "Team name and password are required","data": None}
    