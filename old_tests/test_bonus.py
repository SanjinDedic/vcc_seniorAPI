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


def test_check_bonus():
    # Define team credentials and correct answer for SA question with ID "SA1"
    teams = [
        {"name": "Albion", "password": "xWFv9SKy"},
        {"name": "ApolloParkways1", "password": "H82fdJue"},
        {"name": "ApolloParkways2", "password": "Ke5pafim"},
        {"name": "AscotValeWest1", "password": "3UxfZ0ek"},
        {"name": "AscotValeWest2", "password": "jX36VkwW"}
    ]
    correct_answer = "mississippi"

    # Loop over the first 4 teams and submit correct SA answers, then check the score.
    for i, team in enumerate(teams[:4]):
        response = client.post("/submit_sa_answer", json={
            "id": "1",
            "team_name": team["name"],
            "team_password": team["password"],
            "answer": correct_answer
        })
        assert response.status_code == 200

        # Fetch the team's score
        team_status = client.get("/get_comp_table")
        assert team_status.status_code == 200
        json_dict = team_status.json()
        # Check if the bonus point is awarded (assuming original question points is 1)
        expected_score = 2 if i < 3 else 1
        assert any(team['score'] == expected_score for team in json_dict['teams'])
        