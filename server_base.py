from flask import Flask
from flask import request, abort
import json
import sqlite3

app = Flask(__name__)

NAME_FILE = 'main.db'
def create_users_table():
    conn = sqlite3.connect(NAME_FILE)
    cursor = conn.cursor()
    sql = '''CREATE TABLE IF NOT EXISTS USERS(
    ID INTEGER PRIMARY KEY AUTOINCREMENT,
    USERNAME          TEXT    NOT NULL
    );'''
    cursor.execute(sql)
    conn.commit()

def insert_into_users_table(username):
    conn = sqlite3.connect(NAME_FILE)
    cursor = conn.cursor()
    sql = "INSERT INTO USERS (USERNAME) VALUES(?)"
    cursor.execute(sql, (username, ))
    conn.commit()

def get_user_from_users_table(username):
    conn = sqlite3.connect(NAME_FILE)
    cursor = conn.cursor()
    sql = "SELECT * FROM USERS WHERE USERNAME=(?)"
    user = cursor.execute(sql, (username,)).fetchone()
    conn.close()
    return user

@app.route('/')
def index():
    return 'Hello world!'

@app.route('/users/<username>', methods = ['GET', 'POST'])
def user(username):
    user = get_user_from_users_table(username)
    if request.method == 'GET':
        if user is None:
            abort(404)
        return user[1]

    if request.method == 'POST':
        if user is None:
            insert_into_users_table(username)
        else:
            return user[1]
    else:
        abort(405)

@app.before_first_request
def startup():
    create_users_table()
    insert_into_users_table('user') # user

if __name__ == "__main__":
    app.run()