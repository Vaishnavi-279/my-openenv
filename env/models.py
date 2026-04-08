from pydantic import BaseModel

class SQLObservation(BaseModel):
    schema: str
    broken_query: str
    last_result: str | None = None

class SQLAction(BaseModel):
    query: str

class SQLReward(BaseModel):
    reward: float