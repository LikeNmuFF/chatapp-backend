# Flutter Chat App - Setup & Development Guide

## Prerequisites

Before starting, ensure you have:
1. **Flutter SDK** - [Install Flutter](https://flutter.dev/docs/get-started/install)
2. **Android Studio** - [Install Android Studio](https://developer.android.com/studio)
3. **Git** - For version control
4. **VS Code or Android Studio** - For development

## Step 1: Create Flutter Project

```bash
# Create a new Flutter project
flutter create chatapp_mobile

# Navigate to the project
cd chatapp_mobile
```

## Step 2: Project Structure

Create the following directory structure:

```
chatapp_mobile/
├── lib/
│   ├── main.dart
│   ├── config/
│   │   ├── api_config.dart
│   │   └── socket_config.dart
│   ├── models/
│   │   ├── user_model.dart
│   │   ├── room_model.dart
│   │   └── message_model.dart
│   ├── providers/
│   │   ├── auth_provider.dart
│   │   ├── chat_provider.dart
│   │   └── room_provider.dart
│   ├── screens/
│   │   ├── auth/
│   │   │   ├── login_screen.dart
│   │   │   ├── register_screen.dart
│   │   │   └── splash_screen.dart
│   │   └── chat/
│   │       ├── room_list_screen.dart
│   │       ├── chat_room_screen.dart
│   │       └── room_creation_screen.dart
│   ├── services/
│   │   ├── api_service.dart
│   │   ├── socket_service.dart
│   │   └── storage_service.dart
│   └── widgets/
│       ├── message_bubble.dart
│       ├── room_card.dart
│       ├── user_avatar.dart
│       └── custom_app_bar.dart
├── test/
├── pubspec.yaml
└── README.md
```

## Step 3: Update pubspec.yaml

Add the following dependencies to your `pubspec.yaml`:

```yaml
dependencies:
  flutter:
    sdk: flutter

  # State Management
  provider: ^6.0.0
  
  # HTTP & WebSocket
  http: ^1.1.0
  socket_io_client: ^2.0.0
  
  # Local Storage
  shared_preferences: ^2.2.0
  flutter_secure_storage: ^9.0.0
  
  # JSON & Serialization
  json_serializable: ^6.7.0
  
  # UI & Formatting
  google_fonts: ^6.1.0
  intl: ^0.19.0
  
  # State Management (optional, but recommended)
  riverpod: ^2.4.0

dev_dependencies:
  flutter_test:
    sdk: flutter
  flutter_linter:
  build_runner: ^2.4.0
  json_serializable: ^6.7.0
```

Then run:
```bash
flutter pub get
```

## Step 4: Android Configuration

### AndroidManifest.xml
Ensure you have internet permissions. Update `android/app/src/main/AndroidManifest.xml`:

```xml
<manifest ...>
    <uses-permission android:name="android.permission.INTERNET" />
    <uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />
    ...
</manifest>
```

### Build.gradle
Update `android/app/build.gradle`:

```gradle
android {
    compileSdkVersion 34  // or latest
    
    defaultConfig {
        minSdkVersion 21  // Minimum for modern features
        targetSdkVersion 34
    }
}
```

## Step 5: Configuration Files

### lib/config/api_config.dart
```dart
class ApiConfig {
  static const String baseUrl = 'http://YOUR_BACKEND_URL:5000';
  
  // Auth endpoints
  static const String loginEndpoint = '/api/auth/login';
  static const String registerEndpoint = '/api/auth/register';
  static const String verifyEndpoint = '/api/auth/verify';
  
  // Room endpoints
  static const String roomsEndpoint = '/api/rooms';
  static const String messagesEndpoint = '/api/rooms';
  
  // Socket endpoint
  static const String socketUrl = 'http://YOUR_BACKEND_URL:5000';
}
```

### lib/config/socket_config.dart
```dart
class SocketConfig {
  static const String url = 'http://YOUR_BACKEND_URL:5000';
  
  static const Map<String, dynamic> options = {
    'reconnection': true,
    'reconnectionDelay': 1000,
    'reconnectionDelayMax': 5000,
    'reconnectionAttempts': 99999,
    'transports': ['websocket'],
  };
}
```

## Step 6: Core Services

### lib/services/storage_service.dart
Handles token and preference storage:

```dart
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:shared_preferences/shared_preferences.dart';

class StorageService {
  static const String _tokenKey = 'auth_token';
  static const String _userKey = 'user_data';
  
  static const _secureStorage = FlutterSecureStorage();
  
  // Store token securely
  static Future<void> saveToken(String token) async {
    await _secureStorage.write(key: _tokenKey, value: token);
  }
  
  // Retrieve token
  static Future<String?> getToken() async {
    return await _secureStorage.read(key: _tokenKey);
  }
  
  // Delete token
  static Future<void> deleteToken() async {
    await _secureStorage.delete(key: _tokenKey);
  }
  
  // Save user data
  static Future<void> saveUserData(String userData) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_userKey, userData);
  }
  
  // Get user data
  static Future<String?> getUserData() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_userKey);
  }
}
```

### lib/services/api_service.dart
Handles all HTTP API calls:

```dart
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'api_config.dart';
import 'storage_service.dart';

class ApiService {
  // Helper to get headers with token
  static Future<Map<String, String>> _getHeaders() async {
    final token = await StorageService.getToken();
    return {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      if (token != null) 'Authorization': 'Bearer $token',
    };
  }

  // Registration
  static Future<Map<String, dynamic>> register(
    String username,
    String password,
  ) async {
    final response = await http.post(
      Uri.parse('${ApiConfig.baseUrl}${ApiConfig.registerEndpoint}'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'username': username,
        'password': password,
      }),
    );

    if (response.statusCode == 201) {
      return jsonDecode(response.body);
    } else {
      throw Exception('Registration failed: ${response.body}');
    }
  }

  // Login
  static Future<Map<String, dynamic>> login(
    String username,
    String password,
  ) async {
    final response = await http.post(
      Uri.parse('${ApiConfig.baseUrl}${ApiConfig.loginEndpoint}'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'username': username,
        'password': password,
      }),
    );

    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    } else {
      throw Exception('Login failed: ${response.body}');
    }
  }

  // Get rooms
  static Future<List<dynamic>> getRooms() async {
    final headers = await _getHeaders();
    final response = await http.get(
      Uri.parse('${ApiConfig.baseUrl}${ApiConfig.roomsEndpoint}'),
      headers: headers,
    );

    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    } else {
      throw Exception('Failed to load rooms');
    }
  }

  // Get messages
  static Future<List<dynamic>> getMessages(
    int roomId, {
    int limit = 100,
    int offset = 0,
  }) async {
    final headers = await _getHeaders();
    final response = await http.get(
      Uri.parse(
        '${ApiConfig.baseUrl}${ApiConfig.messagesEndpoint}/$roomId/messages?limit=$limit&offset=$offset',
      ),
      headers: headers,
    );

    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    } else {
      throw Exception('Failed to load messages');
    }
  }

  // Send message
  static Future<Map<String, dynamic>> sendMessage(
    int roomId,
    String content,
  ) async {
    final headers = await _getHeaders();
    final response = await http.post(
      Uri.parse(
        '${ApiConfig.baseUrl}${ApiConfig.messagesEndpoint}/$roomId/messages',
      ),
      headers: headers,
      body: jsonEncode({'content': content}),
    );

    if (response.statusCode == 201) {
      return jsonDecode(response.body);
    } else {
      throw Exception('Failed to send message');
    }
  }
}
```

### lib/services/socket_service.dart
Handles WebSocket connections:

```dart
import 'package:socket_io_client/socket_io_client.dart' as IO;
import 'storage_service.dart';
import 'socket_config.dart';

class SocketService {
  static final SocketService _instance = SocketService._internal();
  
  late IO.Socket socket;
  
  factory SocketService() {
    return _instance;
  }
  
  SocketService._internal();
  
  Future<void> connect() async {
    final token = await StorageService.getToken();
    
    socket = IO.io(
      SocketConfig.url,
      IO.OptionBuilder()
          .setAuth({'token': token})
          .setTransports(['websocket'])
          .enableForceNew()
          .enableAutoConnect()
          .build(),
    );
    
    socket.onConnect((_) {
      print('Socket connected');
    });
    
    socket.onDisconnect((_) {
      print('Socket disconnected');
    });
  }
  
  void joinRoom(int roomId) {
    socket.emit('join_room', {
      'room_id': roomId,
      'token': StorageService.getToken(),
    });
  }
  
  void leaveRoom(int roomId) {
    socket.emit('leave_room', {'room_id': roomId});
  }
  
  void sendMessage(int roomId, String content) {
    socket.emit('message', {
      'room_id': roomId,
      'content': content,
      'token': StorageService.getToken(),
    });
  }
  
  void onMessage(Function(dynamic) callback) {
    socket.on('message', callback);
  }
  
  void onMemberUpdate(Function(dynamic) callback) {
    socket.on('member_update', callback);
  }
  
  void disconnect() {
    socket.disconnect();
  }
}
```

## Step 7: Models

Create data models for type safety and JSON serialization.

### lib/models/user_model.dart
```dart
class User {
  final int id;
  final String username;
  final String avatarColor;
  final String createdAt;
  
  User({
    required this.id,
    required this.username,
    required this.avatarColor,
    required this.createdAt,
  });
  
  factory User.fromJson(Map<String, dynamic> json) {
    return User(
      id: json['id'],
      username: json['username'],
      avatarColor: json['avatar_color'],
      createdAt: json['created_at'],
    );
  }
}
```

### lib/models/room_model.dart
```dart
class Room {
  final int id;
  final String name;
  final String description;
  final bool isGlobal;
  final bool isPrivate;
  final int? ownerId;
  final String? ownerName;
  final String createdAt;
  
  Room({
    required this.id,
    required this.name,
    required this.description,
    required this.isGlobal,
    required this.isPrivate,
    this.ownerId,
    this.ownerName,
    required this.createdAt,
  });
  
  factory Room.fromJson(Map<String, dynamic> json) {
    return Room(
      id: json['id'],
      name: json['name'],
      description: json['description'],
      isGlobal: json['is_global'],
      isPrivate: json['is_private'],
      ownerId: json['owner_id'],
      ownerName: json['owner_name'],
      createdAt: json['created_at'],
    );
  }
}
```

### lib/models/message_model.dart
```dart
class Message {
  final int id;
  final int roomId;
  final int userId;
  final String username;
  final String avatarColor;
  final String content;
  final String createdAt;
  
  Message({
    required this.id,
    required this.roomId,
    required this.userId,
    required this.username,
    required this.avatarColor,
    required this.content,
    required this.createdAt,
  });
  
  factory Message.fromJson(Map<String, dynamic> json) {
    return Message(
      id: json['id'],
      roomId: json['room_id'],
      userId: json['user_id'],
      username: json['username'],
      avatarColor: json['avatar_color'],
      content: json['content'],
      createdAt: json['created_at'],
    );
  }
}
```

## Step 8: State Management Providers

### lib/providers/auth_provider.dart
```dart
import 'package:flutter/material.dart';
import '../models/user_model.dart';
import '../services/api_service.dart';
import '../services/storage_service.dart';

class AuthProvider with ChangeNotifier {
  User? _user;
  String? _token;
  bool _isLoading = false;
  String? _error;
  
  User? get user => _user;
  String? get token => _token;
  bool get isLoading => _isLoading;
  String? get error => _error;
  bool get isAuthenticated => _token != null && _user != null;
  
  Future<bool> login(String username, String password) async {
    _isLoading = true;
    _error = null;
    notifyListeners();
    
    try {
      final response = await ApiService.login(username, password);
      _token = response['token'];
      _user = User.fromJson(response['user']);
      
      await StorageService.saveToken(_token!);
      await StorageService.saveUserData(_user.toString());
      
      _isLoading = false;
      notifyListeners();
      return true;
    } catch (e) {
      _error = e.toString();
      _isLoading = false;
      notifyListeners();
      return false;
    }
  }
  
  Future<bool> register(String username, String password) async {
    _isLoading = true;
    _error = null;
    notifyListeners();
    
    try {
      final response = await ApiService.register(username, password);
      _token = response['token'];
      _user = User.fromJson(response['user']);
      
      await StorageService.saveToken(_token!);
      
      _isLoading = false;
      notifyListeners();
      return true;
    } catch (e) {
      _error = e.toString();
      _isLoading = false;
      notifyListeners();
      return false;
    }
  }
  
  Future<void> logout() async {
    await StorageService.deleteToken();
    _user = null;
    _token = null;
    notifyListeners();
  }
}
```

## Step 9: Run the App

```bash
# Connect an Android device or emulator
flutter devices

# Run the app
flutter run

# Or run in release mode
flutter run --release
```

## Troubleshooting

### Android Emulator Issues
```bash
# List available emulators
flutter emulators

# Launch an emulator
flutter emulators --launch <emulator_name>
```

### Cannot connect to backend
- Ensure backend is running: `python app.py`
- Check backend URL in `lib/config/api_config.dart`
- On Android emulator, use `10.0.2.2` instead of `localhost`
- Update `api_config.dart`:
  ```dart
  static const String baseUrl = 'http://10.0.2.2:5000';
  ```

### Flutter Doctor Issues
```bash
flutter doctor
# Follow the recommended fixes
```

## Building APK

```bash
# Build APK for testing
flutter build apk --release

# Output: build/app/outputs/flutter-app.apk
```

## Building App Bundle (for Google Play Store)

```bash
flutter build appbundle --release
```

## Next Steps

1. Complete authentication screens
2. Implement room listing screen
3. Build chat room UI
4. Add real-time messaging
5. Implement offline support
6. Add push notifications
7. Optimize performance
8. Test thoroughly
9. Prepare for Google Play Store release

---

## Resources

- [Flutter Documentation](https://flutter.dev/docs)
- [Provider State Management](https://pub.dev/packages/provider)
- [Socket.IO Client Dart](https://pub.dev/packages/socket_io_client)
- [Flutter Best Practices](https://flutter.dev/docs/testing/best-practices)
