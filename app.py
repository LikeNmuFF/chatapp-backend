from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room
import sqlite3
import hashlib
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.urandom(24)
socketio = SocketIO(app, cors_allowed_origins="*")

DB = "chat.db"
room_members = {}

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as db:
        db.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                avatar_color TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS rooms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                description TEXT,
                is_global INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                room_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (room_id) REFERENCES rooms(id),
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
        """)
        rooms = [
            ("global",  "Everyone is here 🌐", 1),
            ("general", "Chat about anything 🌍", 0),
            ("random",  "Random fun stuff 🎲", 0),
            ("tech",    "Tech talk 💻", 0),
            ("music",   "Share the vibes 🎵", 0),
        ]
        for name, desc, is_global in rooms:
            try:
                db.execute("INSERT INTO rooms (name, description, is_global) VALUES (?,?,?)", (name, desc, is_global))
            except Exception:
                pass
        db.commit()

def hash_pw(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

AVATAR_COLORS = ["#FF6B9D","#C084FC","#67E8F9","#86EFAC","#FDE68A","#FCA5A5","#818CF8","#34D399"]

@app.route("/")
def index():
    if "user_id" not in session:
        return redirect(url_for("login"))
    return redirect(url_for("chat"))

@app.route("/login", methods=["GET","POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]
        with get_db() as db:
            user = db.execute("SELECT * FROM users WHERE username=? AND password=?", (username, hash_pw(password))).fetchone()
        if user:
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["avatar_color"] = user["avatar_color"]
            return redirect(url_for("chat"))
        error = "Invalid username or password"
    return render_template("login.html", error=error)

@app.route("/register", methods=["GET","POST"])
def register():
    error = None
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]
        if len(username) < 2:
            error = "Username must be at least 2 characters"
        elif len(password) < 4:
            error = "Password must be at least 4 characters"
        else:
            color = AVATAR_COLORS[abs(hash(username)) % len(AVATAR_COLORS)]
            try:
                with get_db() as db:
                    db.execute("INSERT INTO users (username, password, avatar_color) VALUES (?,?,?)", (username, hash_pw(password), color))
                    db.commit()
                return redirect(url_for("login"))
            except sqlite3.IntegrityError:
                error = "Username already taken"
    return render_template("register.html", error=error)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/chat")
def chat():
    if "user_id" not in session:
        return redirect(url_for("login"))
    with get_db() as db:
        rooms = db.execute("SELECT * FROM rooms ORDER BY is_global DESC, name ASC").fetchall()
    return render_template("chat.html", rooms=rooms, username=session["username"], avatar_color=session["avatar_color"])

@app.route("/api/messages/<int:room_id>")
def get_messages(room_id):
    if "user_id" not in session:
        return jsonify([])
    with get_db() as db:
        msgs = db.execute("""
            SELECT m.id, m.content, m.created_at, u.username, u.avatar_color
            FROM messages m JOIN users u ON m.user_id = u.id
            WHERE m.room_id = ? ORDER BY m.created_at DESC LIMIT 80
        """, (room_id,)).fetchall()
    result = []
    for m in reversed(msgs):
        d = dict(m)
        try:
            dt = datetime.strptime(d["created_at"], "%Y-%m-%d %H:%M:%S")
            d["created_at"] = dt.strftime("%H:%M")
        except Exception:
            pass
        result.append(d)
    return jsonify(result)

@socketio.on("join")
def on_join(data):
    room = str(data["room_id"])
    username = session.get("username", "?")
    join_room(room)
    if room not in room_members:
        room_members[room] = {}
    room_members[room][request.sid] = username
    count = len(room_members[room])
    emit("member_update", {"count": count}, room=room)
    emit("status", {"msg": f"{username} joined · {count} online", "type": "join"}, room=room)

@socketio.on("leave")
def on_leave(data):
    room = str(data["room_id"])
    leave_room(room)
    if room in room_members:
        room_members[room].pop(request.sid, None)
        count = len(room_members[room])
        emit("member_update", {"count": count}, room=room)

@socketio.on("disconnect")
def on_disconnect():
    for room, members in list(room_members.items()):
        if request.sid in members:
            members.pop(request.sid)
            count = len(members)
            emit("member_update", {"count": count}, room=room)

@socketio.on("message")
def on_message(data):
    if "user_id" not in session:
        return
    content = data["content"].strip()
    room_id = data["room_id"]
    if not content or len(content) > 1000:
        return
    with get_db() as db:
        cur = db.execute("INSERT INTO messages (room_id, user_id, content) VALUES (?,?,?)", (room_id, session["user_id"], content))
        db.commit()
        msg_id = cur.lastrowid
    timestamp = datetime.now().strftime("%H:%M")
    emit("message", {
        "id": msg_id, "content": content,
        "username": session["username"], "avatar_color": session["avatar_color"],
        "created_at": timestamp,
    }, room=str(room_id))

@socketio.on("typing")
def on_typing(data):
    room = str(data["room_id"])
    username = session.get("username", "?")
    emit("typing", {"username": username}, room=room, include_self=False)

if __name__ == "__main__":
    init_db()
    socketio.run(app, debug=True, host="0.0.0.0", port=5000)
