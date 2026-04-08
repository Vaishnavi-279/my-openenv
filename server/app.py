from fastapi import FastAPI
from env.environment import SQLEnv

app = FastAPI()

env = SQLEnv()

@app.post("/reset")
async def reset():
    return await env.reset()

@app.post("/step")
async def step(action: dict):
    return await env.step(action)