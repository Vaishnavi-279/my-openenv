from pydantic import BaseModel, Field

class SQLObservation(BaseModel):
    schema: str = Field(..., alias="schema_")
    broken_query: str
    last_result: str | None = None
    
    class Config:
        populate_by_name = True

class SQLAction(BaseModel):
    query: str

class SQLReward(BaseModel):
    reward: float