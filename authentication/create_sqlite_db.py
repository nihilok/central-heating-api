import sqlite3

from constants import USER_DB


def create_user_table():
    SQL = """CREATE TABLE IF NOT EXISTS users (
        username text PRIMARY KEY,
        password text NOT NULL
    );"""

    db = sqlite3.connect(USER_DB)
    cursor = db.cursor()
    cursor.execute(SQL)


if __name__ == "__main__":
    create_user_table()
