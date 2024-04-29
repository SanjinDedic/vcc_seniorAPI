import pytest
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from main import app, CURRENT_DIR
from database import create_database
import json

@pytest.fixture(scope="session", autouse=True)
def initialize_database():
    initial_json_path = os.path.join("initial_test.json")
    with open(initial_json_path, 'r') as f:
        initial_data = json.load(f)
    
    teams_json_path = os.path.join(CURRENT_DIR, "teams.json")
    colors_json_path = os.path.join(CURRENT_DIR, "colors.json")
    
    create_database(initial_data, teams_json_path, colors_json_path)
    
    # Insert test team data
    from database import execute_db_query
    execute_db_query("INSERT INTO teams (name, password_hash) VALUES (?, ?)", ("TESTX1", "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW"))
    
    yield
    
    # Clean up the database after tests
    #os.remove(os.path.join("initial.db"))