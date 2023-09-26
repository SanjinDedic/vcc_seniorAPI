import logging
import os
import random
import sqlite3
from datetime import datetime
from difflib import SequenceMatcher

from fastapi import FastAPI,UploadFile, HTTPException, Request, status, File, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import json

CURRENT_DB="comp.db"


class Table(BaseModel):
    name: str

class Generator(BaseModel):
    topic: str
    num: int

class QuickSignUp(BaseModel):
    name: str
    password: str

class Answer(BaseModel):
    id: str
    answer: str
    team_name: str

# Define a User model for login request validation
class User(BaseModel):
    team_name: str
    password: str

class ManualQuestions(BaseModel):
    team_id: int
    scores: dict


# Set up logging
logging.basicConfig(filename='app.log', level=logging.INFO,
                    format='%(asctime)s:%(levelname)s:%(message)s')
logging.info("FastAPI application started")
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
    result = execute_db_query(f"SELECT ip,score,attempted_questions,solved_questions FROM teams WHERE name = ?", (team_name,))
    if not result:
        raise HTTPException(status_code=404, detail="Team not found")
    return result[0]

def get_attempts(team_name: str,id: str):
    result = execute_db_query(f"SELECT attempt_count FROM attempted_questions WHERE team_name = ? AND question_id = ?", (team_name, id,), fetchone=True)
    return result
    
def decrement_question_points(question_id: int):
    execute_db_query("UPDATE questions SET current_points = current_points - 1 WHERE id = ?", (question_id,))

def reset_question_points():
    """Resets the points of all questions to their original points."""
    execute_db_query("UPDATE questions SET current_points = original_points")


def update_team(name: str, score: int, solved_qs: int, attempted_qs: int):
    execute_db_query(
        f"UPDATE teams SET score = ?, attempted_questions = ?, solved_questions = ? WHERE name = ?", 
        params=(score, attempted_qs, solved_qs, name))

def update_attempted_questions(name: str, ip: str, question_id: str, solved: bool, attempts=1):
    existing_record = execute_db_query(f"SELECT * FROM attempted_questions WHERE team_name = ? AND question_id = ?", (name, question_id,), fetchone=True)
    if existing_record:
        # If exists, then update the existing record
        execute_db_query(f"UPDATE attempted_questions SET attempt_count = ?, timestamp = ?, solved = ? WHERE team_name = ? AND question_id = ?", 
        params=(attempts, datetime.now(), solved, name, question_id))
    else:
        # If not, insert a new record
        execute_db_query(
            f"INSERT INTO attempted_questions VALUES (?, ?, ?, ?, ?, ?)",
            params=(name, ip, question_id, datetime.now(), solved, attempts))

def log_submission(is_correct: bool, team_name: str, answer: str, id: str, correct_answer: str, score: Optional[int] = None):
    if is_correct:
        logging.info(
            f"{team_name} submitted {answer} for id {id}. Correct answer is {correct_answer}. "
            f"Current score is {score}."
        )
    else:
        logging.info(
            f"{team_name} submitted {answer} for id {id}. Correct answer is {correct_answer}. "
            f"Score remains unchanged."
        )

