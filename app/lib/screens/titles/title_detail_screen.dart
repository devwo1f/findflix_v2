import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/theme/app_colors.dart';
import '../../providers/title_provider.dart';
import '../../providers/user_provider.dart';
import '../../widgets/availability_badge.dart';
import '../../widgets/genre_chip.dart';
import '../../widgets/rating_widget.dart';
import '../../widgets/shimmer_loading.dart';
import '../../widgets/title_card.dart';

class TitleDetailScreen extends ConsumerStatefulWidget {
  final String titleId;
  const TitleDetailScreen({super.key, required this.titleId});

  @override
  ConsumerState<TitleDetailScreen> createState() => _TitleDetailScreenState();
}

class _TitleDetailScreenState extends ConsumerState<TitleDetailScreen> {
  double _userRating = 0;
  bool _isInWatchlist = false;

  @override
  Widget build(BuildContext context) {
    final titleAsync = ref.watch(titleDetailProvider(widget.titleId));
    final similarAsync = ref.watch(similarTitlesProvider(widget.titleId));
    final theme = Theme.of(context);

    return Scaffold(
      backgroundColor: AppColors.background,
      body: titleAsync.when(
        loading: () => const _LoadingSkeleton(),
        error: (e, _) => Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.error_outline,
                  size: 48, color: AppColors.error),
              const SizedBox(height: 12),
              Text('Failed to load title',
                  style: theme.textTheme.bodyLarge),
              const SizedBox(height: 4),
              Text(e.toString(), style: theme.textTheme.bodySmall),
            ],
          ),
        ),
        data: (title) {
          _isInWatchlist = title.isInWatchlist ||
              ref.watch(watchlistProvider).items.any((t) => t.id == title.id);
          _userRating = title.userRating ?? 0;

          return CustomScrollView(
            slivers: [
              // ── Hero Image ───────────────────────────────────
              SliverAppBar(
                expandedHeight: 320,
                pinned: true,
                backgroundColor: AppColors.background,
                flexibleSpace: FlexibleSpaceBar(
                  background: Stack(
                    fit: StackFit.expand,
                    children: [
                      if (title.backdropUrl != null)
                        CachedNetworkImage(
                          imageUrl: title.backdropUrl!,
                          fit: BoxFit.cover,
                        ),
                      // Gradient overlay
                      const DecoratedBox(
                        decoration: BoxDecoration(
                          gradient: LinearGradient(
                            begin: Alignment.topCenter,
                            end: Alignment.bottomCenter,
                            colors: [
                              Colors.transparent,
                              AppColors.background,
                            ],
                            stops: [0.5, 1.0],
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),

              SliverToBoxAdapter(
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      // ── Title ────────────────────────────────
                      Text(title.title,
                              style: theme.textTheme.displayMedium)
                          .animate()
                          .fadeIn(duration: 350.ms),
                      if (title.tagline != null &&
                          title.tagline!.isNotEmpty) ...[
                        const SizedBox(height: 4),
                        Text(
                          title.tagline!,
                          style: theme.textTheme.bodyMedium?.copyWith(
                            fontStyle: FontStyle.italic,
                            color: AppColors.textTertiary,
                          ),
                        ),
                      ],
                      const SizedBox(height: 10),

                      // ── Meta row ─────────────────────────────
                      Wrap(
                        spacing: 12,
                        runSpacing: 6,
                        crossAxisAlignment: WrapCrossAlignment.center,
                        children: [
                          if (title.year.isNotEmpty)
                            _MetaChip(label: title.year),
                          if (title.runtimeFormatted.isNotEmpty)
                            _MetaChip(label: title.runtimeFormatted),
                          if (title.voteAverage > 0)
                            RatingBadge(rating: title.voteAverage),
                          _MetaChip(
                            label: title.type == 'tv'
                                ? 'TV Series'
                                : 'Movie',
                          ),
                        ],
                      ),
                      const SizedBox(height: 14),

                      // ── Genre chips ──────────────────────────
                      if (title.genres.isNotEmpty)
                        Wrap(
                          spacing: 8,
                          runSpacing: 8,
                          children: title.genres
                              .map((g) =>
                                  GenreChip(label: g, compact: true))
                              .toList(),
                        ),
                      const SizedBox(height: 18),

                      // ── Action buttons ───────────────────────
                      Row(
                        children: [
                          Expanded(
                            child: ElevatedButton.icon(
                              onPressed: () {
                                setState(
                                    () => _isInWatchlist = !_isInWatchlist);
                                if (_isInWatchlist) {
                                  ref
                                      .read(watchlistProvider.notifier)
                                      .add(title);
                                } else {
                                  ref
                                      .read(watchlistProvider.notifier)
                                      .remove(title.id);
                                }
                              },
                              icon: Icon(
                                _isInWatchlist
                                    ? Icons.bookmark_rounded
                                    : Icons.bookmark_add_outlined,
                              ),
                              label: Text(
                                _isInWatchlist
                                    ? 'In Watchlist'
                                    : 'Watchlist',
                              ),
                              style: ElevatedButton.styleFrom(
                                backgroundColor: _isInWatchlist
                                    ? AppColors.primary
                                    : AppColors.surface,
                                foregroundColor: _isInWatchlist
                                    ? Colors.white
                                    : AppColors.textPrimary,
                              ),
                            ),
                          ),
                          const SizedBox(width: 12),
                          Expanded(
                            child: OutlinedButton.icon(
                              onPressed: () {
                                ref
                                    .read(markWatchedProvider)
                                    .markWatched(title.id);
                                ScaffoldMessenger.of(context).showSnackBar(
                                  const SnackBar(
                                    content: Text('Marked as watched'),
                                  ),
                                );
                              },
                              icon: const Icon(
                                  Icons.check_circle_outline),
                              label: const Text('Watched'),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 20),

                      // ── Overview ─────────────────────────────
                      if (title.overview != null &&
                          title.overview!.isNotEmpty) ...[
                        Text('Synopsis',
                            style: theme.textTheme.headlineSmall),
                        const SizedBox(height: 8),
                        Text(
                          title.overview!,
                          style: theme.textTheme.bodyMedium?.copyWith(
                            height: 1.6,
                            color: AppColors.textSecondary,
                          ),
                        ),
                        const SizedBox(height: 24),
                      ],

                      // ── Rate ─────────────────────────────────
                      Text('Rate this',
                          style: theme.textTheme.headlineSmall),
                      const SizedBox(height: 8),
                      RatingWidget(
                        rating: _userRating,
                        onRatingChanged: (r) {
                          setState(() => _userRating = r);
                          ref
                              .read(markWatchedProvider)
                              .markWatched(title.id, rating: r);
                        },
                      ),
                      const SizedBox(height: 24),

                      // ── Cast ─────────────────────────────────
                      if (title.cast.isNotEmpty) ...[
                        Text('Cast',
                            style: theme.textTheme.headlineSmall),
                        const SizedBox(height: 12),
                        SizedBox(
                          height: 110,
                          child: ListView.separated(
                            scrollDirection: Axis.horizontal,
                            itemCount: title.cast.length,
                            separatorBuilder: (_, __) =>
                                const SizedBox(width: 14),
                            itemBuilder: (_, i) {
                              final member = title.cast[i];
                              return SizedBox(
                                width: 70,
                                child: Column(
                                  children: [
                                    CircleAvatar(
                                      radius: 30,
                                      backgroundColor: AppColors.surface,
                                      backgroundImage:
                                          member.profileUrl != null
                                              ? CachedNetworkImageProvider(
                                                  member.profileUrl!)
                                              : null,
                                      child: member.profileUrl == null
                                          ? const Icon(
                                              Icons.person,
                                              color:
                                                  AppColors.textTertiary,
                                            )
                                          : null,
                                    ),
                                    const SizedBox(height: 6),
                                    Text(
                                      member.name,
                                      style: const TextStyle(
                                        fontSize: 11,
                                        color: AppColors.textPrimary,
                                      ),
                                      maxLines: 1,
                                      overflow: TextOverflow.ellipsis,
                                      textAlign: TextAlign.center,
                                    ),
                                    Text(
                                      member.character,
                                      style: const TextStyle(
                                        fontSize: 10,
                                        color: AppColors.textTertiary,
                                      ),
                                      maxLines: 1,
                                      overflow: TextOverflow.ellipsis,
                                      textAlign: TextAlign.center,
                                    ),
                                  ],
                                ),
                              );
                            },
                          ),
                        ),
                        const SizedBox(height: 24),
                      ],

                      // ── Where to Watch ───────────────────────
                      if (title.availability.isNotEmpty) ...[
                        AvailabilityRow(
                          providers: title.availability,
                          showLabel: true,
                        ),
                        const SizedBox(height: 24),
                      ],

                      // ── Similar Titles ───────────────────────
                      Text('Similar Titles',
                          style: theme.textTheme.headlineSmall),
                      const SizedBox(height: 12),
                    ],
                  ),
                ),
              ),

              // Similar titles list
              SliverToBoxAdapter(
                child: similarAsync.when(
                  data: (items) {
                    if (items.isEmpty) {
                      return const Padding(
                        padding: EdgeInsets.symmetric(horizontal: 16),
                        child: Text(
                          'No similar titles found.',
                          style:
                              TextStyle(color: AppColors.textTertiary),
                        ),
                      );
                    }
                    return TitleCardList(titles: items);
                  },
                  loading: () => const ShimmerList(
                    scrollDirection: Axis.horizontal,
                    itemHeight: 210,
                    itemCount: 4,
                  ),
                  error: (_, __) => const SizedBox.shrink(),
                ),
              ),

              const SliverToBoxAdapter(child: SizedBox(height: 60)),
            ],
          );
        },
      ),
    );
  }
}

class _MetaChip extends StatelessWidget {
  final String label;
  const _MetaChip({required this.label});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: AppColors.border, width: 0.5),
      ),
      child: Text(
        label,
        style: const TextStyle(
          color: AppColors.textSecondary,
          fontSize: 12,
          fontWeight: FontWeight.w500,
        ),
      ),
    );
  }
}

class _LoadingSkeleton extends StatelessWidget {
  const _LoadingSkeleton();

  @override
  Widget build(BuildContext context) {
    return const SingleChildScrollView(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          ShimmerLoading(height: 320, borderRadius: 0),
          Padding(
            padding: EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                ShimmerLoading(height: 28, width: 250, borderRadius: 6),
                SizedBox(height: 12),
                ShimmerLoading(height: 16, width: 180, borderRadius: 4),
                SizedBox(height: 20),
                ShimmerLoading(height: 14, borderRadius: 4),
                SizedBox(height: 8),
                ShimmerLoading(height: 14, borderRadius: 4),
                SizedBox(height: 8),
                ShimmerLoading(height: 14, width: 220, borderRadius: 4),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
