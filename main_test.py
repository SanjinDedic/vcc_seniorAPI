import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient
from main import app
import requests
import json
base_url="https://vccfinal.net"
#client = TestClient(base_url=url)

answer_1= """{"teams": 
    [{
        "name": "BlueSharks",
        "solved_questions": null,
        "attempted_questions": 0,
        "score": 0,
        "color": "rgb(16, 196, 190)"
    }, {
        "name": "CyberKnights",
        "solved_questions": null,
        "attempted_questions": 0,
        "score": 0,
        "color": "rgb(23, 244, 190)"
    }, {
        "name": "DarkHorses",
        "solved_questions": null,
        "attempted_questions": 0,
        "score": 0,
        "color": "rgb(182, 150, 20)"
    }, {
        "name": "DataMiners",
        "solved_questions": null,
        "attempted_questions": 0,
        "score": 0,
        "color": "rgb(12, 176, 245)"
    }, {
        "name": "FirePhoenix",
        "solved_questions": null,
        "attempted_questions": 0,
        "score": 0,
        "color": "rgb(150, 187, 30)"
    }, {
        "name": "FrostWolves",
        "solved_questions": null,
        "attempted_questions": 0,
        "score": 0,
        "color": "rgb(178, 142, 29)"
    }, {
        "name": "GoldenBears",
        "solved_questions": null,
        "attempted_questions": 0,
        "score": 0,
        "color": "rgb(1, 203, 148)"
    }, {
        "name": "MightyOwls",
        "solved_questions": null,
        "attempted_questions": 0,
        "score": 26,
        "color": "rgb(192, 157, 6)"
    }, {
        "name": "MoonWalkers",
        "solved_questions": null,
        "attempted_questions": 0,
        "score": 0,
        "color": "rgb(25, 133, 163)"
    }, {
        "name": "MountainGoats",
        "solved_questions": null,
        "attempted_questions": 0,
        "score": 0,
        "color": "rgb(9, 226, 204)"
    }, {
        "name": "QuickFoxes",
        "solved_questions": null,
        "attempted_questions": 0,
        "score": 0,
        "color": "rgb(10, 204, 180)"
    }, {
        "name": "RedWolves",
        "solved_questions": null,
        "attempted_questions": 0,
        "score": 0,
        "color": "rgb(155, 245, 35)"
    }, {
        "name": "SeaLions",
        "solved_questions": null,
        "attempted_questions": 0,
        "score": 0,
        "color": "rgb(204, 133, 26)"
    }, {
        "name": "SilverHawks",
        "solved_questions": null,
        "attempted_questions": 0,
        "score": 0,
        "color": "rgb(154, 163, 40)"
    }, {
        "name": "SkyEagles",
        "solved_questions": null,
        "attempted_questions": 0,
        "score": 0,
        "color": "rgb(155, 176, 30)"
    }, {
        "name": "SolarFlares",
        "solved_questions": null,
        "attempted_questions": 0,
        "score": 0,
        "color": "rgb(43, 224, 216)"
    }, {
        "name": "StarFighters",
        "solved_questions": null,
        "attempted_questions": 0,
        "score": 0,
        "color": "rgb(133, 55, 198)"
    }, {
        "name": "SwiftCats",
        "solved_questions": null,
        "attempted_questions": 0,
        "score": 0,
        "color": "rgb(133, 200, 8)"
    }, {
        "name": "ThunderBolts",
        "solved_questions": null,
        "attempted_questions": 0,
        "score": 0,
        "color": "rgb(250, 41, 206)"
    }, {
        "name": "WindRiders",
        "solved_questions": null,
        "attempted_questions": 0,
        "score": 0,
        "color": "rgb(250, 248, 15)"
    }]}"""
