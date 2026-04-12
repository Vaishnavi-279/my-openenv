"""
SQL Debugger Environment — Inference Script
============================================
Place this file at the ROOT of your project (my-openenv/inference.py).

Required environment variables:
  HF_TOKEN       — HuggingFace API key (mandatory)
  API_BASE_URL   — LLM API endpoint   (default: https://router.huggingface.co/v1)
  MODEL_NAME     — Model identifier   (default: Qwen/Qwen2.5-72B-Instruct)
  IMAGE_NAME     — Docker image name  (default: sql_debugger_env-env:latest)

Stdout format (mandatory):
  [START] task=<name> env=<benchmark> model=<model>
  [STEP]  step=<n> action=<sql> reward=<0.00> done=<true|false> error=<msg|null>
  [END]   success=<true|false> steps=<n> score=<0.000> rewards=<r1,r2,...>
"""

import asyncio
import os
import sys
import textwrap
from typing import List, Optional

from openai import OpenAI

# ── Add sql_debugger_env to path when running from repo root ──────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "sql_debugger_env"))

from sql_debugger_env.client import SqlDebuggerEnv
from sql_debugger_env.models import SqlDebuggerAction

# ── Environment variables ──────────────────────────────────────────────────────
IMAGE_NAME   = os.getenv("IMAGE_NAME", "sql_debugger_env-env:latest")
HF_TOKEN     = os.getenv("HF_TOKEN") or os.getenv("OPENAI_API_KEY")
API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME   = os.getenv("MODEL_NAME",   "Qwen/Qwen2.5-72B-Instruct")

BENCHMARK             = "sql_debugger"
MAX_STEPS             = 5
TEMPERATURE           = 0.2
MAX_TOKENS            = 512
SUCCESS_SCORE_THRESHOLD = 0.5
MAX_TOTAL_REWARD      = float(MAX_STEPS)   # perfect score each step = 1.0 × 5

ALL_TASK_IDS = [
    "task_easy_syntax",
    "task_medium_join",
    "task_hard_complex",
]

# ── Mandatory stdout helpers ───────────────────────────────────────────────────

def log_start(task: str, env: str, model: str) -> None:
    print(f"[START] task={task} env={env} model={model}", flush=True)


def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str]) -> None:
    action_clean = action.replace("\n", " ").replace("\r", " ").strip()
    print(
        f"[STEP] step={step} action={action_clean} "
        f"reward={reward:.2f} done={str(done).lower()} error={error if error else 'null'}",
        flush=True,
    )


def log_end(success: bool, steps: int, score: float, rewards: List[float]) -> None:
    print(
        f"[END] success={str(success).lower()} steps={steps} "
        f"score={score:.3f} rewards={','.join(f'{r:.2f}' for r in rewards)}",
        flush=True,
    )

# ── Prompt ─────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = textwrap.dedent("""
    You are an expert SQL debugging assistant.
    You will receive a broken SQL query, the database schema, and feedback from previous attempts.
    Your job is to return ONLY the corrected SQL query — no explanation, no markdown, no code fences.
    The query must be a single valid SQLite SELECT statement that returns the expected rows in the correct order.
""").strip()


def build_prompt(obs) -> str:
    history_block = ""
    actual_str = str(obs.execution_result) if obs.execution_result is not None else "no result"
    error_str  = obs.error_message if obs.error_message else "none"
    return textwrap.dedent(f"""
        TASK ({obs.difficulty}):
        {obs.task_description}

        SCHEMA:
        {obs.schema_ddl.strip()}

        ORIGINAL BROKEN QUERY:
        {obs.broken_query}

        ATTEMPT: {obs.attempt} / {obs.max_attempts}
        LAST ERROR:  {error_str}
        LAST RESULT: {actual_str}
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
        # Strip accidental markdown fences
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
        success = score >= SUCCESS_SCORE_THRESHOLD

    finally:
        try:
            await env.close()
        except Exception as exc:
            print(f"[DEBUG] env.close() error: {exc}", flush=True)
        log_end(success=success, steps=steps_taken, score=score, rewards=rewards)

    return score

# ── Main ───────────────────────────────────────────────────────────────────────

async def main() -> None:
    if not HF_TOKEN:
        raise ValueError("HF_TOKEN or OPENAI_API_KEY must be set")

    client = OpenAI(base_url=API_BASE_URL, api_key=HF_TOKEN)

    all_scores: List[float] = []
    for task_id in ALL_TASK_IDS:
        score = await run_task(client, task_id)
        all_scores.append(score)
        print(f"[INFO] task={task_id} score={score:.3f}", flush=True)

    avg = sum(all_scores) / len(all_scores)
    print(f"[INFO] overall_avg_score={avg:.3f}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
