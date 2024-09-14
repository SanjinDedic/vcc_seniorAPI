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