@app.get("/test")
async def test(request: Request):
      return {"message":"This is a test"}


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
    SELECT teams.id, teams.name, manual_scores.q1_score, manual_scores.q2_score, manual_scores.q3_score
    FROM teams
    LEFT JOIN manual_scores ON teams.id = manual_scores.team_id
    """)
    
    teams = [
        {
        "team_id": row[0],
            "team_name": row[1],
            "q1_score": row[2],
            "q2_score": row[3],
            "q3_score": row[4]
        } for row in rows
    ]
    
    return teams

@app.get("/questions")
async def get_questions():
    # Fetching the questions with a maximum of 10 options
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
            'content_link': question[16]  # Adjust this index if needed
        }

        transformed_questions.append(transformed_question)

    return {"questions": transformed_questions}


@app.post("/submit_mcqs_answer")
async def submit_answer_mcqs(a: Answer):
    try:
        correct_ans, question_pts = get_question(id=a.id)
        print("correct ans found",correct_ans)
        team_ip, score, attempted_qs, solved_qs = get_team(team_name=a.team_name)
        print("team fetched")
        
        is_correct = a.answer == correct_ans
        print("correct status", is_correct)
        attempted_qs += 1
        print('reached far')
        if is_correct:
            score += question_pts
            solved_qs += 1
            log_submission(is_correct, a.team_name, a.answer, a.id, correct_ans)
            print('attempting logging')
            update_team(name=a.team_name, score=score, solved_qs=solved_qs, attempted_qs=attempted_qs)
            update_attempted_questions(name=a.team_name, ip=team_ip, question_id=a.id, solved=is_correct)
            decrement_question_points(question_id=a.id)
            return {"message": "Correct"}
        
        log_submission(is_correct, a.team_name, a.answer, a.id, correct_ans)
        update_team(name=a.team_name, score=score, solved_qs=solved_qs, attempted_qs=attempted_qs)
        update_attempted_questions(name=a.team_name, ip=team_ip, question_id=a.id, solved=is_correct)

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
        print("correct ans found",correct_ans)
        team_ip, score, attempted_qs, solved_qs = get_team(team_name=a.team_name)
        print("team fetched")
        previous_attempts = get_attempts(team_name=a.team_name,id=a.id)
        
        
        attempts_made = 1 if not previous_attempts else previous_attempts[0]+1
        is_correct = a.answer == correct_ans or similar(correct_ans, a.answer)
        print("correct status", is_correct)
        print('reached far')
        if is_correct:
            attempted_qs += 1
            score += question_pts
            solved_qs += 1
            log_submission(is_correct, a.team_name, a.answer, a.id, correct_ans)
            print('attempting logging')
            update_team(name=a.team_name, score=score, solved_qs=solved_qs, attempted_qs=attempted_qs)
            update_attempted_questions(name=a.team_name, ip=team_ip, question_id=a.id, solved=is_correct,attempts=attempts_made)
            decrement_question_points(question_id=a.id)
            return {"message": "Correct"}
        #log_submission(is_correct, a.team_name, a.answer, a.id, correct_ans)
        
        if attempts_made >= 3:  # Assuming 3 attempts are allowed for SA
            attempted_qs += 1
            update_team(name=a.team_name, score=score, solved_qs=solved_qs, attempted_qs=attempted_qs)
            update_attempted_questions(name=a.team_name, ip=team_ip, question_id=a.id, solved=is_correct,attempts=attempts_made)
            return {"message": "Incorrect", "correct_answer": correct_ans}
        
        #print(attempts_made)
        update_attempted_questions(name=a.team_name, ip=team_ip, question_id=a.id, solved=is_correct,attempts=attempts_made)
        
        return {"message": "Try again"}
    except HTTPException as e:
        raise e
    except Exception as e:
        logging.error("Error occurred when submitting answer", exc_info=True)
        raise HTTPException(status_code=500, detail="An error occurred when submitting the answer.")


@app.post("/quick_signup_sec")
async def quick_signup(team: QuickSignUp, request: Request):
    team_color = random_color()
    print("team color", team_color)
    # Get client IP address
    client_ip = request.client.host
    print("client ip", client_ip)
    existing_team = execute_db_query("SELECT * FROM teams WHERE name = ? AND password = ?", (team.name,team.password,), fetchone=True)
    if existing_team is not None:
        return {"message": "Team already exists"}
    #check if there is another team with the same IP
    #existing_team = execute_db_query("SELECT * FROM teams WHERE ip = ?", (client_ip,), fetchone=True)
    #if existing_team is not None:
    #    return {"message": "Another team already exists with the same IP address"}
    print("team about to be created")
    # Create a new team and include the IP address
    execute_db_query("INSERT INTO teams (name, password, ip, score,color, attempted_questions, solved_questions) VALUES (?, ?, ?, ?, ?, ?, ?)", (team.name,team.password, client_ip,0,team_color, 0, 0, ))

    #access_token = Authorize.create_access_token(subject=team.name)
    return {"status": "success"}

@app.get("/json-files/")
async def list_json_files():
    try:
        files = [f for f in os.listdir("json") if os.path.isfile(os.path.join("json", f)) and f.endswith(".json")]
        return {"status": "success", "files": files}
    except Exception as e:
        return {"status": "error", "message": str(e)}

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
                "id" INTEGER,
                "name" TEXT NOT NULL,
                "password" TEXT NOT NULL,
                "ip" TEXT,
                "score" INTEGER DEFAULT 0,
                "color" TEXT,
                "attempted_questions" INTEGER DEFAULT 0,
                "solved_questions" INTEGER DEFAULT 0,
                PRIMARY KEY("id")
            );
            """

            questions_table = """
            CREATE TABLE "questions" (
                "id" INTEGER,
                "content" TEXT NOT NULL,
                "answer" TEXT NOT NULL,
                "original_points" INTEGER NOT NULL,
                "current_points" INTEGER,
                "type" TEXT,
                "question_group" INTEGER,
                "option_a" TEXT,
                "option_b" TEXT,
                "option_c" TEXT,
                "option_d" TEXT,
                "option_e" TEXT,
                "option_f" TEXT,
                "option_g" TEXT,
                "option_h" TEXT,
                "option_i" TEXT,
                "option_j" TEXT,
                "image_link" TEXT,
                "content_link" TEXT,
                PRIMARY KEY("id")
            );
            """

            attempted_questions_table = """
            CREATE TABLE "attempted_questions" (
                "team_name" text,
                "ip" text,
                "question_id" INTEGER,
                "timestamp" datetime,
                "solved" boolean NOT NULL,
                "attempt_count" INTEGER DEFAULT 0,
                FOREIGN KEY("team_name") REFERENCES "teams"("name"),
                FOREIGN KEY("question_id") REFERENCES "questions"("id")
            );
            """

            manual_question_table = """
            CREATE TABLE "manual_scores" (
                "team_id"	INTEGER UNIQUE,
                "q1_score"	INTEGER,
                "q2_score"	INTEGER,
                "q3_score"	INTEGER,
                FOREIGN KEY("team_id") REFERENCES "teams"("id")
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

            conn.commit()
            conn.close()

            
            CURRENT_DB=f"{file.filename}.db"

            return {"status": "success", "message": f"Database {file.filename}.db created successfully!"}
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    else:
        return {"status": "failed", "message": "File Not uploaded"}
        
   
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
async def team_login(user: User):
    try:
        result = execute_db_query("SELECT password FROM teams WHERE name=?",(user.team_name,))
        if result and result[0][0]==user.password:

            return {"status": "success", "message": "Logged in successfully"}
        else:
            return {"status": "failed", "message": "No team found with these credentials"}
            
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error: {e}")


@app.post("/update_manual_score/")
async def update_manual_score(data: ManualQuestions):
    try:
        old_scores = execute_db_query("SELECT q1_score, q2_score, q3_score FROM manual_scores WHERE team_id = ?",(data.team_id,))
        
        if not old_scores:
            old_scores = (0,0,0)
        else:
            old_scores = old_scores[0]
        score_diff = (int(data.scores['q1_score'])+int(data.scores['q2_score'])+int(data.scores['q3_score'])) - sum(old_scores)
        execute_db_query("""
                INSERT OR REPLACE INTO manual_scores (team_id, q1_score, q2_score, q3_score)
                VALUES (?, ?, ?, ?)
            """,(data.team_id, data.scores['q1_score'], data.scores['q2_score'], data.scores['q3_score'],))
        
        execute_db_query(" UPDATE teams SET score = score + ? WHERE id = ?",(score_diff, data.team_id,))

        return {"status": "success"}
    except Exception as e:
        return {"status": "failed"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
    