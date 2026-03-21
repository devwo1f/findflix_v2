import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/constants/api_constants.dart';
import '../core/network/api_client.dart';
import '../core/network/api_interceptors.dart';
import '../models/user.dart';

// ── Firebase Auth Instance ────────────────────────────────────────────

final firebaseAuthProvider = Provider<FirebaseAuth>((ref) {
  return FirebaseAuth.instance;
});

// ── Auth State Stream ─────────────────────────────────────────────────

final authStateProvider = StreamProvider<User?>((ref) {
  return ref.watch(firebaseAuthProvider).authStateChanges();
});

// ── Token Provider ────────────────────────────────────────────────────

final tokenProvider = FutureProvider<String?>((ref) async {
  final authState = ref.watch(authStateProvider);
  return authState.whenOrNull(
    data: (user) => user?.getIdToken(),
  );
});

// ── Current App User ──────────────────────────────────────────────────

final currentUserProvider = FutureProvider<AppUser?>((ref) async {
  final authState = ref.watch(authStateProvider);
  final user = authState.asData?.value;
  if (user == null) return null;

  // Sync token for API calls.
  final token = await user.getIdToken();
  ref.read(tokenStringProvider.notifier).state = token;

  try {
    final api = ref.read(apiClientProvider);
    final data =
        await api.get<Map<String, dynamic>>(ApiConstants.userProfile);
    return AppUser.fromJson(data);
  } catch (_) {
    // Fallback to Firebase user if backend is unavailable.
    return AppUser(
      id: user.uid,
      email: user.email ?? '',
      displayName: user.displayName ?? '',
      photoUrl: user.photoURL,
      createdAt: user.metadata.creationTime ?? DateTime.now(),
    );
  }
});

// ── Auth Service ──────────────────────────────────────────────────────

final authServiceProvider = Provider<AuthService>((ref) {
  return AuthService(ref);
});

class AuthService {
  final Ref _ref;

  AuthService(this._ref);

  FirebaseAuth get _auth => _ref.read(firebaseAuthProvider);

  /// Sign in with email and password.
  Future<UserCredential> login({
    required String email,
    required String password,
  }) async {
    try {
      final credential = await _auth.signInWithEmailAndPassword(
        email: email.trim(),
        password: password,
      );

      // Push token into interceptor.
      final token = await credential.user?.getIdToken();
      _ref.read(tokenStringProvider.notifier).state = token;

      return credential;
    } on FirebaseAuthException catch (e) {
      throw _mapAuthException(e);
    }
  }

  /// Create a new account.
  Future<UserCredential> signup({
    required String name,
    required String email,
    required String password,
  }) async {
    try {
      final credential = await _auth.createUserWithEmailAndPassword(
        email: email.trim(),
        password: password,
      );

      await credential.user?.updateDisplayName(name.trim());

      // Register in backend.
      try {
        final token = await credential.user?.getIdToken();
        _ref.read(tokenStringProvider.notifier).state = token;
        final api = _ref.read(apiClientProvider);
        await api.post(ApiConstants.signup, data: {
          'uid': credential.user?.uid,
          'email': email.trim(),
          'display_name': name.trim(),
        });
      } catch (_) {
        // Non-critical: backend sync can happen later.
      }

      return credential;
    } on FirebaseAuthException catch (e) {
      throw _mapAuthException(e);
    }
  }

  /// Send password reset email.
  Future<void> resetPassword(String email) async {
    try {
      await _auth.sendPasswordResetEmail(email: email.trim());
    } on FirebaseAuthException catch (e) {
      throw _mapAuthException(e);
    }
  }

  /// Sign out.
  Future<void> logout() async {
    _ref.read(tokenStringProvider.notifier).state = null;
    await _auth.signOut();
  }

  /// Convert Firebase errors to user-friendly messages.
  String _mapAuthException(FirebaseAuthException e) {
    switch (e.code) {
      case 'user-not-found':
        return 'No account found with this email.';
      case 'wrong-password':
        return 'Incorrect password. Please try again.';
      case 'email-already-in-use':
        return 'An account already exists with this email.';
      case 'weak-password':
        return 'Password is too weak. Use at least 6 characters.';
      case 'invalid-email':
        return 'Please enter a valid email address.';
      case 'too-many-requests':
        return 'Too many attempts. Please try again later.';
      case 'network-request-failed':
        return 'Network error. Please check your connection.';
      default:
        return e.message ?? 'Authentication failed. Please try again.';
    }
  }
}
