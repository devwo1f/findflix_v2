import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:go_router/go_router.dart';

import '../core/theme/app_colors.dart';
import '../models/recommendation.dart';
import 'availability_badge.dart';
import 'rating_widget.dart';
import 'shimmer_loading.dart';

/// Large cinematic recommendation card with poster, match score, reason,
/// and quick-action buttons.
class RecommendationCard extends StatelessWidget {
  final Recommendation recommendation;
  final VoidCallback? onWatchlist;
  final VoidCallback? onWatched;
  final VoidCallback? onSkip;

  const RecommendationCard({
    super.key,
    required this.recommendation,
    this.onWatchlist,
    this.onWatched,
    this.onSkip,
  });

  @override
  Widget build(BuildContext context) {
    final title = recommendation.title;
    final matchPct = recommendation.matchPercentage;
    final theme = Theme.of(context);

    return GestureDetector(
      onTap: () => context.push('/title/${title.id}'),
      child: Container(
        margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        decoration: BoxDecoration(
          color: AppColors.card,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: AppColors.border, width: 0.5),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.35),
              blurRadius: 20,
              offset: const Offset(0, 8),
            ),
          ],
        ),
        clipBehavior: Clip.antiAlias,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            // ── Backdrop / Poster image ─────────────────────────
            Stack(
              children: [
                SizedBox(
                  height: 200,
                  width: double.infinity,
                  child: title.backdropUrl != null
                      ? CachedNetworkImage(
                          imageUrl: title.backdropUrl!,
                          fit: BoxFit.cover,
                          placeholder: (_, __) =>
                              const ShimmerLoading(height: 200),
                          errorWidget: (_, __, ___) =>
                              _imageFallback(),
                        )
                      : title.posterUrl != null
                          ? CachedNetworkImage(
                              imageUrl: title.posterUrl!,
                              fit: BoxFit.cover,
                              placeholder: (_, __) =>
                                  const ShimmerLoading(height: 200),
                              errorWidget: (_, __, ___) =>
                                  _imageFallback(),
                            )
                          : _imageFallback(),
                ),
                // Gradient overlay
                Positioned.fill(
                  child: DecoratedBox(
                    decoration: BoxDecoration(
                      gradient: LinearGradient(
                        begin: Alignment.topCenter,
                        end: Alignment.bottomCenter,
                        colors: [
                          Colors.transparent,
                          AppColors.card.withOpacity(0.85),
                        ],
                        stops: const [0.4, 1.0],
                      ),
                    ),
                  ),
                ),
                // Match badge
                Positioned(
                  top: 12,
                  right: 12,
                  child: Container(
                    padding: const EdgeInsets.symmetric(
                        horizontal: 10, vertical: 6),
                    decoration: BoxDecoration(
                      color: AppColors.matchColor(matchPct.toDouble())
                          .withOpacity(0.9),
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: Text(
                      '$matchPct% Match',
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 13,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ),
                ),
                // Rating badge
                if (title.voteAverage > 0)
                  Positioned(
                    top: 12,
                    left: 12,
                    child: RatingBadge(rating: title.voteAverage),
                  ),
              ],
            ),

            // ── Text content ────────────────────────────────────
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 12, 16, 0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Title row
                  Text(
                    title.title,
                    style: theme.textTheme.headlineSmall,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                  const SizedBox(height: 4),
                  // Meta
                  Row(
                    children: [
                      if (title.year.isNotEmpty)
                        Text(title.year,
                            style: theme.textTheme.bodySmall),
                      if (title.runtimeFormatted.isNotEmpty) ...[
                        const _Dot(),
                        Text(title.runtimeFormatted,
                            style: theme.textTheme.bodySmall),
                      ],
                      if (title.genres.isNotEmpty) ...[
                        const _Dot(),
                        Flexible(
                          child: Text(
                            title.genres.take(2).join(', '),
                            style: theme.textTheme.bodySmall,
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                      ],
                    ],
                  ),
                  const SizedBox(height: 10),
                  // Reason
                  Text(
                    recommendation.reason,
                    style: theme.textTheme.bodyMedium?.copyWith(
                      fontStyle: FontStyle.italic,
                      color: AppColors.textSecondary,
                    ),
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                  ),
                  const SizedBox(height: 10),
                  // Availability
                  if (title.availability.isNotEmpty)
                    AvailabilityRow(providers: title.availability),
                ],
              ),
            ),

            const SizedBox(height: 8),

            // ── Quick actions ───────────────────────────────────
            Padding(
              padding: const EdgeInsets.fromLTRB(8, 0, 8, 12),
              child: Row(
                children: [
                  _ActionButton(
                    icon: Icons.bookmark_add_outlined,
                    label: 'Watchlist',
                    onTap: onWatchlist,
                  ),
                  _ActionButton(
                    icon: Icons.check_circle_outline,
                    label: 'Watched',
                    onTap: onWatched,
                  ),
                  _ActionButton(
                    icon: Icons.skip_next_outlined,
                    label: 'Skip',
                    onTap: onSkip,
                    subtle: true,
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    ).animate().fadeIn(duration: 400.ms).slideY(
          begin: 0.05,
          end: 0,
          duration: 400.ms,
          curve: Curves.easeOut,
        );
  }

  Widget _imageFallback() {
    return Container(
      color: AppColors.surface,
      child: const Center(
        child: Icon(Icons.movie_rounded, size: 56, color: AppColors.textTertiary),
      ),
    );
  }
}

// ── Helpers ───────────────────────────────────────────────────────────

class _Dot extends StatelessWidget {
  const _Dot();

  @override
  Widget build(BuildContext context) {
    return const Padding(
      padding: EdgeInsets.symmetric(horizontal: 6),
      child: Text(
        '\u2022',
        style: TextStyle(color: AppColors.textTertiary, fontSize: 10),
      ),
    );
  }
}

class _ActionButton extends StatelessWidget {
  final IconData icon;
  final String label;
  final VoidCallback? onTap;
  final bool subtle;

  const _ActionButton({
    required this.icon,
    required this.label,
    this.onTap,
    this.subtle = false,
  });

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: TextButton.icon(
        onPressed: onTap,
        icon: Icon(
          icon,
          size: 18,
          color: subtle ? AppColors.textTertiary : AppColors.primary,
        ),
        label: Text(
          label,
          style: TextStyle(
            fontSize: 12,
            color: subtle ? AppColors.textTertiary : AppColors.primary,
          ),
        ),
      ),
    );
  }
}

/// Shimmer loading variant of the recommendation card.
class ShimmerRecommendationCardLarge extends StatelessWidget {
  const ShimmerRecommendationCardLarge({super.key});

  @override
  Widget build(BuildContext context) {
    return const Padding(
      padding: EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          ShimmerLoading(height: 200, borderRadius: 20),
          SizedBox(height: 12),
          ShimmerLoading(height: 22, width: 220, borderRadius: 6),
          SizedBox(height: 8),
          ShimmerLoading(height: 14, width: 160, borderRadius: 4),
          SizedBox(height: 8),
          ShimmerLoading(height: 14, width: 280, borderRadius: 4),
        ],
      ),
    );
  }
}
