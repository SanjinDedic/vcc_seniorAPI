# Project Sitemap

## .

[main.py](./main.py)
### ./main.py
```
import os
from difflib import SequenceMatcher
from fastapi import FastAPI,UploadFile, Request, HTTPException, status, File, Query, Depends ,Body
from database import execute_db_query, get_question, get_attempts_count, decrement_question_points, reset_question_points, update_team, update_attempted_questions, create_database, update_questions
from models import Answer, Admin, Team, Score, TeamScores, TeamsInput, ResponseModel
from auth import create_access_token, get_current_user, verify_password, get_password_hash
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import json
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from datetime import datetime, timedelta
from config import ADMIN_PASSWORD, ACCESS_TOKEN_EXPIRE_MINUTES,CURRENT_DIR,CURRENT_DB,BACKUP_DIR

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")


# main.py
@asynccontextmanager
async def lifespan(app: FastAPI):
    with open(os.path.join(CURRENT_DIR, "initial.json"), 'r') as f:
        initial_data = json.load(f)
    teams_json_path = os.path.join(CURRENT_DIR, "teams.json")
    colors_json_path = os.path.join(CURRENT_DIR, "colors.json")
    create_database(initial_data, teams_json_path, colors_json_path)
    yield


app = FastAPI(lifespan=lifespan)

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


def similar(s1, s2, threshold=0.6):
    if s1.isalpha() and s2.isalpha():
        s1 = s1.lower()
        s2 = s2.lower()
    else:
        threshold = 0.75
    similarity_ratio = SequenceMatcher(None, s1, s2).ratio()
    #if s1 and s2 are strings and not numeric
    return similarity_ratio >= threshold

@app.get("/version", response_model=ResponseModel)
async def version():
    return ResponseModel(status="success", message="Version retrieved successfully", data="0.0.1")

@app.get("/get_comp_table", response_model=ResponseModel)
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
    
    return ResponseModel(status="success", message="Teams retrieved successfully", data=teams)

@app.get("/manual_questions", response_model=ResponseModel)
async def manual_questions(current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        return ResponseModel(status="failed", message="Admincredentials are wrong")
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
    
    return ResponseModel(status="success", message="Manual Questions retrieved successfully", data=teams)
    
@app.get("/questions", response_model=ResponseModel)
async def get_questions(current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "student":
        return ResponseModel(status="failed", message="Student credentials are wrong")
    team_name = current_user["team_name"]
    result = execute_db_query("SELECT * FROM teams WHERE name = ?",(team_name,))
    if not result:
        return ResponseModel(status="failed", message="Team credentials are wrong")
    
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

        return ResponseModel(status="success", message="Questions retrieved successfully", data=transformed_questions)
    else:
        return ResponseModel(status="failed", message="Team credentials are wrong")

@app.post("/submit_mcqs_answer", response_model=ResponseModel)
async def submit_answer_mcqs(a: Answer, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "student":
        return ResponseModel(status="failed", message="Student credentials are wrong")  
    team_name = current_user["team_name"]
    result = execute_db_query("SELECT * FROM teams WHERE name = ?",(team_name,))
    if not result:
        return ResponseModel(status="failed", message="Team credentials are wrong")
    
    #check if team and question in attempted_questions table if not return error
    existing = execute_db_query("SELECT * FROM attempted_questions WHERE team_name = ? AND question_id = ?", (team_name, a.id,), fetchone=True)
    if existing:
        return ResponseModel(status="failed", message="Question already attempted")
    try:
        correct_ans, question_pts = get_question(id=a.id)
        is_correct = a.answer == correct_ans
        if is_correct:
            update_attempted_questions(name=team_name, question_id=a.id, solved=is_correct)
            update_team(name=team_name, points=question_pts)
            decrement_question_points(question_id=a.id)
            return ResponseModel(status="success", message="Submission was successful", data="Correct")  
        update_attempted_questions(name=team_name, question_id=a.id, solved=is_correct)
        return ResponseModel(status="success", message="Submission was successful", data="Incorrect")
    
    except Exception as e:
        return ResponseModel(status="failed", message="An error occurred while submitting the answer:"+ str(e))


@app.post("/submit_sa_answer", response_model=ResponseModel)
async def submit_answer_sa(a: Answer, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "student":
        return ResponseModel(status="failed", message="Student credentials are wrong")
    team_name = current_user["team_name"]
    result = execute_db_query("SELECT * FROM teams WHERE name = ?",(team_name,))
    if not result:
        return ResponseModel(status="failed", message="Team credentials are wrong")
    
    try:
        correct_ans, question_pts = get_question(id=a.id)
        attempts_made = get_attempts_count(team_name=team_name,id=a.id)
        if attempts_made >= 3:
            return ResponseModel(status="success", message="Submission was successful", data="No attempts left")
        is_correct = a.answer == correct_ans or similar(correct_ans, a.answer)
        if is_correct:
            update_team(name=team_name, points=question_pts)
            update_attempted_questions(name=team_name, question_id=a.id, solved=is_correct)
            decrement_question_points(question_id=a.id)
            return ResponseModel(status="success", message="Submission was successful", data="Correct")
        
        update_attempted_questions(name=team_name, question_id=a.id, solved=is_correct)
        if attempts_made < 2: # attempts was already incremented in update_attempted_questions
            return ResponseModel(status="success", message="Submission was successful", data="Try again")
        else:
            return ResponseModel(status="success", message="Submission was successful", data="Incorrect")
    except Exception as e:
        return ResponseModel(status="failed", message="An error occurred while submitting the answer:"+ str(e))
        
@app.post("/team_login", response_model=ResponseModel)
async def team_login(user: Team):
    if not user.team_name or  not user.password:
        return ResponseModel(status="failed", message="Team name and password are required")
    try:
        print("Trying to execute database query...")
        result = execute_db_query("SELECT password_hash FROM teams WHERE name=?",(user.team_name,), fetchone=True)
        print("Database query executed.")
        if result is not None:
            print("Result found.")
            hashed_password = result[0]
            if verify_password(user.password, hashed_password):
                print("Password verified.")
                access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
                access_token = create_access_token(
                    data={"sub": user.team_name, "role": "student"}, 
                    expires_delta=access_token_expires
                )
                print("Access token created.")
                return ResponseModel(status="success", message="Login successful", data=access_token)
        print("No team found with the provided credentials.")
        return ResponseModel(status="failed", message="No team found with these credentials")
    except Exception as e:
        print("An exception occurred:", str(e))
        return ResponseModel(status="failed", message=str(e))
            

@app.post("/team_signup", response_model=ResponseModel)
async def quick_signup(team: Team):
    if not team.team_name or  not team.password:
        return ResponseModel(status="failed", message="Team credentials are empty")
    try:
        team_color = "rgb(222,156,223)"
        existing_team = execute_db_query("SELECT password_hash FROM teams WHERE name = ?", (team.team_name,), fetchone=True)
        if existing_team is not None:
            hashed_password = existing_team[0]
            if verify_password(team.password, hashed_password):
                return ResponseModel(status="failed", message="Team already exists")
            
        team_hashed_password = get_password_hash(team.password)

        execute_db_query("INSERT INTO teams (name, password_hash, score, color) VALUES (?, ?, ?, ?)", (team.team_name,team_hashed_password,0,team_color))
        
        
        execute_db_query("INSERT INTO manual_scores (team_name, q1_score, q2_score, q3_score, q4_score) VALUES (?, ?, ?, ?, ?)",(team.team_name,0,0,0,0))

        return ResponseModel(status="success", message="Team has been added")
    
    except Exception as e:   
        return ResponseModel(status="failed", message=str(e))
        
@app.get("/json-files", response_model=ResponseModel)
async def list_json_files(current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        return ResponseModel(status="failed", message="Only admins can reset team data.")
    try:
        json_dir = os.path.join(CURRENT_DIR, "json")
        files = [f for f in os.listdir(json_dir) if os.path.isfile(os.path.join(json_dir, f)) and f.endswith(".json")]
        return ResponseModel(status="success", message="Files retrieved successfully", data=files)
    except Exception as e:
        return ResponseModel(status="failed", message=str(e))

@app.post("/set_json", response_model=ResponseModel)
async def set_json(filename: str,current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        return ResponseModel(status="failed", message="Only admins can reset team data.")
    global CURRENT_DB

    if filename:
        CURRENT_DB=os.path.join(CURRENT_DIR, f"{filename[:-5]}.db")
        return ResponseModel(status="success", message="File set successfully")
    else:
        return ResponseModel(status="failed", message="No filename provided")

@app.post("/reset_rankings", response_model=ResponseModel)
async def reset_team_data(team_name: str = Query(None, description="The name of the team to reset. If not provided, all teams will be reset."), current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        return ResponseModel(status="failed", message="Only admins can reset team data.")
    try:
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
            return ResponseModel(status="success", message=f"Data for team '{team_name}' has been reset.")
        else:
            return ResponseModel(status="success", message="Data for all teams has been reset.")

    except Exception as e:
        return ResponseModel(status="failed", message="Error occured: "+str(e))

@app.post("/reset_questions_score", response_model=ResponseModel)
async def reset_questions_score(current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin" :
        return ResponseModel(status="failed", message="Only admins can reset team data.")
    try:
        reset_question_points()
        return ResponseModel(status="success", message="Questions scores have been reset")
    except Exception as e:
        return ResponseModel(status="failed", message="Error occured: "+str(e))


@app.post("/admin_login", response_model=ResponseModel)
async def admin_login(a: Admin):
    if not a.password:
        return ResponseModel(status="failed", message="Admin credentials are wrong")
    if a.password != ADMIN_PASSWORD:
        return ResponseModel(status="failed", message="Admin credentials are wrong")
    else:
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": "admin", "role": "admin"}, 
            expires_delta=access_token_expires
        )
        return ResponseModel(status="success", message="Login successful", data=access_token)



@app.post("/update_manual_score", response_model=ResponseModel)
async def update_manual_score(data: TeamsInput, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        return ResponseModel(status="failed", message="Only admins can reset team data.")
    try:
        for team in data.teams:
            scores = team.scores
            # Check conditions for scores
            if not 0 <= scores.q1_score <= 600:
                return ResponseModel(status="failed", message="q1_score out of range for team: " + team.team_name)
            if not 0 <= scores.q2_score <= 600:
                return ResponseModel(status="failed", message="q2_score out of range for team: " + team.team_name)
            if not 0 <= scores.q3_score <= 1000:
                return ResponseModel(status="failed", message="q3_score out of range for team: " + team.team_name)
            if not -10000 <= scores.q4_score <= 10000:
                return ResponseModel(status="failed", message="q4_score out of range for team: " + team.team_name)
            
        for team in data.teams:
            team_name = team.team_name
            scores = team.scores
            execute_db_query("""UPDATE manual_scores
                        SET q1_score = ?, q2_score = ?, q3_score = ?, q4_score = ?
                        WHERE team_name = ?""", (scores.q1_score, scores.q2_score, scores.q3_score, scores.q4_score, team_name,))
        
        return ResponseModel(status="success", message="Manual scores have been updated.")
    except Exception as e:
        return ResponseModel(status="failed", message=str(e))


@app.post("/upload", response_model=ResponseModel)
async def upload_database(file: UploadFile = File(None), current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        return ResponseModel(status="failed", message="Only admins can reset team data.")
    global CURRENT_DB
    
    if file:
        try:
            # Ensure it's a JSON file
            if not file.filename.endswith(".json"):
                return ResponseModel(status="failed", message="Wrong file type")
                
            file_location = os.path.join(CURRENT_DIR,"json", file.filename)
            if os.path.exists(file_location):
                CURRENT_DB = os.path.join(CURRENT_DIR, f"{file.filename[0:-5]}.db")
                return ResponseModel(status="failed", message=f"File '{file.filename}' already uploaded!")
            
            content = file.file.read()
            
            with open(file_location, "wb+") as file_object:
                file_object.write(content)
                
            data = json.loads(content)
            CURRENT_DB = os.path.join(CURRENT_DIR, f"{file.filename[0:-5]}.db")
            
            # Call create_database function
            teams_json_path = os.path.join(CURRENT_DIR, "teams.json")
            colors_json_path = os.path.join(CURRENT_DIR, "colors.json")
            create_database(data, teams_json_path, colors_json_path)
            

            return ResponseModel(status="success", message=f"Database {file.filename}.db created successfully!")
        except Exception as e:
            ResponseModel(status="failed", message="Error occured: "+str(e))
    else:
        return ResponseModel(status="failed", message="No file provided")


@app.get("/current_json", response_model=ResponseModel)
async def get_current_json(current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Only admins can access this endpoint.")
    try:
        with open(CURRENT_DIR + "/initial.json", 'r') as f:
            json_data = json.load(f)
        return ResponseModel(status="success", message="Current JSON data retrieved.", data=json_data)
    except FileNotFoundError:
        return ResponseModel(status="failed", message="Current JSON file not found.")
    except Exception as e:
        return ResponseModel(status="failed", message=f"An error occurred: {str(e)}")
    

@app.post("/update_json", response_model=ResponseModel)
async def update_json(new_json: dict = Body(...), current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Only admins can access this endpoint.")
    try:
        # Backup the current JSON with a timestamp
        if os.path.exists(CURRENT_DIR + "/initial.json"):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"backup_{timestamp}.json"
            backup_path = os.path.join(BACKUP_DIR, backup_filename)
            os.rename(CURRENT_DIR + "/initial.json", backup_path)

        # Save the new JSON data
        with open(CURRENT_DIR + "/initial.json", 'w') as f:
            json.dump(new_json, f, indent=4)
        
        updated = update_questions(new_json)
        if not updated:
            return ResponseModel(status="failed", message="Failed to update JSON data.")
        return ResponseModel(status="success", message="JSON data updated successfully.")
    except Exception as e:
        return ResponseModel(status="failed", message=f"An error occurred: {str(e)}")
    
```
[initial.db](./initial.db)
### ./initial.db
```
SQLite format 3   @                                                                     .WJ
ø £ ÞÍ
»£	Û                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         5'')tablemanual_scoresmanual_scoresCREATE TABLE "manual_scores" (
            "team_name"	TEXT UNIQUE,
            "q1_score"	INTEGER,
            "q2_score"	INTEGER,
            "q3_score"	INTEGER,
            "q4_score"  INTEGER,
            FOREIGN KEY("team_name") REFERENCES "teams"("name")
        )9M' indexsqlite_autoindex_manual_scores_1manual_scores"33ktableattempted_questionsattempted_questionsCREATE TABLE "attempted_questions" (
            "team_name"	text,
            "question_id"	INTEGER,
            "timestamp"	datetime,
            "solved"	boolean NOT NULL,
            FOREIGN KEY("team_name") REFERENCES "teams"("name"),
            FOREIGN KEY("question_id") REFERENCES "questions"("id")
            PRIMARY KEY("team_name", "timestamp")
        )EY3 indexsqlite_autoindex_attempted_questions_1attempted_questionsYtablequestionsquestionsCREATE TABLE "questions" (
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
        )l7tableteamsteamsCREATE TABLE "teams" (
            "name"	TEXT NOT NULL UNIQUE,
            "password_hash"	TEXT NOT NULL,
            "score"	INTEGER DEFAULT 0,
            "color"	TEXT,
            PRIMARY KEY("name")
        ))= indexsqlite_autoindex_teams_1teams       

Þ 
' ¥Jï9
'
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 Z-SanjinX$2b$12$oNSP3xCtHQUpY6Awe0EDSeFjcR8hf58Z3stLFFcympWZ3SlItFceq2rgb(159,145,133)Y-NewTeam$2b$12$3o1BsRoO7VWpHzw/TU3HYuFZNReyKHbim7kRaz3yUyQhz1vvUk4Fyrgb(222,156,223)   [                                                                                       Z-Danijela$2b$12$1/HQ8Fl93fhqRRJjsPX62ObdjwZxtjNAN3DUasu40Q2GMG61/k96Orgb(131,208,166)X-Nathan$2b$12$sgcF7s87nPcnxS7kyULz7.bwYJP1E0uepsQXn7NesaNwWEoOm7HcCrgb(249,224,139)Y-Tester3$2b$12$HP/6oqvx.5WjA6vLu1KBn.VMue8bqhxYT/0XQSyBsWy4mblsvneDWrgb(210,224,232)Y-Tester2$2b$12$BP3gfJEYfhP0TyTEOfB10OzrIPwDnnxUcshYsvY6jgkPL0Y3qube6rgb(130,170,234)Y-Tester1$2b$12$K1VfYVNLt6u5Gh2KRaGFd.ka1R4puCnaANSoVZiXdf0I/bLjTn312rgb(171,239,177)
   ­ ÅÒ­¹õéÝ                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       NewTeamSanjinXDanijela
NathanTester3Tester2
	Tester1   ç    ûöñìç                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    
         
   	
    Ø¯]4                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       'ASanjinX2024-10-07 10:33:38.390972'ASanjinX2024-10-07 10:33:38.379856'ASanjinX2024-10-07 10:33:38.367211'ASanjinX2024-10-07 10:33:38.345839'ASanjinX2024-10-07 10:33:38.324092&	A	SanjinX2024-10-07 10:33:38.303840
    Ú³e>                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   &ASanjinX2024-10-07 10:33:38.390972&ASanjinX2024-10-07 10:33:38.379856&ASanjinX2024-10-07 10:33:38.367211&ASanjinX2024-10-07 10:33:38.345839&ASanjinX2024-10-07 10:33:38.324092%A	SanjinX2024-10-07 10:33:38.303840
Ó  ðâÄµ¦                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           SanjinXd È,
NewTeam
Tester3
Tester2
Tester1              NathanDanijela
   ­ ôé­ÝÑÅ¹                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       NewTeamTester3Tester2Tester1SanjinX
Nathan	Danijela
   ) Þ
È
)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   \ G9997;9A   

Introcing the Lambda Function```python
# Define a simple lambda function to square a number
square = lambda x: x ** 2

