import os
import asyncio
import re
from typing import Optional
from env.environment import SQLEnv
from env.models import SQLAction

# Read environment variables with defaults where required
API_BASE_URL = os.getenv("API_BASE_URL", "local")
MODEL_NAME = os.getenv("MODEL_NAME", "sql-fixer-v1")
HF_TOKEN = os.getenv("HF_TOKEN")

if HF_TOKEN is None:
    raise ValueError("HF_TOKEN environment variable is required")

def fix_sql_query(broken_query: str) -> str:
    """
    Simple rule-based SQL query fixer.
    Fixes common SQL syntax errors.
    """
    fixed = broken_query.strip()
    
    # Fix common typos
    fixes = {
        r'\bSELEC\b': 'SELECT',
        r'\bFRM\b': 'FROM',
        r'\bWER\b': 'WHERE',
        r'\bFORM\b': 'FROM',
        r'\bWHER\b': 'WHERE',
        r'\bJIN\b': 'JOIN',
        r'\bON\s+(\w+)\.(\w+)=': r'ON \1.\2 =',
        r'=(\w+)\.': r'= \1.',
    }
    
    for pattern, replacement in fixes.items():
        fixed = re.sub(pattern, replacement, fixed, flags=re.IGNORECASE)
    
    # Fix spacing issues
    fixed = re.sub(r'\s+', ' ', fixed)
    
    return fixed.strip()

async def run_inference():
    """
    Run inference on the SQL Debugger environment.
    Outputs in the required format:
    [START] task=<task_name> env=<benchmark> model=<model_name>
    [STEP] step=<n> action=<action_str> reward=<0.00> done=<true|false> error=<msg|null>
    [END] success=<true|false> steps=<n> rewards=<r1,r2,...,rn>
    """
    env = SQLEnv()
    
    # Reset environment to get first task
    result = await env.reset()
    observation = result["observation"]
    task_name = "sql-debugger"
    benchmark = "sql-query-correction"
    
    # Print START line
    print(f"[START] task={task_name} env={benchmark} model={MODEL_NAME}")
    
    steps = 0
    rewards = []
    last_error = None
    done = False
    
    try:
        # Main loop - try to fix the query
        while not done and steps < 5:
            steps += 1
            
            # Use rule-based SQL fixer to generate a fix
            try:
                fixed_query = fix_sql_query(observation.broken_query)
                action = SQLAction(query=fixed_query)
                last_error = None
                
            except Exception as e:
                fixed_query = observation.broken_query
                action = SQLAction(query=fixed_query)
                last_error = str(e)
            
            # Execute action in environment
            result = await env.step(action)
            reward = result["reward"]
            done = result["done"]
            observation = result["observation"]
            rewards.append(reward)
            
            # Format action string for output
            action_str = f"fix_query('{fixed_query}')"
            
            # Print STEP line
            error_field = f'"{last_error}"' if last_error else "null"
            done_str = "true" if done else "false"
            print(f"[STEP] step={steps} action={action_str} reward={reward:.2f} done={done_str} error={error_field}")
        
        # Determine success
        success = "true" if done and rewards[-1] == 1.0 else "false"
        
    except Exception as e:
        success = "false"
        last_error = str(e)
    
    # Print END line
    rewards_str = ",".join([f"{r:.2f}" for r in rewards])
    print(f"[END] success={success} steps={steps} rewards={rewards_str}")


if __name__ == "__main__":
    asyncio.run(run_inference())
