import logging
import os
import random
import sqlite3
from datetime import datetime
from difflib import SequenceMatcher
from fastapi import FastAPI,UploadFile, HTTPException, status, File, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import json

CURRENT_DB="comp.db"

class TeamSignUp(BaseModel):
    name: str
    password: str

class Answer(BaseModel):
    id: str
    answer: str
    team_name: str
    
class Team(BaseModel):
    team_name: str
    password: str

class Score(BaseModel):
    q1_score: int
    q2_score: int
    q3_score: int
    q4_score: int

class TeamScores(BaseModel):
    team_name: str
    scores: Score

class TeamsInput(BaseModel):
    teams: List[TeamScores]

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database function
def execute_db_query(query, params=(), fetchone=False, db=None):
    if db is None:
        db=CURRENT_DB
    try:
        conn = sqlite3.connect(db)
        c = conn.cursor()
        c.execute(query, params)
        conn.commit()
        if fetchone:
            return c.fetchone()
        else:
            return c.fetchall()
    except Exception as e:
        logging.error("Error occurred when executing database query", exc_info=True)
        raise e
    finally:
        conn.close()


def similar(s1, s2, threshold=0.6):
    similarity_ratio = SequenceMatcher(None, s1, s2).ratio()
    return similarity_ratio >= threshold

def random_color():
    a = random.randint(130, 255)
    b = random.randint(130, 255)
    c = random.randint(0, 60)
    rgb = [a, b, c]
    random.shuffle(rgb)
    return f"rgb({rgb[0]}, {rgb[1]}, {rgb[2]})"

def get_question(id: str):
    result = execute_db_query("SELECT answer,current_points FROM questions WHERE id = ?", (id, ))
    if not result:
        raise HTTPException(status_code=404, detail="Question not found")
    return result[0]


def get_team(team_name: str):
    result = execute_db_query(f"SELECT score,attempted_questions,solved_questions FROM teams WHERE name = ?", (team_name,))
    if not result:
        raise HTTPException(status_code=404, detail="Team not found")
    return result[0]

def get_attempts(team_name: str,id: str):
    result = execute_db_query(f"SELECT attempt_count FROM attempted_questions WHERE team_name = ? AND question_id = ?", (team_name, id,), fetchone=True)
    return result
    
def decrement_question_points(question_id: int):
    execute_db_query("UPDATE questions SET current_points = current_points - 1 WHERE id = ?", (question_id,))

def reset_question_points():
    execute_db_query("UPDATE questions SET current_points = original_points")


def update_team(name: str, score: int, solved_qs: int, attempted_qs: int):
    execute_db_query(
        f"UPDATE teams SET score = ?, attempted_questions = ?, solved_questions = ? WHERE name = ?", 
        params=(score, attempted_qs, solved_qs, name))

def update_attempted_questions(name: str, question_id: str, solved: bool, attempts=1):
    existing_record = execute_db_query(f"SELECT * FROM attempted_questions WHERE team_name = ? AND question_id = ?", (name, question_id,), fetchone=True)
    if existing_record:
        execute_db_query(f"UPDATE attempted_questions SET attempt_count = ?, timestamp = ?, solved = ? WHERE team_name = ? AND question_id = ?", 
        params=(attempts, datetime.now(), solved, name, question_id))
    else:
        execute_db_query(
            f"INSERT INTO attempted_questions VALUES (?, ?, ?, ?, ?)",
            params=(name, question_id, datetime.now(), solved, attempts))


@app.get("/get_comp_table")
async def get_comp_table():
    raw_teams = execute_db_query(f"SELECT name, solved_questions, attempted_questions, score, color FROM teams")
    
    teams = [
        {
            "name": team[0],
            "solved_questions": team[1],
            "attempted_questions": team[2],
            "score": team[3],
            "color": team[4]
        }
        for team in raw_teams
    ]
    
    return {"teams": teams}

@app.get("/manual_questions/")
async def manual_questions():
    rows = execute_db_query(f"""
    SELECT team_name, q1_score, q2_score, q3_score, q4_score
    FROM manual_scores """)
    
    teams = [
        {
            "team_name": row[0],
            "q1_score": row[1],
            "q2_score": row[2],
            "q3_score": row[3],
            "q4_score": row[4]
        } for row in rows
    ]
    
    return teams

