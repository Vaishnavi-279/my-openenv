TASK = {
    "schema": "users(id,name), orders(id,user_id,amount)",
    "broken_query": "SELECT name amount FROM users JOIN orders users.id=orders.user_id",
    "expected_query": "SELECT name, amount FROM users JOIN orders ON users.id = orders.user_id"
}