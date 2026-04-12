# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""
Data models for the Sql Debugger Env Environment.

The sql_debugger_env environment is a simple test environment that echoes back messages.
"""

from typing import Any, Dict, List, Optional
from openenv.core.env_server.types import Action, Observation
from pydantic import Field


class SqlDebuggerAction(Action):
    """Action for the Sql Debugger Env environment - just a message to echo."""

    sql: str = Field(..., description="SQL query to execute")


class SqlDebuggerObservation(Observation):
    """Observation from the Sql Debugger Env environment - the echoed message."""

    # echoed_message: str = Field(default="", description="The echoed message")
    # message_length: int = Field(default=0, description="Length of the echoed message")
    task_id: str = Field(default="", description="Unique task identifier.")
    difficulty: str = Field(default="", description="Task difficulty: easy / medium / hard.")
    task_description: str = Field(default="", description="Natural language description of what the query must do.")
    schema_ddl: str = Field(default="", description="CREATE TABLE + INSERT statements the query runs against.")
    broken_query: str = Field(default="", description="The original broken query the agent must fix.")
    error_message: str = Field(default="", description="SQLite error from the last submitted query (empty if none).")
    execution_result: Optional[List[Dict[str, Any]]] = Field(
        default=None, description="Rows returned by the last submitted query (None if it errored)."
    )
    expected_result: Optional[List[Dict[str, Any]]] = Field(
        default=None, description="Ground-truth rows the agent must match exactly."
    )
    attempt: int = Field(default=0, description="Number of step() calls made this episode.")
    max_attempts: int = Field(default=5, description="Maximum attempts allowed per episode.")
    hint: Optional[str] = Field(default=None, description="Optional hint about the type of bug.")
    is_correct: bool = Field(default=False, description="Whether the last submitted query is correct.")
