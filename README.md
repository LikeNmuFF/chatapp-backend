# 💬 Blip — Real-time Chat App

A modern, playful real-time chat application built with Flask + SocketIO.

## ✨ Features
- 🔐 User registration & login (session-based auth)
- ⚡ Real-time messaging via WebSockets (SocketIO)
- 📜 Persistent chat history (SQLite)
- 🏠 Multiple chat rooms (general, random, tech, music)
- 🎨 Unique avatar colors per user
- 📱 Responsive layout

## 🚀 Quick Start

### 1. Install dependencies
```bash
pip install flask flask-socketio
```

### 2. Run the app
```bash
python app.py
```

### 3. Open in browser
```
http://localhost:5000
```

## 📁 Project Structure
```
chatapp/
├── app.py              # Flask app + SocketIO server
├── requirements.txt    # Python dependencies
├── chat.db             # SQLite database (auto-created)
└── templates/
    ├── login.html      # Sign in page
    ├── register.html   # Registration page
    └── chat.html       # Main chat interface
```

## 🔧 Tech Stack
- **Backend**: Python + Flask + Flask-SocketIO
- **Database**: SQLite (zero config!)
- **Frontend**: Vanilla JS + Socket.IO client
- **Fonts**: Nunito + Space Mono (Google Fonts)
- **Auth**: Flask sessions + SHA-256 password hashing

## 💡 Usage Tips
- Press **Enter** to send a message
- Press **Shift+Enter** for a new line
- Click emoji buttons to insert them quickly
- Switch between rooms in the left sidebar

## 🔒 Security Notes
This is a demo app. For production:
- Use `bcrypt` instead of SHA-256 for password hashing
- Set a strong `SECRET_KEY` (not random on each start)
- Use a production WSGI server (gunicorn + eventlet)
- Add CSRF protection
