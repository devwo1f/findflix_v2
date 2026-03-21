/// Central registry of all API endpoints and configuration constants.
class ApiConstants {
  ApiConstants._();

  // ── Base URL ─────────────────────────────────────────────────────
  static const String baseUrl = 'https://api.findflix.com/api/v1';
  static const String devBaseUrl = 'http://localhost:8000/api/v1';

  // ── Timeouts (milliseconds) ──────────────────────────────────────
  static const int connectTimeout = 15000;
  static const int receiveTimeout = 30000;
  static const int sendTimeout = 15000;

  // ── Auth ─────────────────────────────────────────────────────────
  static const String login = '/auth/login';
  static const String signup = '/auth/signup';
  static const String logout = '/auth/logout';
  static const String refreshToken = '/auth/refresh';
  static const String resetPassword = '/auth/reset-password';
  static const String profile = '/auth/profile';

  // ── Questionnaire ────────────────────────────────────────────────
  static const String submitQuestionnaire = '/questionnaire';
  static const String getQuestionnaire = '/questionnaire';

  // ── Recommendations ──────────────────────────────────────────────
  static const String recommendations = '/recommendations';
  static const String trending = '/recommendations/trending';
  static const String personalized = '/recommendations/personalized';
  static const String becauseYouLiked = '/recommendations/because-you-liked';
  static const String recommendationFeedback = '/recommendations/feedback';

  // ── Titles ───────────────────────────────────────────────────────
  static const String titles = '/titles';
  static String titleDetail(String id) => '/titles/$id';
  static String similarTitles(String id) => '/titles/$id/similar';
  static String titleAvailability(String id) => '/titles/$id/availability';
  static const String search = '/titles/search';

  // ── Watchlist ────────────────────────────────────────────────────
  static const String watchlist = '/watchlist';
  static String watchlistItem(String id) => '/watchlist/$id';

  // ── Watch History ────────────────────────────────────────────────
  static const String watchHistory = '/history';
  static String historyItem(String id) => '/history/$id';

  // ── User ─────────────────────────────────────────────────────────
  static const String userProfile = '/user/profile';
  static const String userStats = '/user/stats';
  static const String userPreferences = '/user/preferences';
  static const String tasteProfile = '/user/taste-profile';

  // ── Admin ────────────────────────────────────────────────────────
  static const String adminStats = '/admin/stats';
  static const String adminUsers = '/admin/users';
  static const String adminLogs = '/admin/logs';
  static const String adminSync = '/admin/sync-tmdb';
  static const String adminModelInfo = '/admin/model-info';

  // ── TMDb Image Base ──────────────────────────────────────────────
  static const String tmdbImageBase = 'https://image.tmdb.org/t/p';
  static String posterUrl(String path, {String size = 'w500'}) =>
      '$tmdbImageBase/$size$path';
  static String backdropUrl(String path, {String size = 'w1280'}) =>
      '$tmdbImageBase/$size$path';

  // ── Headers ──────────────────────────────────────────────────────
  static const Map<String, String> defaultHeaders = {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
    'X-Client': 'findflix-flutter',
  };
}
