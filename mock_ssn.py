from flask import Flask, request, render_template_string, redirect, make_response
import sqlite3

app = Flask(__name__)

db_file = 'mock_ssn.db'

def init_db():
    conn = sqlite3.connect(db_file)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        password TEXT NOT NULL
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS objects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        velocity TEXT NOT NULL,
        risk_level TEXT NOT NULL
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS comments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        comment TEXT NOT NULL
    )''')
    c.execute("INSERT INTO users (username, password) VALUES ('admin', 'admin')")  # plain text
    c.execute("INSERT INTO objects (name, velocity, risk_level) VALUES ('SAT-A1', '7.8 km/s', 'low')")
    c.execute("INSERT INTO objects (name, velocity, risk_level) VALUES ('DEBRIS-29B', '3.2 km/s', 'high')")
    conn.commit()
    conn.close()

@app.route('/')
def home():
    return redirect('/login')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = sqlite3.connect(db_file)
        c = conn.cursor()
        # vulnerable to SQL injection
        c.execute(f"SELECT * FROM users WHERE username = '{username}' AND password = '{password}'")
        user = c.fetchone()
        conn.close()

        if user:
            resp = make_response(redirect('/dashboard'))
            resp.set_cookie('username', username)
            return resp
        return 'Invalid credentials'

    return render_template_string('''
        <h2>SSN Mock Login</h2>
        <form method="post">
            Username: <input type="text" name="username"><br>
            Password: <input type="password" name="password"><br>
            <input type="submit" value="Login">
        </form>
    ''')

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    username = request.cookies.get('username')
    if not username:
        return redirect('/login')

    conn = sqlite3.connect(db_file)
    c = conn.cursor()
    c.execute("SELECT * FROM objects")
    data = c.fetchall()

    if request.method == 'POST':
        comment = request.form['comment']
        c.execute("INSERT INTO comments (username, comment) VALUES (?, ?)", (username, comment))
        conn.commit()

    c.execute("SELECT username, comment FROM comments")
    comments = c.fetchall()
    conn.close()

    object_html = '<ul>' + ''.join([f"<li>{obj[1]} — {obj[2]} — Risk: {obj[3]}</li>" for obj in data]) + '</ul>'
    comment_html = '<ul>' + ''.join([f"<li><b>{c[0]}</b>: {c[1]}</li>" for c in comments]) + '</ul>'

    return render_template_string(f'''
        <h2>Welcome, {username}</h2>
        <h3>Tracked Space Objects</h3>
        {object_html}

        <h3>Comments</h3>
        {comment_html}
        <form method="post">
            <textarea name="comment" rows="3" cols="50"></textarea><br>
            <input type="submit" value="Post Comment">
        </form>

        <a href="/logout">Logout</a>
    ''')

@app.route('/logout')
def logout():
    resp = make_response(redirect('/login'))
    resp.set_cookie('username', '', expires=0)
    return resp

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