@app.get("/questions")
async def get_questions():
    
    questions = execute_db_query("SELECT id, content, current_points, type, question_group, option_a, option_b, option_c, option_d, option_e, option_f, option_g, option_h, option_i, option_j, image_link, content_link FROM questions")

    transformed_questions = []

    for question in questions:
        # Extracting options from the fetched row (from option_a to option_j)
        options = question[5:15]  # Adjust indices accordingly based on your table's structure

        # Filtering out null options
        valid_options = [opt for opt in options if opt is not None]

        # Constructing the question object
        transformed_question = {
            'id': question[0],
            'content': question[1],
            'current_points': question[2],
            'type': question[3],
            'question_group': question[4],
            'options': valid_options,
            'image_link': question[15],
            'content_link': question[16] 
        }

        transformed_questions.append(transformed_question)

    return {"questions": transformed_questions}


@app.post("/submit_mcqs_answer")
async def submit_answer_mcqs(a: Answer):
    try:
        correct_ans, question_pts = get_question(id=a.id)
        score, attempted_qs, solved_qs = get_team(team_name=a.team_name)
        is_correct = a.answer == correct_ans
        attempted_qs += 1
        if is_correct:
            score += question_pts
            solved_qs += 1
            update_team(name=a.team_name, score=score, solved_qs=solved_qs, attempted_qs=attempted_qs)
            update_attempted_questions(name=a.team_name, question_id=a.id, solved=is_correct)
            decrement_question_points(question_id=a.id)
            return {"message": "Correct"}
        
        update_team(name=a.team_name, score=score, solved_qs=solved_qs, attempted_qs=attempted_qs)
        update_attempted_questions(name=a.team_name, question_id=a.id, solved=is_correct)

        return {"message": "Incorrect", "correct_answer": correct_ans}
    except HTTPException as e:
        raise e
    except Exception as e:
        logging.error("Error occurred when submitting answer", exc_info=True)
        raise HTTPException(status_code=500, detail="An error occurred when submitting the answer.")

@app.post("/submit_sa_answer")
async def submit_answer_sa(a: Answer):
    try:
        correct_ans, question_pts = get_question(id=a.id)
        score, attempted_qs, solved_qs = get_team(team_name=a.team_name)
        previous_attempts = get_attempts(team_name=a.team_name,id=a.id)
        
        attempts_made = 1 if not previous_attempts else previous_attempts[0]+1
        is_correct = a.answer == correct_ans or similar(correct_ans, a.answer)
        if is_correct:
            attempted_qs += 1
            score += question_pts
            solved_qs += 1
            update_team(name=a.team_name, score=score, solved_qs=solved_qs, attempted_qs=attempted_qs)
            update_attempted_questions(name=a.team_name, question_id=a.id, solved=is_correct,attempts=attempts_made)
            decrement_question_points(question_id=a.id)
            return {"message": "Correct"}
        
        if attempts_made >= 3: 
            attempted_qs += 1
            update_team(name=a.team_name, score=score, solved_qs=solved_qs, attempted_qs=attempted_qs)
            update_attempted_questions(name=a.team_name, question_id=a.id, solved=is_correct,attempts=attempts_made)
            return {"message": "Incorrect", "correct_answer": correct_ans}
        
        update_attempted_questions(name=a.team_name, question_id=a.id, solved=is_correct,attempts=attempts_made)
        
        return {"message": "Try again"}
    except HTTPException as e:
        raise e
    except Exception as e:
        logging.error("Error occurred when submitting answer", exc_info=True)
        raise HTTPException(status_code=500, detail="An error occurred when submitting the answer.")


