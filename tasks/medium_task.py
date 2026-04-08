TASK = {
    "schema": "orders(id, user_id, amount)",
    "broken_query": "SELECT amount FORM orders WER amount > 100",
    "expected_query": "SELECT amount FROM orders WHERE amount > 100"
}