# Use the lambda function
result = square(5)
print(f"The square of 5 is: {result}")
```

What is the output of this program?bmcqsThe square of 5 is: 10The square of 5 is: 25The square of 5 is: 5The square of 5 is: 125An error occurs because lambda functions are not allowed in PythonThe square of 5 is: 52The program prints nothing| '    

Ready Set Go!
```python
set1 = {1, 2, 3, 4, 5}
set2 = {4, 5, 6, 7, 8}

# Perform set operations
union_set = set1.union(set2)
intersection_set = set1.intersection(set2)
difference_set = set1.difference(set2)

result = len(union_set) + len(intersection_set) + len(difference_set)

print(result)
```

What will be the output of this program?a22mcqs131415161718~ 1y[ye!y-   

Stringing me along
```python
text = "Python programming is fun and educational"

words = text.lower().split()

long_words = []
for word in words:
    if len(word) > 5:
        long_words.append(word)

print(long_words)
```

What will be the output of this program?b22mcqs```python
['python', 'programming']
``````python
['python', 'programming', 'educational']
``````python
['python', 'programming', 'fun', 'educational']
``````python
['programming', 'educational']
``````python
['python', 'programming', 'is', 'fun', 'and', 'educational']
``````python
['PYTHON', 'PROGRAMMING', 'EDUCATIONAL']
``````python
[]
```y [uu[I   

Just looking up fruits in my Dictionary
```python
fruit_basket = {'apple': 3, 'banana': 2, 'orange': 4, 'pear': 1}