answer_2="""[{
    "team_name": "BlueSharks",
    "q1_score": 0,
    "q2_score": 0,
    "q3_score": 0,
    "q4_score": 0
}, {
    "team_name": "CyberKnights",
    "q1_score": 0,
    "q2_score": 0,
    "q3_score": 0,
    "q4_score": 0
}, {
    "team_name": "DarkHorses",
    "q1_score": 0,
    "q2_score": 0,
    "q3_score": 0,
    "q4_score": 0
}, {
    "team_name": "DataMiners",
    "q1_score": 0,
    "q2_score": 0,
    "q3_score": 0,
    "q4_score": 0
}, {
    "team_name": "FirePhoenix",
    "q1_score": 0,
    "q2_score": 0,
    "q3_score": 0,
    "q4_score": 0
}, {
    "team_name": "FrostWolves",
    "q1_score": 0,
    "q2_score": 0,
    "q3_score": 0,
    "q4_score": 0
}, {
    "team_name": "GoldenBears",
    "q1_score": 0,
    "q2_score": 0,
    "q3_score": 0,
    "q4_score": 0
}, {
    "team_name": "MightyOwls",
    "q1_score": 5,
    "q2_score": 8,
    "q3_score": 7,
    "q4_score": 6
}, {
    "team_name": "MoonWalkers",
    "q1_score": 0,
    "q2_score": 0,
    "q3_score": 0,
    "q4_score": 0
}, {
    "team_name": "MountainGoats",
    "q1_score": 0,
    "q2_score": 0,
    "q3_score": 0,
    "q4_score": 0
}, {
    "team_name": "QuickFoxes",
    "q1_score": 0,
    "q2_score": 0,
    "q3_score": 0,
    "q4_score": 0
}, {
    "team_name": "RedWolves",
    "q1_score": 0,
    "q2_score": 0,
    "q3_score": 0,
    "q4_score": 0
}, {
    "team_name": "SeaLions",
    "q1_score": 0,
    "q2_score": 0,
    "q3_score": 0,
    "q4_score": 0
}, {
    "team_name": "SilverHawks",
    "q1_score": 0,
    "q2_score": 0,
    "q3_score": 0,
    "q4_score": 0
}, {
    "team_name": "SkyEagles",
    "q1_score": 0,
    "q2_score": 0,
    "q3_score": 0,
    "q4_score": 0
}, {
    "team_name": "SolarFlares",
    "q1_score": 0,
    "q2_score": 0,
    "q3_score": 0,
    "q4_score": 0
}, {
    "team_name": "StarFighters",
    "q1_score": 0,
    "q2_score": 0,
    "q3_score": 0,
    "q4_score": 0
}, {
    "team_name": "SwiftCats",
    "q1_score": 0,
    "q2_score": 0,
    "q3_score": 0,
    "q4_score": 0
}, {
    "team_name": "ThunderBolts",
    "q1_score": 0,
    "q2_score": 0,
    "q3_score": 0,
    "q4_score": 0
}, {
    "team_name": "WindRiders",
    "q1_score": 0,
    "q2_score": 0,
    "q3_score": 0,
    "q4_score": 0
}]
"""
answer_3="""{
    "questions": [{
        "id": 1,
        "content": "Where is VCC held?",
        "current_points": 10,
        "type": "mcqs",
        "question_group": 1,
        "options": ["Athens", "Melbourne", "Geelong", "Darwin", "Hobart", "Online"],
        "image_link": "images/11.png",
        "content_link": "http://sample.content.link",
        "attempt_count": 0,
        "solved": null
    }, {
        "id": 2,
        "content": "What do call this symbol + ?",
        "current_points": 20,
        "type": "short answer",
        "question_group": 1,
        "options": [],
        "image_link": "images/1s1.png",
        "content_link": "https://www.youtube.com/watch?v=uegzHgKcyqk",
        "attempt_count": 0,
        "solved": null
    }, {
        "id": 3,
        "content": "What is the technique called where an attacker intercepts communication between two parties without their knowledge?",
        "current_points": 10,
        "type": "short answer",
        "question_group": 1,
        "options": [],
        "image_link": "images_sec/4.png",
        "content_link": "",
        "attempt_count": 0,
        "solved": null
    }, {
        "id": 4,
        "content": "Which type of malware is designed to replicate itself and spread to other computers?",
        "current_points": 10,
        "type": "mcqs",
        "question_group": 2,
        "options": ["Virus", "Worm", "Trojan", "Ransomware", "", ""],
        "image_link": "images_sec/5.png",
        "content_link": "",
        "attempt_count": 0,
        "solved": null
    }, {
        "id": 5,
        "content": "What is the process of trying to decode encrypted or hashed data called?",
        "current_points": 10,
        "type": "short answer",
        "question_group": 2,
        "options": [],
        "image_link": "images_sec/6.png",
        "content_link": "",
        "attempt_count": 0,
        "solved": null
    }, {
        "id": 6,
        "content": "Which of the following is a popular tool used for password cracking?",
        "current_points": 10,
        "type": "mcqs",
        "question_group": 2,
        "options": ["John the Ripper", "Nessus", "Burp Suite", "Aircrack-ng", "", ""],
        "image_link": "images_sec/7.png",
        "content_link": "",
        "attempt_count": 0,
        "solved": null
    }, {
        "id": 7,
        "content": "What method is used to disguise a harmful link or website to make it appear legitimate?",
        "current_points": 10,
        "type": "short answer",
        "question_group": 2,
        "options": [],
        "image_link": "images_sec/8.png",
        "content_link": "",
        "attempt_count": 0,
        "solved": null
    }, {
        "id": 8,
        "content": "What is the process of attempting to gain unauthorized access to a computer system by posing as an authorized user?",
        "current_points": 10,
        "type": "mcqs",
        "question_group": 2,
        "options": ["Spoofing", "Phishing", "Brute-Force Attack", "Social Engineering", "", ""],
        "image_link": "images_sec/9.png",
        "content_link": "",
        "attempt_count": 0,
        "solved": null
    }, {
        "id": 9,
        "content": "What is the technique used by hackers to exploit a buffer overflow vulnerability in a targeted system?",
        "current_points": 10,
        "type": "short answer",
        "question_group": 2,
        "options": [],
        "image_link": "images_sec/10.png",
        "content_link": "",
        "attempt_count": 0,
        "solved": null
    }]
}"""
test_answer_1=json.loads(answer_1)
test_answer_2=json.loads(answer_2)
test_answer_3=json.loads(answer_3)


