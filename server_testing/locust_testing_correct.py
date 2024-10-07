import json
import random
import threading
from itertools import cycle
from locust import HttpUser, task, between
from requests.exceptions import ConnectionError

with open('teams.json', 'r') as f:
    teams_data = json.load(f)
    teams_list = teams_data['teams']

with open('initial.json', 'r') as f:
    questions_data = json.load(f)
    questions_list = questions_data['questions']

# Assign unique IDs to questions if they don't have one
for idx, question in enumerate(questions_list):
    question.setdefault('id', idx + 1)

random.shuffle(teams_list)
teams_iterator = cycle(teams_list)
iterator_lock = threading.Lock()

class QuizUser(HttpUser):
    wait_time = between(1, 2)  # Adjust as needed

    def on_start(self):
        with iterator_lock:
            self.team = next(teams_iterator)
        self.login()
        self.unanswered_questions = questions_list.copy()

    def login(self):
        try:
            response = self.client.post("/team_login", json={
                "team_name": self.team['name'],
                "password": self.team['password']
            })
            if response.status_code == 200:
                self.access_token = response.json()['data']
                self.client.headers.update({
                    "Authorization": f"Bearer {self.access_token}"
                })
                print(f"Team {self.team['name']} logged in successfully.")
            else:
                print(f"Login failed for team {self.team['name']}")
        except Exception as e:
            print(f"Exception during login for team {self.team['name']}: {e}")

    @task
    def answer_all_questions(self):
        while self.unanswered_questions:
            question = self.unanswered_questions.pop(0)
            if question['type'] == 'mcqs':
                self.submit_mcq_answer(question)
            elif question['type'] == 'short answer':
                self.submit_sa_answer(question)
            else:
                print(f"Unknown question type: {question['type']}")

    def submit_mcq_answer(self, question):
        # Use the correct answer from the question
        correct_answer = question.get('answer')

        answer_data = {
            "id": str(question.get('id')),
            "answer": correct_answer
        }

        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self.client.post("/submit_mcqs_answer", json=answer_data)
                if response.status_code == 200:
                    print(f"Team {self.team['name']} submitted MCQ correct answer for question {question.get('id')}")
                    return
                else:
                    print(f"Team {self.team['name']} failed to submit MCQ answer for question {question.get('id')}")
                    print(f"Response: {response.text}")
                    break
            except ConnectionError as e:
                print(f"ConnectionError on attempt {attempt+1} for team {self.team['name']} question {question.get('id')}: {e}")
                if attempt < max_retries - 1:
                    continue
                else:
                    print(f"Failed to submit after {max_retries} attempts.")
            except Exception as e:
                print(f"Exception while submitting MCQ answer: {e}")
                break

    def submit_sa_answer(self, question):
        # Always use the correct answer
        answer_text = question.get('answer')

        answer_data = {
            "id": str(question.get('id')),
            "answer": answer_text
        }

        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self.client.post("/submit_sa_answer", json=answer_data)
                if response.status_code == 200:
                    print(f"Team {self.team['name']} submitted SA correct answer for question {question.get('id')}")
                    return
                else:
                    print(f"Team {self.team['name']} failed to submit SA answer for question {question.get('id')}")
                    print(f"Response: {response.text}")
                    break
            except ConnectionError as e:
                print(f"ConnectionError on attempt {attempt+1} for team {self.team['name']} question {question.get('id')}: {e}")
                if attempt < max_retries - 1:
                    continue
                else:
                    print(f"Failed to submit after {max_retries} attempts.")
            except Exception as e:
                print(f"Exception while submitting SA answer: {e}")
                break

    @task
    def view_question(self):
        try:
            response = self.client.get("/questions")
            if response.status_code != 200:
                print(f"Failed to view questions")
        except Exception as e:
            print(f"Exception while viewing questions: {e}")