fruit_basket['banana'] += 2
fruit_basket.pop('pear')

print(fruit_basket)
```

What will be the output of this program?c22mcqs```python
{'apple': 3, 'banana': 2, 'orange': 4}
``````python
{'apple': 3, 'banana': 4, 'orange': 4, 'pear': 1}
``````python
{'apple': 3, 'banana': 4, 'orange': 4}
``````python
{'apple': 3, 'banana': 2, 'orange': 4, 'pear': 1}
``````python
{'apple': 3, 'orange': 4}
``````python
{'apple': 3, 'banana': 4, 'orange': 4, 'pear': None}
``````python
KeyError: 'pear'
```A Ge'    

The condition of my conditionWhat will this python program print?

```python
x, y, z = 10, 10, 5

if x > y and y > z:
    print('A')
elif x >= y and y > z:
    print('B')
elif x == y and y != z:
    print('C')
elif x + y > z:
    print('D')
else:
    print('E')
```b22mcqsABCDB,C and DB, C, D and E 1Q+7    

Whoa, what's this?
```python
import turtle

t = turtle.Turtle()

for i in range(36):
    t.forward(10)
    t.circle(100)
    t.right(10)
```

Predict the shape drawn by the turtle:f22mcqsA single circleA squareA flower-like patternA spiralA starA donut )	!!!     

Turtle Polygon
```python
import turtle

t = turtle.Turtle()

for i in range(6):
    t.backward(100)
    t.right(60)

# What shape will be drawn by this turtle program?
```

Predict the shape drawn by the turtle:b21mcqsA squareA hexagonA pentagonAn octagonA triangle
   Þ 
Þ                                                                                                                                                                                                                                                                                                                                                                                                                                                                              7 #okmw     

Weather API
```python
import requests

api_key = "your_api_key"
city = "London"
url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"

response = requests.get(url)
data = response.json()

temperature = data['main']['temp']

if temperature < 10:
    print(f"It's cold in {city} with {temperature}Â°C")
elif 10 <= temperature < 20:
    print(f"It's mild in {city} with {temperature}Â°C")
else:
    print(f"It's warm in {city} with {temperature}Â°C")
```

What does this API call and code do?bKKmcqsPrints the current weather description for LondonCategorizes and prints London's temperature as cold, mild, or warmDisplays the wind speed and direction in LondonShows the probability of precipitation in LondonRetrieves and prints the air quality index for Londonl
 eEA)s[k)   

Python Decorators: The Russian Doll Function```python
def babushka_doll(matryoshka):
    def wrapper():
        print('Opening the outer doll...')
        matryoshka()
        print('Closing the outer doll...')
    return wrapper

def tiny_doll():
    print('Surprise! Tiny doll found!')

tiny_doll = babushka_doll(tiny_doll)
tiny_doll()
```

What is the output of this Russian doll function?b22mcqs
Surprise! Tiny doll found!Opening the outer doll...
Surprise! Tiny doll found!
Closing the outer doll...Opening the outer doll...
Closing the outer doll...An error occurs: too many nested dolls!None (The dolls are too tightly nested to open)Opening the outer doll...
Opening the middle doll...
Surprise! Tiny doll found!
Closing the middle doll...
Closing the outer doll...Surprise! Tiny doll found!
Opening the outer doll...
Closing the outer doll...	 WOu{}/    

List Comprehension Math Comprehension
```python
numbers = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

result = [n**2 for n in numbers if n % 2 == 0]

print(result)
```

What will be the output of this program?b22mcqs	Every second number between 1 and 10: 2, 4, 6, . . .Squares of even numbers between 1 and 10: 4, 16, 36, . . .Squares of all numbers between 1 and 10: 1, 4, 9, . . .Double of even numbers between 1 and 10: 4, 8, 12, . . .Cubes of even numbers between 1 and 10: 8, 64, 216, . . .An empty list: []g 5+owwo)soO  

Elf Height Converter```python
def elf_height_converter(conversion_factor):
    return lambda in_: round(in_ * conversion_factor, 1)

elf_to_human = elf_height_converter(1.5)
elf_to_dwarf = elf_height_converter(0.8)

print(f"An elf who is 40 in tall would be {elf_to_human(40)} in tall as a human.")
print(f"An elf who is 40 in tall would be {elf_to_dwarf(40)} in tall as a dwarf.")
```

What is the output of this program?

Read more about Python lambda functions here: [Python Lambda Functions](https://www.w3schools.com/python/python_lambda.asp)c22mcqsAn elf who is 40 in tall would be 60 in tall as a human.
An elf who is 40 in tall would be 32 in tall as a dwarf.An elf who is 40 in tall would be 60.0 in tall as a human.
An elf who is 40 in tall would be 32.0 in tall as a dwarf.An elf who is 40 in tall would be 60.0 in tall as a human.
An elf who is 40 in tall would be 32.0 in tall as a dwarf.An elf who is 40 in tall would be 60 in tall as a human.
An elf who is 40 in tall would be 32 in tall as a dwarf.An error occurs because lambda functions can't be used inside other functions.An elf who is 40 in tall would be 1.5 in tall as a human.
An elf who is 40 in tall would be 0.8 in tall as a dwarf.An elf who is 40 in tall would be 40 in tall as a human.
An elf who is 40 in tall would be 40 in tall as a dwarf.elf_to_human(40)
elf_to_dwarf(40)
    Àe                                                                                                                                                                                                                                                                               m C/%          
ABabies with High AllowancesFrom the 'boss_baby_corp.json' file, determine how many babies have an allowance above 85 baby bucks per week. Provide the number of such babies.29ddshort answer/files/boss_baby_corp.jsonS 1O  
IText File AnalysisAnalyze the provided text file 'pride_and_prejudice.txt' (contents of 'Pride and Prejudice' by Jane Austen) and determine the top 5 most frequent words (excluding the 10 most common stop words provided below). What is the 3rd most frequent word?

Here's some starter code to help you read the file and exclude the stop words:

```python
# List of 10 most common stop words to exclude
stop_words = ['the', 'and', 'to', 'of', 'a', 'in', 'that', 'is', 'was', 'it']

# Place the file in the same folder as your python program 
# Then open the file with UTF-8 encoding
with open('pride_and_prejudice.txt', 'r', encoding='utf-8') as file:
    text = file.read().lower()

# Print the first 500 characters to verify the content
print(text[:500])h  mcqsielizabethbennetdarcynotveryhershe/files/pride_and_prejudice.txtX
 1I%          

The Coin ConundrumGiven a set of coin denominations [1, 5, 10, 25, 50] and a target amount of 7654 cents, write a Python program to find the minimum number of coins needed to make up that amount. What is this minimum number?

Hint: Greed has something to do with the  best method of solving this problem.157ddshort answer
= +	?
-W  

Random User API
```python
import requests
from datetime import datetime
import pytz

url = "https://api.randomuser.me/"

response = requests.get(url)
data = response.json()

user = data['results'][0]
name = f"{user['name']['first']} {user['name']['last']}"
timezone = user['location']['timezone']['offset']
password = user['login']['password']

def get_greeting(timezone):
    offset = int(timezone.split(':')[0])
    user_time = datetime.now(pytz.FixedOffset(offset * 60))
    hour = user_time.hour
    if 5 <= hour < 12:
        return "Good morning"
    elif 12 <= hour < 18:
        return "Good afternoon"
    elif 18 <= hour < 22:
        return "Good evening"
    else:
        return "What are you doing up at this time of night"

def get_password_score(password):
    score = 0
    if len(password) >= 8:
        score += 2
    if any(c.isupper() for c in password):
        score += 2
    if any(c.islower() for c in password):
        score += 2
    if any(c.isdigit() for c in password):
        score += 2
    if any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in password):
        score += 2
    return score

password_score = get_password_score(password)
greeting = get_greeting(timezone)

message = f"{greeting}, {name}! I am your site's Cyber bot, and I will provide you a score out of 10 for your password complexity."
message += f"\nYour password score is: {password_score}/10. "

if password_score >= 8:
    message += "Your password is strong, congratulations!"
elif 5 <= password_score < 8:
    message += "You should consider changing your password."
else:
    message += "You need to change your password immediately."

print(message)
```

What does this code do?cKKmcqsCreates a playlist based on a user's timezone and password strengthGenerates a random social media profile with a secure passwordGenerates a custom greeting based on timezone and provides a password strength assessmentRecommends a new password based on user's current passwordSuggests a trending cybersecurity topic for the user to researchAnalyzes the user's password and provides a detailed breakdown of its weaknessesGenerates a greeting based on the user's location and checks if their password has been compromised in known data breachesCreates a personalized cybersecurity report including the user's IP address and recent login attempts
   8 Ñ
