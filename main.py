import logging
import os
import random
import sqlite3
from datetime import datetime
from difflib import SequenceMatcher
from fastapi import FastAPI,UploadFile, Request, HTTPException, status, File, Query, Depends,Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import json

CURRENT_DB="initial.db"

class TeamSignUp(BaseModel):
    name: str
    password: str

class Answer(BaseModel):
    id: str
    answer: str
    team_name: str
    team_password: str

class Admin(BaseModel):
    admin_password: str
    
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

origins = [
    "http://localhost",
    "http://localhost:8080",
    "https://vccfinal.com",
    "https://vccfinal.com:8000",
    "http://172.21.80.1"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
    if s1.isalpha() and s2.isalpha():
        s1 = s1.lower()
        s2 = s2.lower()
    similarity_ratio = SequenceMatcher(None, s1, s2).ratio()
    #if s1 and s2 are strings and not numeric
    return similarity_ratio >= threshold

def get_question(id: str):
    result = execute_db_query("SELECT answer,current_points FROM questions WHERE id = ?", (id, ))
    if not result:
        raise HTTPException(status_code=404, detail="Question not found")
    return result[0]

def get_attempts_count(team_name: str,id: str):
    count = execute_db_query("SELECT COUNT(*) FROM attempted_questions WHERE team_name = ? AND question_id = ?", (team_name, id,))
    return count[0][0]

def decrement_question_points(question_id: int):
    execute_db_query("UPDATE questions SET current_points = current_points - 1 WHERE id = ?", (question_id,))

def reset_question_points():
    execute_db_query("UPDATE questions SET current_points = original_points")

def update_team(name: str, points: int):
    execute_db_query("UPDATE teams SET score = score + ? WHERE name = ?", (points, name))

def update_attempted_questions(name: str, question_id: str, solved: bool):
    execute_db_query(
        f"INSERT INTO attempted_questions VALUES (?, ?, ?, ?)",
        params=(name, question_id, datetime.now(), solved)
    )

@app.get("/get_comp_table")
async def get_comp_table():
    status = execute_db_query(f"""
        SELECT 
            t.name, 
            SUM(a.solved) AS solved_questions,
            COUNT(DISTINCT a.question_id) AS attempted_questions,
            t.score + m.q1_score + m.q2_score + m.q3_score + m.q4_score AS score,
            t.color
        FROM 
            teams t
        LEFT JOIN 
            attempted_questions a ON t.name = a.team_name
        LEFT JOIN
            manual_scores m ON t.name = m.team_name
        GROUP BY 
            t.name
        ORDER BY
            t.score DESC;""")

    teams = [
        {
            "name": row[0],
            "solved_questions": row[1],
            "attempted_questions": row[2],
            "score": row[3],
            "color": row[4]
        } for row in status
    ]
    
    return {"teams": teams}

@app.get("/manual_questions/{admin_password}")
async def manual_questions(admin_password:str):
    if not admin_password:
        return {"status": "failed", "message": "Admin credentials are wrong"}
    if admin_password != "BOSSMAN":
        return {"status": "failed", "message": "Admin credentials are wrong"}
    else:
    
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

@app.get("/questions/{team_name}/{team_password}")
async def get_questions(team_name : str,team_password : str):
    if not team_name or not team_password:
        return False
    result = execute_db_query("SELECT * FROM teams WHERE name = ? and password = ?",(team_name,team_password,))
    if not result:
        return {"status": "failed", "message": "Team credentials are wrong"}
    
    questions = execute_db_query("SELECT * FROM questions")
    teams = execute_db_query("SELECT name FROM teams")
    team_names = [team[0] for team in teams]
    # Dictionary to store transformed questions
    transformed_questions = []
    if team_name in team_names:
        team_score = execute_db_query("SELECT score FROM teams WHERE name = ? ",(team_name,))
        for question in questions:
            # Extracting options from the fetched row (from option_a to option_j)
            options = question[8:18]  # Adjusting indices based on your provided table's structure

            # Filtering out null options
            valid_options = [opt for opt in options if opt is not None]

            # Check attempts for each question for the specified team
            attempt_data = execute_db_query("""
                SELECT COUNT(*), MAX(solved)
                FROM attempted_questions
                WHERE team_name = ? AND question_id = ?
            """, (team_name, question[0],),fetchone=True)

            attempt_count = attempt_data[0]
            solved_status = attempt_data[1]

            # Constructing the question object
            transformed_question = {
                'id': question[0],
                'title':question[1],
                'content': question[2],
                'current_points': question[5],
                'type': question[6],
                'question_group': question[7],
                'options': valid_options,
                'image_link': question[18],
                'content_link': question[19],
                'attempt_count': attempt_count,
                'solved': solved_status,
                'score': team_score
            }

            transformed_questions.append(transformed_question)

        return {"questions": transformed_questions}
    else:
        return {"questions": "Error"}

@app.post("/submit_mcqs_answer")
async def submit_answer_mcqs(a: Answer):
    if not a.team_name or not a.team_password:
        return False
    result = execute_db_query("SELECT * FROM teams WHERE name = ? and password = ?",(a.team_name,a.team_password,))
    if not result:
        return {"status": "failed", "message": "Team credentials are wrong"}
    
    #check if team and question in attempted_questions table if not return error
    existing = execute_db_query("SELECT * FROM attempted_questions WHERE team_name = ? AND question_id = ?", (a.team_name, a.id,), fetchone=True)
    if existing:
        return {"message": "Question already attempted"}
    try:
        correct_ans, question_pts = get_question(id=a.id)
        is_correct = a.answer == correct_ans
        if is_correct:
            update_attempted_questions(name=a.team_name, question_id=a.id, solved=is_correct)
            update_team(name=a.team_name, points=question_pts)
            decrement_question_points(question_id=a.id)
            return {"message": "Correct"}  
        update_attempted_questions(name=a.team_name, question_id=a.id, solved=is_correct)
        return {"message": "Incorrect"}
    
    except Exception as e:
        return {"message":"An error occurred when submitting the answer."}

@app.post("/submit_sa_answer")
async def submit_answer_sa(a: Answer):
    if not a.team_name or not a.team_password:
        return False
    result = execute_db_query("SELECT * FROM teams WHERE name = ? and password = ?",(a.team_name,a.team_password,))
    if not result:
        return {"status": "failed", "message": "Team credentials are wrong"}
    
    try:
        correct_ans, question_pts = get_question(id=a.id)
        attempts_made = get_attempts_count(team_name=a.team_name,id=a.id)
        if attempts_made >= 3:
            return {"message": "No attempts left"}
        is_correct = a.answer == correct_ans or similar(correct_ans, a.answer)
        if is_correct:
            update_team(name=a.team_name, points=question_pts)
            update_attempted_questions(name=a.team_name, question_id=a.id, solved=is_correct)
            decrement_question_points(question_id=a.id)
            return {"message": "Correct"}
        update_attempted_questions(name=a.team_name, question_id=a.id, solved=is_correct)
        if attempts_made < 2: # attempts was already incremented in update_attempted_questions
            return {"message": "Try again"}
        else:
            return {"message": "Incorrect"}
    except Exception as e:
        return {"message":"An error occurred when submitting the answer."}
        

@app.post("/team_signup/")
async def quick_signup(team: TeamSignUp,a: Admin):
    if not a.admin_password:
        return {"status": "failed", "message": "Admin credentials are wrong"}
    if a.admin_password != "BOSSMAN":
        return {"status": "failed", "message": "Admin credentials are wrong"}
    else:
        try:
            team_color = random_color()
            existing_team = execute_db_query("SELECT * FROM teams WHERE name = ? AND password = ?", (team.name,team.password,), fetchone=True)
            if existing_team is not None:
                return {"status":"failed", "message": "Team already exists"}
            
            execute_db_query("INSERT INTO teams (name, password, score, color) VALUES (?, ?, ?, ?)", (team.name,team.password,0,team_color))
            
            execute_db_query("INSERT INTO manual_scores (team_name, q1_score, q2_score, q3_score, q4_score) VALUES (?, ?, ?, ?, ?)",(team.name,0,0,0,0,0))

            return {"status": "success", "message": "Team has been added"}
        
        except Exception as e:   
            return {"status":"failed", "message": "Error occured"}
        
@app.get("/json-files/{admin_password}")
async def list_json_files(admin_password:str):
    if not admin_password:
        return {"status": "failed", "message": "Admin credentials are wrong"}
    if admin_password != "BOSSMAN":
        return {"status": "failed", "message": "Admin credentials are wrong"}
    else:
        try:
            files = [f for f in os.listdir("json") if os.path.isfile(os.path.join("json", f)) and f.endswith(".json")]
            return {"status": "success", "files": files}
        except Exception as e:
            return {"status": "error", "message": str(e)}

   
@app.post("/set_json/")
async def set_json(filename: str,a: Admin):
    global CURRENT_DB
    if not a.admin_password:
        return {"status": "failed", "message": "Admin credentials are wrong"}
    if a.admin_password != "BOSSMAN":
        return {"status": "failed", "message": "Admin credentials are wrong"}
    else:
        if filename:
            CURRENT_DB=f"{filename[:-5]}.db"
            return {"status": "success", "message": "Database updated!"}
        else:
            return {"status": "failed", "message": "Wrong file selected!"}

@app.post("/reset_rankings/")
async def reset_team_data(team_name: str = Query(None, description="The name of the team to reset. If not provided, all teams will be reset."),a: Admin = Body(..., embed=True)):
    try:
        if not a.admin_password:
            return {"status": "failed", "message": "Admin credentials are wrong"}
        if a.admin_password != "BOSSMAN":
            return {"status": "failed", "message": "Admin credentials are wrong"}
        else:
            # Reset stats for a specific team
            if team_name:
                execute_db_query("""
                    UPDATE teams 
                    SET score = 0 
                    WHERE name = ?
                """, (team_name, ))

                execute_db_query("""
                    DELETE FROM attempted_questions
                    WHERE team_name = ?
                """, (team_name, ))

                execute_db_query("""
                    UPDATE manual_scores SET q1_score = 0, q2_score = 0,  q3_score = 0,  q4_score = 0 
                    WHERE team_name = ?
                """, (team_name, ))
            # Reset stats for all teams
            else:
                execute_db_query("""
                    UPDATE teams 
                    SET score = 0 
                """)

                execute_db_query("""
                    DELETE FROM attempted_questions
                """)

                execute_db_query("""
                    UPDATE manual_scores SET q1_score = 0, q2_score = 0,  q3_score = 0,  q4_score = 0
                """)

            if team_name:
                return {"status": "success", "message": f"Data for team '{team_name}' has been reset."}
            else:
                return {"status": "success", "message": "Data for all teams has been reset."}

    except Exception as e:
        return {"status": "failed", "message": "Cannot reset due to an error"}

@app.post("/reset_questions_score/")
async def reset_questions_score(a: Admin):
    try:
        if not a.admin_password:
            return {"status": "failed", "message": "Admin credentials are wrong"}
        if a.admin_password != "BOSSMAN":
            return {"status": "failed", "message": "Admin credentials are wrong"}
        else:
            reset_question_points()
            return {"status": "success", "message": "Questions scores have been reset. "}
    except Exception as e:
        return {"status": "failed", "message": "Cannot reset due to an error"}
    
@app.post("/team_login")
async def team_login(user: Team):
    try:
        result = execute_db_query("SELECT password FROM teams WHERE name=?",(user.team_name,))
        if result and result[0][0]==user.password:

            return {"status": "success", "message": "Logged in successfully"}
        else:
            return {"status": "failed", "message": "No team found with these credentials"}
            
    except Exception as e:
         return {"status": "failed", "message": "Server error"}

@app.post("/admin_login")
async def admin_login(a: Admin):
    if not a.admin_password:
        return {"status": "failed", "message": "Admin credentials are wrong"}
    if a.admin_password != "BOSSMAN":
        return {"status": "failed", "message": "Admin credentials are wrong"}
    else:
        return {"status": "success"}



@app.post("/update_manual_score/")
async def update_manual_score(data: TeamsInput,a: Admin):
    if not a.admin_password:
        return {"status": "failed", "message": "Admin credentials are wrong"}
    if a.admin_password != "BOSSMAN":
        return {"status": "failed", "message": "Admin credentials are wrong"}
    else:
        try:
            for team in data.teams:
                scores = team.scores
                # Check conditions for scores
                if not 0 <= scores.q1_score <= 600:
                    return {"status": "failed", "message": "q1_score out of range for team: " + team.team_name}
                if not 0 <= scores.q2_score <= 600:
                    return {"status": "failed", "message": "q2_score out of range for team: " + team.team_name}
                if not 0 <= scores.q3_score <= 1000:
                    return {"status": "failed", "message": "q3_score out of range for team: " + team.team_name}
                if not -10000 <= scores.q4_score <= 10000:
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


@app.post("/upload/{admin_password}")
async def upload_database(admin_password:str,file: UploadFile = File(...)):
    global CURRENT_DB
    if not admin_password:
        return {"status": "failed", "message": "Admin credentials are wrong"}
    if admin_password != "BOSSMAN":
        return {"status": "failed", "message": "Admin credentials are wrong"}
    else:
        if file:
            try:
                # Ensure it's a JSON file
                if not file.filename.endswith(".json"):
                    return {"status": "error", "message": f"Wrong json format or file uploaded!"}
                    
                file_location = os.path.join("json", file.filename)
                if os.path.exists(file_location):
                    CURRENT_DB = f"{file.filename[0:-5]}.db"
                    return {"status": "error", "message": f"File '{file.filename}' already uploaded!"}
                
                content = file.file.read()
                
                with open(file_location, "wb+") as file_object:
                    file_object.write(content)
                    
                data = json.loads(content)
                CURRENT_DB = f"{file.filename[0:-5]}.db"
                
                # Call create_database function
                create_database(data)

                return {"status": "success", "message": f"Database {file.filename}.db created successfully!"}
            except Exception as e:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        else:
            return {"status": "failed", "message": "File Not uploaded"}


def create_database(data):
    db_file_path = f"{CURRENT_DB}"

    # Delete the database file if it already exists
    if os.path.exists(db_file_path):
        os.remove(db_file_path)
    try:
        conn = sqlite3.connect(db_file_path)
        cursor = conn.cursor()
        
        # Define tables
        teams_table = """
        CREATE TABLE "teams" (
            "name"	TEXT NOT NULL UNIQUE,
            "password"	TEXT NOT NULL,
            "score"	INTEGER DEFAULT 0,
            "color"	TEXT,
            PRIMARY KEY("name")
        );
        """
        questions_table = """
        CREATE TABLE "questions" (
            "id"	INTEGER,
            "title"     TEXT,
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
            FOREIGN KEY("team_name") REFERENCES "teams"("name"),
            FOREIGN KEY("question_id") REFERENCES "questions"("id")
            PRIMARY KEY("team_name", "timestamp")
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

        for question in data['questions']:
            cursor.execute(
                "INSERT INTO questions (content, title, answer, original_points, current_points, type, question_group, option_a, option_b, option_c, option_d, option_e, option_f, option_g, option_h, option_i, option_j, image_link, content_link) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    question['content'],
                    question['title'],
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
        with open('colors.json', 'r') as file:
            data = json.load(file)
            color_list = data["colors"]*5
        for team in teams_list:
            cursor.execute("INSERT INTO teams (name, password, score, color) VALUES (?,?,?,?)",(team["name"], team["password"], 0, color_list.pop(0)))

        cursor.execute("""INSERT INTO manual_scores (team_name, q1_score, q2_score, q3_score, q4_score)
        SELECT name, 0, 0, 0, 0 FROM teams
        WHERE name NOT IN (SELECT team_name FROM manual_scores);""")

        conn.commit()
        conn.close()
    except Exception as e:
        logging.error("An error occurred when creating the database", exc_info=True)
        raise e


if __name__ == "__main__":
    with open('initial.json', 'r') as f:
        initial_data = json.load(f)
    create_database(initial_data)
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)