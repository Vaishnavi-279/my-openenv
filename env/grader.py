def grade_query(agent_query: str, expected_query: str) -> float:
    """
    Simple deterministic grader.
    """

    agent = agent_query.strip().lower()
    expected = expected_query.strip().lower()

    if agent == expected:
        return 1.0

    if "select" in agent and "from" in agent:
        return 0.4

    if "where" in agent:
        return 0.7

    return 0.0