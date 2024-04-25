from fastapi.testclient import TestClient
import os,sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from main import app

client = TestClient(app)


def test_admin_login():
    response = client.post("/admin_login", json={"admin_password": "BOSSMAN"})
    assert response.status_code == 200
    assert response.json() == {"status": "success"}

    response = client.post("/admin_login", json={"admin_password": "WRONGPASS"})
    assert response.status_code == 200
    assert response.json() == {"status": "failed", "message": "Admin credentials are wrong"}

    response = client.post("/admin_login", json={"adminpassword": "WRONGPASS"})
    assert response.status_code == 422
    

def test_team_login():
    response = client.post("/team_login", json={"team_name": "BrunswickSC1", "password": "ighEMkOP"})
    assert response.status_code == 200
    assert "access_token" in response.json()

    response = client.post("/team_login", json={"team_name": "BrunswickSC1", "password": "wrongpass"})
    assert response.status_code == 200
    assert response.json() == {"status": "failed", "message": "No team found with these credentials"}

    response = client.post("/team_login", json={"team": "BrunswickSC1", "password": "wrongpass"})
    assert response.status_code == 422
    