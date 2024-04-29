import sqlite3
import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
import json
from passlib.context import CryptContext
from datetime import datetime

CURRENT_DB = "initial.db"  # Update this based on your current database file
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

@asynccontextmanager
async def lifespan(app: FastAPI):
    with open("initial.json", 'r') as f:  # Update the path to your initial data file
        initial_data = json.load(f)
    create_database(initial_data)
    yield

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

def create_database(data, teams_json_path, colors_json_path):
    db_file_path = CURRENT_DB  # Update this based on your current database file path

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