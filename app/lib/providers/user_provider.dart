import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/constants/api_constants.dart';
import '../core/network/api_client.dart';
import '../models/title_model.dart';
import '../models/user.dart';

// ── User Stats ────────────────────────────────────────────────────────

final userStatsProvider = FutureProvider.autoDispose<UserStats>((ref) async {
  final api = ref.read(apiClientProvider);
  final data = await api.get<Map<String, dynamic>>(ApiConstants.userStats);
  return UserStats.fromJson(data);
});

// ── Watchlist ─────────────────────────────────────────────────────────

final watchlistProvider =
    StateNotifierProvider<WatchlistNotifier, WatchlistState>((ref) {
  return WatchlistNotifier(ref);
});

class WatchlistState {
  final List<TitleModel> items;
  final bool isLoading;
  final String? error;

  const WatchlistState({
    this.items = const [],
    this.isLoading = false,
    this.error,
  });

  WatchlistState copyWith({
    List<TitleModel>? items,
    bool? isLoading,
    String? error,
  }) {
    return WatchlistState(
      items: items ?? this.items,
      isLoading: isLoading ?? this.isLoading,
      error: error,
    );
  }
}

class WatchlistNotifier extends StateNotifier<WatchlistState> {
  final Ref _ref;

  WatchlistNotifier(this._ref) : super(const WatchlistState()) {
    load();
  }

  Future<void> load() async {
    state = state.copyWith(isLoading: true, error: null);
    try {
      final api = _ref.read(apiClientProvider);
      final data = await api.get<List<dynamic>>(ApiConstants.watchlist);
      final list = data
          .map((e) {
            final entry = e as Map<String, dynamic>;
            final titleData = entry['title'] as Map<String, dynamic>?;
            return titleData != null ? TitleModel.fromJson(titleData) : null;
          })
          .whereType<TitleModel>()
          .toList();
      state = state.copyWith(items: list, isLoading: false);
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: 'Failed to load watchlist.',
      );
    }
  }

  Future<void> add(TitleModel title) async {
    // Optimistic update.
    state = state.copyWith(
      items: [title.copyWith(isInWatchlist: true), ...state.items],
    );
    try {
      final api = _ref.read(apiClientProvider);
      await api.post(ApiConstants.watchlist, data: {'title_id': title.id});
    } catch (_) {
      // Revert on failure.
      state = state.copyWith(
        items: state.items.where((t) => t.id != title.id).toList(),
      );
    }
  }

  Future<void> remove(String titleId) async {
    final backup = state.items;
    state = state.copyWith(
      items: state.items.where((t) => t.id != titleId).toList(),
    );
    try {
      final api = _ref.read(apiClientProvider);
      await api.delete(ApiConstants.watchlistItem(titleId));
    } catch (_) {
      state = state.copyWith(items: backup);
    }
  }

  bool isInWatchlist(String titleId) {
    return state.items.any((t) => t.id == titleId);
  }
}

// ── Watch History ─────────────────────────────────────────────────────

final watchHistoryProvider =
    FutureProvider.autoDispose<List<TitleModel>>((ref) async {
  final api = ref.read(apiClientProvider);
  final data = await api.get<List<dynamic>>(ApiConstants.watchHistory);
  return data
      .map((e) {
        final entry = e as Map<String, dynamic>;
        final titleData = entry['title'] as Map<String, dynamic>?;
        return titleData != null ? TitleModel.fromJson(titleData) : null;
      })
      .whereType<TitleModel>()
      .toList();
});

// ── Mark as Watched ───────────────────────────────────────────────────

final markWatchedProvider = Provider<MarkWatchedService>((ref) {
  return MarkWatchedService(ref);
});

class MarkWatchedService {
  final Ref _ref;

  MarkWatchedService(this._ref);

  Future<void> markWatched(String titleId, {double? rating}) async {
    final api = _ref.read(apiClientProvider);
    await api.post(ApiConstants.watchHistory, data: {
      'title_id': titleId,
      if (rating != null) 'rating': rating,
    });
  }

  Future<void> removeFromHistory(String titleId) async {
    final api = _ref.read(apiClientProvider);
    await api.delete(ApiConstants.historyItem(titleId));
  }
}

// ── Taste Profile ─────────────────────────────────────────────────────

const _tmdbGenreNames = <String, String>{
  '28': 'Action', '12': 'Adventure', '16': 'Animation', '35': 'Comedy',
  '80': 'Crime', '99': 'Documentary', '18': 'Drama', '10751': 'Family',
  '14': 'Fantasy', '36': 'History', '27': 'Horror', '10402': 'Music',
  '9648': 'Mystery', '10749': 'Romance', '878': 'Sci-Fi', '53': 'Thriller',
  '10752': 'War', '37': 'Western', '10770': 'TV Movie',
};

List<String> _extractList(dynamic raw, {bool mapGenreIds = false}) {
  if (raw is List) {
    return raw.map((e) {
      final s = e.toString();
      return mapGenreIds ? (_tmdbGenreNames[s] ?? s) : s;
    }).toList();
  }
  if (raw is Map) {
    return raw.keys.map((k) {
      final s = k.toString();
      return mapGenreIds ? (_tmdbGenreNames[s] ?? s) : s;
    }).toList();
  }
  return <String>[];
}

final tasteProfileProvider =
    FutureProvider.autoDispose<Map<String, dynamic>>((ref) async {
  final api = ref.read(apiClientProvider);
  try {
    final data = await api.get<Map<String, dynamic>>(ApiConstants.tasteProfile);
    return {
      'top_genres': _extractList(data['genre_preferences'], mapGenreIds: true),
      'top_moods': _extractList(data['mood_preferences']),
    };
  } catch (_) {
    return {'top_genres': <String>[], 'top_moods': <String>[]};
  }
});

// ── Dashboard Aggregate ───────────────────────────────────────────────

final dashboardStatsProvider =
    FutureProvider.autoDispose<DashboardStats>((ref) async {
  final stats = await ref.watch(userStatsProvider.future);
  return DashboardStats(
    watchedCount: stats.watchedCount,
    watchlistCount: stats.watchlistCount,
    avgRating: stats.averageRating,
    hoursWatched: stats.totalHoursWatched,
    topGenre: stats.topGenre,
  );
});

class DashboardStats {
  final int watchedCount;
  final int watchlistCount;
  final double avgRating;
  final int hoursWatched;
  final String topGenre;

  const DashboardStats({
    required this.watchedCount,
    required this.watchlistCount,
    required this.avgRating,
    required this.hoursWatched,
    required this.topGenre,
  });
}
