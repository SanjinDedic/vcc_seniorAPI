from locust import HttpUser, task, between
import json
import random

class QuizUser(HttpUser):
    wait_time = between(1, 5)

    def on_start(self):
        self.login()

    def login(self):
        response = self.client.post("/login", json={
            "username": f"user{random.randint(1, 1000)}",
            "password": "password123"
        })
        if response.status_code == 200:
            self.access_token = response.json().get("access_token")
            self.client.headers.update({
                "Authorization": f"Bearer {self.access_token}"
            })
        else:
            print("Login failed")

    @task(3)
    def answer_question(self):
        question_id = random.randint(1, 100)
        response = self.client.post("/answer", json={
            "question_id": question_id,
            "answer": "Your answer here"
        })
        if response.status_code != 200:
            print(f"Failed to answer question {question_id}")

    @task(1)
    def view_question(self):
        question_id = random.randint(1, 100)
        response = self.client.get(f"/questions/{question_id}")
        if response.status_code != 200:
            print(f"Failed to view question {question_id}")