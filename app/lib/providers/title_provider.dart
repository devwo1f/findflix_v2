import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/constants/api_constants.dart';
import '../core/network/api_client.dart';
import '../models/title_model.dart';

// ── Title Detail ──────────────────────────────────────────────────────

final titleDetailProvider =
    FutureProvider.autoDispose.family<TitleModel, String>((ref, id) async {
  final api = ref.read(apiClientProvider);
  final data =
      await api.get<Map<String, dynamic>>(ApiConstants.titleDetail(id));
  return TitleModel.fromJson(data);
});

// ── Similar Titles ────────────────────────────────────────────────────

final similarTitlesProvider =
    FutureProvider.autoDispose.family<List<TitleModel>, String>((ref, id) async {
  final api = ref.read(apiClientProvider);
  final data = await api.get<List<dynamic>>(ApiConstants.similarTitles(id));
  return data
      .map((e) => TitleModel.fromJson(e as Map<String, dynamic>))
      .toList();
});

// ── Search ────────────────────────────────────────────────────────────

final searchQueryProvider = StateProvider<String>((ref) => '');

final searchFiltersProvider = StateProvider<SearchFilters>(
  (ref) => const SearchFilters(),
);

class SearchFilters {
  final String? genre;
  final int? year;
  final String? type; // 'movie' | 'tv' | null (both)

  const SearchFilters({this.genre, this.year, this.type});

  SearchFilters copyWith({
    String? genre,
    int? year,
    String? type,
    bool clearGenre = false,
    bool clearYear = false,
    bool clearType = false,
  }) {
    return SearchFilters(
      genre: clearGenre ? null : (genre ?? this.genre),
      year: clearYear ? null : (year ?? this.year),
      type: clearType ? null : (type ?? this.type),
    );
  }

  Map<String, dynamic> toQueryParams() {
    final params = <String, dynamic>{};
    if (genre != null) params['genre'] = genre;
    if (year != null) params['year'] = year;
    if (type != null) params['type'] = type;
    return params;
  }

  bool get hasActiveFilters => genre != null || year != null || type != null;
}

final searchResultsProvider =
    FutureProvider.autoDispose<List<TitleModel>>((ref) async {
  final query = ref.watch(searchQueryProvider);
  if (query.trim().length < 2) return [];

  final filters = ref.watch(searchFiltersProvider);
  final api = ref.read(apiClientProvider);

  final params = <String, dynamic>{
    'q': query.trim(),
    ...filters.toQueryParams(),
  };

  final data = await api.get<Map<String, dynamic>>(
    ApiConstants.search,
    queryParameters: params,
  );

  final list = data['items'] as List<dynamic>? ?? [];
  return list
      .map((e) => TitleModel.fromJson(e as Map<String, dynamic>))
      .toList();
});

// ── Recent Searches (local) ───────────────────────────────────────────

final recentSearchesProvider =
    StateNotifierProvider<RecentSearchesNotifier, List<String>>((ref) {
  return RecentSearchesNotifier();
});

class RecentSearchesNotifier extends StateNotifier<List<String>> {
  RecentSearchesNotifier() : super([]);

  void add(String query) {
    final trimmed = query.trim();
    if (trimmed.isEmpty) return;
    final updated = [trimmed, ...state.where((s) => s != trimmed)];
    state = updated.take(10).toList();
  }

  void remove(String query) {
    state = state.where((s) => s != query).toList();
  }

  void clear() {
    state = [];
  }
}