def test_get_comp_table():
    response = requests.get(f"{base_url}/get_comp_table")
    assert response.status_code == 200
    assert response.json() == test_answer_1


def test_get_manual_questions():
    response = requests.get(f"{base_url}/manual_questions",headers={"Password": "BOSSMAN"})
    assert response.status_code == 200
    assert response.json() == test_answer_2


def test_get_team_questions():
    response = requests.get(f"{base_url}/questions/RedWolves",headers={"Team-Name": "RedWolves","Team-Password": "123"})
    assert response.status_code == 200
    assert response.json() == test_answer_3

def test_get_any_team_questions():
    response = requests.get(f"{base_url}/questions/anything",headers={"Team-Name": "RedWolves","Team-Password": "123"})
    assert response.status_code == 200
    assert response.json() == {"questions":"Error"}

def test_submit_mcqs_answer_correct():
    payload = {
    "id": "1",
    "answer": "b",
    "team_name": "RedWolves"
    }
    response = requests.post(f"{base_url}/submit_mcqs_answer",headers={"Team-Name": "RedWolves","Team-Password": "123"},json=payload)
    assert response.status_code == 200
    assert response.json() == {"message":"Correct"}

def test_submit_mcqs_answer_incorrect():
    payload = {
    "id": "4",
    "answer": "a",
    "team_name": "RedWolves"
    }
    response = requests.post(f"{base_url}/submit_mcqs_answer",headers={"Team-Name": "RedWolves","Team-Password": "123"},json=payload)
    assert response.status_code == 200
    assert response.json() == {"message":"Incorrect"}

def test_submit_mcqs_answer_already_attempted():

    payload = {
    "id": "1",
    "answer": "a",
    "team_name": "RedWolves"
    }
    response = requests.post(f"{base_url}/submit_mcqs_answer",headers={"Team-Name": "RedWolves","Team-Password": "123"},json=payload)
    assert response.status_code == 200
    assert response.json() == {"message":"Question already attempted"}