h
l»Û8                                                                                                                                                                                                                                                                                                G ;{5%          

The Light Bulb SequenceYou have a row of 5 light bulbs, all initially turned off. Every day for 10 days, you perform the following operation:
- For each bulb (from left to right), if the current day number plus the bulb's position (1-5) is divisible by 3, toggle that bulb's state.

Question: What is the state of each light bulb (on or off) after 10 days? 

*(ANSWER FORMAT: On, Off, On, Off, On)*Off, On, On, Off, Onddshort answerV UIkgggi     
1Counting Text Files in a Zip ArchiveYou are provided with a zip file containing over 200 subfolders and more than 50 text files. Your task is to determine:

1. How many text files are in the zip file?
2. How many of these text files are not empty?

You can use any method, such as writing a program or manual inspection, to find the answers.

*Hint:* You might find [this tutorial](https://www.tutorialspoint.com/file-searching-using-python) helpful.cddmcqsTotal text files: 250
Non-empty text files: 200Total text files: 50
Non-empty text files: 25Total text files: 60
Non-empty text files: 42Total text files: 72
Non-empty text files: 60Total text files: 100
Non-empty text files: 50/files/archive.zip] Su#%          
9400 colours but one shines the mostAn image `color_patch.png` has been provided. This image contains a 20x20 grid of randomly colored pixels.

![Color Patch](/files/color_patch.png)

Your task is to determine the brightest color in the above color patch. The brightness of a color is defined as the maximum value among its R, G, and B components. Provide your answer as three integers separated by commas (R,G,B) representing the brightest color found in the image.

To complete this task, you'll need to analyze the RGB values of each pixel in the image. You will need to search the web for information on how to get RGB values for individual pixels using Python243,255,235ddshort answer/files/color_patch.png. 51%          
IBitcoin TrillionaireThe program below is a simplified bitcoin exchange simulator.

If you select the **buy** option, you will be asked to enter a $ value of how much bitcoin to buy. What input can you enter to guarantee a balance of $1,000,000,000,000 (one trillion dollars) or more?

[HINT: READ THIS](https://docs.python.org/3/library/functions.html#float)inf  short answer/files/bitcoin_trillionaire.py Oa-%          
;Most Transactions Between PlayersUsing the CSV file of play money transfers among eight friends, identify all pairs of players who had the highest number of transactions between them (regardless of direction). Then provide the names of the 2 players with the most transactions (in alphabetical order so for example: Alice and Bob).Helena and Mehdiddshort answer/files/transactions.csv_ -
3%          
;Top Money SenderFrom the CSV file recording play money transfers among eight friends, determine which player sent the highest total amount of money. Then, calculate *to two decimal places* the total amount of money that this player sent. (ANSWER FORMAT: 'Bob sent 100.52')Helena sent 6302.87ddshort answer/files/transactions.csvf _{%          
AWhich Department has the Most Baby Bucks?Using the 'boss_baby_corp.json' file, calculate the average baby buck allowance for each department. List the top 3 departments in order from highest average allowance to lowest, separated by commas.Playtime Strategy, Formula Development, Diaper Researchddshort answer/files/boss_baby_corp.json, 5m_%          
AThe Baby Buck MogulsWrite down the first names in alphabetical order, separated by commas, of the highest baby buck-earning baby in each department. You can find the data in 'boss_baby_corp.json'.Deborah, Jeffrey, Joseph, Melissa, Ronaldddshort answer/files/boss_baby_corp.json
   È 
È                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            S 7©?!  

The Prisoner's EscapeIn a prison, there are 8 prisoners (numbered 0-7) and 8 doors (numbered 0-7). Each door leads to freedom for a specific prisoner. The doors are randomly shuffled each day. The escape attempt follows these rules:

1. Each prisoner is allowed to open up to 5 doors.
2. If all prisoners find their exit door, they all escape. If even one fails, they all stay in prison.
3. If a prisoner's number matches their exit door number, that door becomes permanently locked, reducing the available doors for the subsequent prisoners.
4. The prisoners attempt to escape in order, from prisoner 0 to prisoner 7.

Your task is to implement the `prisoner_strategy` function to maximize the probability of all prisoners escaping.

Question: What is the approximate probability of all prisoners escaping with your implemented strategy?

Implement your strategy in the provided Python code and run the simulation to find the probability.

```python
import random

def prisoner_strategy(prisoner_number, available_doors):
    """
    Implement the strategy for a single prisoner trying to escape.
    
    :param prisoner_number: The number of the current prisoner (0-7)
    :param available_doors: A set of door numbers that are still available
    :return: A list of door numbers the prisoner will try (max 5)
    """
    # TODO: Implement your strategy here
    # Remember: 
    # - You can try up to 5 doors
    # - available_doors is a set of integers representing available door numbers
    # - Return a list of door numbers to try (must be a subset of available_doors)
    pass

def simulate_prison_escape(simulations=100000):
    success_count = 0

    for _ in range(simulations):
        exit_doors = list(range(8))
        random.shuffle(exit_doors)
        available_doors = set(range(8))
        all_prisoners_succeeded = True

        for prisoner_number in range(8):
            doors_to_try = prisoner_strategy(prisoner_number, available_doors)
            
            if len(doors_to_try) > 5 or not set(doors_to_try).issubset(available_doors):
                raise ValueError("Invalid strategy: too many doors or unavailable doors selected")

            if exit_doors[prisoner_number] in doors_to_try:
                if exit_doors[prisoner_number] == prisoner_number:
                    available_doors.discard(prisoner_number)
            else:
                all_prisoners_succeeded = False
                break

        if all_prisoners_succeeded:
            success_count += 1

    probability = success_count / simulations
    print(f"The approximate probability of all prisoners escaping is: {probability}")

simulate_prison_escape()
```cddmcqsAbout 0.1%About 1%About 6%About 11%About 16%About 19%About 23%About 38%_ =O%          

The Semi-Perfect ShuffleYou have 9 cards numbered 1 to 9, in order. You perform a "semi-perfect shuffle" where you split the deck into two unequal halves (4 on the left and 5 on the right) and then interleave them perfectly, with the right half (bottom) going first. For example, after one shuffle, the order would be: 5, 1, 6, 2, 7, 3, 8, 4, 9.

Question: How many shuffles does it take to return the cards to their original order?

You can approach this problem through logical reasoning or by implementing your own simulation. Explain your method and show your work.6ddshort answer
   	Á 	Á                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       < ;MMMMMMM[   

The Dice Reroll DilemmaYou're playing a game where you roll three six-sided dice. After seeing the result, you have an option to reroll 1,2 or all 3 dice. 
You win if your final sum is higher than the sum of three dice rolled by the house.

Consider two strategies:
A) Keep your current roll if the total is more than 10, reroll all dice otherwise.
B) Keep the highest die rolled and reroll the other two.

Question: Which strategy gives you a better chance of winning? By approximately how much?

You can use the provided Python starter code to implement and test these strategies, or work it out mathematically. Can you think of an even better strategy?

```python
import random

def play_dice_game(strategy, n_games=10000):
    wins = 0
    for _ in range(n_games):
        dice = [random.randint(1, 6) for _ in range(3)]
        if strategy(dice):
            wins += 1
    return wins

def strategy_reroll_if_not_above_10(dice):
    # Implement the strategy
    pass

def strategy_keep_highest(dice):
    # Implement the strategy
    pass

# Example usage
n_games = 10000
strategy_a_wins = play_dice_game(strategy_reroll_if_not_above_10, n_games)
strategy_b_wins = play_dice_game(strategy_keep_highest, n_games)

print(f"Strategy A wins: {strategy_a_wins/n_games:.2%}")
print(f"Strategy B wins: {strategy_b_wins/n_games:.2%}")
```bddmcqsStrategy A is better by about 2%Strategy B is better by about 2%Strategy A is better by about 5%Strategy B is better by about 5%Strategy A is better by about 9%Strategy B is better by about 9%Both strategies are approximately equal
```
[models.py](./models.py)
### ./models.py
```
from pydantic import BaseModel
from typing import List, Optional, Any

class Answer(BaseModel):
    id: str
    answer: str

class Admin(BaseModel):
    name: str
    password: str

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

class ResponseModel(BaseModel):
    status: str
    message: str
    data: Optional[Any] = None
```
[initial.json](./initial.json)
### ./initial.json
```
{
  "questions": [
    {
      "title": "Turtle Polygon",
      "content": "\n```python\nimport turtle\n\nt = turtle.Turtle()\n\nfor i in range(6):\n    t.backward(100)\n    t.right(60)\n\n# What shape will be drawn by this turtle program?\n```\n\nPredict the shape drawn by the turtle:",
      "answer": "b",
      "original_points": 50,
      "type": "mcqs",
      "question_group": 1,
      "option_a": "A square",
      "option_b": "A hexagon",
      "option_c": "A pentagon",
      "option_d": "An octagon",
      "option_e": "A triangle",
      "image_link": "",
      "content_link": ""
    },
    {
      "title": "Whoa, what's this?",
      "content": "\n```python\nimport turtle\n\nt = turtle.Turtle()\n\nfor i in range(36):\n    t.forward(10)\n    t.circle(100)\n    t.right(10)\n```\n\nPredict the shape drawn by the turtle:",
      "answer": "f",
      "original_points": 50,
      "type": "mcqs",
      "question_group": 2,
      "option_a": "A single circle",
      "option_b": "A square",
      "option_c": "A flower-like pattern",
      "option_d": "A spiral",
      "option_e": "A star",
      "option_f": "A donut",
      "image_link": "",
      "content_link": ""
    },
    {
      "title": "The condition of my condition",
      "content": "What will this python program print?\n\n```python\nx, y, z = 10, 10, 5\n\nif x > y and y > z:\n    print('A')\nelif x >= y and y > z:\n    print('B')\nelif x == y and y != z:\n    print('C')\nelif x + y > z:\n    print('D')\nelse:\n    print('E')\n```",
      "answer": "b",
      "original_points": 50,
      "type": "mcqs",
      "question_group": 3,
      "option_a": "A",
      "option_b": "B",
      "option_c": "C",
      "option_d": "D",
      "option_e": "B,C and D",
      "option_f": "B, C, D and E",
      "image_link": "",
      "content_link": ""
    },
    {
      "title": "Just looking up fruits in my Dictionary",
      "content": "\n```python\nfruit_basket = {'apple': 3, 'banana': 2, 'orange': 4, 'pear': 1}\n\nfruit_basket['banana'] += 2\nfruit_basket.pop('pear')\n\nprint(fruit_basket)\n```\n\nWhat will be the output of this program?",
      "answer": "c",
      "original_points": 50,
      "type": "mcqs",
      "question_group": 4,
      "option_a": "```python\n{'apple': 3, 'banana': 2, 'orange': 4}\n```",
      "option_b": "```python\n{'apple': 3, 'banana': 4, 'orange': 4, 'pear': 1}\n```",
      "option_c": "```python\n{'apple': 3, 'banana': 4, 'orange': 4}\n```",
      "option_d": "```python\n{'apple': 3, 'banana': 2, 'orange': 4, 'pear': 1}\n```",
      "option_e": "```python\n{'apple': 3, 'orange': 4}\n```",
      "option_f": "```python\n{'apple': 3, 'banana': 4, 'orange': 4, 'pear': None}\n```",
      "option_g": "```python\nKeyError: 'pear'\n```",
      "image_link": "",
      "content_link": ""
    },
    {
      "title": "Stringing me along",
      "content": "\n```python\ntext = \"Python programming is fun and educational\"\n\nwords = text.lower().split()\n\nlong_words = []\nfor word in words:\n    if len(word) > 5:\n        long_words.append(word)\n\nprint(long_words)\n```\n\nWhat will be the output of this program?",
      "answer": "b",
      "original_points": 50,
      "type": "mcqs",
      "question_group": 5,
      "option_a": "```python\n['python', 'programming']\n```",
      "option_b": "```python\n['python', 'programming', 'educational']\n```",
      "option_c": "```python\n['python', 'programming', 'fun', 'educational']\n```",
      "option_d": "```python\n['programming', 'educational']\n```",
      "option_e": "```python\n['python', 'programming', 'is', 'fun', 'and', 'educational']\n```",
      "option_f": "```python\n['PYTHON', 'PROGRAMMING', 'EDUCATIONAL']\n```",
      "option_g": "```python\n[]\n```",
      "image_link": "",
      "content_link": ""
    },
    {
      "title": "Ready Set Go!",
      "content": "\n```python\nset1 = {1, 2, 3, 4, 5}\nset2 = {4, 5, 6, 7, 8}\n\n# Perform set operations\nunion_set = set1.union(set2)\nintersection_set = set1.intersection(set2)\ndifference_set = set1.difference(set2)\n\nresult = len(union_set) + len(intersection_set) + len(difference_set)\n\nprint(result)\n```\n\nWhat will be the output of this program?",
      "answer": "a",
      "original_points": 50,
      "type": "mcqs",
      "question_group": 6,
      "option_a": "13",
      "option_b": "14",
      "option_c": "15",
      "option_d": "16",
      "option_e": "17",
      "option_f": "18",
      "image_link": "",
      "content_link": ""
    },
    {
      "title": "Introcing the Lambda Function",
      "content": "```python\n# Define a simple lambda function to square a number\nsquare = lambda x: x ** 2\n\n# Use the lambda function\nresult = square(5)\nprint(f\"The square of 5 is: {result}\")\n```\n\nWhat is the output of this program?",
      "answer": "b",
      "original_points": 30,
      "type": "mcqs",
      "question_group": 7,
      "option_a": "The square of 5 is: 10",
      "option_b": "The square of 5 is: 25",
      "option_c": "The square of 5 is: 5",
      "option_d": "The square of 5 is: 125",
      "option_e": "An error occurs because lambda functions are not allowed in Python",
      "option_f": "The square of 5 is: 52",
      "option_g": "The program prints nothing",
      "image_link": "",
      "content_link": ""
    },
    {
      "title": "Elf Height Converter",
      "content": "```python\ndef elf_height_converter(conversion_factor):\n    return lambda in_: round(in_ * conversion_factor, 1)\n\nelf_to_human = elf_height_converter(1.5)\nelf_to_dwarf = elf_height_converter(0.8)\n\nprint(f\"An elf who is 40 in tall would be {elf_to_human(40)} in tall as a human.\")\nprint(f\"An elf who is 40 in tall would be {elf_to_dwarf(40)} in tall as a dwarf.\")\n```\n\nWhat is the output of this program?\n\nRead more about Python lambda functions here: [Python Lambda Functions](https://www.w3schools.com/python/python_lambda.asp)",
      "answer": "c",
      "original_points": 50,
      "type": "mcqs",
      "question_group": 8,
      "option_a": "An elf who is 40 in tall would be 60 in tall as a human.\nAn elf who is 40 in tall would be 32 in tall as a dwarf.",
      "option_b": "An elf who is 40 in tall would be 60.0 in tall as a human.\nAn elf who is 40 in tall would be 32.0 in tall as a dwarf.",
      "option_c": "An elf who is 40 in tall would be 60.0 in tall as a human.\nAn elf who is 40 in tall would be 32.0 in tall as a dwarf.",
      "option_d": "An elf who is 40 in tall would be 60 in tall as a human.\nAn elf who is 40 in tall would be 32 in tall as a dwarf.",
      "option_e": "An error occurs because lambda functions can't be used inside other functions.",
      "option_f": "An elf who is 40 in tall would be 1.5 in tall as a human.\nAn elf who is 40 in tall would be 0.8 in tall as a dwarf.",
      "option_g": "An elf who is 40 in tall would be 40 in tall as a human.\nAn elf who is 40 in tall would be 40 in tall as a dwarf.",
      "option_h": "elf_to_human(40)\nelf_to_dwarf(40)",
      "image_link": "",
      "content_link": ""
    },
    {
      "title": "List Comprehension Math Comprehension",
      "content": "\n```python\nnumbers = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]\n\nresult = [n**2 for n in numbers if n % 2 == 0]\n\nprint(result)\n```\n\nWhat will be the output of this program?",
      "answer": "b",
      "original_points": 50,
      "type": "mcqs",
      "question_group": 9,
      "option_a": "Every second number between 1 and 10: 2, 4, 6, . . .",
      "option_b": "Squares of even numbers between 1 and 10: 4, 16, 36, . . .",
      "option_c": "Squares of all numbers between 1 and 10: 1, 4, 9, . . .",
      "option_d": "Double of even numbers between 1 and 10: 4, 8, 12, . . .",
      "option_e": "Cubes of even numbers between 1 and 10: 8, 64, 216, . . .",
      "option_f": "An empty list: []",
      "image_link": "",
      "content_link": ""
    },
    {
      "title": "Python Decorators: The Russian Doll Function",
      "content": "```python\ndef babushka_doll(matryoshka):\n    def wrapper():\n        print('Opening the outer doll...')\n        matryoshka()\n        print('Closing the outer doll...')\n    return wrapper\n\ndef tiny_doll():\n    print('Surprise! Tiny doll found!')\n\ntiny_doll = babushka_doll(tiny_doll)\ntiny_doll()\n```\n\nWhat is the output of this Russian doll function?",
      "answer": "b",
      "original_points": 50,
      "type": "mcqs",
      "question_group": 10,
      "option_a": "Surprise! Tiny doll found!",
      "option_b": "Opening the outer doll...\nSurprise! Tiny doll found!\nClosing the outer doll...",
      "option_c": "Opening the outer doll...\nClosing the outer doll...",
      "option_d": "An error occurs: too many nested dolls!",
      "option_e": "None (The dolls are too tightly nested to open)",
      "option_f": "Opening the outer doll...\nOpening the middle doll...\nSurprise! Tiny doll found!\nClosing the middle doll...\nClosing the outer doll...",
      "option_g": "Surprise! Tiny doll found!\nOpening the outer doll...\nClosing the outer doll...",
      "image_link": "",
      "content_link": ""
    },
    {
      "title": "Weather API",
      "content": "\n```python\nimport requests\n\napi_key = \"your_api_key\"\ncity = \"London\"\nurl = f\"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric\"\n\nresponse = requests.get(url)\ndata = response.json()\n\ntemperature = data['main']['temp']\n\nif temperature < 10:\n    print(f\"It's cold in {city} with {temperature}°C\")\nelif 10 <= temperature < 20:\n    print(f\"It's mild in {city} with {temperature}°C\")\nelse:\n    print(f\"It's warm in {city} with {temperature}°C\")\n```\n\nWhat does this API call and code do?",
      "answer": "b",
      "original_points": 75,
      "type": "mcqs",
      "question_group": 11,
      "option_a": "Prints the current weather description for London",
      "option_b": "Categorizes and prints London's temperature as cold, mild, or warm",
      "option_c": "Displays the wind speed and direction in London",
      "option_d": "Shows the probability of precipitation in London",
      "option_e": "Retrieves and prints the air quality index for London",
      "image_link": "",
      "content_link": ""
    },
    {
      "title": "Random User API",
      "content": "\n```python\nimport requests\nfrom datetime import datetime\nimport pytz\n\nurl = \"https://api.randomuser.me/\"\n\nresponse = requests.get(url)\ndata = response.json()\n\nuser = data['results'][0]\nname = f\"{user['name']['first']} {user['name']['last']}\"\ntimezone = user['location']['timezone']['offset']\npassword = user['login']['password']\n\ndef get_greeting(timezone):\n    offset = int(timezone.split(':')[0])\n    user_time = datetime.now(pytz.FixedOffset(offset * 60))\n    hour = user_time.hour\n    if 5 <= hour < 12:\n        return \"Good morning\"\n    elif 12 <= hour < 18:\n        return \"Good afternoon\"\n    elif 18 <= hour < 22:\n        return \"Good evening\"\n    else:\n        return \"What are you doing up at this time of night\"\n\ndef get_password_score(password):\n    score = 0\n    if len(password) >= 8:\n        score += 2\n    if any(c.isupper() for c in password):\n        score += 2\n    if any(c.islower() for c in password):\n        score += 2\n    if any(c.isdigit() for c in password):\n        score += 2\n    if any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in password):\n        score += 2\n    return score\n\npassword_score = get_password_score(password)\ngreeting = get_greeting(timezone)\n\nmessage = f\"{greeting}, {name}! I am your site's Cyber bot, and I will provide you a score out of 10 for your password complexity.\"\nmessage += f\"\\nYour password score is: {password_score}/10. \"\n\nif password_score >= 8:\n    message += \"Your password is strong, congratulations!\"\nelif 5 <= password_score < 8:\n    message += \"You should consider changing your password.\"\nelse:\n    message += \"You need to change your password immediately.\"\n\nprint(message)\n```\n\nWhat does this code do?",
      "answer": "c",
      "original_points": 75,
      "type": "mcqs",
      "question_group": 12,
      "option_a": "Creates a playlist based on a user's timezone and password strength",
      "option_b": "Generates a random social media profile with a secure password",
      "option_c": "Generates a custom greeting based on timezone and provides a password strength assessment",
      "option_d": "Recommends a new password based on user's current password",
      "option_e": "Suggests a trending cybersecurity topic for the user to research",
      "option_f": "Analyzes the user's password and provides a detailed breakdown of its weaknesses",
      "option_g": "Generates a greeting based on the user's location and checks if their password has been compromised in known data breaches",
      "option_h": "Creates a personalized cybersecurity report including the user's IP address and recent login attempts",
      "image_link": "",
      "content_link": ""
    },
    {
      "title": "The Coin Conundrum",
      "content": "Given a set of coin denominations [1, 5, 10, 25, 50] and a target amount of 7654 cents, write a Python program to find the minimum number of coins needed to make up that amount. What is this minimum number?\n\nHint: Greed has something to do with the  best method of solving this problem.",
      "answer": "157",
      "original_points": 100,
      "type": "short answer",
      "question_group": 13,
      "image_link": "",
      "content_link": ""
    },
    {
      "title": "Text File Analysis",
      "content": "Analyze the provided text file 'pride_and_prejudice.txt' (contents of 'Pride and Prejudice' by Jane Austen) and determine the top 5 most frequent words (excluding the 10 most common stop words provided below). What is the 3rd most frequent word?\n\nHere's some starter code to help you read the file and exclude the stop words:\n\n```python\n# List of 10 most common stop words to exclude\nstop_words = ['the', 'and', 'to', 'of', 'a', 'in', 'that', 'is', 'was', 'it']\n\n# Place the file in the same folder as your python program \n# Then open the file with UTF-8 encoding\nwith open('pride_and_prejudice.txt', 'r', encoding='utf-8') as file:\n    text = file.read().lower()\n\n# Print the first 500 characters to verify the content\nprint(text[:500])",
      "answer": "h",
      "original_points": 150,
      "type": "mcqs",
      "question_group": 14,
      "option_a": "i",
      "option_b": "elizabeth",
      "option_c": "bennet",
      "option_d": "darcy",
      "option_e": "not",
      "option_f": "very",
      "option_g": "her",
      "option_h": "she",
      "image_link": "",
      "content_link": "/files/pride_and_prejudice.txt"
    },
    {
      "title": "Babies with High Allowances",
      "content": "From the 'boss_baby_corp.json' file, determine how many babies have an allowance above 85 baby bucks per week. Provide the number of such babies.",
      "answer": "29",
      "original_points": 100,
      "type": "short answer",
      "question_group": 15,
      "image_link": "",
      "content_link": "/files/boss_baby_corp.json"
    },
    {
      "title": "The Baby Buck Moguls",
      "content": "Write down the first names in alphabetical order, separated by commas, of the highest baby buck-earning baby in each department. You can find the data in 'boss_baby_corp.json'.",
      "answer": "Deborah, Jeffrey, Joseph, Melissa, Ronald",
      "original_points": 100,
      "type": "short answer",
      "question_group": 15,
      "image_link": "",
      "content_link": "/files/boss_baby_corp.json"
    },
    {
      "title": "Which Department has the Most Baby Bucks?",
      "content": "Using the 'boss_baby_corp.json' file, calculate the average baby buck allowance for each department. List the top 3 departments in order from highest average allowance to lowest, separated by commas.",
      "answer": "Playtime Strategy, Formula Development, Diaper Research",
      "original_points": 100,
      "type": "short answer",
      "question_group": 15,
      "image_link": "",
      "content_link": "/files/boss_baby_corp.json"
    },
    {
      "title": "Top Money Sender",
      "content": "From the CSV file recording play money transfers among eight friends, determine which player sent the highest total amount of money. Then, calculate *to two decimal places* the total amount of money that this player sent. (ANSWER FORMAT: 'Bob sent 100.52')",
      "answer": "Helena sent 6302.87",
      "original_points": 100,
      "type": "short answer",
      "question_group": 16,
      "image_link": "",
      "content_link": "/files/transactions.csv"
    },
    {
      "title": "Most Transactions Between Players",
      "content": "Using the CSV file of play money transfers among eight friends, identify all pairs of players who had the highest number of transactions between them (regardless of direction). Then provide the names of the 2 players with the most transactions (in alphabetical order so for example: Alice and Bob).",
      "answer": "Helena and Mehdi",
      "original_points": 100,
      "type": "short answer",
      "question_group": 16,
      "image_link": "",
      "content_link": "/files/transactions.csv"
    },
    {
      "title": "Bitcoin Trillionaire",
      "content": "The program below is a simplified bitcoin exchange simulator.\n\nIf you select the **buy** option, you will be asked to enter a $ value of how much bitcoin to buy. What input can you enter to guarantee a balance of $1,000,000,000,000 (one trillion dollars) or more?\n\n[HINT: READ THIS](https://docs.python.org/3/library/functions.html#float)",
      "answer": "inf",
      "original_points": 150,
      "type": "short answer",
      "question_group": 17,
      "image_link": "",
      "content_link": "/files/bitcoin_trillionaire.py"
    },
    {
      "title": "400 colours but one shines the most",
      "content": "An image `color_patch.png` has been provided. This image contains a 20x20 grid of randomly colored pixels.\n\n![Color Patch](/files/color_patch.png)\n\nYour task is to determine the brightest color in the above color patch. The brightness of a color is defined as the maximum value among its R, G, and B components. Provide your answer as three integers separated by commas (R,G,B) representing the brightest color found in the image.\n\nTo complete this task, you'll need to analyze the RGB values of each pixel in the image. You will need to search the web for information on how to get RGB values for individual pixels using Python",
      "answer": "243,255,235",
      "original_points": 100,
      "type": "short answer",
      "question_group": 18,
      "image_link": "",
      "content_link": "/files/color_patch.png"
    },
    {
      "title": "Counting Text Files in a Zip Archive",
      "content": "You are provided with a zip file containing over 200 subfolders and more than 50 text files. Your task is to determine:\n\n1. How many text files are in the zip file?\n2. How many of these text files are not empty?\n\nYou can use any method, such as writing a program or manual inspection, to find the answers.\n\n*Hint:* You might find [this tutorial](https://www.tutorialspoint.com/file-searching-using-python) helpful.",
      "answer": "c",
      "original_points": 100,
      "type": "mcqs",
      "question_group": 19,
      "option_a": "Total text files: 250\nNon-empty text files: 200",
      "option_b": "Total text files: 50\nNon-empty text files: 25",
      "option_c": "Total text files: 60\nNon-empty text files: 42",
      "option_d": "Total text files: 72\nNon-empty text files: 60",
      "option_e": "Total text files: 100\nNon-empty text files: 50",
      "image_link": "",
      "content_link": "/files/archive.zip"
    },
    {
      "title": "The Light Bulb Sequence",
      "content": "You have a row of 5 light bulbs, all initially turned off. Every day for 10 days, you perform the following operation:\n- For each bulb (from left to right), if the current day number plus the bulb's position (1-5) is divisible by 3, toggle that bulb's state.\n\nQuestion: What is the state of each light bulb (on or off) after 10 days? \n\n*(ANSWER FORMAT: On, Off, On, Off, On)*",
      "answer": "Off, On, On, Off, On",
      "original_points": 100,
      "type": "short answer",
      "question_group": 20,
      "image_link": "",
      "content_link": ""
    },
    {
      "title": "The Semi-Perfect Shuffle",
      "content": "You have 9 cards numbered 1 to 9, in order. You perform a \"semi-perfect shuffle\" where you split the deck into two unequal halves (4 on the left and 5 on the right) and then interleave them perfectly, with the right half (bottom) going first. For example, after one shuffle, the order would be: 5, 1, 6, 2, 7, 3, 8, 4, 9.\n\nQuestion: How many shuffles does it take to return the cards to their original order?\n\nYou can approach this problem through logical reasoning or by implementing your own simulation. Explain your method and show your work.",
      "answer": "6",
      "original_points": 100,
      "type": "short answer",
      "question_group": 21,
      "image_link": "",
      "content_link": ""
    },
    {
      "title": "The Prisoner's Escape",
      "content": "In a prison, there are 8 prisoners (numbered 0-7) and 8 doors (numbered 0-7). Each door leads to freedom for a specific prisoner. The doors are randomly shuffled each day. The escape attempt follows these rules:\n\n1. Each prisoner is allowed to open up to 5 doors.\n2. If all prisoners find their exit door, they all escape. If even one fails, they all stay in prison.\n3. If a prisoner's number matches their exit door number, that door becomes permanently locked, reducing the available doors for the subsequent prisoners.\n4. The prisoners attempt to escape in order, from prisoner 0 to prisoner 7.\n\nYour task is to implement the `prisoner_strategy` function to maximize the probability of all prisoners escaping.\n\nQuestion: What is the approximate probability of all prisoners escaping with your implemented strategy?\n\nImplement your strategy in the provided Python code and run the simulation to find the probability.\n\n```python\nimport random\n\ndef prisoner_strategy(prisoner_number, available_doors):\n    \"\"\"\n    Implement the strategy for a single prisoner trying to escape.\n    \n    :param prisoner_number: The number of the current prisoner (0-7)\n    :param available_doors: A set of door numbers that are still available\n    :return: A list of door numbers the prisoner will try (max 5)\n    \"\"\"\n    # TODO: Implement your strategy here\n    # Remember: \n    # - You can try up to 5 doors\n    # - available_doors is a set of integers representing available door numbers\n    # - Return a list of door numbers to try (must be a subset of available_doors)\n    pass\n\ndef simulate_prison_escape(simulations=100000):\n    success_count = 0\n\n    for _ in range(simulations):\n        exit_doors = list(range(8))\n        random.shuffle(exit_doors)\n        available_doors = set(range(8))\n        all_prisoners_succeeded = True\n\n        for prisoner_number in range(8):\n            doors_to_try = prisoner_strategy(prisoner_number, available_doors)\n            \n            if len(doors_to_try) > 5 or not set(doors_to_try).issubset(available_doors):\n                raise ValueError(\"Invalid strategy: too many doors or unavailable doors selected\")\n\n            if exit_doors[prisoner_number] in doors_to_try:\n                if exit_doors[prisoner_number] == prisoner_number:\n                    available_doors.discard(prisoner_number)\n            else:\n                all_prisoners_succeeded = False\n                break\n\n        if all_prisoners_succeeded:\n            success_count += 1\n\n    probability = success_count / simulations\n    print(f\"The approximate probability of all prisoners escaping is: {probability}\")\n\nsimulate_prison_escape()\n```",
      "answer": "c",
      "original_points": 100,
      "type": "mcqs",
      "question_group": 22,
      "option_a": "About 0.1%",
      "option_b": "About 1%",
      "option_c": "About 6%",
      "option_d": "About 11%",
      "option_e": "About 16%",
      "option_f": "About 19%",
      "option_g": "About 23%",
      "option_h": "About 38%",
      "image_link": "",
      "content_link": ""
    },
    {
      "title": "The Dice Reroll Dilemma",
      "content": "You're playing a game where you roll three six-sided dice. After seeing the result, you have an option to reroll 1,2 or all 3 dice. \nYou win if your final sum is higher than the sum of three dice rolled by the house.\n\nConsider two strategies:\nA) Keep your current roll if the total is more than 10, reroll all dice otherwise.\nB) Keep the highest die rolled and reroll the other two.\n\nQuestion: Which strategy gives you a better chance of winning? By approximately how much?\n\nYou can use the provided Python starter code to implement and test these strategies, or work it out mathematically. Can you think of an even better strategy?\n\n```python\nimport random\n\ndef play_dice_game(strategy, n_games=10000):\n    wins = 0\n    for _ in range(n_games):\n        dice = [random.randint(1, 6) for _ in range(3)]\n        if strategy(dice):\n            wins += 1\n    return wins\n\ndef strategy_reroll_if_not_above_10(dice):\n    # Implement the strategy\n    pass\n\ndef strategy_keep_highest(dice):\n    # Implement the strategy\n    pass\n\n# Example usage\nn_games = 10000\nstrategy_a_wins = play_dice_game(strategy_reroll_if_not_above_10, n_games)\nstrategy_b_wins = play_dice_game(strategy_keep_highest, n_games)\n\nprint(f\"Strategy A wins: {strategy_a_wins/n_games:.2%}\")\nprint(f\"Strategy B wins: {strategy_b_wins/n_games:.2%}\")\n```",
      "answer": "b",
      "original_points": 100,
      "type": "mcqs",
      "question_group": 23,
      "option_a": "Strategy A is better by about 2%",
      "option_b": "Strategy B is better by about 2%",
      "option_c": "Strategy A is better by about 5%",
      "option_d": "Strategy B is better by about 5%",
      "option_e": "Strategy A is better by about 9%",
      "option_f": "Strategy B is better by about 9%",
      "option_g": "Both strategies are approximately equal",
      "image_link": "",
      "content_link": ""
    }
  ]
}
```
[database.py](./database.py)
### ./database.py
```
import sqlite3
import os
import logging
from fastapi import FastAPI, HTTPException
import json
from passlib.context import CryptContext
from datetime import datetime
from config import CURRENT_DB,CURRENT_DIR

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def execute_db_query(query, params=(), fetchone=False, db=None):
    if db is None:
        db = CURRENT_DB
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

def get_question(id: str):
    result = execute_db_query("SELECT answer, current_points FROM questions WHERE id = ?", (id,))
    if not result:
        raise HTTPException(status_code=404, detail="Question not found")
    return result[0]

def get_attempts_count(team_name: str, id: str):
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
        "INSERT INTO attempted_questions VALUES (?, ?, ?, ?)",
        params=(name, question_id, datetime.now(), solved)
    )

def update_questions(data):
    try:
        execute_db_query('DELETE FROM questions')
        
        for question in data['questions']:
            execute_db_query(
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
        return True
    except Exception as e:
        return False
def create_database(data, teams_json_path, colors_json_path):
    db_file_path = os.path.join(CURRENT_DIR, f"{CURRENT_DB}")  # Update this based on your current database file path

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
            "password_hash"	TEXT NOT NULL,
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

        with open(teams_json_path, 'r') as file:
            data = json.load(file)
            teams_list = data['teams']

        with open(colors_json_path, 'r') as file:
            data = json.load(file)
            color_list = data["colors"] * 5

        for team in teams_list:
            hashed_password = pwd_context.hash(team["password"])
            cursor.execute("INSERT INTO teams (name, password_hash, score, color) VALUES (?, ?, ?, ?)",
                           (team["name"], hashed_password, 0, color_list.pop(0)))

        cursor.execute("""
        INSERT INTO manual_scores (team_name, q1_score, q2_score, q3_score, q4_score)
        SELECT name, 0, 0, 0, 0 FROM teams
        WHERE name NOT IN (SELECT team_name FROM manual_scores);
        """)

        conn.commit()
        conn.close()
    except Exception as e:
        logging.error("An error occurred when creating the database", exc_info=True)
        raise e
```
[comp.db](./comp.db)
### ./comp.db
```
SQLite format 3   @                                                                     .[4
ø 	 ãÍ%
	
H                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        5'')tablemanual_scoresmanual_scoresCREATE TABLE "manual_scores" (
            "team_name"	TEXT UNIQUE,
            "q1_score"	INTEGER,
            "q2_score"	INTEGER,
            "q3_score"	INTEGER,
            "q4_score"  INTEGER,
            FOREIGN KEY("team_name") REFERENCES "teams"("name")
        )9M' indexsqlite_autoindex_manual_scores_1manual_scores33etableattempted_questionsattempted_questionsCREATE TABLE "attempted_questions" (
            "team_name"	text,
            "question_id"	INTEGER,
            "timestamp"	datetime,
            "solved"	boolean NOT NULL,
            "attempt_count"	INTEGER DEFAULT 0,
            FOREIGN KEY("team_name") REFERENCES "teams"("name"),
            FOREIGN KEY("question_id") REFERENCES "questions"("id")
        );EtablequestionsquestionsCREATE TABLE "questions" (
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
        )g-tableteamsteamsCREATE TABLE "teams" (
            "name"	TEXT NOT NULL UNIQUE,
            "password"	TEXT NOT NULL,
            "score"	INTEGER DEFAULT 0,
            "color"	TEXT,
            PRIMARY KEY("name")
        ))= indexsqlite_autoindex_teams_1teams       
   
 Ý¸lE üÙ±f@
