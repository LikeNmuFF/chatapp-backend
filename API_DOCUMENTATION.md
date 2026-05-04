# Chat App - REST API & WebSocket Documentation

## Base URL
```
http://localhost:5000
```

## Authentication
All API endpoints (except `/api/auth/register` and `/api/auth/login`) require a JWT token in the `Authorization` header:

```
Authorization: Bearer <token>
```

## Response Format
All responses are JSON with the following standard format:

Success:
```json
{
  "data": {...}
}
```

Error:
```json
{
  "error": "Error message"
}
```

---

## Authentication Endpoints

### Register User
**POST** `/api/auth/register`

Creates a new user account.

**Request:**
```json
{
  "username": "john_doe",
  "password": "securepassword"
}
```

**Response (201):**
```json
{
  "token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "user": {
    "id": 1,
    "username": "john_doe",
    "avatar_color": "#FF6B9D",
    "created_at": "2024-01-15T10:30:00"
  }
}
```

**Errors:**
- `400`: Username/password validation failed
- `409`: Username already taken

---

### Login
**POST** `/api/auth/login`

Authenticates a user and returns a JWT token.

**Request:**
```json
{
  "username": "john_doe",
  "password": "securepassword"
}
```

**Response (200):**
```json
{
  "token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "user": {
    "id": 1,
    "username": "john_doe",
    "avatar_color": "#FF6B9D",
    "created_at": "2024-01-15T10:30:00"
  }
}
```

**Errors:**
- `401`: Invalid credentials

---

### Verify Token
**GET** `/api/auth/verify`

Verifies if a token is valid and returns user info.

**Headers:**
```
Authorization: Bearer <token>
```

**Response (200):**
```json
{
  "user": {
    "id": 1,
    "username": "john_doe",
    "avatar_color": "#FF6B9D",
    "created_at": "2024-01-15T10:30:00"
  }
}
```

**Errors:**
- `401`: Invalid or expired token

---

## User Endpoints

### Get User Profile
**GET** `/api/users/<username>`

Gets public profile information for a user.

**Headers:**
```
Authorization: Bearer <token>
```

**Response (200):**
```json
{
  "id": 1,
  "username": "john_doe",
  "avatar_color": "#FF6B9D",
  "created_at": "2024-01-15T10:30:00"
}
```

**Errors:**
- `404`: User not found

---

### Search Users
**GET** `/api/users/search?q=<query>`

Searches for users by username.

**Headers:**
```
Authorization: Bearer <token>
```

**Query Parameters:**
- `q` (string, required): Search query (min 1 char)

**Response (200):**
```json
[
  {
    "id": 1,
    "username": "john_doe",
    "avatar_color": "#FF6B9D",
    "created_at": "2024-01-15T10:30:00"
  }
]
```

---

## Room Endpoints

### List User's Rooms
**GET** `/api/rooms`

Gets all rooms accessible by the authenticated user.

**Headers:**
```
Authorization: Bearer <token>
```

**Response (200):**
```json
[
  {
    "id": 1,
    "name": "global",
    "description": "Everyone is here 🌐",
    "is_global": true,
    "is_private": false,
    "owner_id": null,
    "owner_name": null,
    "created_at": "2024-01-15T10:30:00"
  }
]
```

---

### Create Room
**POST** `/api/rooms`

Creates a new room.

**Headers:**
```
Authorization: Bearer <token>
Content-Type: application/json
```

**Request:**
```json
{
  "name": "my-room",
  "description": "A fun room",
  "is_private": false,
  "invites": ["user1", "user2"]
}
```

**Response (201):**
```json
{
  "room": {
    "id": 10,
    "name": "my-room",
    "description": "A fun room",
    "is_global": false,
    "is_private": false,
    "owner_id": 1,
    "owner_name": "john_doe",
    "created_at": "2024-01-15T10:30:00"
  },
  "invited": ["user1", "user2"],
  "not_found": []
}
```

**Errors:**
- `400`: Invalid room name
- `400`: Room name already exists

---

### Get Room Details
**GET** `/api/rooms/<room_id>`

Gets detailed information about a room.

**Headers:**
```
Authorization: Bearer <token>
```

**Response (200):**
```json
{
  "id": 1,
  "name": "global",
  "description": "Everyone is here 🌐",
  "is_global": true,
  "is_private": false,
  "owner_id": null,
  "owner_name": null,
  "created_at": "2024-01-15T10:30:00"
}
```

**Errors:**
- `404`: Room not found
- `403`: Access denied (for private rooms)

---

### Invite Users to Room
**POST** `/api/rooms/<room_id>/invite`

Invites users to a private room (owner only).

**Headers:**
```
Authorization: Bearer <token>
Content-Type: application/json
```

