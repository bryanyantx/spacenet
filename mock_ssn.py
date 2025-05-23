from flask import Flask, request, render_template_string, redirect, make_response, url_for
import sqlite3

app = Flask(__name__)

db_file = 'mock_ssn.db'

STYLE = '''
<style>
    body {
        background-color: #0f111a;
        color: #f8f9fa;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        padding: 2em;
    }
    h2, h3 {
        color: #5be7a9;
    }
    a {
        color: #5be7e7;
        text-decoration: none;
    }
    a:hover {
        text-decoration: underline;
    }
    form {
        margin-top: 1em;
    }
    input, textarea {
        background-color: #1a1d2d;
        color: #f8f9fa;
        border: 1px solid #5be7a9;
        padding: 0.5em;
        margin-bottom: 0.5em;
        width: 100%;
    }
    input[type="submit"] {
        background-color: #5be7a9;
        color: #0f111a;
        cursor: pointer;
        width: auto;
    }
    input[type="submit"]:hover {
        background-color: #50c69e;
    }
    ul {
        list-style: none;
        padding-left: 0;
    }
    li {
        background-color: #1a1d2d;
        margin: 0.5em 0;
        padding: 1em;
        border-left: 4px solid #5be7a9;
    }
</style>
'''

def init_db():
    conn = sqlite3.connect(db_file)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'user'
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS objects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        velocity TEXT NOT NULL,
        risk_level TEXT NOT NULL,
        altitude TEXT,
        orbit_type TEXT,
        last_seen TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS comments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        comment TEXT NOT NULL
    )''')

    # Insert default users if not already present
    c.execute("SELECT COUNT(*) FROM users")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO users (username, password, role) VALUES ('admin', 'admin', 'admin')")
        c.execute("INSERT INTO users (username, password, role) VALUES ('guest', 'guest', 'user')")

    # Insert default objects if not already present
    c.execute("SELECT COUNT(*) FROM objects")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO objects (name, velocity, risk_level, altitude, orbit_type, last_seen) VALUES ('SAT-A1', '7.8 km/s', 'low', '500 km', 'LEO', '2025-04-19 16:00 UTC')")
        c.execute("INSERT INTO objects (name, velocity, risk_level, altitude, orbit_type, last_seen) VALUES ('DEBRIS-29B', '3.2 km/s', 'high', '950 km', 'MEO', '2025-04-18 12:30 UTC')")

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
        c.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
        user = c.fetchone()
        conn.close()

        if user:
            resp = make_response(redirect('/dashboard'))
            resp.set_cookie('username', username)
            resp.set_cookie('role', user[3])
            return resp
        return STYLE + '<h2>Invalid credentials</h2>'

    return render_template_string(STYLE + '''
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
    role = request.cookies.get('role')
    if not username:
        return redirect('/login')

    conn = sqlite3.connect(db_file)
    c = conn.cursor()
    c.execute("SELECT * FROM objects")
    data = c.fetchall()

    if request.method == 'POST' and 'comment' in request.form:
        comment = request.form['comment']
        c.execute("INSERT INTO comments (username, comment) VALUES (?, ?)", (username, comment))
        conn.commit()

    c.execute("SELECT username, comment FROM comments")
    comments = c.fetchall()
    conn.close()

    object_html = '<ul>' + ''.join([
        f"<li><a href='/object/{obj[0]}'>{obj[1]}</a> — {obj[2]} — Risk: {obj[3]} " + (f"<a href='/confirm_delete/{obj[0]}'>[delete]</a>" if role == 'admin' else '') + "</li>"
        for obj in data
    ]) + '</ul>'

    comment_html = '<ul>' + ''.join([f"<li><b>{c[0]}</b>: {c[1]}</li>" for c in comments]) + '</ul>'

    return render_template_string(STYLE + f'''
        <h2>Welcome, {username}</h2>
        <h3>Tracked Space Objects</h3>
        {object_html}
        <a href="/add_object">Add New Object</a>

        <h3>Comments</h3>
        {comment_html}
        <form method="post">
            <textarea name="comment" rows="3" cols="50"></textarea><br>
            <input type="submit" value="Post Comment">
        </form>

        <a href="/logout">Logout</a>
    ''')

