TASK = {
    "schema": "users(id, name, age)",
    "broken_query": "SELEC name FRM users",
    "expected_query": "SELECT name FROM users"
}