# # Copyright (c) Meta Platforms, Inc. and affiliates.
# # All rights reserved.
# #
# # This source code is licensed under the BSD-style license found in the
# # LICENSE file in the root directory of this source tree.

# """
# Sql Debugger Env Environment Implementation.

# A simple test environment that echoes back messages sent to it.
# Perfect for testing HTTP server infrastructure.
# """

# import os
# from uuid import uuid4

# from openenv.core.env_server.interfaces import Environment
# from openenv.core.env_server.types import State

# try:
#     from ..executor import execute_sql, grade, rows_match
#     from ..models import SqlDebuggerAction, SqlDebuggerObservation
#     from ..tasks import ALL_TASKS, TASK_ORDER, Task
# except ImportError:
#     from executor import execute_sql, grade, rows_match
#     from models import SqlDebuggerAction, SqlDebuggerObservation
#     from tasks import ALL_TASKS, TASK_ORDER, Task

# MAX_ATTEMPTS = 5
# _DEFAULT_TASK = os.getenv("SQL_DEBUGGER_TASK", "task_easy_syntax")


# class SqlDebuggerEnvironment(Environment):
#     """
#     A simple echo environment that echoes back messages.

#     This environment is designed for testing the HTTP server infrastructure.
#     It maintains minimal state and simply echoes back whatever message it receives.

#     Example:
#         >>> env = SqlDebuggerEnvironment()
#         >>> obs = env.reset()
#         >>> print(obs.echoed_message)  # "Sql Debugger Env environment ready!"
#         >>>
#         >>> obs = env.step(SqlDebuggerAction(message="Hello"))
#         >>> print(obs.echoed_message)  # "Hello"
#         >>> print(obs.message_length)  # 5
#     """

#     # Enable concurrent WebSocket sessions.
#     # Set to True if your environment isolates state between instances.
#     # When True, multiple WebSocket clients can connect simultaneously, each
#     # getting their own environment instance (when using factory mode in app.py).
#     SUPPORTS_CONCURRENT_SESSIONS: bool = True

#     def __init__(self):
#         """Initialize the sql_debugger_env environment."""
#         self._state = State(episode_id=str(uuid4()), step_count=0)
#         self._reset_count = 0

#     def reset(self) -> SqlDebuggerObservation:
#         """
#         Reset the environment.

#         Returns:
#             SqlDebuggerObservation with a ready message
#         """
#         self._state = State(episode_id=str(uuid4()), step_count=0)
#         self._reset_count += 1

#         return SqlDebuggerObservation(
#             echoed_message="Sql Debugger Env environment ready!",
#             message_length=0,
#             done=False,
#             reward=0.0,
#         )

#     def step(self, action: SqlDebuggerAction) -> SqlDebuggerObservation:  # type: ignore[override]
#         """
#         Execute a step in the environment by echoing the message.

#         Args:
#             action: SqlDebuggerAction containing the message to echo

#         Returns:
#             SqlDebuggerObservation with the echoed message and its length
#         """
#         self._state.step_count += 1

#         message = action.message
#         length = len(message)

#         # Simple reward: longer messages get higher rewards
#         reward = length * 0.1

#         return SqlDebuggerObservation(
#             echoed_message=message,
#             message_length=length,
#             done=False,
#             reward=reward,
#             metadata={"original_message": message, "step": self._state.step_count},
#         )

#     @property
#     def state(self) -> State:
#         """
#         Get the current environment state.

#         Returns:
#             Current State with episode_id and step_count
#         """
#         return self._state

"""
SQL Debugger Environment Implementation.
"""

import os
from uuid import uuid4

from openenv.core.env_server.interfaces import Environment
from openenv.core.env_server.types import State

try:
    from ..executor import execute_sql, grade, rows_match
    from ..models import SqlDebuggerAction, SqlDebuggerObservation
    from ..tasks import ALL_TASKS, Task
except ImportError:
    from executor import execute_sql, grade, rows_match
    from models import SqlDebuggerAction, SqlDebuggerObservation
    from tasks import ALL_TASKS, Task

MAX_ATTEMPTS = 5


class SqlDebuggerEnvironment(Environment):
    """
    SQL Debugger RL Environment.

    The agent receives a broken SQL query and must fix it within MAX_ATTEMPTS.
    Reward is shaped across the full trajectory — not just binary end-of-episode.
    """

    SUPPORTS_CONCURRENT_SESSIONS: bool = True

    def __init__(self):
        self._task: Task = ALL_TASKS[os.getenv("SQL_DEBUGGER_TASK", "task_easy_syntax")]
        self._state = State(episode_id=str(uuid4()), step_count=0)
        self._attempt: int = 0
        self._done: bool = False
        self._last_error: str = ""
        self._last_result = None

    def reset(self) -> SqlDebuggerObservation:
        task_id = os.getenv("SQL_DEBUGGER_TASK", "task_easy_syntax")
        self._task = ALL_TASKS.get(task_id, ALL_TASKS["task_easy_syntax"])
        self._state = State(episode_id=str(uuid4()), step_count=0)
        self._attempt = 0
        self._done = False
        self._last_error = ""
        self._last_result = None
        return self._observe(reward=0.0)

    def step(self, action: SqlDebuggerAction) -> SqlDebuggerObservation:  # type: ignore[override]
        if self._done:
            return self._observe(reward=0.0)

        self._attempt += 1
        self._state.step_count += 1

        rows, error = execute_sql(self._task.schema_ddl, action.sql.strip())
        self._last_error = error or ""
        self._last_result = rows

        base = grade(rows, self._task.expected_result)
        penalty = 0.05 * max(0, self._attempt - 1)
        reward = round(max(0.0, min(1.0, base - penalty)), 4)

        perfect = rows is not None and rows_match(rows, self._task.expected_result)
        self._done = perfect or (self._attempt >= MAX_ATTEMPTS)

        return self._observe(reward=reward)

    @property
    def state(self) -> State:
        return self._state

    def _observe(self, reward: float) -> SqlDebuggerObservation:
        return SqlDebuggerObservation(
            task_id=self._task.id,
            difficulty=self._task.difficulty,
            task_description=self._task.description,
            schema_ddl=self._task.schema_ddl,
            broken_query=self._task.broken_query,
            error_message=self._last_error,
            execution_result=self._last_result,
            expected_result=self._task.expected_result,
            attempt=self._attempt,
            max_attempts=MAX_ATTEMPTS,
            hint=self._task.hint,
            is_correct=self._done and self._last_result is not None and rows_match(self._last_result, self._task.expected_result),
            done=self._done,
            reward=reward,
        )