import sqlite3


def seed(path):
    con = sqlite3.connect(path / "app.db")
    con.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, email TEXT)")
    con.executemany(
        "INSERT INTO users (name, email) VALUES (?, ?)",
        [
            ("Alice", "alice@example.com"),
            ("Bob", "bob@example.com"),
            ("Carol", "carol@example.com"),
        ],
    )
    con.commit()
    con.close()
