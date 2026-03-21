import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/constants/api_constants.dart';
import '../core/network/api_client.dart';
import '../models/recommendation.dart';

// ── Personalized Recommendations ──────────────────────────────────────

final recommendationsProvider =
    FutureProvider.autoDispose<List<Recommendation>>((ref) async {
  final api = ref.read(apiClientProvider);
  final data = await api.get<Map<String, dynamic>>(ApiConstants.personalized);
  final list = data['recommendations'] as List<dynamic>? ?? [];
  return list
      .map((e) => Recommendation.fromJson(e as Map<String, dynamic>))
      .toList();
});

// ── Trending ──────────────────────────────────────────────────────────

final trendingProvider =
    FutureProvider.autoDispose<List<Recommendation>>((ref) async {
  final api = ref.read(apiClientProvider);
  final data = await api.get<Map<String, dynamic>>(ApiConstants.trending);
  final list = data['results'] as List<dynamic>? ?? [];
  return list
      .map((e) => Recommendation.fromJson(e as Map<String, dynamic>))
      .toList();
});

// ── "Because you liked X" ─────────────────────────────────────────────

final becauseYouLikedProvider =
    FutureProvider.autoDispose<List<Recommendation>>((ref) async {
  final api = ref.read(apiClientProvider);
  final data =
      await api.get<Map<String, dynamic>>(ApiConstants.becauseYouLiked);
  final list = data['results'] as List<dynamic>? ?? [];
  return list
      .map((e) => Recommendation.fromJson(e as Map<String, dynamic>))
      .toList();
});

// ── Recommendation Feed (paginated) ───────────────────────────────────

final recommendationFeedProvider = StateNotifierProvider.autoDispose<
    RecommendationFeedNotifier, RecommendationFeedState>((ref) {
  return RecommendationFeedNotifier(ref);
});

class RecommendationFeedState {
  final List<Recommendation> items;
  final bool isLoading;
  final bool hasMore;
  final String? error;
  final int currentIndex;

  const RecommendationFeedState({
    this.items = const [],
    this.isLoading = false,
    this.hasMore = true,
    this.error,
    this.currentIndex = 0,
  });

  RecommendationFeedState copyWith({
    List<Recommendation>? items,
    bool? isLoading,
    bool? hasMore,
    String? error,
    int? currentIndex,
  }) {
    return RecommendationFeedState(
      items: items ?? this.items,
      isLoading: isLoading ?? this.isLoading,
      hasMore: hasMore ?? this.hasMore,
      error: error,
      currentIndex: currentIndex ?? this.currentIndex,
    );
  }
}

class RecommendationFeedNotifier
    extends StateNotifier<RecommendationFeedState> {
  final Ref _ref;
  int _page = 1;

  RecommendationFeedNotifier(this._ref)
      : super(const RecommendationFeedState()) {
    loadMore();
  }

  Future<void> loadMore() async {
    if (state.isLoading || !state.hasMore) return;
    state = state.copyWith(isLoading: true, error: null);

    try {
      final api = _ref.read(apiClientProvider);
      final data = await api.get<Map<String, dynamic>>(
        ApiConstants.recommendations,
        queryParameters: {'page': _page, 'limit': 10},
      );
      final list = (data['results'] as List<dynamic>? ?? [])
          .map((e) => Recommendation.fromJson(e as Map<String, dynamic>))
          .toList();

      _page++;
      state = state.copyWith(
        items: [...state.items, ...list],
        isLoading: false,
        hasMore: list.length >= 10,
      );
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: 'Failed to load recommendations.',
      );
    }
  }

  void setCurrentIndex(int index) {
    state = state.copyWith(currentIndex: index);
    // Pre-fetch when nearing the end.
    if (index >= state.items.length - 3) {
      loadMore();
    }
  }

  Future<void> refresh() async {
    _page = 1;
    state = const RecommendationFeedState();
    await loadMore();
  }
}

// ── Feedback ──────────────────────────────────────────────────────────

final recommendationFeedbackProvider =
    Provider<RecommendationFeedbackService>((ref) {
  return RecommendationFeedbackService(ref);
});

class RecommendationFeedbackService {
  final Ref _ref;

  RecommendationFeedbackService(this._ref);

  Future<void> submit(RecommendationFeedback feedback) async {
    final api = _ref.read(apiClientProvider);
    await api.post(
      ApiConstants.recommendationFeedback,
      data: feedback.toJson(),
    );
  }
}
