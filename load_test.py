from locust import HttpUser, task, between

#pip install locust
#locust -f load_test.py
#localhost:8089

class UserBehavior(HttpUser):
    wait_time = between(1, 2)

    team_data = {
        "teams": [
      "RedWolves",
      "BlueSharks",
      "ThunderBolts",
      "QuickFoxes",
      "CyberKnights",
      "DataMiners",
      "SkyEagles",
      "SeaLions",
      "MountainGoats",
      "DarkHorses",
      "SilverHawks",
      "GoldenBears",
      "SwiftCats",
      "MightyOwls",
      "FrostWolves",
      "SolarFlares",
      "MoonWalkers",
      "StarFighters",
      "WindRiders",
      "FirePhoenix"
    ]
    }

    @task(1)
    def get_comp_table(self):
        self.client.get("/get_comp_table")
    
    @task(2)
    def get_manual_questions(self):
        self.client.get("/get_manual_questions",headers={"Password": "BOSSMAN"})

    @task(4)
    def get_questions_for_teams(self):
        for team_name in self.team_data["teams"]:
            self.client.get(f"/questions/{team_name}",headers={"Team-Name": "RedWolves","Team-Password": "123"})
    
    @task(5)
    def submit_answer(self):
     
        for team_name in self.team_data["teams"]:
            payload = {
                "id": "1",
                "answer": "b",
                "team_name": team_name
            }
            self.client.post("/submit_mcqs_answer",headers={"Team-Name": "RedWolves","Team-Password": "123"}, json=payload)