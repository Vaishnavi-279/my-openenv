# server/app.py

from fastapi import FastAPI
from env.environment import SQLEnv
from env.models import SQLAction

app = FastAPI()
env = SQLEnv()

@app.get("/")
async def root():
    return {
        "message": "SQL Debugger Environment API",
        "endpoints": {
            "POST /reset": "Reset environment and get a new task",
            "POST /step": "Submit a corrected query (body: {\"query\": \"...\"})",
            "POST /state": "Get current training state"
        }
    }

@app.get("/reset")
@app.post("/reset")
async def reset():
    result = await env.reset()
    return {
        "schema": result["observation"].schema,
        "broken_query": result["observation"].broken_query,
        "reward": result["reward"],
        "done": result["done"],
        "info": result["info"]
    }

@app.post("/step")
async def step(action: SQLAction):
    result = await env.step(action)
    return {
        "schema": result["observation"].schema,
        "broken_query": result["observation"].broken_query,
        "last_result": result["observation"].last_result,
        "reward": result["reward"],
        "done": result["done"],
        "info": result["info"]
    }

@app.get("/state")
@app.post("/state")
async def state():
    return env.state()

def main():
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)

# This is REQUIRED for validator
if __name__ == "__main__":
    main()