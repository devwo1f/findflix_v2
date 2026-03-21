import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/theme/app_colors.dart';
import '../../providers/user_provider.dart';
import '../../widgets/empty_state.dart';
import '../../widgets/shimmer_loading.dart';
import '../../widgets/title_card.dart';

class WatchlistScreen extends ConsumerStatefulWidget {
  const WatchlistScreen({super.key});

  @override
  ConsumerState<WatchlistScreen> createState() => _WatchlistScreenState();
}

class _WatchlistScreenState extends ConsumerState<WatchlistScreen> {
  bool _isGridView = true;
  String _sortBy = 'added'; // 'added' | 'title' | 'rating'

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(watchlistProvider);
    final notifier = ref.read(watchlistProvider.notifier);
    final theme = Theme.of(context);

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        title: const Text('Watchlist'),
        actions: [
          // Sort
          PopupMenuButton<String>(
            icon: const Icon(Icons.sort_rounded),
            onSelected: (v) => setState(() => _sortBy = v),
            itemBuilder: (_) => [
              _sortItem('added', 'Date Added'),
              _sortItem('title', 'Title'),
              _sortItem('rating', 'Rating'),
            ],
          ),
          // View toggle
          IconButton(
            onPressed: () => setState(() => _isGridView = !_isGridView),
            icon: Icon(
              _isGridView
                  ? Icons.view_list_rounded
                  : Icons.grid_view_rounded,
            ),
          ),
        ],
      ),
      body: _buildBody(state, notifier, theme),
    );
  }

  PopupMenuItem<String> _sortItem(String value, String label) {
    return PopupMenuItem(
      value: value,
      child: Row(
        children: [
          if (_sortBy == value)
            const Icon(Icons.check, size: 16, color: AppColors.primary),
          if (_sortBy == value) const SizedBox(width: 8),
          Text(label),
        ],
      ),
    );
  }

  Widget _buildBody(
    WatchlistState state,
    WatchlistNotifier notifier,
    ThemeData theme,
  ) {
    if (state.isLoading && state.items.isEmpty) {
      return _isGridView
          ? GridView.builder(
              padding: const EdgeInsets.all(16),
              gridDelegate:
                  const SliverGridDelegateWithFixedCrossAxisCount(
                crossAxisCount: 3,
                childAspectRatio: 0.55,
                crossAxisSpacing: 12,
                mainAxisSpacing: 12,
              ),
              itemCount: 6,
              itemBuilder: (_, __) => const ShimmerTitleCard(),
            )
          : const ShimmerList(itemHeight: 90, itemCount: 5);
    }

    if (state.items.isEmpty) {
      return EmptyState(
        icon: Icons.bookmark_outline_rounded,
        title: 'Your watchlist is empty',
        subtitle:
            'Browse recommendations and save titles you want to watch.',
        actionLabel: 'Discover',
        onAction: () => context.go('/home'),
      );
    }

    final sorted = _sortedItems(state.items);

    if (_isGridView) {
      return GridView.builder(
        padding: const EdgeInsets.all(16),
        gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
          crossAxisCount: 3,
          childAspectRatio: 0.5,
          crossAxisSpacing: 12,
          mainAxisSpacing: 12,
        ),
        itemCount: sorted.length,
        itemBuilder: (_, index) => TitleCard(
          title: sorted[index],
          width: double.infinity,
          height: 165,
        ).animate().fadeIn(
              delay: Duration(milliseconds: index * 40),
              duration: 300.ms,
            ),
      );
    }

    return ListView.builder(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      itemCount: sorted.length,
      itemBuilder: (_, index) {
        final title = sorted[index];
        return Dismissible(
          key: ValueKey(title.id),
          direction: DismissDirection.endToStart,
          background: Container(
            alignment: Alignment.centerRight,
            padding: const EdgeInsets.only(right: 24),
            margin: const EdgeInsets.only(bottom: 8),
            decoration: BoxDecoration(
              color: AppColors.error.withOpacity(0.15),
              borderRadius: BorderRadius.circular(14),
            ),
            child: const Icon(Icons.delete_outline,
                color: AppColors.error),
          ),
          onDismissed: (_) => notifier.remove(title.id),
          child: Card(
            margin: const EdgeInsets.only(bottom: 8),
            child: ListTile(
              leading: ClipRRect(
                borderRadius: BorderRadius.circular(8),
                child: title.posterUrl != null
                    ? Image.network(
                        title.posterUrl!,
                        width: 50,
                        height: 75,
                        fit: BoxFit.cover,
                      )
                    : Container(
                        width: 50,
                        height: 75,
                        color: AppColors.surface,
                        child: const Icon(Icons.movie_rounded,
                            color: AppColors.textTertiary),
                      ),
              ),
              title: Text(
                title.title,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
              subtitle: Text(
                [title.year, title.runtimeFormatted]
                    .where((s) => s.isNotEmpty)
                    .join(' \u2022 '),
                style: const TextStyle(
                  color: AppColors.textTertiary,
                  fontSize: 12,
                ),
              ),
              trailing: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  if (title.voteAverage > 0) ...[
                    const Icon(Icons.star_rounded,
                        size: 14, color: AppColors.ratingGold),
                    const SizedBox(width: 2),
                    Text(
                      title.ratingFormatted,
                      style: const TextStyle(
                        color: AppColors.ratingGold,
                        fontSize: 12,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ],
                  const SizedBox(width: 8),
                  const Icon(Icons.chevron_right_rounded,
                      color: AppColors.textTertiary),
                ],
              ),
              onTap: () => context.push('/title/${title.id}'),
            ),
          ),
        ).animate().fadeIn(
              delay: Duration(milliseconds: index * 40),
              duration: 300.ms,
            );
      },
    );
  }

  List _sortedItems(List items) {
    final list = List.of(items);
    switch (_sortBy) {
      case 'title':
        list.sort((a, b) => a.title.compareTo(b.title));
        break;
      case 'rating':
        list.sort((a, b) => b.voteAverage.compareTo(a.voteAverage));
        break;
      default:
        // Keep original order (date added).
        break;
    }
    return list;
  }
}
