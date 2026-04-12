"""
SQL Debugger — Task definitions (easy / medium / hard).

Each task has a broken query the agent must fix.
Grading is fully deterministic: compare actual vs expected rows.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class Task:
    id: str
    difficulty: str
    description: str
    schema_ddl: str
    broken_query: str
    expected_result: List[Dict[str, Any]]
    hint: Optional[str] = None
    bug_type: str = ""


# ── EASY: three keyword typos ─────────────────────────────────────────────────
TASK_EASY = Task(
    id="task_easy_syntax",
    difficulty="easy",
    description=(
        "Return the name and salary of every employee in the 'Engineering' department, "
        "ordered by salary descending. Fix the query — it has three keyword typos."
    ),
    schema_ddl="""
CREATE TABLE employees (
    id      INTEGER PRIMARY KEY,
    name    TEXT    NOT NULL,
    dept    TEXT    NOT NULL,
    salary  REAL    NOT NULL
);
INSERT INTO employees VALUES (1, 'Alice',   'Engineering', 95000);
INSERT INTO employees VALUES (2, 'Bob',     'Engineering', 88000);
INSERT INTO employees VALUES (3, 'Carol',   'Marketing',   72000);
INSERT INTO employees VALUES (4, 'Dave',    'Engineering', 102000);
INSERT INTO employees VALUES (5, 'Eve',     'HR',          65000);
""",
    broken_query="SELEC name, salary FORM employees WHERE dept = 'Engineering' ORDER BY salary DESK;",
    expected_result=[
        {"name": "Dave",  "salary": 102000.0},
        {"name": "Alice", "salary": 95000.0},
        {"name": "Bob",   "salary": 88000.0},
    ],
    hint="Three SQL keywords are misspelled: SELEC, FORM, DESK.",
    bug_type="syntax_typo",
)

# ── MEDIUM: wrong JOIN column + wrong aggregation ─────────────────────────────
TASK_MEDIUM = Task(
    id="task_medium_join",
    difficulty="medium",
    description=(
        "Return each customer's name and the total value of their orders "
        "(quantity × unit_price), ordered by total_value descending. "
        "The query has a wrong JOIN condition and a wrong aggregation expression."
    ),
    schema_ddl="""
CREATE TABLE customers (
    id    INTEGER PRIMARY KEY,
    name  TEXT    NOT NULL
);
CREATE TABLE orders (
    id           INTEGER PRIMARY KEY,
    customer_id  INTEGER NOT NULL,
    quantity     INTEGER NOT NULL,
    unit_price   REAL    NOT NULL
);
INSERT INTO customers VALUES (1, 'Acme Corp');
INSERT INTO customers VALUES (2, 'Globex');
INSERT INTO customers VALUES (3, 'Initech');
INSERT INTO orders VALUES (1, 1, 3, 250.0);
INSERT INTO orders VALUES (2, 1, 1, 500.0);
INSERT INTO orders VALUES (3, 2, 5, 100.0);
INSERT INTO orders VALUES (4, 3, 2, 750.0);
""",
    broken_query=(
        "SELECT c.name, SUM(o.quantity) AS total_value "
        "FROM customers c "
        "JOIN orders o ON c.id = o.id "
        "GROUP BY c.name "
        "ORDER BY total_value DESC;"
    ),
    expected_result=[
        {"name": "Initech",   "total_value": 1500.0},
        {"name": "Acme Corp", "total_value": 1250.0},
        {"name": "Globex",    "total_value": 500.0},
    ],
    hint="Fix the JOIN column (o.id → o.customer_id) and the aggregation (SUM quantity → SUM quantity*unit_price).",
    bug_type="wrong_join_wrong_aggregation",
)

# ── HARD: NULL handling + HAVING + ORDER BY direction ────────────────────────
TASK_HARD = Task(
    id="task_hard_complex",
    difficulty="hard",
    description=(
        "Return the name and average review score for every product whose average score "
        "is strictly above the overall average score across all products. "
        "NULL scores must be ignored. Results ordered by avg_score descending. "
        "There are three simultaneous bugs — find and fix all of them."
    ),
    schema_ddl="""
CREATE TABLE products (
    id    INTEGER PRIMARY KEY,
    name  TEXT    NOT NULL
);
CREATE TABLE reviews (
    id         INTEGER PRIMARY KEY,
    product_id INTEGER NOT NULL,
    score      REAL             -- nullable
);
INSERT INTO products VALUES (1, 'Widget A');
INSERT INTO products VALUES (2, 'Widget B');
INSERT INTO products VALUES (3, 'Widget C');
INSERT INTO products VALUES (4, 'Widget D');
INSERT INTO reviews VALUES (1,  1, 4.5);
INSERT INTO reviews VALUES (2,  1, 5.0);
INSERT INTO reviews VALUES (3,  2, 3.0);
INSERT INTO reviews VALUES (4,  2, 3.5);
INSERT INTO reviews VALUES (5,  3, 4.0);
INSERT INTO reviews VALUES (6,  3, NULL);
INSERT INTO reviews VALUES (7,  4, 2.0);
INSERT INTO reviews VALUES (8,  4, 2.5);
""",
    broken_query=(
        "SELECT p.name, AVG(r.score) AS avg_score "
        "FROM products p "
        "LEFT JOIN reviews r ON p.id = r.product_id "
        "GROUP BY p.name "
        "HAVING AVG(r.score) > (SELECT AVG(score) FROM reviews) "
        "ORDER BY avg_score ASC;"
    ),
    expected_result=[
        {"name": "Widget A", "avg_score": 4.75},
        {"name": "Widget C", "avg_score": 4.0},
    ],
    hint=(
        "Three bugs: (1) subquery must exclude NULLs with WHERE score IS NOT NULL, "
        "(2) use INNER JOIN instead of LEFT JOIN so NULL scores don't skew group averages, "
        "(3) ORDER BY should be DESC not ASC."
    ),
    bug_type="null_join_order",
)

ALL_TASKS: Dict[str, Task] = {
    TASK_EASY.id:   TASK_EASY,
    TASK_MEDIUM.id: TASK_MEDIUM,
    TASK_HARD.id:   TASK_HARD,
}

# For convenient iteration in difficulty order
TASK_ORDER = [TASK_EASY.id, TASK_MEDIUM.id, TASK_HARD.id]
