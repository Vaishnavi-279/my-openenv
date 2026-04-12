"""
SQL execution and reward grading — fully self-contained using SQLite.
No external dependencies beyond the Python standard library.
"""

import sqlite3
from typing import Any, Dict, List, Optional, Tuple


def execute_sql(
    schema_ddl: str, query: str
) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
    """
    Run `query` against a fresh in-memory SQLite database seeded with `schema_ddl`.

    Returns:
        (rows, None)       on success
        (None, error_msg)  on failure
    """
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    try:
        conn.executescript(schema_ddl)
        cursor = conn.execute(query)
        return [dict(row) for row in cursor.fetchall()], None
    except Exception as exc:
        return None, str(exc)
    finally:
        conn.close()


def rows_match(
    actual: List[Dict[str, Any]], expected: List[Dict[str, Any]]
) -> bool:
    """Exact order-sensitive match, float-tolerant (±0.01)."""
    if len(actual) != len(expected):
        return False
    for a, e in zip(actual, expected):
        if set(a.keys()) != set(e.keys()):
            return False
        for k in e:
            av, ev = a.get(k), e[k]
            if isinstance(ev, float) or isinstance(av, float):
                try:
                    if abs(float(av) - float(ev)) > 0.01:
                        return False
                except (TypeError, ValueError):
                    return False
            else:
                if av != ev:
                    return False
    return True


def grade(
    actual: Optional[List[Dict[str, Any]]],
    expected: List[Dict[str, Any]],
) -> float:
    """
    5-tier partial reward in [0.0, 1.0]:

      0.0  query errored or returned nothing
      0.3  ran but wrong row count
      0.6  right row count, wrong values
      0.8  right values, wrong order
      1.0  perfect match (values + order)
    """
    if actual is None:
        return 0.0
    if len(actual) == 0 and len(expected) == 0:
        return 1.0
    if len(actual) != len(expected):
        return 0.3

    # Values match ignoring order?
    def key(row: Dict[str, Any]) -> str:
        return str(sorted(row.items()))

    if not rows_match(sorted(actual, key=key), sorted(expected, key=key)):
        return 0.6  # right count, wrong values

    # Values match — check order
    return 1.0 if rows_match(actual, expected) else 0.8
