import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/theme/app_colors.dart';
import '../../providers/auth_provider.dart';
import '../../providers/recommendation_provider.dart';
import '../../widgets/recommendation_card.dart';
import '../../widgets/shimmer_loading.dart';
import '../../widgets/title_card.dart';

class DashboardScreen extends ConsumerWidget {
  const DashboardScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final user = ref.watch(currentUserProvider);
    final recommendations = ref.watch(recommendationsProvider);
    final trending = ref.watch(trendingProvider);
    final becauseYouLiked = ref.watch(becauseYouLikedProvider);
    final theme = Theme.of(context);

    final displayName = user.asData?.value?.displayName ?? 'there';
    final firstName = displayName.split(' ').first;

    return Scaffold(
      backgroundColor: AppColors.background,
      body: RefreshIndicator(
        color: AppColors.primary,
        backgroundColor: AppColors.surface,
        onRefresh: () async {
          ref.invalidate(recommendationsProvider);
          ref.invalidate(trendingProvider);
          ref.invalidate(becauseYouLikedProvider);
        },
        child: CustomScrollView(
          slivers: [
            // ── App Bar ──────────────────────────────────────────
            SliverAppBar(
              floating: true,
              snap: true,
              backgroundColor: AppColors.background,
              title: Row(
                children: [
                  ShaderMask(
                    shaderCallback: (bounds) =>
                        AppColors.primaryGradient.createShader(bounds),
                    child: const Text(
                      'FindFlix',
                      style: TextStyle(
                        fontSize: 24,
                        fontWeight: FontWeight.w800,
                        color: Colors.white,
                      ),
                    ),
                  ),
                ],
              ),
              actions: [
                IconButton(
                  onPressed: () => context.push('/home/search'),
                  icon: const Icon(Icons.search_rounded),
                ),
              ],
            ),

            // ── Greeting ─────────────────────────────────────────
            SliverToBoxAdapter(
              child: Padding(
                padding:
                    const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                child: Text(
                  'Hey $firstName',
                  style: theme.textTheme.headlineLarge,
                ).animate().fadeIn(duration: 400.ms),
              ),
            ),

            // ── Top Picks ────────────────────────────────────────
            _SectionHeader(
              title: 'Top Picks For You',
              onSeeAll: () => context.push('/home/recommendations'),
            ),
            SliverToBoxAdapter(
              child: recommendations.when(
                data: (recs) {
                  if (recs.isEmpty) {
                    return const Padding(
                      padding: EdgeInsets.symmetric(horizontal: 16),
                      child: Text(
                        'No recommendations yet. Complete the questionnaire to get started!',
                        style: TextStyle(color: AppColors.textTertiary),
                      ),
                    );
                  }
                  return TitleCardList(
                    titles: recs.take(10).map((r) => r.title).toList(),
                  );
                },
                loading: () => const ShimmerList(
                  scrollDirection: Axis.horizontal,
                  itemHeight: 240,
                  itemCount: 4,
                ),
                error: (e, _) => _ErrorRow(message: e.toString()),
              ),
            ),

            const SliverToBoxAdapter(child: SizedBox(height: 24)),

            // ── Trending Now ─────────────────────────────────────
            const _SectionHeader(title: 'Trending Now'),
            SliverToBoxAdapter(
              child: trending.when(
                data: (items) {
                  if (items.isEmpty) {
                    return const SizedBox.shrink();
                  }
                  return TitleCardList(
                    titles: items.take(10).map((r) => r.title).toList(),
                  );
                },
                loading: () => const ShimmerList(
                  scrollDirection: Axis.horizontal,
                  itemHeight: 240,
                  itemCount: 4,
                ),
                error: (e, _) => _ErrorRow(message: e.toString()),
              ),
            ),

            const SliverToBoxAdapter(child: SizedBox(height: 24)),

            // ── Because You Liked ────────────────────────────────
            const _SectionHeader(title: 'Because You Liked'),
            SliverToBoxAdapter(
              child: becauseYouLiked.when(
                data: (items) {
                  if (items.isEmpty) return const SizedBox.shrink();
                  return TitleCardList(
                    titles: items.take(10).map((r) => r.title).toList(),
                  );
                },
                loading: () => const ShimmerList(
                  scrollDirection: Axis.horizontal,
                  itemHeight: 240,
                  itemCount: 4,
                ),
                error: (_, __) => const SizedBox.shrink(),
              ),
            ),

            // Bottom padding for nav bar.
            const SliverToBoxAdapter(child: SizedBox(height: 100)),
          ],
        ),
      ),
    );
  }
}

// ── Helpers ───────────────────────────────────────────────────────────

class _SectionHeader extends StatelessWidget {
  final String title;
  final VoidCallback? onSeeAll;

  const _SectionHeader({required this.title, this.onSeeAll});

  @override
  Widget build(BuildContext context) {
    return SliverToBoxAdapter(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(16, 8, 16, 12),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(title, style: Theme.of(context).textTheme.headlineSmall),
            if (onSeeAll != null)
              GestureDetector(
                onTap: onSeeAll,
                child: Text(
                  'See all',
                  style: TextStyle(
                    color: AppColors.primary,
                    fontSize: 13,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }
}

class _ErrorRow extends StatelessWidget {
  final String message;
  const _ErrorRow({required this.message});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      child: Row(
        children: [
          const Icon(Icons.error_outline, color: AppColors.error, size: 18),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              message,
              style: const TextStyle(color: AppColors.error, fontSize: 13),
            ),
          ),
        ],
      ),
    );
  }
}
