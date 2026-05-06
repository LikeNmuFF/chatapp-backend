# 💬 Blip — Real-time Chat App

A modern, playful real-time chat application built with Flask + SocketIO.

## ✨ Features
- 🔐 Secure Auth: User registration & login with **Bcrypt** and **JWT**
- 🛡️ **Anti-DDoS**: Integrated rate-limiting for all API endpoints
- 🔑 **Message Encryption**: Server-side AES encryption for chat messages
- ⚡ Real-time messaging via WebSockets (SocketIO)
- 📜 Persistent chat history (PostgreSQL/SQLite)
- 🏠 Multiple chat rooms with private room support
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
- **Security**: Flask-Bcrypt, Flask-Limiter, Flask-Talisman, Cryptography (Fernet)
- **Database**: PostgreSQL / SQLite
- **Auth**: JWT (JSON Web Tokens)
- **Frontend**: Vanilla JS + Socket.IO client

## 💡 Usage Tips
- Press **Enter** to send a message
- Press **Shift+Enter** for a new line
- Click emoji buttons to insert them quickly
- Switch between rooms in the left sidebar

## 🔒 Security Implementation
- **Password Hashing**: Uses `bcrypt` with unique salts for maximum security.
- **Rate Limiting**: Protects against brute-force and DDoS attacks via `Flask-Limiter`.
- **Message Decryption/Encryption**: Messages are encrypted using AES-256 (Fernet) before being stored.
- **Security Headers**: `Flask-Talisman` enforces HSTS, XSS protection, and MIME sniffing prevention.
- **CORS**: Secure cross-origin resource sharing configuration.
