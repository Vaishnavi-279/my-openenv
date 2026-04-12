"""
SQL Debugger Environment — Inference Script
"""

import asyncio
import os
import sys
import textwrap
from typing import List, Optional

from openai import OpenAI

# ── Ensure sql_debugger_env is importable ─────────────────────────────────────
# Add the directory containing sql_debugger_env to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sql_debugger_env.client import SqlDebuggerEnv
from sql_debugger_env.models import SqlDebuggerAction

# ── Environment variables ──────────────────────────────────────────────────────
IMAGE_NAME   = os.getenv("IMAGE_NAME", "sql_debugger_env-env:latest")
API_KEY      = os.getenv("HF_TOKEN") or os.getenv("OPENAI_API_KEY")
API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME   = os.getenv("MODEL_NAME",   "Qwen/Qwen2.5-72B-Instruct")

BENCHMARK             = "sql_debugger"
MAX_STEPS             = 5
TEMPERATURE           = 0.2
MAX_TOKENS            = 512
SUCCESS_SCORE_THRESHOLD = 0.1
MAX_TOTAL_REWARD      = float(MAX_STEPS)

ALL_TASK_IDS = [
    "task_easy_syntax",
    "task_medium_join",
    "task_hard_complex",
]

# ── Logging ────────────────────────────────────────────────────────────────────

def log_start(task: str, env: str, model: str) -> None:
    print(f"[START] task={task} env={env} model={model}", flush=True)

def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str]) -> None:
    action_clean = action.replace("\n", " ").replace("\r", " ").strip()
    error_val = error if error else "null"
    print(
        f"[STEP] step={step} action={action_clean} "
        f"reward={reward:.2f} done={str(done).lower()} error={error_val}",
        flush=True,
    )

def log_end(success: bool, steps: int, score: float, rewards: List[float]) -> None:
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(
        f"[END] success={str(success).lower()} steps={steps} "
        f"score={score:.3f} rewards={rewards_str}",
        flush=True,
    )

# ── Prompt ─────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = textwrap.dedent("""
    You are an expert SQL debugging assistant.
    You will receive a broken SQL query, the database schema, and feedback from previous attempts.
    Return ONLY the corrected SQL query — no explanation, no markdown, no code fences.
    The query must be a single valid SQLite SELECT statement.
""").strip()


def build_prompt(obs) -> str:
    return textwrap.dedent(f"""
        TASK ({obs.difficulty}):
        {obs.task_description}

        SCHEMA:
        {obs.schema_ddl.strip()}

        ORIGINAL BROKEN QUERY:
        {obs.broken_query}

        ATTEMPT: {obs.attempt} / {obs.max_attempts}
        LAST ERROR:  {obs.error_message or 'none'}
        LAST RESULT: {obs.execution_result or 'no result'}
        EXPECTED:    {obs.expected_result}
        HINT:        {obs.hint or 'none'}

        Return ONLY the corrected SQL query:
    """).strip()


def get_sql(client: OpenAI, obs) -> str:
    try:
        resp = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": build_prompt(obs)},
            ],
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
            stream=False,
        )
        text = (resp.choices[0].message.content or "").strip()
        if text.startswith("```"):
            text = "\n".join(
                l for l in text.split("\n") if not l.strip().startswith("```")
            ).strip()
        return text or obs.broken_query
    except Exception as exc:
        print(f"[DEBUG] LLM call failed: {exc}", flush=True)
        return obs.broken_query


# ── Single task episode ────────────────────────────────────────────────────────

async def run_task(client: OpenAI, task_id: str) -> float:
    env = await SqlDebuggerEnv.from_docker_image(
        IMAGE_NAME,
        env_vars={"SQL_DEBUGGER_TASK": task_id},
    )

    rewards:    List[float] = []
    steps_taken = 0
    score       = 0.0
    success     = False

    log_start(task=task_id, env=BENCHMARK, model=MODEL_NAME)

    try:
        result = await env.reset()
        obs    = result.observation

        for step in range(1, MAX_STEPS + 1):
            if result.done:
                break

            sql    = get_sql(client, obs)
            result = await env.step(SqlDebuggerAction(sql=sql))
            obs    = result.observation

            reward = result.reward or 0.0
            done   = result.done
            error  = obs.error_message if obs.error_message else None

            rewards.append(reward)
            steps_taken = step

            log_step(step=step, action=sql, reward=reward, done=done, error=error)

            if done:
                break

        score   = sum(rewards) / MAX_TOTAL_REWARD if MAX_TOTAL_REWARD > 0 else 0.0
        score   = min(max(score, 0.0), 1.0)
        success = score >= SUCCESS_SCORE_THRESHOLD or (len(rewards) > 0 and max(rewards) >= 1.0)

    except Exception as exc:
        print(f"[DEBUG] Task {task_id} failed: {exc}", flush=True)
    finally:
        try:
            await env.close()
        except Exception as e:
            print(f"[DEBUG] env.close() error: {e}", flush=True)
        log_end(success=success, steps=steps_taken, score=score, rewards=rewards)

    return score


# ── Main ───────────────────────────────────────────────────────────────────────

async def main() -> None:
    if not API_KEY:
        raise ValueError("HF_TOKEN or OPENAI_API_KEY must be set")

    client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)

    all_scores: List[float] = []
    for task_id in ALL_TASK_IDS:
        score = await run_task(client, task_id)
        all_scores.append(score)
        print(f"[INFO] task={task_id} score={score:.3f}", flush=True)

    avg = sum(all_scores) / len(all_scores)
    print(f"[INFO] overall_avg_score={avg:.3f}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())