def test_submit_mcqs_answer_error():
    payload = {
    "id": "9",
    "answer": "66",
    "team_name": "RedWdolves"
    }
    response = requests.post(f"{base_url}/submit_mcqs_answer",headers={"Team-Name": "RedWolves","Team-Password": "123"},json=payload)
    assert response.status_code == 200
    assert response.json() == {"message":"An error occurred when submitting the answer."}

def test_submit_sa_answer_correct():
    payload = {
    "id": "2",
    "answer": "plus",
    "team_name": "RedWolves"
    }
    response = requests.post(f"{base_url}/submit_sa_answer",headers={"Team-Name": "RedWolves","Team-Password": "123"},json=payload)
    assert response.status_code == 200
    assert response.json() == {"message":"Correct"}

def test_submit_sa_answer_incorrect():
    payload = {
    "id": "5",
    "answer": "dsa",
    "team_name": "RedWolves"
    }
    for i in range(3):
        response = requests.post(f"{base_url}/submit_sa_answer",headers={"Team-Name": "RedWolves","Team-Password": "123"},json=payload)
    assert response.status_code == 200
    assert response.json() == {"message":"Incorrect"}

def test_submit_sa_answer_try_again():

    payload = {
    "id": "3",
    "answer": "a",
    "team_name": "RedWolves"
    }
    response = requests.post(f"{base_url}/submit_sa_answer",headers={"Team-Name": "RedWolves","Team-Password": "123"},json=payload)
    assert response.status_code == 200
    assert response.json() == {"message":"Try again"}

def test_submit_sa_answer_full_attempts():

    payload = {
    "id": "2",
    "answer": "pl",
    "team_name": "RedWolves"
    }
    response = requests.post(f"{base_url}/submit_sa_answer",headers={"Team-Name": "RedWolves","Team-Password": "123"},json=payload)
    assert response.status_code == 200
    assert response.json() == {"message":"Question already attempted"}


def test_submit_sa_answer_error():
    payload = {
    "id": "96",
    "answer": "6gf",
    "team_name": "RedWdolvesdaww"
    }
    response = requests.post(f"{base_url}/submit_sa_answer",headers={"Team-Name": "RedWolves","Team-Password": "123"},json=payload)
    assert response.status_code == 200
    assert response.json() == {"message":"An error occurred when submitting the answer."}

def test_team_signup():
    payload = {
    "name": "NewTeam",
    "password": "123"
    }
    response = requests.post(f"{base_url}/team_signup/",headers={"Password": "BOSSMAN"},json=payload)
    assert response.status_code == 200
    assert response.json() == {"status": "success", "message": "Team has been added"}

def test_team_signup_exists():
    payload = {
    "name": "RedWolves",
    "password": "123"
    }
    response = requests.post(f"{base_url}/team_signup/",json=payload)
    assert response.status_code == 200
    assert response.json() == {"status":"failed", "message": "Team already exists"}

def json_files():
   
    response = requests.post(f"{base_url}/json-files/",headers={"Password": "BOSSMAN"})
    assert response.status_code == 200
    #assert response.json() == {"message":"An error occurred when submitting the answer."}

def set_json():
    payload = {
    "filename": "test.json"
    }
    response = requests.post(f"{base_url}/set_json/",headers={"Password": "BOSSMAN"},json=payload)
    assert response.status_code == 200
    assert response.json() == {"status": "failed", "message": "Wrong file selected!"}

def reset_rankings():
    response = requests.post(f"{base_url}/reset_rankings/",headers={"Password": "BOSSMAN"})
    assert response.status_code == 200
    assert response.json() == {"status": "success", "message": "Data for all teams has been reset."}

def reset_question_score():
    
    response = requests.post(f"{base_url}/reset_questions_score/",headers={"Password": "BOSSMAN"})
    assert response.status_code == 200
    assert response.json() == {"status": "success", "message": "Questions scores have been reset. "}

def team_login_correct():
    payload = {
    "team_name": "RedWdolves",
    "password": "123"
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




