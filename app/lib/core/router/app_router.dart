import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../providers/auth_provider.dart';
import '../../screens/admin/admin_screen.dart';
import '../../screens/auth/login_screen.dart';
import '../../screens/auth/signup_screen.dart';
import '../../screens/home/dashboard_screen.dart';
import '../../screens/home/home_screen.dart';
import '../../screens/onboarding/questionnaire_screen.dart';
import '../../screens/profile/profile_screen.dart';
import '../../screens/recommendations/recommendation_feed_screen.dart';
import '../../screens/search/search_screen.dart';
import '../../screens/settings/settings_screen.dart';
import '../../screens/splash/splash_screen.dart';
import '../../screens/titles/title_detail_screen.dart';
import '../../screens/watchlist/watchlist_screen.dart';

// ── Route Names ───────────────────────────────────────────────────────

class AppRoutes {
  AppRoutes._();

  static const String splash = '/';
  static const String login = '/login';
  static const String signup = '/signup';
  static const String onboarding = '/onboarding';
  static const String home = '/home';
  static const String recommendations = 'recommendations';
  static const String search = 'search';
  static const String watchlist = 'watchlist';
  static const String profile = 'profile';
  static const String titleDetail = '/title/:id';
  static const String settings = '/settings';
  static const String admin = '/admin';
}

// ── GoRouter Provider ─────────────────────────────────────────────────

final routerProvider = Provider<GoRouter>((ref) {
  final authState = ref.watch(authStateProvider);

  return GoRouter(
    initialLocation: AppRoutes.splash,
    debugLogDiagnostics: true,
    redirect: (context, state) {
      final isLoggedIn = authState.asData?.value != null;
      final isAuthRoute = state.matchedLocation == AppRoutes.login ||
          state.matchedLocation == AppRoutes.signup;
      final isSplash = state.matchedLocation == AppRoutes.splash;

      // Let splash load on its own.
      if (isSplash) return null;

      // Not authenticated → login.
      if (!isLoggedIn && !isAuthRoute) return AppRoutes.login;

      // Authenticated but on auth pages → home.
      if (isLoggedIn && isAuthRoute) return AppRoutes.home;

      return null;
    },
    routes: [
      // Splash
      GoRoute(
        path: AppRoutes.splash,
        builder: (context, state) => const SplashScreen(),
      ),

      // Auth
      GoRoute(
        path: AppRoutes.login,
        builder: (context, state) => const LoginScreen(),
      ),
      GoRoute(
        path: AppRoutes.signup,
        builder: (context, state) => const SignupScreen(),
      ),

      // Onboarding
      GoRoute(
        path: AppRoutes.onboarding,
        builder: (context, state) => const QuestionnaireScreen(),
      ),

      // Home (shell route with bottom nav)
      ShellRoute(
        builder: (context, state, child) => HomeScreen(child: child),
        routes: [
          GoRoute(
            path: AppRoutes.home,
            builder: (context, state) => const DashboardScreen(),
            routes: [
              GoRoute(
                path: AppRoutes.recommendations,
                builder: (context, state) =>
                    const RecommendationFeedScreen(),
              ),
              GoRoute(
                path: AppRoutes.search,
                builder: (context, state) => const SearchScreen(),
              ),
              GoRoute(
                path: AppRoutes.watchlist,
                builder: (context, state) => const WatchlistScreen(),
              ),
              GoRoute(
                path: AppRoutes.profile,
                builder: (context, state) => const ProfileScreen(),
              ),
            ],
          ),
        ],
      ),

      // Title Detail (outside shell)
      GoRoute(
        path: AppRoutes.titleDetail,
        builder: (context, state) {
          final id = state.pathParameters['id']!;
          return TitleDetailScreen(titleId: id);
        },
      ),

      // Settings
      GoRoute(
        path: AppRoutes.settings,
        builder: (context, state) => const SettingsScreen(),
      ),

      // Admin
      GoRoute(
        path: AppRoutes.admin,
        builder: (context, state) => const AdminScreen(),
      ),
    ],
    errorBuilder: (context, state) => Scaffold(
      body: Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.error_outline, size: 64, color: Colors.white54),
            const SizedBox(height: 16),
            Text(
              'Page not found',
              style: Theme.of(context).textTheme.headlineMedium,
            ),
            const SizedBox(height: 24),
            ElevatedButton(
              onPressed: () => context.go(AppRoutes.home),
              child: const Text('Go Home'),
            ),
          ],
        ),
      ),
    ),
  );
});