÷
Ñ
¬

_
;
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     $#/FirePhoenix123rgb(201, 47, 208)"!-WindRiders123rgb(154, 182, 3)%%/StarFighters123rgb(29, 186, 186)$#/MoonWalkers123rgb(35, 199, 204)##-SolarFlares123rgb(243, 5, 166)$#/FrostWolves123rgb(167, 22, 229)#!/MightyOwls123rgb(30, 249, 220)"
/SwiftCats123rgb(162, 161, 13)$#/GoldenBears123rgb(205, 19, 239)$#/SilverHawks123rgb(26, 199, 206)#
!/DarkHorses123rgb(165, 249, 37)&	'/MountainGoats123rgb(17, 244, 145)!/SeaLions123rgb(255, 162, 51)"/SkyEagles123rgb(201, 40, 133)#!/DataMiners123rgb(13, 226, 173)%%/CyberKnights123rgb(136, 28, 231)#!/QuickFoxes123rgb(54, 194, 221)%%/ThunderBolts123rgb(38, 192, 229)#!/BlueSharks123rgb(27, 187, 196)!-RedWolves123rgb(213, 8, 175)
   Ë ä³h¤ËH+ûwÄóXê:ÓÛ                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           #FirePhoenix!WindRiders%StarFighters#MoonWalkers#SolarFlares#FrostWolves!MightyOwls
