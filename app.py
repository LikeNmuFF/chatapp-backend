from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room
import sqlite3
import hashlib
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", os.urandom(24))
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
                is_private INTEGER DEFAULT 0,
                owner_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (owner_id) REFERENCES users(id)
            );
            CREATE TABLE IF NOT EXISTS room_invites (
                room_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                invited_by INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (room_id, user_id),
                FOREIGN KEY (room_id) REFERENCES rooms(id),
                FOREIGN KEY (user_id) REFERENCES users(id)
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
        # Seed default public rooms
        rooms = [
            ("global",  "Everyone is here 🌐", 1, 0),
            ("general", "Chat about anything 🌍", 0, 0),
            ("random",  "Random fun stuff 🎲", 0, 0),
            ("tech",    "Tech talk 💻", 0, 0),
            ("music",   "Share the vibes 🎵", 0, 0),
        ]
        for name, desc, is_global, is_private in rooms:
            try:
                db.execute("INSERT INTO rooms (name, description, is_global, is_private) VALUES (?,?,?,?)",
                           (name, desc, is_global, is_private))
            except Exception:
                pass
        db.commit()

def hash_pw(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

AVATAR_COLORS = ["#FF6B9D","#C084FC","#67E8F9","#86EFAC","#FDE68A","#FCA5A5","#818CF8","#34D399"]

def get_user_rooms(user_id):
    """Get all rooms a user has access to."""
    with get_db() as db:
        # Public rooms + private rooms where user is invited or owner
        rooms = db.execute("""
            SELECT r.*, u.username as owner_name
            FROM rooms r
            LEFT JOIN users u ON r.owner_id = u.id
            WHERE r.is_private = 0
               OR r.owner_id = ?
               OR EXISTS (
                   SELECT 1 FROM room_invites ri
                   WHERE ri.room_id = r.id AND ri.user_id = ?
               )
            ORDER BY r.is_global DESC, r.is_private ASC, r.name ASC
        """, (user_id, user_id)).fetchall()
    return rooms

# ── Auth ──────────────────────────────────────────────────────────────────────
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
            user = db.execute("SELECT * FROM users WHERE username=? AND password=?",
                              (username, hash_pw(password))).fetchone()
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
                    db.execute("INSERT INTO users (username, password, avatar_color) VALUES (?,?,?)",
                               (username, hash_pw(password), color))
                    db.commit()
                return redirect(url_for("login"))
            except sqlite3.IntegrityError:
                error = "Username already taken"
    return render_template("register.html", error=error)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# ── Chat ──────────────────────────────────────────────────────────────────────
@app.route("/chat")
def chat():
    if "user_id" not in session:
        return redirect(url_for("login"))
    rooms = get_user_rooms(session["user_id"])
    return render_template("chat.html", rooms=rooms,
                           username=session["username"],
                           avatar_color=session["avatar_color"],
                           user_id=session["user_id"])

# ── Room API ──────────────────────────────────────────────────────────────────
@app.route("/api/rooms/create", methods=["POST"])
def create_room():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json()
    name = data.get("name", "").strip().lower().replace(" ", "-")
    description = data.get("description", "").strip()
    is_private = 1 if data.get("is_private") else 0
    invites = data.get("invites", [])  # list of usernames

    if not name or len(name) < 2:
        return jsonify({"error": "Room name must be at least 2 characters"}), 400
    if len(name) > 30:
        return jsonify({"error": "Room name too long (max 30 chars)"}), 400

    with get_db() as db:
        # Check name taken
        existing = db.execute("SELECT id FROM rooms WHERE name=?", (name,)).fetchone()
        if existing:
            return jsonify({"error": f'Room "#{name}" already exists'}), 400
        # Create room
        cur = db.execute(
            "INSERT INTO rooms (name, description, is_global, is_private, owner_id) VALUES (?,?,0,?,?)",
            (name, description or f"#{name} room", is_private, session["user_id"]))
        db.commit()
        room_id = cur.lastrowid

        # Process invites
        invited = []
        failed = []
        for uname in invites:
            uname = uname.strip()
            if not uname or uname == session["username"]:
                continue
            user = db.execute("SELECT id FROM users WHERE username=?", (uname,)).fetchone()
            if user:
                try:
                    db.execute("INSERT INTO room_invites (room_id, user_id, invited_by) VALUES (?,?,?)",
                               (room_id, user["id"], session["user_id"]))
                    invited.append(uname)
                except Exception:
                    pass
            else:
                failed.append(uname)
        db.commit()

        room = db.execute("""
            SELECT r.*, u.username as owner_name
            FROM rooms r LEFT JOIN users u ON r.owner_id = u.id
            WHERE r.id = ?
        """, (room_id,)).fetchone()

    return jsonify({
        "room": dict(room),
        "invited": invited,
        "not_found": failed
    })

@app.route("/api/rooms/<int:room_id>/invite", methods=["POST"])
def invite_to_room(room_id):
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json()
    usernames = data.get("usernames", [])

    with get_db() as db:
        room = db.execute("SELECT * FROM rooms WHERE id=?", (room_id,)).fetchone()
        if not room:
            return jsonify({"error": "Room not found"}), 404
        if room["owner_id"] != session["user_id"]:
            return jsonify({"error": "Only the room owner can invite members"}), 403

        invited, failed = [], []
        for uname in usernames:
            uname = uname.strip()
            if not uname or uname == session["username"]:
                continue
            user = db.execute("SELECT id FROM users WHERE username=?", (uname,)).fetchone()
            if user:
                try:
                    db.execute("INSERT OR IGNORE INTO room_invites (room_id, user_id, invited_by) VALUES (?,?,?)",
                               (room_id, user["id"], session["user_id"]))
                    invited.append(uname)
                except Exception:
                    pass
            else:
                failed.append(uname)
        db.commit()

    return jsonify({"invited": invited, "not_found": failed})

@app.route("/api/rooms/<int:room_id>/members")
def get_room_members_list(room_id):
    if "user_id" not in session:
        return jsonify([])
    with get_db() as db:
        room = db.execute("SELECT * FROM rooms WHERE id=?", (room_id,)).fetchone()
        if not room:
            return jsonify([])
        members = []
        # Owner
        if room["owner_id"]:
            owner = db.execute("SELECT id, username, avatar_color FROM users WHERE id=?",
                               (room["owner_id"],)).fetchone()
            if owner:
                members.append({**dict(owner), "role": "owner"})
        # Invited members
        invited = db.execute("""
            SELECT u.id, u.username, u.avatar_color FROM users u
            JOIN room_invites ri ON ri.user_id = u.id
            WHERE ri.room_id = ? AND u.id != ?
        """, (room_id, room["owner_id"] or 0)).fetchall()
        for m in invited:
            members.append({**dict(m), "role": "member"})
    return jsonify(members)

@app.route("/api/rooms/<int:room_id>/leave", methods=["POST"])
def leave_room_api(room_id):
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    with get_db() as db:
        room = db.execute("SELECT * FROM rooms WHERE id=?", (room_id,)).fetchone()
        if not room:
            return jsonify({"error": "Room not found"}), 404
        if room["is_global"] or not room["is_private"]:
            return jsonify({"error": "Cannot leave public rooms"}), 400
        # Owner deletes room, member removes invite
        if room["owner_id"] == session["user_id"]:
            db.execute("DELETE FROM messages WHERE room_id=?", (room_id,))
            db.execute("DELETE FROM room_invites WHERE room_id=?", (room_id,))
            db.execute("DELETE FROM rooms WHERE id=?", (room_id,))
        else:
            db.execute("DELETE FROM room_invites WHERE room_id=? AND user_id=?",
                       (room_id, session["user_id"]))
        db.commit()
    return jsonify({"ok": True})

@app.route("/api/rooms/<int:room_id>/kick", methods=["POST"])
def kick_member(room_id):
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json()
    target_id = data.get("user_id")
    with get_db() as db:
        room = db.execute("SELECT * FROM rooms WHERE id=?", (room_id,)).fetchone()
        if not room or room["owner_id"] != session["user_id"]:
            return jsonify({"error": "Not authorized"}), 403
        db.execute("DELETE FROM room_invites WHERE room_id=? AND user_id=?", (room_id, target_id))
        db.commit()
    return jsonify({"ok": True})

@app.route("/api/users/search")
def search_users():
    if "user_id" not in session:
        return jsonify([])
    q = request.args.get("q", "").strip()
    if len(q) < 1:
        return jsonify([])
    with get_db() as db:
        users = db.execute("""
            SELECT username, avatar_color FROM users
            WHERE username LIKE ? AND username != ?
            LIMIT 8
        """, (f"%{q}%", session["username"])).fetchall()
    return jsonify([dict(u) for u in users])

@app.route("/api/messages/<int:room_id>")
def get_messages(room_id):
    if "user_id" not in session:
        return jsonify([])
    # Access check
    with get_db() as db:
        room = db.execute("SELECT * FROM rooms WHERE id=?", (room_id,)).fetchone()
        if not room:
            return jsonify([])
        if room["is_private"]:
            has_access = (room["owner_id"] == session["user_id"] or
                db.execute("SELECT 1 FROM room_invites WHERE room_id=? AND user_id=?",
                           (room_id, session["user_id"])).fetchone())
            if not has_access:
                return jsonify([])
        msgs = db.execute("""
            SELECT m.id, m.user_id, m.content, m.created_at, u.username, u.avatar_color
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

# ── SocketIO ──────────────────────────────────────────────────────────────────
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
            emit("member_update", {"count": len(members)}, room=room)

@socketio.on("message")
def on_message(data):
    if "user_id" not in session:
        return
    content = data["content"].strip()
    room_id = data["room_id"]
    if not content or len(content) > 1000:
        return
    with get_db() as db:
        cur = db.execute("INSERT INTO messages (room_id, user_id, content) VALUES (?,?,?)",
                         (room_id, session["user_id"], content))
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

init_db()

if __name__ == "__main__":
    socketio.run(app, debug=True, host="0.0.0.0", port=5000)