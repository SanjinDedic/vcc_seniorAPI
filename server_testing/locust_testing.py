import json
import random
import threading
from itertools import cycle
from locust import HttpUser, task, between

with open('teams.json', 'r') as f:
    teams_data = json.load(f)
    teams_list = teams_data['teams']

with open('initial.json', 'r') as f:
    questions_data = json.load(f)
    questions_list = questions_data['questions']

for idx, question in enumerate(questions_list):
    question.setdefault('id', idx + 1)

mcq_questions = [q for q in questions_list if q['type'] == 'mcqs']
sa_questions = [q for q in questions_list if q['type'] == 'short answer']

random.shuffle(teams_list)
teams_iterator = cycle(teams_list)
iterator_lock = threading.Lock()


class QuizUser(HttpUser):
    wait_time = between(1, 5)

    def on_start(self):
        with iterator_lock:
            self.team = next(teams_iterator)
        self.login()

    def login(self):
        response = self.client.post("/team_login", json={
            "team_name": self.team['name'],
            "password": self.team['password']
        })
        if response.status_code == 200:
            self.access_token = response.json()['data']
            self.client.headers.update({
                "Authorization": f"Bearer {self.access_token}"
            })
        else:
            print(f"Login failed for team {self.team['name']}")

    @task(3)
    def answer_question(self):
        question_type = random.choice(['mcq', 'sa'])

        if question_type == 'mcq' and mcq_questions:
            question = random.choice(mcq_questions)
            self.submit_mcq_answer(question)
        elif question_type == 'sa' and sa_questions:
            question = random.choice(sa_questions)
            self.submit_sa_answer(question)
        else:
            # If one type is empty, fallback to the other
            if mcq_questions:
                question = random.choice(mcq_questions)
                self.submit_mcq_answer(question)
            elif sa_questions:
                question = random.choice(sa_questions)
                self.submit_sa_answer(question)

    def submit_mcq_answer(self, question):
        options = ['a', 'b', 'c', 'd', 'e']
        selected_option = random.choice(options)

        # Prepare the answer data
        answer_data = {
            "id": str(question.get('id')),
            "answer": selected_option
        }

        response = self.client.post("/submit_mcqs_answer", json=answer_data)
        if response.status_code != 200:
            print(f"Team {self.team['name']} failed to submit MCQ answer for question {question.get('id')}")
        else:
            print(f"Team {self.team['name']} submitted MCQ answer to question {question.get('id')}")

    def submit_sa_answer(self, question):
        if random.random() < 0.5:
            answer_text = question.get('answer')  # Correct answer
        else:
            answer_text = str(random.randint(1, 200))  # Random incorrect answer

        answer_data = {
            "id": str(question.get('id')),
            "answer": answer_text
        }

        response = self.client.post("/submit_sa_answer", json=answer_data)
        if response.status_code != 200:
            print(f"Team {self.team['name']} failed to submit SA answer for question {question.get('id')}")
        else:
            print(f"Team {self.team['name']} submitted SA answer to question {question.get('id')}")

    @task(1)
    def view_question(self):
        response = self.client.get(f"/questions")
        if response.status_code != 200:
            print(f"Failed to view questions")