SwiftCats
#GoldenBears#SilverHawks!DarkHorses
'MountainGoats	SeaLions
SkyEagles!DataMiners%CyberKnights!QuickFoxes%ThunderBolts!BlueSharks	RedWolves
   
	 HÇ"
wÐRª
;	                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 
 Y%           /
What is the technique used by hackers to exploit a buffer overflow vulnerability in a targeted system?d

short_answerimages_sec/10.png^	 s+ 11

    -
What is the process of attempting to gain unauthorized access to a computer system by posing as an authorized user?d

multiple_choiceSpoofingPhishingBrute-Force AttackSocial Engineeringimages_sec/9.png ;%           -
What method is used to disguise a harmful link or website to make it appear legitimate?a

short_answerimages_sec/8.png% + +!#

    -
Which of the following is a popular tool used for password cracking?d

multiple_choiceJohn the RipperNessusBurp SuiteAircrack-ngimages_sec/7.png| %           -
What is the process of trying to decode encrypted or hashed data called?a

short_answerimages_sec/6.png$ 5+ !

    -
Which type of malware is designed to replicate itself and spread to other computers?c

multiple_choiceVirusWormTrojanRansomwareimages_sec/5.png( u%           -
What is the technique called where an attacker intercepts communication between two parties without their knowledge?c

short_answerimages_sec/4.png" E+ 

    -
Which of the following programming languages is most commonly used for writing exploit code?a

multiple_choicePythonRubyCJavaimages_sec/3.png #%           -
What is the common name for vulnerabilities that are unknown to the vendor?a

short_answerimages_sec/2.png5 ;+ !-

    -
Which of the following tools is often used for network discovery and security auditing?d

multiple_choiceNmapWiresharkMetasploitAll of the aboveimages_sec/1.png
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              
    îÚÈ¶£}kXC1 ýìÙÅ´                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               !WindRiders%ThunderBoltsSwiftCats%StarFighters#SolarFlaresSkyEagles#SilverHawks
