import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../core/constants/api_constants.dart';
import '../core/network/api_client.dart';
import '../core/network/api_interceptors.dart';
import '../models/user.dart';

const _accessTokenKey = 'findflix_access_token';
const _refreshTokenKey = 'findflix_refresh_token';

// ── Auth State ───────────────────────────────────────────────────────

final authStateProvider = StateNotifierProvider<AuthStateNotifier, AsyncValue<AppUser?>>((ref) {
  return AuthStateNotifier(ref);
});

class AuthStateNotifier extends StateNotifier<AsyncValue<AppUser?>> {
  final Ref _ref;

  AuthStateNotifier(this._ref) : super(const AsyncValue.data(null)) {
    _tryRestoreSession();
  }

  Future<void> _tryRestoreSession() async {
    final prefs = await SharedPreferences.getInstance();
    final token = prefs.getString(_accessTokenKey);
    if (token == null || token.isEmpty) {
      state = const AsyncValue.data(null);
      return;
    }

    _ref.read(tokenStringProvider.notifier).state = token;

    try {
      final api = _ref.read(apiClientProvider);
      final data = await api.get<Map<String, dynamic>>(ApiConstants.profile);
      state = AsyncValue.data(AppUser.fromJson(data));
    } catch (_) {
      await prefs.remove(_accessTokenKey);
      await prefs.remove(_refreshTokenKey);
      _ref.read(tokenStringProvider.notifier).state = null;
      state = const AsyncValue.data(null);
    }
  }

  void setUser(AppUser user) {
    state = AsyncValue.data(user);
  }

  void clear() {
    state = const AsyncValue.data(null);
  }
}

// ── Current App User (convenience alias) ─────────────────────────────

final currentUserProvider = Provider<AsyncValue<AppUser?>>((ref) {
  return ref.watch(authStateProvider);
});

// ── Auth Service ─────────────────────────────────────────────────────

final authServiceProvider = Provider<AuthService>((ref) {
  return AuthService(ref);
});

class AuthService {
  final Ref _ref;

  AuthService(this._ref);

  Future<void> login({
    required String email,
    required String password,
  }) async {
    final api = _ref.read(apiClientProvider);
    final data = await api.post<Map<String, dynamic>>(
      ApiConstants.login,
      data: {'email': email.trim(), 'password': password},
    );

    final accessToken = data['access_token'] as String;
    final refreshToken = data['refresh_token'] as String? ?? '';

    await _persistTokens(accessToken, refreshToken);
    _ref.read(tokenStringProvider.notifier).state = accessToken;

    final profileData = await api.get<Map<String, dynamic>>(ApiConstants.profile);
    final user = AppUser.fromJson(profileData);
    _ref.read(authStateProvider.notifier).setUser(user);
  }

  Future<void> signup({
    required String name,
    required String email,
    required String password,
  }) async {
    final api = _ref.read(apiClientProvider);
    final data = await api.post<Map<String, dynamic>>(
      ApiConstants.signup,
      data: {
        'email': email.trim(),
        'password': password,
        'display_name': name.trim(),
      },
    );

    final accessToken = data['access_token'] as String;
    final refreshToken = data['refresh_token'] as String? ?? '';

    await _persistTokens(accessToken, refreshToken);
    _ref.read(tokenStringProvider.notifier).state = accessToken;

    final profileData = await api.get<Map<String, dynamic>>(ApiConstants.profile);
    final user = AppUser.fromJson(profileData);
    _ref.read(authStateProvider.notifier).setUser(user);
  }

  Future<void> resetPassword(String email) async {
    final api = _ref.read(apiClientProvider);
    await api.post(
      ApiConstants.resetPassword,
      data: {'email': email.trim()},
    );
  }

  Future<void> logout() async {
    _ref.read(tokenStringProvider.notifier).state = null;
    _ref.read(authStateProvider.notifier).clear();
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_accessTokenKey);
    await prefs.remove(_refreshTokenKey);
  }

  Future<void> _persistTokens(String access, String refresh) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_accessTokenKey, access);
    await prefs.setString(_refreshTokenKey, refresh);
  }
}