@app.route('/object/<int:object_id>')
def object_detail(object_id):
    conn = sqlite3.connect(db_file)
    c = conn.cursor()
    c.execute("SELECT * FROM objects WHERE id = ?", (object_id,))
    obj = c.fetchone()
    conn.close()

    if not obj:
        return STYLE + "<h2>Object not found</h2>"

    return render_template_string(STYLE + f'''
        <h2>{obj[1]}</h2>
        <ul>
            <li><b>Velocity:</b> {obj[2]}</li>
            <li><b>Risk Level:</b> {obj[3]}</li>
            <li><b>Altitude:</b> {obj[4]}</li>
            <li><b>Orbit Type:</b> {obj[5]}</li>
            <li><b>Last Seen:</b> {obj[6]}</li>
        </ul>
        <a href="/dashboard">Back to Dashboard</a>
    ''')

@app.route('/add_object', methods=['GET', 'POST'])
def add_object():
    username = request.cookies.get('username')
    if not username:
        return redirect('/login')

    if request.method == 'POST':
        name = request.form['name']
        velocity = request.form['velocity']
        risk_level = request.form['risk_level']
        altitude = request.form['altitude']
        orbit_type = request.form['orbit_type']
        last_seen = request.form['last_seen']

        conn = sqlite3.connect(db_file)
        c = conn.cursor()
        c.execute("INSERT INTO objects (name, velocity, risk_level, altitude, orbit_type, last_seen) VALUES (?, ?, ?, ?, ?, ?)",
                  (name, velocity, risk_level, altitude, orbit_type, last_seen))
        conn.commit()
        conn.close()

        return redirect('/dashboard')

    return render_template_string(STYLE + '''
        <h2>Add New Space Object</h2>
        <form method="post">
            Name: <input type="text" name="name"><br>
            Velocity: <input type="text" name="velocity"><br>
            Risk Level: <input type="text" name="risk_level"><br>
            Altitude: <input type="text" name="altitude"><br>
            Orbit Type: <input type="text" name="orbit_type"><br>
            Last Seen: <input type="text" name="last_seen"><br>
            <input type="submit" value="Add Object">
        </form>
        <a href="/dashboard">Cancel</a>
    ''')

@app.route('/confirm_delete/<int:object_id>')
def confirm_delete(object_id):
    role = request.cookies.get('role')
    if role != 'admin':
        return STYLE + "<h2>Access Denied</h2>"

    conn = sqlite3.connect(db_file)
    c = conn.cursor()
    c.execute("SELECT name FROM objects WHERE id = ?", (object_id,))
    obj = c.fetchone()
    conn.close()
    if not obj:
        return STYLE + "<h2>Object not found</h2>"

    return render_template_string(STYLE + f'''
        <h2>Confirm Deletion</h2>
        <p>Are you sure you want to delete <strong>{obj[0]}</strong>?</p>
        <form method="post" action="/delete_object/{object_id}">
            <input type="submit" value="Yes, Delete">
            <a href="/dashboard">Cancel</a>
        </form>
    ''')

@app.route('/delete_object/<int:object_id>', methods=['POST'])
def delete_object(object_id):
    role = request.cookies.get('role')
    if role != 'admin':
        return STYLE + "<h2>Access Denied</h2>"

    conn = sqlite3.connect(db_file)
    c = conn.cursor()
    c.execute("DELETE FROM objects WHERE id = ?", (object_id,))
    conn.commit()
    conn.close()
    return redirect('/dashboard')

@app.route('/logout')
def logout():
    resp = make_response(redirect('/login'))
    resp.set_cookie('username', '', expires=0)
    resp.set_cookie('role', '', expires=0)
    return resp

if __name__ == '__main__':
    init_db()
    app.run(debug=True)