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