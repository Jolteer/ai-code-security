import sqlite3

from fastapi import FastAPI

app = FastAPI()


@app.get("/users/search")
def search_users(name: str):
    con = sqlite3.connect("app.db")
    try:
        # VULNERABLE (CWE-89): user input is formatted directly into SQL.
        rows = con.execute(
            f"SELECT id, name, email FROM users WHERE name = '{name}'"
        ).fetchall()
    finally:
        con.close()
    return [{"id": r[0], "name": r[1], "email": r[2]} for r in rows]
