import os
from difflib import SequenceMatcher
from fastapi import FastAPI,UploadFile, Request, HTTPException, status, File, Query, Depends ,Body
from database import execute_db_query, get_question, get_attempts_count, decrement_question_points, reset_question_points, update_team, update_attempted_questions, create_database
from models import Answer, Admin, Team, Score, TeamScores, TeamsInput
from auth import create_access_token, get_current_user, verify_password, get_password_hash
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import json
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from datetime import datetime, timedelta
from config import ADMIN_PASSWORD, ACCESS_TOKEN_EXPIRE_MINUTES,CURRENT_DIR,CURRENT_DB

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

@app.get("/manual_questions")
async def manual_questions(current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")
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
async def get_questions(current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "student":
        raise HTTPException(status_code=403, detail="Forbidden")
    team_name = current_user["team_name"]
    result = execute_db_query("SELECT * FROM teams WHERE name = ?",(team_name,))
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
async def submit_answer_mcqs(a: Answer, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "student":
        raise HTTPException(status_code=403, detail="Forbidden")
    team_name = current_user["team_name"]
    result = execute_db_query("SELECT * FROM teams WHERE name = ?",(team_name,))
    if not result:
        return {"status": "failed", "message": "Team credentials are wrong"}
    
    #check if team and question in attempted_questions table if not return error
    existing = execute_db_query("SELECT * FROM attempted_questions WHERE team_name = ? AND question_id = ?", (team_name, a.id,), fetchone=True)
    if existing:
        return {"message": "Question already attempted"}
    try:
        correct_ans, question_pts = get_question(id=a.id)
        is_correct = a.answer == correct_ans
        if is_correct:
            update_attempted_questions(name=team_name, question_id=a.id, solved=is_correct)
            update_team(name=team_name, points=question_pts)
            decrement_question_points(question_id=a.id)
            return {"message": "Correct"}  
        update_attempted_questions(name=team_name, question_id=a.id, solved=is_correct)
        return {"message": "Incorrect"}
    
    except Exception as e:
        return {"message":"An error occurred when submitting the answer."}

@app.post("/submit_sa_answer")
async def submit_answer_sa(a: Answer, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "student":
        raise HTTPException(status_code=403, detail="Forbidden")
    team_name = current_user["team_name"]
    result = execute_db_query("SELECT * FROM teams WHERE name = ?",(team_name,))
    if not result:
        return {"status": "failed", "message": "Team credentials are wrong"}
    
    try:
        correct_ans, question_pts = get_question(id=a.id)
        attempts_made = get_attempts_count(team_name=team_name,id=a.id)
        if attempts_made >= 3:
            return {"message": "No attempts left"}
        is_correct = a.answer == correct_ans or similar(correct_ans, a.answer)
        if is_correct:
            update_team(name=team_name, points=question_pts)
            update_attempted_questions(name=team_name, question_id=a.id, solved=is_correct)
            decrement_question_points(question_id=a.id)
            return {"message": "Correct"}
        
        update_attempted_questions(name=team_name, question_id=a.id, solved=is_correct)
        if attempts_made < 2: # attempts was already incremented in update_attempted_questions
            return {"message": "Try again"}
        else:
            return {"message": "Incorrect"}
    except Exception as e:
        return {"message":"An error occurred when submitting the answer."}
        
@app.post("/team_login")
async def team_login(user: Team):
    if not user.team_name or  not user.password:
        return {"status":"failed", "message": "Team credentials are empty"}
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
                return {"access_token": access_token, "token_type": "bearer"}
        print("No team found with the provided credentials.")
        return {"status": "failed", "message": "No team found with these credentials"}
    except Exception as e:
        print("An exception occurred:", str(e))
        return {"status": "failed", "message": "Server error"}
            

@app.post("/team_signup")
async def quick_signup(team: Team):
    if not team.team_name or  not team.password:
        return {"status":"failed", "message": "Team credentials are empty"}
    try:
        team_color = "rgb(222,156,223)"
        existing_team = execute_db_query("SELECT password_hash FROM teams WHERE name = ?", (team.team_name,), fetchone=True)
        if existing_team is not None:
            hashed_password = existing_team[0]
            if verify_password(team.password, hashed_password):
                return {"status":"failed", "message": "Team already exists"}
            
        team_hashed_password = get_password_hash(team.password)

        execute_db_query("INSERT INTO teams (name, password_hash, score, color) VALUES (?, ?, ?, ?)", (team.team_name,team_hashed_password,0,team_color))
        
        
        execute_db_query("INSERT INTO manual_scores (team_name, q1_score, q2_score, q3_score, q4_score) VALUES (?, ?, ?, ?, ?)",(team.team_name,0,0,0,0))

        return {"status": "success", "message": "Team has been added"}
    
    except Exception as e:   
        return {"status":"failed", "message": f"Error occured {e}"}
        
@app.get("/json-files")
async def list_json_files(current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")
    try:
        files = [f for f in os.listdir("json") if os.path.isfile(os.path.join("json", f)) and f.endswith(".json")]
        return {"status": "success", "files": files}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/set_json/")
async def set_json(filename: str,current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")
    global CURRENT_DB

    if filename:
        CURRENT_DB=os.path.join(CURRENT_DIR, f"{filename[:-5]}.db")
        return {"status": "success", "message": "Database updated!"}
    else:
        return {"status": "failed", "message": "Wrong file selected!"}

@app.post("/reset_rankings/")
async def reset_team_data(team_name: str = Query(None, description="The name of the team to reset. If not provided, all teams will be reset."), current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")
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
            return {"status": "success", "message": f"Data for team '{team_name}' has been reset."}
        else:
            return {"status": "success", "message": "Data for all teams has been reset."}

    except Exception as e:
        return {"status": "failed", "message": "Cannot reset due to an error"}

@app.post("/reset_questions_score")
async def reset_questions_score(current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin" :
        raise HTTPException(status_code=403, detail="Forbidden")
    try:
        reset_question_points()
        return {"status": "success", "message": "Questions scores have been reset."}
    except Exception as e:
        return {"status": "failed", "message": "Cannot reset due to an error"}


@app.post("/admin_login")
async def admin_login(a: Admin):
    if not a.admin_password:
        return {"status": "failed", "message": "Admin credentials are wrong"}
    if a.admin_password != ADMIN_PASSWORD:
        return {"status": "failed", "message": "Admin credentials are wrong"}
    else:
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": "admin", "role": "admin"}, 
            expires_delta=access_token_expires
        )
        return {"access_token": access_token, "token_type": "bearer"}



@app.post("/update_manual_score")
async def update_manual_score(data: TeamsInput, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")
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


@app.post("/upload")
async def upload_database(file: UploadFile = File(None), current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")
    global CURRENT_DB
    
    if file:
        try:
            # Ensure it's a JSON file
            if not file.filename.endswith(".json"):
                return {"status": "error", "message": f"Wrong json format or file uploaded!"}
                
            file_location = os.path.join(CURRENT_DIR,"json", file.filename)
            if os.path.exists(file_location):
                CURRENT_DB = os.path.join(CURRENT_DIR, f"{file.filename[0:-5]}.db")
                return {"status": "error", "message": f"File '{file.filename}' already uploaded!"}
            
            content = file.file.read()
            
            with open(file_location, "wb+") as file_object:
                file_object.write(content)
                
            data = json.loads(content)
            CURRENT_DB = os.path.join(CURRENT_DIR, f"{file.filename[0:-5]}.db")
            
            # Call create_database function
            teams_json_path = os.path.join(CURRENT_DIR, "teams.json")
            colors_json_path = os.path.join(CURRENT_DIR, "colors.json")
            create_database(data, teams_json_path, colors_json_path)
            

            return {"status": "success", "message": f"Database {file.filename}.db created successfully!"}
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    else:
        return {"status": "failed", "message": "File Not uploaded"}
