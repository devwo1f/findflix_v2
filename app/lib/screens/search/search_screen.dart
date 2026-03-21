import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/theme/app_colors.dart';
import '../../providers/title_provider.dart';
import '../../widgets/empty_state.dart';
import '../../widgets/genre_chip.dart';
import '../../widgets/shimmer_loading.dart';
import '../../widgets/title_card.dart';

class SearchScreen extends ConsumerStatefulWidget {
  const SearchScreen({super.key});

  @override
  ConsumerState<SearchScreen> createState() => _SearchScreenState();
}

class _SearchScreenState extends ConsumerState<SearchScreen> {
  final _searchCtrl = TextEditingController();
  Timer? _debounce;

  @override
  void dispose() {
    _debounce?.cancel();
    _searchCtrl.dispose();
    super.dispose();
  }

  void _onSearchChanged(String query) {
    _debounce?.cancel();
    _debounce = Timer(const Duration(milliseconds: 400), () {
      ref.read(searchQueryProvider.notifier).state = query;
      if (query.trim().length >= 2) {
        ref.read(recentSearchesProvider.notifier).add(query);
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final query = ref.watch(searchQueryProvider);
    final results = ref.watch(searchResultsProvider);
    final recentSearches = ref.watch(recentSearchesProvider);
    final filters = ref.watch(searchFiltersProvider);
    final theme = Theme.of(context);

    final showResults = query.trim().length >= 2;

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        title: const Text('Search'),
        backgroundColor: AppColors.background,
      ),
      body: Column(
        children: [
          // ── Search bar ──────────────────────────────────────────
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 4, 16, 8),
            child: TextField(
              controller: _searchCtrl,
              onChanged: _onSearchChanged,
              decoration: InputDecoration(
                hintText: 'Search movies & shows...',
                prefixIcon: const Icon(Icons.search_rounded),
                suffixIcon: query.isNotEmpty
                    ? IconButton(
                        onPressed: () {
                          _searchCtrl.clear();
                          ref.read(searchQueryProvider.notifier).state = '';
                        },
                        icon: const Icon(Icons.close_rounded),
                      )
                    : null,
              ),
            ),
          ),

          // ── Filter chips ────────────────────────────────────────
          SizedBox(
            height: 42,
            child: ListView(
              scrollDirection: Axis.horizontal,
              padding: const EdgeInsets.symmetric(horizontal: 16),
              children: [
                _FilterChip(
                  label: 'Movies',
                  isSelected: filters.type == 'movie',
                  onTap: () {
                    final notifier =
                        ref.read(searchFiltersProvider.notifier);
                    notifier.state = filters.type == 'movie'
                        ? filters.copyWith(clearType: true)
                        : filters.copyWith(type: 'movie');
                  },
                ),
                const SizedBox(width: 8),
                _FilterChip(
                  label: 'TV Shows',
                  isSelected: filters.type == 'tv',
                  onTap: () {
                    final notifier =
                        ref.read(searchFiltersProvider.notifier);
                    notifier.state = filters.type == 'tv'
                        ? filters.copyWith(clearType: true)
                        : filters.copyWith(type: 'tv');
                  },
                ),
                const SizedBox(width: 8),
                ..._yearFilters(filters),
              ],
            ),
          ),

          const SizedBox(height: 8),

          // ── Body ────────────────────────────────────────────────
          Expanded(
            child: showResults
                ? _SearchResults(results: results)
                : _RecentSearches(
                    searches: recentSearches,
                    onTap: (s) {
                      _searchCtrl.text = s;
                      ref.read(searchQueryProvider.notifier).state = s;
                    },
                    onClear: () =>
                        ref.read(recentSearchesProvider.notifier).clear(),
                  ),
          ),
        ],
      ),
    );
  }

  List<Widget> _yearFilters(SearchFilters filters) {
    final years = [2025, 2024, 2023, 2022];
    return years.map((y) {
      return Padding(
        padding: const EdgeInsets.only(right: 8),
        child: _FilterChip(
          label: y.toString(),
          isSelected: filters.year == y,
          onTap: () {
            final notifier = ref.read(searchFiltersProvider.notifier);
            notifier.state = filters.year == y
                ? filters.copyWith(clearYear: true)
                : filters.copyWith(year: y);
          },
        ),
      );
    }).toList();
  }
}

class _FilterChip extends StatelessWidget {
  final String label;
  final bool isSelected;
  final VoidCallback onTap;

  const _FilterChip({
    required this.label,
    required this.isSelected,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
        decoration: BoxDecoration(
          color: isSelected
              ? AppColors.primary.withOpacity(0.2)
              : AppColors.surface,
          borderRadius: BorderRadius.circular(10),
          border: Border.all(
            color: isSelected ? AppColors.primary : AppColors.border,
          ),
        ),
        child: Text(
          label,
          style: TextStyle(
            color:
                isSelected ? AppColors.textPrimary : AppColors.textSecondary,
            fontSize: 13,
            fontWeight: isSelected ? FontWeight.w600 : FontWeight.w400,
          ),
        ),
      ),
    );
  }
}

class _SearchResults extends StatelessWidget {
  final AsyncValue results;

  const _SearchResults({required this.results});

  @override
  Widget build(BuildContext context) {
    return results.when(
      loading: () => GridView.builder(
        padding: const EdgeInsets.all(16),
        gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
          crossAxisCount: 3,
          childAspectRatio: 0.55,
          crossAxisSpacing: 12,
          mainAxisSpacing: 12,
        ),
        itemCount: 6,
        itemBuilder: (_, __) => const ShimmerTitleCard(),
      ),
      error: (e, _) => EmptyState(
        icon: Icons.error_outline,
        title: 'Search failed',
        subtitle: e.toString(),
      ),
      data: (titles) {
        final list = titles as List;
        if (list.isEmpty) {
          return const EmptyState(
            icon: Icons.search_off_rounded,
            title: 'No results',
            subtitle: 'Try a different search term or adjust filters.',
          );
        }
        return GridView.builder(
          padding: const EdgeInsets.all(16),
          gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
            crossAxisCount: 3,
            childAspectRatio: 0.5,
            crossAxisSpacing: 12,
            mainAxisSpacing: 12,
          ),
          itemCount: list.length,
          itemBuilder: (_, index) => TitleCard(
            title: list[index],
            width: double.infinity,
            height: 165,
          ).animate().fadeIn(
                delay: Duration(milliseconds: index * 50),
                duration: 300.ms,
              ),
        );
      },
    );
  }
}

class _RecentSearches extends StatelessWidget {
  final List<String> searches;
  final ValueChanged<String> onTap;
  final VoidCallback onClear;

  const _RecentSearches({
    required this.searches,
    required this.onTap,
    required this.onClear,
  });

  @override
  Widget build(BuildContext context) {
    if (searches.isEmpty) {
      return const EmptyState(
        icon: Icons.search_rounded,
        title: 'Start searching',
        subtitle: 'Find movies and shows you love.',
      );
    }

    return ListView(
      padding: const EdgeInsets.symmetric(horizontal: 16),
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text('Recent Searches',
                style: Theme.of(context).textTheme.titleSmall),
            TextButton(onPressed: onClear, child: const Text('Clear')),
          ],
        ),
        ...searches.map(
          (s) => ListTile(
            leading:
                const Icon(Icons.history, color: AppColors.textTertiary),
            title: Text(s),
            contentPadding: EdgeInsets.zero,
            onTap: () => onTap(s),
            dense: true,
          ),
        ),
      ],
    );
  }
}