**Request:**
```json
{
  "usernames": ["user1", "user2"]
}
```

**Response (200):**
```json
{
  "invited": ["user1", "user2"],
  "not_found": []
}
```

**Errors:**
- `403`: Only owner can invite
- `404`: Room not found

---

### Get Room Members
**GET** `/api/rooms/<room_id>/members`

Gets list of members in a room.

**Headers:**
```
Authorization: Bearer <token>
```

**Response (200):**
```json
[
  {
    "id": 1,
    "username": "john_doe",
    "avatar_color": "#FF6B9D",
    "role": "owner"
  },
  {
    "id": 2,
    "username": "jane_smith",
    "avatar_color": "#C084FC",
    "role": "member"
  }
]
```

---

### Leave Room
**POST** `/api/rooms/<room_id>/leave`

Leaves a room (owner deletes it, members just leave).

**Headers:**
```
Authorization: Bearer <token>
```

**Response (200):**
```json
{
  "ok": true
}
```

**Errors:**
- `400`: Cannot leave global/public room
- `404`: Room not found

---

### Kick Member from Room
**POST** `/api/rooms/<room_id>/kick`

Removes a member from a room (owner only).

**Headers:**
```
Authorization: Bearer <token>
Content-Type: application/json
```

**Request:**
```json
{
  "user_id": 5
}
```

**Response (200):**
```json
{
  "ok": true
}
```

**Errors:**
- `403`: Only owner can kick
- `404`: Room not found

---

## Message Endpoints

### Get Room Messages
**GET** `/api/rooms/<room_id>/messages?limit=50&offset=0`

Gets message history for a room.

**Headers:**
```
Authorization: Bearer <token>
```

**Query Parameters:**
- `limit` (int, default: 100): Number of messages to fetch
- `offset` (int, default: 0): Pagination offset

**Response (200):**
```json
[
  {
    "id": 1,
    "room_id": 1,
    "user_id": 1,
    "username": "john_doe",
    "avatar_color": "#FF6B9D",
    "content": "Hello everyone!",
    "created_at": "2024-01-15T10:30:00"
  }
]
```

**Errors:**
- `403`: Access denied (for private rooms)
- `404`: Room not found

---

### Send Message
**POST** `/api/rooms/<room_id>/messages`

Sends a message to a room (also broadcasts via WebSocket).

**Headers:**
```
Authorization: Bearer <token>
Content-Type: application/json
```

**Request:**
```json
{
  "content": "Hello everyone!"
}
```

**Response (201):**
```json
{
  "id": 1,
  "room_id": 1,
  "user_id": 1,
  "username": "john_doe",
  "avatar_color": "#FF6B9D",
  "content": "Hello everyone!",
  "created_at": "2024-01-15T10:30:00"
}
```

**Errors:**
- `400`: Invalid message
- `403`: Access denied
- `404`: Room not found

---

## WebSocket Events

### Connection
**Event:** `connect`

Connect to WebSocket with token authentication.

**Auth Data:**
```json
{
  "token": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

---

### Join Room
**Emit:** `join_room`

Join a room and start receiving real-time updates.

**Data:**
```json
{
  "token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "room_id": 1
}
```

**Receives:**
- `member_update`: Updated member count
- `status`: User joined message

---

### Leave Room
**Emit:** `leave_room`

Leave a room.

**Data:**
```json
{
  "room_id": 1
}
```

---

### Send Message
**Emit:** `message`

Send a real-time message.

**Data:**
```json
{
  "token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "room_id": 1,
  "content": "Hello!"
}
```

**Broadcast Event:** `message`
```json
{
  "id": 1,
  "room_id": 1,
  "user_id": 1,
  "username": "john_doe",
  "avatar_color": "#FF6B9D",
  "content": "Hello!",
  "created_at": "2024-01-15T10:30:00"
}
```

---

### Typing Indicator
**Emit:** `typing`

Notify room that you're typing.

**Data:**
```json
{
  "token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "room_id": 1
}
```

**Broadcast Event:** `typing` (to other users)
```json
{
  "username": "john_doe"
}
```

---

### Member Update
**Receive:** `member_update`

Receives updated member count.

**Data:**
```json
{
  "count": 5
}
```

---

## Error Handling

All errors follow this format:

```json
{
  "error": "Error message describing what went wrong"
}
```

Common HTTP status codes:
- `200`: Success
- `201`: Created
- `400`: Bad request
- `401`: Unauthorized
- `403`: Forbidden
- `404`: Not found
- `409`: Conflict (e.g., username exists)

---

## Token Expiration

Tokens expire after **7 days**. When expired, make a new login request to get a fresh token.

---

## Rate Limiting

No rate limiting implemented yet. Add in production!

---

## CORS

CORS is enabled for all origins. Restrict in production!