@app.post("/team_signup/")
async def quick_signup(team: TeamSignUp):
    try:
        team_color = random_color()
        existing_team = execute_db_query("SELECT * FROM teams WHERE name = ? AND password = ?", (team.name,team.password,), fetchone=True)
        if existing_team is not None:
            return {"status":"failed", "message": "Team already exists"}
        
        execute_db_query("INSERT INTO teams (name, password, score,color, attempted_questions, solved_questions) VALUES (?, ?, ?, ?, ?, ?)", (team.name,team.password,0,team_color, 0, 0, ))
        
        execute_db_query("INSERT INTO manual_scores (team_name, q1_score, q2_score, q3_score, q4_score) VALUES (?, ?, ?, ?, ?)",(team.name,0,0,0,0,))

        return {"status": "success", "message": "Team has been added"}
    
    except Exception as e:   
        return {"status":"failed", "message": "Error occured"}
        
@app.get("/json-files/")
async def list_json_files():
    try:
        files = [f for f in os.listdir("json") if os.path.isfile(os.path.join("json", f)) and f.endswith(".json")]
        return {"status": "success", "files": files}
    except Exception as e:
        return {"status": "error", "message": str(e)}

   
@app.post("/set_json/")
async def set_json(filename: str):
    if filename:
        CURRENT_DB=f"{filename}.db"
        return {"status": "success", "message": "Database updated!"}
    else:
        return {"status": "failed", "message": "Wrong file selected!"}

@app.post("/reset_rankings/")
async def reset_team_data(team_name: str = Query(None, description="The name of the team to reset. If not provided, all teams will be reset.")):
    try:
        

        # Reset stats for a specific team
        if team_name:
            execute_db_query("""
                UPDATE teams 
                SET score = 0, attempted_questions = 0, solved_questions = 0 
                WHERE name = ?
            """, (team_name, ))

            execute_db_query("""
                DELETE FROM attempted_questions
                WHERE team_name = ?
            """, (team_name, ))
        # Reset stats for all teams
        else:
            execute_db_query("""
                UPDATE teams 
                SET score = 0, attempted_questions = 0, solved_questions = 0
            """)

            execute_db_query("""
                DELETE FROM attempted_questions
            """)

        if team_name:
            return {"status": "success", "message": f"Data for team '{team_name}' has been reset."}
        else:
            return {"status": "success", "message": "Data for all teams has been reset."}

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error: {e}")

@app.post("/reset_questions_score/")
async def reset_questions_score():
    try:
        reset_question_points()
        return {"status": "success", "message": "Questions scores have been reset. "}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error: {e}")
    
@app.post("/team_login")
async def team_login(user: Team):
    try:
        result = execute_db_query("SELECT password FROM teams WHERE name=?",(user.team_name,))
        if result and result[0][0]==user.password:

            return {"status": "success", "message": "Logged in successfully"}
        else:
            return {"status": "failed", "message": "No team found with these credentials"}
            
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error: {e}")


@app.post("/update_manual_score/")
async def update_manual_score(data: TeamsInput):
    try:
        for team in data.teams:
            scores = team.scores
            
            # Check conditions for scores
            if not 0 <= scores.q1_score <= 15:
                return {"status": "failed", "message": "q1_score out of range for team: " + team.team_name}
            if not 0 <= scores.q2_score <= 15:
                return {"status": "failed", "message": "q2_score out of range for team: " + team.team_name}
            if not 0 <= scores.q3_score <= 15:
                return {"status": "failed", "message": "q3_score out of range for team: " + team.team_name}
            if not -100 <= scores.q4_score <= 100:
                return {"status": "failed", "message": "q4_score out of range for team: " + team.team_name}
            
        for team in data.teams:
            team_name = team.team_name
            scores = team.scores
            execute_db_query("""UPDATE manual_scores
                        SET q1_score = ?, q2_score = ?, q3_score = ?, q4_score = ?
                        WHERE team_name = ?""", (scores.q1_score, scores.q2_score, scores.q3_score, scores.q4_score, team_name,))
        
        return {"status": "success"}
    except Exception as e:
        return {"status": "failed"}


