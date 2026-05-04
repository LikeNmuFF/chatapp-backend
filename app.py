from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room
import sqlite3
import hashlib
import os
import jwt
from datetime import datetime, timedelta
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "your-secret-key-change-in-production")
JWT_SECRET = os.environ.get("JWT_SECRET", "jwt-secret-key-change-in-production")
JWT_EXPIRATION = 86400 * 7  # 7 days

socketio = SocketIO(app, cors_allowed_origins="*")

DB = "chat.db"
room_members = {}

# ──────────────────────────────────────────────────────────────────────────────
# DATABASE & UTILITIES
# ──────────────────────────────────────────────────────────────────────────────

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

def generate_token(user_id):
    """Generate JWT token"""
    payload = {
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(seconds=JWT_EXPIRATION),
        'iat': datetime.utcnow()
    }
    return jwt.encode(payload, JWT_SECRET, algorithm='HS256')

def verify_token(token):
    """Verify JWT token and return user_id"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        return payload.get('user_id')
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def get_auth_user():
    """Extract user from JWT token in Authorization header"""
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return None
    token = auth_header[7:]  # Remove 'Bearer ' prefix
    return verify_token(token)

def token_required(f):
    """Decorator to require valid JWT token"""
    @wraps(f)
    def decorated(*args, **kwargs):
        user_id = get_auth_user()
        if not user_id:
            return jsonify({"error": "Unauthorized"}), 401
        return f(user_id, *args, **kwargs)
    return decorated

def get_user_rooms(user_id):
    """Get all rooms a user has access to."""
    with get_db() as db:
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

def format_user_data(user):
    """Convert user row to dict"""
    return {
        "id": user["id"],
        "username": user["username"],
        "avatar_color": user["avatar_color"],
        "created_at": user["created_at"]
    }

def format_room_data(room):
    """Convert room row to dict"""
    return {
        "id": room["id"],
        "name": room["name"],
        "description": room["description"],
        "is_global": bool(room["is_global"]),
        "is_private": bool(room["is_private"]),
        "owner_id": room["owner_id"],
        "owner_name": room["owner_name"],
        "created_at": room["created_at"]
    }

def format_message_data(msg):
    """Convert message row to dict"""
    d = {
        "id": msg["id"],
        "room_id": msg["room_id"],
        "user_id": msg["user_id"],
        "username": msg["username"],
        "avatar_color": msg["avatar_color"],
        "content": msg["content"],
        "created_at": msg["created_at"]
    }
    try:
        dt = datetime.strptime(d["created_at"], "%Y-%m-%d %H:%M:%S")
        d["created_at"] = dt.isoformat()
    except:
        pass
    return d

# ──────────────────────────────────────────────────────────────────────────────
# AUTHENTICATION ENDPOINTS
# ──────────────────────────────────────────────────────────────────────────────

@app.route("/api/auth/register", methods=["POST"])
def api_register():
    """Register a new user"""
    data = request.get_json()
    username = data.get("username", "").strip()
    password = data.get("password", "")

    if len(username) < 2:
        return jsonify({"error": "Username must be at least 2 characters"}), 400
    if len(password) < 4:
        return jsonify({"error": "Password must be at least 4 characters"}), 400

    color = AVATAR_COLORS[abs(hash(username)) % len(AVATAR_COLORS)]

    with get_db() as db:
        try:
            cur = db.execute(
                "INSERT INTO users (username, password, avatar_color) VALUES (?,?,?)",
                (username, hash_pw(password), color)
            )
            db.commit()
            user_id = cur.lastrowid
            
            user = db.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
            token = generate_token(user_id)
            
            return jsonify({
                "token": token,
                "user": format_user_data(user)
            }), 201
        except sqlite3.IntegrityError:
            return jsonify({"error": "Username already taken"}), 409

@app.route("/api/auth/login", methods=["POST"])
def api_login():
    """Login user"""
    data = request.get_json()
    username = data.get("username", "").strip()
    password = data.get("password", "")

    with get_db() as db:
        user = db.execute(
            "SELECT * FROM users WHERE username=? AND password=?",
            (username, hash_pw(password))
        ).fetchone()

    if not user:
        return jsonify({"error": "Invalid username or password"}), 401

    token = generate_token(user["id"])
    return jsonify({
        "token": token,
        "user": format_user_data(user)
    }), 200

@app.route("/api/auth/logout", methods=["POST"])
@token_required
def api_logout(user_id):
    """Logout user (token-based, just return OK)"""
    return jsonify({"ok": True}), 200

@app.route("/api/auth/verify", methods=["GET"])
@token_required
def api_verify_token(user_id):
    """Verify if token is valid and get user info"""
    with get_db() as db:
        user = db.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    
    if not user:
        return jsonify({"error": "User not found"}), 404

    return jsonify({"user": format_user_data(user)}), 200

# ──────────────────────────────────────────────────────────────────────────────
# USER ENDPOINTS
# ──────────────────────────────────────────────────────────────────────────────

@app.route("/api/users/<username>", methods=["GET"])
@token_required
def get_user_profile(user_id, username):
    """Get public user profile"""
    with get_db() as db:
        user = db.execute(
            "SELECT id, username, avatar_color, created_at FROM users WHERE username=?",
            (username,)
        ).fetchone()

    if not user:
        return jsonify({"error": "User not found"}), 404

    return jsonify(format_user_data(user)), 200

@app.route("/api/users/search", methods=["GET"])
@token_required
def search_users(user_id):
    """Search users by username"""
    q = request.args.get("q", "").strip()

    if len(q) < 1:
        return jsonify([]), 200

    with get_db() as db:
        users = db.execute("""
            SELECT id, username, avatar_color, created_at FROM users
            WHERE username LIKE ? LIMIT 20
        """, (f"%{q}%",)).fetchall()

    return jsonify([format_user_data(u) for u in users]), 200

# ──────────────────────────────────────────────────────────────────────────────
# ROOM ENDPOINTS
# ──────────────────────────────────────────────────────────────────────────────

@app.route("/api/rooms", methods=["GET"])
@token_required
def get_user_accessible_rooms(user_id):
    """Get all rooms accessible by user"""
    rooms = get_user_rooms(user_id)
    return jsonify([format_room_data(r) for r in rooms]), 200

@app.route("/api/rooms", methods=["POST"])
@token_required
def create_room(user_id):
    """Create a new room"""
    data = request.get_json()
    name = data.get("name", "").strip().lower().replace(" ", "-")
    description = data.get("description", "").strip()
    is_private = bool(data.get("is_private", False))
    invites = data.get("invites", [])

    if not name or len(name) < 2:
        return jsonify({"error": "Room name must be at least 2 characters"}), 400
    if len(name) > 30:
        return jsonify({"error": "Room name too long (max 30 chars)"}), 400

    with get_db() as db:
        # Check if name exists
        existing = db.execute("SELECT id FROM rooms WHERE name=?", (name,)).fetchone()
        if existing:
            return jsonify({"error": f'Room "#{name}" already exists'}), 400

        # Create room
        cur = db.execute(
            "INSERT INTO rooms (name, description, is_global, is_private, owner_id) VALUES (?,?,0,?,?)",
            (name, description or f"#{name} room", 1 if is_private else 0, user_id)
        )
        db.commit()
        room_id = cur.lastrowid

        # Process invites
        invited = []
        failed = []
        for uname in invites:
            uname = uname.strip()
            if not uname:
                continue
            user = db.execute("SELECT id FROM users WHERE username=?", (uname,)).fetchone()
            if user:
                try:
                    db.execute(
                        "INSERT INTO room_invites (room_id, user_id, invited_by) VALUES (?,?,?)",
                        (room_id, user["id"], user_id)
                    )
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
        "room": format_room_data(room),
        "invited": invited,
        "not_found": failed
    }), 201

@app.route("/api/rooms/<int:room_id>", methods=["GET"])
@token_required
def get_room(user_id, room_id):
    """Get room details"""
    with get_db() as db:
        room = db.execute("SELECT * FROM rooms WHERE id=?", (room_id,)).fetchone()

    if not room:
        return jsonify({"error": "Room not found"}), 404

    # Check access
    if room["is_private"]:
        has_access = (room["owner_id"] == user_id or
            get_db().execute(
                "SELECT 1 FROM room_invites WHERE room_id=? AND user_id=?",
                (room_id, user_id)
            ).fetchone())
        if not has_access:
            return jsonify({"error": "Access denied"}), 403

    return jsonify(format_room_data(room)), 200

@app.route("/api/rooms/<int:room_id>/invite", methods=["POST"])
@token_required
def invite_to_room(user_id, room_id):
    """Invite users to room (owner only)"""
    data = request.get_json()
    usernames = data.get("usernames", [])

    with get_db() as db:
        room = db.execute("SELECT * FROM rooms WHERE id=?", (room_id,)).fetchone()

        if not room:
            return jsonify({"error": "Room not found"}), 404

        if room["owner_id"] != user_id:
            return jsonify({"error": "Only room owner can invite"}), 403

        invited = []
        failed = []
        for uname in usernames:
            uname = uname.strip()
            if not uname:
                continue
            user = db.execute("SELECT id FROM users WHERE username=?", (uname,)).fetchone()
            if user:
                try:
                    db.execute(
                        "INSERT OR IGNORE INTO room_invites (room_id, user_id, invited_by) VALUES (?,?,?)",
                        (room_id, user["id"], user_id)
                    )
                    invited.append(uname)
                except Exception:
                    pass
            else:
                failed.append(uname)
        db.commit()

    return jsonify({"invited": invited, "not_found": failed}), 200

@app.route("/api/rooms/<int:room_id>/members", methods=["GET"])
@token_required
def get_room_members(user_id, room_id):
    """Get room members"""
    with get_db() as db:
        room = db.execute("SELECT * FROM rooms WHERE id=?", (room_id,)).fetchone()

        if not room:
            return jsonify({"error": "Room not found"}), 404

        members = []
        # Owner
        if room["owner_id"]:
            owner = db.execute(
                "SELECT id, username, avatar_color FROM users WHERE id=?",
                (room["owner_id"],)
            ).fetchone()
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

    return jsonify(members), 200

@app.route("/api/rooms/<int:room_id>/leave", methods=["POST"])
@token_required
def leave_room(user_id, room_id):
    """Leave or delete room"""
    with get_db() as db:
        room = db.execute("SELECT * FROM rooms WHERE id=?", (room_id,)).fetchone()

        if not room:
            return jsonify({"error": "Room not found"}), 404

        if room["is_global"]:
            return jsonify({"error": "Cannot leave global room"}), 400

        # Owner deletes room, member removes invite
        if room["owner_id"] == user_id:
            db.execute("DELETE FROM messages WHERE room_id=?", (room_id,))
            db.execute("DELETE FROM room_invites WHERE room_id=?", (room_id,))
            db.execute("DELETE FROM rooms WHERE id=?", (room_id,))
        else:
            db.execute("DELETE FROM room_invites WHERE room_id=? AND user_id=?",
                       (room_id, user_id))

        db.commit()

    return jsonify({"ok": True}), 200

@app.route("/api/rooms/<int:room_id>/kick", methods=["POST"])
@token_required
def kick_member(user_id, room_id):
    """Kick member from room (owner only)"""
    data = request.get_json()
    target_user_id = data.get("user_id")

    with get_db() as db:
        room = db.execute("SELECT * FROM rooms WHERE id=?", (room_id,)).fetchone()

        if not room:
            return jsonify({"error": "Room not found"}), 404

        if room["owner_id"] != user_id:
            return jsonify({"error": "Only owner can kick members"}), 403

        db.execute("DELETE FROM room_invites WHERE room_id=? AND user_id=?",
                   (room_id, target_user_id))
        db.commit()

    return jsonify({"ok": True}), 200

# ──────────────────────────────────────────────────────────────────────────────
# MESSAGE ENDPOINTS
# ──────────────────────────────────────────────────────────────────────────────

@app.route("/api/rooms/<int:room_id>/messages", methods=["GET"])
@token_required
def get_room_messages(user_id, room_id):
    """Get room message history"""
    limit = request.args.get("limit", 100, type=int)
    offset = request.args.get("offset", 0, type=int)

    with get_db() as db:
        room = db.execute("SELECT * FROM rooms WHERE id=?", (room_id,)).fetchone()

        if not room:
            return jsonify({"error": "Room not found"}), 404

        # Check access
        if room["is_private"]:
            has_access = (room["owner_id"] == user_id or
                db.execute(
                    "SELECT 1 FROM room_invites WHERE room_id=? AND user_id=?",
                    (room_id, user_id)
                ).fetchone())
            if not has_access:
                return jsonify({"error": "Access denied"}), 403

        messages = db.execute("""
            SELECT m.id, m.room_id, m.user_id, m.content, m.created_at,
                   u.username, u.avatar_color
            FROM messages m
            JOIN users u ON m.user_id = u.id
            WHERE m.room_id = ?
            ORDER BY m.created_at DESC
            LIMIT ? OFFSET ?
        """, (room_id, limit, offset)).fetchall()

    return jsonify([format_message_data(m) for m in reversed(messages)]), 200

@app.route("/api/rooms/<int:room_id>/messages", methods=["POST"])
@token_required
def send_message(user_id, room_id):
    """Send message to room"""
    data = request.get_json()
    content = data.get("content", "").strip()

    if not content or len(content) > 1000:
        return jsonify({"error": "Invalid message"}), 400

    with get_db() as db:
        room = db.execute("SELECT * FROM rooms WHERE id=?", (room_id,)).fetchone()

        if not room:
            return jsonify({"error": "Room not found"}), 404

        # Check access
        if room["is_private"]:
            has_access = (room["owner_id"] == user_id or
                db.execute(
                    "SELECT 1 FROM room_invites WHERE room_id=? AND user_id=?",
                    (room_id, user_id)
                ).fetchone())
            if not has_access:
                return jsonify({"error": "Access denied"}), 403

        cur = db.execute(
            "INSERT INTO messages (room_id, user_id, content) VALUES (?,?,?)",
            (room_id, user_id, content)
        )
        db.commit()
        msg_id = cur.lastrowid

        msg = db.execute("""
            SELECT m.id, m.room_id, m.user_id, m.content, m.created_at,
                   u.username, u.avatar_color
            FROM messages m
            JOIN users u ON m.user_id = u.id
            WHERE m.id = ?
        """, (msg_id,)).fetchone()

    return jsonify(format_message_data(msg)), 201

# ──────────────────────────────────────────────────────────────────────────────
# WEBSOCKET EVENTS (For real-time messaging)
# ──────────────────────────────────────────────────────────────────────────────

@socketio.on("connect")
def on_connect(auth):
    """WebSocket connection with token auth"""
    if auth and 'token' in auth:
        user_id = verify_token(auth['token'])
        if user_id:
            return True
    return False

@socketio.on("join_room")
def on_join(data):
    """Join a room"""
    token = data.get("token")
    user_id = verify_token(token)
    
    if not user_id:
        emit("error", {"message": "Unauthorized"})
        return

    room_id = str(data["room_id"])
    join_room(room_id)

    with get_db() as db:
        user = db.execute("SELECT username FROM users WHERE id=?", (user_id,)).fetchone()
        username = user["username"] if user else "Unknown"

    if room_id not in room_members:
        room_members[room_id] = {}
    room_members[room_id][request.sid] = {"user_id": user_id, "username": username}

    count = len(room_members[room_id])
    emit("member_update", {"count": count}, room=room_id)
    emit("status", {
        "message": f"{username} joined · {count} online",
        "type": "join"
    }, room=room_id)

@socketio.on("leave_room")
def on_leave(data):
    """Leave a room"""
    room_id = str(data["room_id"])
    leave_room(room_id)

    if room_id in room_members and request.sid in room_members[room_id]:
        room_members[room_id].pop(request.sid)
        count = len(room_members[room_id])
        emit("member_update", {"count": count}, room=room_id)

@socketio.on("disconnect")
def on_disconnect():
    """Handle disconnect"""
    for room_id, members in list(room_members.items()):
        if request.sid in members:
            members.pop(request.sid)
            emit("member_update", {"count": len(members)}, room=room_id)

@socketio.on("message")
def on_message(data):
    """Receive and broadcast message"""
    token = data.get("token")
    user_id = verify_token(token)

    if not user_id:
        emit("error", {"message": "Unauthorized"})
        return

    content = data["content"].strip()
    room_id = data["room_id"]

    if not content or len(content) > 1000:
        return

    with get_db() as db:
        room = db.execute("SELECT * FROM rooms WHERE id=?", (room_id,)).fetchone()
        if not room:
            emit("error", {"message": "Room not found"})
            return

        # Check access
        if room["is_private"]:
            has_access = (room["owner_id"] == user_id or
                db.execute(
                    "SELECT 1 FROM room_invites WHERE room_id=? AND user_id=?",
                    (room_id, user_id)
                ).fetchone())
            if not has_access:
                emit("error", {"message": "Access denied"})
                return

        cur = db.execute(
            "INSERT INTO messages (room_id, user_id, content) VALUES (?,?,?)",
            (room_id, user_id, content)
        )
        db.commit()
        msg_id = cur.lastrowid

        msg = db.execute("""
            SELECT m.id, m.room_id, m.user_id, m.content, m.created_at,
                   u.username, u.avatar_color
            FROM messages m
            JOIN users u ON m.user_id = u.id
            WHERE m.id = ?
        """, (msg_id,)).fetchone()

    emit("message", format_message_data(msg), room=str(room_id))

@socketio.on("typing")
def on_typing(data):
    """Broadcast typing indicator"""
    token = data.get("token")
    user_id = verify_token(token)

    if not user_id:
        return

    room_id = str(data["room_id"])

    with get_db() as db:
        user = db.execute("SELECT username FROM users WHERE id=?", (user_id,)).fetchone()
        username = user["username"] if user else "Unknown"

    emit("typing", {"username": username}, room=room_id, include_self=False)

# ──────────────────────────────────────────────────────────────────────────────
# LEGACY HTML ROUTES (for backward compatibility with web)
# ──────────────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    if "user_id" not in session:
        return redirect(url_for("login"))
    return redirect(url_for("chat"))

@app.route("/login", methods=["GET", "POST"])
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

@app.route("/register", methods=["GET", "POST"])
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

@app.route("/chat")
def chat():
    if "user_id" not in session:
        return redirect(url_for("login"))
    rooms = get_user_rooms(session["user_id"])
    return render_template("chat.html", rooms=rooms,
                           username=session["username"],
                           avatar_color=session["avatar_color"],
                           user_id=session["user_id"])

init_db()

if __name__ == "__main__":
    socketio.run(app, debug=True, host="0.0.0.0", port=5000)
