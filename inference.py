import os
import asyncio
from typing import Optional
from transformers import pipeline
from env.environment import SQLEnv
from env.models import SQLAction

# Read environment variables with defaults where required
API_BASE_URL = os.getenv("API_BASE_URL", "local")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt2")
HF_TOKEN = os.getenv("HF_TOKEN")

if HF_TOKEN is None:
    raise ValueError("HF_TOKEN environment variable is required")

# Initialize local text generation pipeline
try:
    llm = pipeline("text-generation", model=MODEL_NAME, device=-1)  # CPU only
except Exception as e:
    # Fallback to smaller model if specified model fails
    print(f"Warning: Could not load {MODEL_NAME}, using distilgpt2 instead")
    llm = pipeline("text-generation", model="distilgpt2", device=-1)

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
            
            # Use LLM to generate a fix for the broken query
            prompt = f"""Fix this SQL query:
Broken: {observation.broken_query}
Schema: {observation.schema}
Fixed: """
            
            try:
                response = llm(
                    prompt,
                    max_length=100,
                    do_sample=False,
                    num_return_sequences=1
                )
                
                generated_text = response[0]["generated_text"]
                # Extract just the fixed query part
                if "Fixed: " in generated_text:
                    fixed_query = generated_text.split("Fixed: ")[1].strip()
                else:
                    fixed_query = generated_text.replace(prompt, "").strip()
                
                # Clean up the query (remove extra text)
                if "\n" in fixed_query:
                    fixed_query = fixed_query.split("\n")[0]
                    
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