@app.post("/upload/")
async def upload_database(file: UploadFile = File(...)):
    global CURRENT_DB
    if file:
        try:
            # Ensure it's a JSON file
            if not file.filename.endswith(".json"):
                return {"status": "error", "message": f"Wrong json format or file uploaded!"}
                
            file_location = os.path.join("json", file.filename)
            if os.path.exists(file_location):
                
                CURRENT_DB=f"{file.filename}.db"
                return {"status": "error", "message": f"File '{file.filename}' already uploaded!"}
            
            content = file.file.read()
            

            with open(file_location, "wb+") as file_object:
                file_object.write(content)

            data = json.loads(content)

            # Create and initialize database
            conn = sqlite3.connect(f"{file.filename}.db")
            cursor = conn.cursor()

            # Define tables
            teams_table = """
            CREATE TABLE "teams" (
                "name"	TEXT NOT NULL UNIQUE,
                "password"	TEXT NOT NULL,
                "score"	INTEGER DEFAULT 0,
                "color"	TEXT,
                "attempted_questions"	INTEGER DEFAULT 0,
                "solved_questions"	INTEGER DEFAULT 0,
                PRIMARY KEY("name")
            );
            """

            questions_table = """
            CREATE TABLE "questions" (
                "id"	INTEGER,
                "content"	TEXT NOT NULL,
                "answer"	TEXT NOT NULL,
                "original_points"	INTEGER NOT NULL,
                "current_points"	INTEGER,
                "type"	TEXT,
                "question_group"	INTEGER,
                "option_a"	TEXT,
                "option_b"	TEXT,
                "option_c"	TEXT,
                "option_d"	TEXT,
                "option_e"	TEXT,
                "option_f"	TEXT,
                "option_g"	TEXT,
                "option_h"	TEXT,
                "option_i"	TEXT,
                "option_j"	TEXT,
                "image_link"	TEXT,
                "content_link"	TEXT,
                PRIMARY KEY("id")
            );
            """

            attempted_questions_table = """
            CREATE TABLE "attempted_questions" (
                "team_name"	text,
                "question_id"	INTEGER,
                "timestamp"	datetime,
                "solved"	boolean NOT NULL,
                "attempt_count"	INTEGER DEFAULT 0,
                FOREIGN KEY("team_name") REFERENCES "teams"("name"),
                FOREIGN KEY("question_id") REFERENCES "questions"("id")
            );
            """

            manual_question_table = """
            CREATE TABLE "manual_scores" (
                "team_name"	TEXT UNIQUE,
                "q1_score"	INTEGER,
                "q2_score"	INTEGER,
                "q3_score"	INTEGER,
                "q4_score"  INTEGER,
                FOREIGN KEY("team_name") REFERENCES "teams"("name")
            );
            """

            cursor.execute(teams_table)
            cursor.execute(questions_table)
            cursor.execute(attempted_questions_table)
            cursor.execute(manual_question_table)
            # Insert data from the JSON into the questions table
            for question in data['questions']:
                cursor.execute(
                    "INSERT INTO questions (content, answer, original_points, current_points, type, question_group, option_a, option_b, option_c, option_d, option_e, option_f, option_g, option_h, option_i, option_j, image_link, content_link) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        question['content'],
                        question['answer'],
                        question['original_points'],
                        question['original_points'],
                        question['type'],
                        question['question_group'],
                        question.get('option_a', None),
                        question.get('option_b', None),
                        question.get('option_c', None),
                        question.get('option_d', None),
                        question.get('option_e', None),
                        question.get('option_f', None),
                        question.get('option_g', None),
                        question.get('option_h', None),
                        question.get('option_i', None),
                        question.get('option_j', None),
                        question.get('image_link', None),
                        question.get('content_link', None)
                    )
                )

            with open('teams.json', 'r') as file:
                data = json.load(file)
                teams_list = data['teams']

            for team in teams_list:
                cursor.execute("INSERT INTO teams (name, password, score, color, attempted_questions, solved_questions) VALUES (?,?,?,?,?,?)",(team, "123", 0, random_color(), 0, 0))

            cursor.execute("""INSERT INTO manual_scores (team_name, q1_score, q2_score, q3_score, q4_score)
            SELECT name, 0, 0, 0, 0 FROM teams
            WHERE name NOT IN (SELECT team_name FROM manual_scores);""")

            conn.commit()
            conn.close()

            
            CURRENT_DB=f"{file.filename}.db"

            return {"status": "success", "message": f"Database {file.filename}.db created successfully!"}
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    else:
        return {"status": "failed", "message": "File Not uploaded"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)