SeaLionsRedWolves!QuickFoxes
'MountainGoats	#MoonWalkers!MightyOwls#GoldenBears#FrostWolves#FirePhoenix!DataMiners!DarkHorses%CyberKnights!BlueSharks
   Ë òáÒÃ³£tbSE8(
ùëÚË                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           !WindRiders%ThunderBolts
SwiftCats%StarFighters#SolarFlares
SkyEagles#SilverHawksSeaLions

RedWolves!QuickFoxes'MountainGoats
#MoonWalkers	!MightyOwls#GoldenBears#FrostWolves#FirePhoenix!DataMiners!DarkHorses%CyberKnights
!	BlueSharks
```
[colors.json](./colors.json)
### ./colors.json
```
{
    "colors": [
        "rgb(171,239,177)",
        "rgb(130,170,234)",
        "rgb(210,224,232)",
        "rgb(249,224,139)",
        "rgb(131,208,166)",
        "rgb(159,145,133)",
        "rgb(169,240,179)",
        "rgb(222,197,242)",
        "rgb(244,182,202)",
        "rgb(169,138,168)",
        "rgb(132,239,199)",
        "rgb(162,231,235)",
        "rgb(207,137,202)",
        "rgb(250,143,214)",
        "rgb(203,198,253)",
        "rgb(182,158,222)",
        "rgb(247,228,184)",
        "rgb(183,176,193)",
        "rgb(163,183,143)",
        "rgb(229,184,226)",
        "rgb(206,184,244)",
        "rgb(189,179,246)",
        "rgb(227,134,192)",
        "rgb(184,204,187)",
        "rgb(227,178,183)",
        "rgb(189,243,209)",
        "rgb(236,232,182)",
        "rgb(183,215,144)",
        "rgb(159,204,202)",
        "rgb(184,240,241)",
        "rgb(206,175,189)",
        "rgb(191,206,210)",
        "rgb(184,149,226)",
        "rgb(172,231,251)",
        "rgb(142,177,231)",
        "rgb(153,173,210)",
        "rgb(225,183,175)",
        "rgb(141,166,167)",
        "rgb(141,247,201)",
        "rgb(222,176,223)"
    ]
}
```
[auth.py](./auth.py)
### ./auth.py
```
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from datetime import datetime, timedelta
from config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES
from passlib.context import CryptContext

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.now() + expires_delta if expires_delta else datetime.now() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        team_name: str = payload.get("sub")
        user_role: str = payload.get("role")
        if team_name is None or user_role not in ["student", "admin"]:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    return {"team_name": team_name, "role": user_role}
```
[config.py](./config.py)
### ./config.py
```
import os
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv('SECRET_KEY')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
CURRENT_DIR = os.path.dirname(__file__)
CURRENT_DB = os.path.join(CURRENT_DIR, "initial.db")
BACKUP_DIR = os.path.join(CURRENT_DIR, "backup")

```
[.env](./.env)
### ./.env
```
SECRET_KEY="VCC2023LOGIN"
ADMIN_PASSWORD="BOSSMAN"
```
[teams.json](./teams.json)
### ./teams.json
```
{
  "teams": [
    {
      "name": "Tester1",
      "password": "652093ccm"
    },
    {
      "name": "Tester2",
      "password": "652093ccm"
    },
    {
      "name": "Tester3",
      "password": "652093ccm"
    },
    {
      "name": "Nathan",
      "password": "f43vc46v6"
    },
    {
      "name": "Danijela",
      "password": "d435h67876"
    },
    {
      "name": "SanjinX",
      "password": "652093"
    }
  ]
}


```
[template.json](./template.json)
### ./template.json
```
{
    "questions": [
        {
            "content": "What is 2+2?",
            "answer": "a",
            "original_points": 10,
            "type": "mcqs",
            "question_group": 1,
            "option_a": "4",
            "option_b": "3",
            "option_c": "5",
            "option_d": "8",
            "option_e": "1",
            "option_f": "10",
            "image_link": "http://sample.image.link",
            "content_link": "http://sample.content.link"
        },
        {
            "content": "What do call this symbol + ?",
            "answer": "Addition",
            "original_points": 20,
            "type": "short answer",
            "question_group": 2,
            "image_link": "http://another.image.link",
            "content_link": "http://sample.content.link"
        },
        {
            "content": "Which symbol is multiplication?",
            "answer": "b",
            "original_points": 20,
            "type": "Another type",
            "question_group": 2,
            "option_a": "images_sec/30.png",
            "option_b": "images_sec/30.png",
            "image_link": "http://another.image.link",
            "content_link": "http://sample.content.link"
        }
    ]
}
```
[app.log](./app.log)
### ./app.log
```
2023-09-27 13:16:44,534:INFO:FastAPI application started

```
[__init__.py](./__init__.py)
### ./__init__.py
```

```
[setup_database.py](./setup_database.py)
### ./setup_database.py
```
import os
import json
from database import create_database
from config import CURRENT_DIR, CURRENT_DB

def setup_database():
    print(f"Setting up database: {CURRENT_DB}")

    # Load data from initial.json
    initial_json_path = os.path.join(CURRENT_DIR, "initial.json")
    with open(initial_json_path, 'r') as f:
        initial_data = json.load(f)

    # Set paths for teams.json and colors.json
    teams_json_path = os.path.join(CURRENT_DIR, "teams.json")
    colors_json_path = os.path.join(CURRENT_DIR, "colors.json")

    # Create the database
    create_database(initial_data, teams_json_path, colors_json_path)

    print(f"Database setup complete. Database file: {CURRENT_DB}")

if __name__ == "__main__":
    setup_database()
```
