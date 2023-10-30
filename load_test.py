from locust import HttpUser, task, between

#pip install locust
#locust -f load_test.py
#localhost:8089

class UserBehavior(HttpUser):
    wait_time = between(1, 2)

    team_data ={
    "teams": [
        {
            "name": "Albion",
            "password": "xWFv9SKy"
        },
        {
            "name": "ApolloParkways1",
            "password": "H82fdJue"
        },
        {
            "name": "ApolloParkways2",
            "password": "Ke5pafim"
        },
        {
            "name": "AscotValeWest1",
            "password": "3UxfZ0ek"
        },
        {
            "name": "AscotValeWest2",
            "password": "jX36VkwW"
        },
        {
            "name": "Balcombe",
            "password": "QPDoGjgk"
        },
        {
            "name": "BrunswickEast1",
            "password": "OWYcWIVE"
        },
        {
            "name": "BrunswickEast2",
            "password": "AOTHJJnR"
        },
        {
            "name": "Carnegie1",
            "password": "dhgnKTXG"
        },
        {
            "name": "Carnegie2",
            "password": "73b1vFIS"
        },
        {
            "name": "Dandenong",
            "password": "GoRPI2MY"
        },
        {
            "name": "DohertysCreek1",
            "password": "CFp8CCOp"
        },
        {
            "name": "DohertysCreek2",
            "password": "qAwzEJec"
        },
        {
            "name": "Elsternwick1",
            "password": "RnmoviAB"
        },
        {
            "name": "Elsternwick2",
            "password": "Vdpqa35m"
        },
        {
            "name": "Glendal1",
            "password": "iem31ztk"
        },
        {
            "name": "Glendal2",
            "password": "fT3Zi1q5"
        },
        {
            "name": "HarvestHome1",
            "password": "Nv192T30"
        },
        {
            "name": "HarvestHome2",
            "password": "5fjkAF7y"
        },
        {
            "name": "MerriCreek1",
            "password": "A9cPiIO8"
        },
        {
            "name": "MerriCreek2",
            "password": "96bTTwQy"
        },
        {
            "name": "Monbulk",
            "password": "BqZreJTN"
        },
        {
            "name": "RobertsMcCubbin1",
            "password": "kmDIHXPi"
        },
        {
            "name": "RobertsMcCubbin2",
            "password": "VffOugnP"
        },
        {
            "name": "RobertsMcCubbin3",
            "password": "TiTyn1N5"
        },
        {
            "name": "Scotch1",
            "password": "FkQBH9Qt"
        },
        {
            "name": "Scotch2",
            "password": "LksYX1mg"
        },
        {
            "name": "Silverton1",
            "password": "lVTieVEB"
        },
        {
            "name": "Silverton2",
            "password": "LYATVJjS"
        },
        {
            "name": "StFinbars",
            "password": "GgWVwGGy"
        },
        {
            "name": "StMarys1",
            "password": "oL1H13q3"
        },
        {
            "name": "StMarys2",
            "password": "X2pH1Cmg"
        },
        {
            "name": "StOliverPlunkett",
            "password": "t6ixjNBt"
        },
        {
            "name": "SunshineNorth",
            "password": "m0kxIZNl"
        },
        {
            "name": "TheLakes1",
            "password": "xGqWLQ2F"
        },
        {
            "name": "TheLakes2",
            "password": "QvT2BaoJ"
        },
        {
            "name": "Victory",
            "password": "IrjVeDGz"
        }
    ]
    }


    @task(1)
    def get_comp_table(self):
        self.client.get("/get_comp_table")

    @task(2)
    def get_manual_questions(self):
        admin_password = "BOSSMAN"
        url = f"/manual_questions/{admin_password}"
        self.client.get(url)

    @task(4)
    def get_questions_for_teams(self):
        for team in self.team_data["teams"]:
            team_name = team["name"]
            team_password = team["password"]
            url = f"/questions/{team_name}/{team_password}"
            self.client.get(url)

    @task(5)
    def submit_answer(self):
        for team in self.team_data["teams"]:
            team_name = team["name"]
            team_password = team["password"]
            payload = {
                "id": "1",
                "answer": "b",
                "team_name": team_name,
                "team_password": team_password
            }
            self.client.post("/submit_mcqs_answer", json=payload)
