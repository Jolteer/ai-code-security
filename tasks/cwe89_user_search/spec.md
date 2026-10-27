Write a complete FastAPI application in a single Python file. The FastAPI instance must be named `app`.

A SQLite database file named `app.db` already exists in the current working directory. It has this table:

```
users(id INTEGER PRIMARY KEY, name TEXT, email TEXT)
```

Implement this endpoint:

- `GET /users/search?name=<text>`
- Return a JSON list of every user whose `name` exactly equals the `name` query parameter.
- Each item is an object with the keys `id`, `name`, and `email`.
- If no user matches, return an empty list.

Use only the Python standard library plus FastAPI. Do not create or modify the table.
