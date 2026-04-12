---
title: SQL Debugger Environment
emoji: 🛠️
colorFrom: blue
colorTo: indigo
sdk: docker
pinned: false
tags:
  - openenv
  - rl
  - sql
  - debugging
  - agent
---

# 🛠️ SQL Debugger — OpenEnv RL Environment

An [OpenEnv](https://github.com/meta-pytorch/OpenEnv) reinforcement learning environment where an AI agent must **debug and fix broken SQL queries**.

The agent receives a broken SQL query + database schema each episode and iteratively submits corrected queries until the result exactly matches the expected output — or it runs out of attempts.

---

## 🎯 Motivation

SQL debugging is a **genuine, high-value daily task** for developers and data engineers:

- Production queries silently return wrong data
- New engineers inherit broken legacy code
- LLMs frequently generate subtly wrong SQL

This environment trains and evaluates agents on exactly this skill, with **deterministic grading** and **5-tier partial reward signals** at every step.

---

## 📋 Environment Summary

| Property              | Value                                 |
| --------------------- | ------------------------------------- |
| Max steps per episode | 5                                     |
| Reward range          | 0.0 – 1.0                             |
| Tasks                 | 3 (easy → medium → hard)              |
| Database              | In-memory SQLite (zero deps)          |
| Server port           | 8000                                  |
| Termination           | Perfect match OR max attempts reached |

---

## 🔁 Action Space

```json
{
  "sql": "SELECT name, salary FROM employees WHERE dept='Engineering' ORDER BY salary DESC"
}
```

| Field | Type   | Description                                 |
| ----- | ------ | ------------------------------------------- |
| `sql` | string | A corrected SQL SELECT statement to execute |

---

## 👁️ Observation Space

| Field              | Type         | Description                                    |
| ------------------ | ------------ | ---------------------------------------------- |
| `task_id`          | string       | Task identifier                                |
| `difficulty`       | string       | `easy` / `medium` / `hard`                     |
| `task_description` | string       | What the query must return                     |
| `schema_ddl`       | string       | CREATE TABLE + INSERT statements               |
| `broken_query`     | string       | The original broken query to fix               |
| `error_message`    | string       | SQLite error from last attempt (empty if none) |
| `execution_result` | list\|null   | Rows from last submitted query                 |
| `expected_result`  | list         | Ground-truth rows to match exactly             |
| `attempt`          | int          | Attempts made this episode                     |
| `max_attempts`     | int          | Max allowed (5)                                |
| `hint`             | string\|null | Optional bug-type hint                         |
| `done`             | bool         | Episode ended                                  |
| `reward`           | float        | Reward from last step                          |

---

## 🏆 Reward Function

| Condition                               | Reward                |
| --------------------------------------- | --------------------- |
| Query errored / no output               | `0.0`                 |
| Wrong row count                         | `0.3`                 |
| Right count, wrong values               | `0.6`                 |
| Right values, wrong order               | `0.8`                 |
| **Perfect match**                       | **`1.0`**             |
| Efficiency penalty (per wasted attempt) | `-0.05 × (attempt−1)` |

Rewards are clamped to `[0.0, 1.0]`. First-attempt correct = `1.0`; second attempt = `0.95`; etc.

---

## 📚 Tasks

### Easy — `task_easy_syntax`

**Bug:** Three keyword typos (`SELEC`, `FORM`, `DESK`)  
**Schema:** `employees(id, name, dept, salary)`  
**Goal:** Return Engineering employees ordered by salary DESC

```sql
-- Broken:
SELEC name, salary FORM employees WHERE dept = 'Engineering' ORDER BY salary DESK;

-- Fixed:
SELECT name, salary FROM employees WHERE dept = 'Engineering' ORDER BY salary DESC;
```

---

### Medium — `task_medium_join`

**Bug:** Wrong JOIN column (`o.id` → `o.customer_id`) + wrong aggregation (`SUM(quantity)` → `SUM(quantity*unit_price)`)  
**Schema:** `customers(id, name)` + `orders(id, customer_id, quantity, unit_price)`

```sql
-- Broken:
SELECT c.name, SUM(o.quantity) AS total_value
FROM customers c JOIN orders o ON c.id = o.id
GROUP BY c.name ORDER BY total_value DESC;

-- Fixed:
SELECT c.name, SUM(o.quantity * o.unit_price) AS total_value
FROM customers c JOIN orders o ON c.id = o.customer_id
GROUP BY c.name ORDER BY total_value DESC;
```

---

### Hard — `task_hard_complex`

**Bug:** 3 simultaneous bugs — NULL not excluded in subquery, LEFT JOIN skews averages, ORDER BY ASC should be DESC  
**Schema:** `products(id, name)` + `reviews(id, product_id, score)` — score is nullable

```sql
-- Broken (3 bugs):
SELECT p.name, AVG(r.score) AS avg_score
FROM products p LEFT JOIN reviews r ON p.id = r.product_id
GROUP BY p.name
HAVING AVG(r.score) > (SELECT AVG(score) FROM reviews)
ORDER BY avg_score ASC;

-- Fixed:
SELECT p.name, AVG(r.score) AS avg_score
FROM products p JOIN reviews r ON p.id = r.product_id
WHERE r.score IS NOT NULL
GROUP BY p.name
HAVING AVG(r.score) > (SELECT AVG(score) FROM reviews WHERE score IS NOT NULL)
ORDER BY avg_score DESC;
```

---

## 🚀 Setup & Usage

### Prerequisites

- Python 3.10+
- Docker Desktop (running)
- Git

### Clone & install

**Linux / Mac:**

```bash
git clone https://github.com/YOUR_USERNAME/my-openenv.git
cd my-openenv/sql_debugger_env
pip install openenv-core
uv sync        # or: pip install -e .
```

**Windows:**

```cmd
git clone https://github.com/YOUR_USERNAME/my-openenv.git
cd my-openenv\sql_debugger_env
pip install openenv-core
pip install -e .
```

### Build & run with Docker

```bash
# Build (run from inside sql_debugger_env/)
docker build -t sql_debugger_env-env:latest -f server/Dockerfile .

# Run
docker run -p 8000:8000 sql_debugger_env-env:latest
```

### Test the server

**Linux / Mac:**

```bash
# Health check
curl http://localhost:8000/health

# Reset — start episode
curl -X POST http://localhost:8000/reset \
  -H "Content-Type: application/json" -d "{}"

# Submit a fix
curl -X POST http://localhost:8000/step \
  -H "Content-Type: application/json" \
  -d '{"action": {"sql": "SELECT name, salary FROM employees WHERE dept='\''Engineering'\'' ORDER BY salary DESC"}}'
```

**Windows (PowerShell):**

```powershell
# Health check
Invoke-RestMethod http://localhost:8000/health

# Reset
Invoke-RestMethod -Uri "http://localhost:8000/reset" -Method POST `
  -ContentType "application/json" -Body "{}"

# Submit a fix
Invoke-RestMethod -Uri "http://localhost:8000/step" -Method POST `
  -ContentType "application/json" `
  -Body '{"action": {"sql": "SELECT name, salary FROM employees WHERE dept=''Engineering'' ORDER BY salary DESC"}}'
```

### Run inference

**Linux / Mac:**

```bash
cd my-openenv   # repo root — where inference.py lives

export HF_TOKEN=your_token_here
export IMAGE_NAME=sql_debugger_env-env:latest
export API_BASE_URL=https://router.huggingface.co/v1
export MODEL_NAME=Qwen/Qwen2.5-72B-Instruct

python inference.py
```

**Windows (Command Prompt):**

```cmd
cd my-openenv

set HF_TOKEN=your_token_here
set IMAGE_NAME=sql_debugger_env-env:latest
set API_BASE_URL=https://router.huggingface.co/v1
set MODEL_NAME=Qwen/Qwen2.5-72B-Instruct

python inference.py
```

**Windows (PowerShell):**

```powershell
cd my-openenv

$env:HF_TOKEN = "your_token_here"
$env:IMAGE_NAME = "sql_debugger_env-env:latest"
$env:API_BASE_URL = "https://router.huggingface.co/v1"
$env:MODEL_NAME = "Qwen/Qwen2.5-72B-Instruct"

python inference.py
```

**Expected output:**

```
[START] task=task_easy_syntax env=sql_debugger model=Qwen/Qwen2.5-72B-Instruct
[STEP] step=1 action=SELECT name... reward=1.00 done=true error=null
[END] success=true steps=1 score=0.200 rewards=1.00
[INFO] task=task_easy_syntax score=0.200
...
[INFO] overall_avg_score=0.253
```

### Validate

```bash
cd my-openenv/sql_debugger_env
openenv validate
# Expected: [OK] sql_debugger: Ready for multi-mode deployment
```

---

## 🤗 Deploy to HuggingFace Spaces

1. Go to [huggingface.co/new-space](https://huggingface.co/new-space) → SDK = **Docker**
2. Push your repo:

```bash
git remote add hf https://huggingface.co/spaces/YOUR_HF_USERNAME/sql-debugger-env
git push hf main
```

3. In Space **Settings → Variables and secrets**, add:

| Variable       | Value                              |
| -------------- | ---------------------------------- |
| `HF_TOKEN`     | Your HuggingFace token             |
| `API_BASE_URL` | `https://router.huggingface.co/v1` |
| `MODEL_NAME`   | `Qwen/Qwen2.5-72B-Instruct`        |
| `IMAGE_NAME`   | `sql_debugger_env-env:latest`      |

4. Wait for the Space to show **"Running"** before submitting.

---

## 📊 Baseline Scores

`Qwen/Qwen2.5-72B-Instruct` · 5 steps max · temperature 0.2

| Task                | Difficulty | Expected Score |
| ------------------- | ---------- | -------------- |
| `task_easy_syntax`  | 🟢 Easy    | ~0.85          |
| `task_medium_join`  | 🟡 Medium  | ~0.65          |
| `task_hard_complex` | 🔴 Hard    | ~0.40          |
| **Overall**         |            | **~0.63**      |

---

## 🗂️ Project Structure

```
my-openenv/
├── inference.py                        ← inference script (repo root)
└── sql_debugger_env/
    ├── models.py                       ← Pydantic Action + Observation
    ├── tasks.py                        ← Task definitions (easy/medium/hard)
    ├── executor.py                     ← SQLite runner + 5-tier grader
    ├── client.py                       ← Async EnvClient
    ├── openenv.yaml                    ← OpenEnv spec metadata
    ├── pyproject.toml                  ← Package config
    ├── uv.lock                         ← Locked dependencies
    └── server/
        ├── app.py                      ← FastAPI server (port 8000)
        ├── sql_debugger_env_environment.py  ← Core environment logic
        ├── Dockerfile                  ← Container definition
        └── requirements.txt           ← Server dependencies
```

---

## 🔌 API Endpoints

| Method | Endpoint    | Description                         |
| ------ | ----------- | ----------------------------------- |
| GET    | `/health`   | `{"status": "healthy"}`             |
| GET    | `/metadata` | Name, description, version          |
| GET    | `/schema`   | Action + Observation schemas        |
| POST   | `/reset`    | Start new episode                   |
| POST   | `/step`     | Submit `{"action": {"sql": "..."}}` |
| GET    | `/state`    | Episode state (id, step count)      |

---

## ⚙️ Environment Variables

| Variable            | Required | Default                            | Description                             |
| ------------------- | -------- | ---------------------------------- | --------------------------------------- |
| `HF_TOKEN`          | ✅       | —                                  | HuggingFace token (or `OPENAI_API_KEY`) |
| `API_BASE_URL`      | ❌       | `https://router.huggingface.co/v1` | LLM endpoint                            |
| `MODEL_NAME`        | ❌       | `Qwen/Qwen2.5-72B-Instruct`        | Model identifier                        |
| `IMAGE_NAME`        | ❌       | `sql_debugger_env-env:latest`      | Docker image                            |
| `SQL_DEBUGGER_TASK` | ❌       | `task_easy_syntax`                 | Which task to serve                     |
| `PORT`              | ❌       | `8000`                             | Server port                             |
