import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/router/app_router.dart';
import '../../core/theme/app_colors.dart';
import '../../providers/auth_provider.dart';
import '../../providers/user_provider.dart';
import '../../widgets/shimmer_loading.dart';

class ProfileScreen extends ConsumerWidget {
  const ProfileScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final user = ref.watch(currentUserProvider);
    final stats = ref.watch(userStatsProvider);
    final tasteProfile = ref.watch(tasteProfileProvider);
    final theme = Theme.of(context);

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        title: const Text('Profile'),
        actions: [
          IconButton(
            onPressed: () => context.push(AppRoutes.settings),
            icon: const Icon(Icons.settings_rounded),
          ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.symmetric(horizontal: 16),
        child: Column(
          children: [
            const SizedBox(height: 16),

            // ── Avatar & Name ────────────────────────────────────
            user.when(
              data: (u) {
                if (u == null) return const SizedBox.shrink();
                return Column(
                  children: [
                    CircleAvatar(
                      radius: 44,
                      backgroundColor: AppColors.primary.withOpacity(0.2),
                      backgroundImage: u.photoUrl != null
                          ? NetworkImage(u.photoUrl!)
                          : null,
                      child: u.photoUrl == null
                          ? Text(
                              u.displayName.isNotEmpty
                                  ? u.displayName[0].toUpperCase()
                                  : '?',
                              style: const TextStyle(
                                fontSize: 36,
                                fontWeight: FontWeight.w700,
                                color: AppColors.primary,
                              ),
                            )
                          : null,
                    ),
                    const SizedBox(height: 14),
                    Text(u.displayName,
                        style: theme.textTheme.headlineMedium),
                    const SizedBox(height: 4),
                    Text(u.email,
                        style: theme.textTheme.bodySmall?.copyWith(
                            color: AppColors.textTertiary)),
                  ],
                ).animate().fadeIn(duration: 350.ms);
              },
              loading: () => const Column(
                children: [
                  ShimmerLoading(
                      width: 88, height: 88, borderRadius: 44),
                  SizedBox(height: 14),
                  ShimmerLoading(
                      width: 160, height: 22, borderRadius: 6),
                  SizedBox(height: 4),
                  ShimmerLoading(
                      width: 200, height: 14, borderRadius: 4),
                ],
              ),
              error: (_, __) => const SizedBox.shrink(),
            ),

            const SizedBox(height: 28),

            // ── Stats ────────────────────────────────────────────
            stats.when(
              data: (s) => Row(
                children: [
                  _StatBox(
                      label: 'Watched', value: s.watchedCount.toString()),
                  const SizedBox(width: 12),
                  _StatBox(
                      label: 'Watchlist',
                      value: s.watchlistCount.toString()),
                  const SizedBox(width: 12),
                  _StatBox(
                      label: 'Avg Rating',
                      value: s.averageRating.toStringAsFixed(1)),
                ],
              ).animate().fadeIn(delay: 150.ms, duration: 350.ms),
              loading: () => Row(
                children: List.generate(
                  3,
                  (_) => const Expanded(
                    child: Padding(
                      padding: EdgeInsets.symmetric(horizontal: 6),
                      child: ShimmerLoading(height: 72, borderRadius: 14),
                    ),
                  ),
                ),
              ),
              error: (_, __) => const SizedBox.shrink(),
            ),

            const SizedBox(height: 28),

            // ── Taste Profile Summary ────────────────────────────
            tasteProfile.when(
              data: (data) {
                final topGenres =
                    (data['top_genres'] as List<dynamic>?)?.cast<String>() ??
                        [];
                final topMoods =
                    (data['top_moods'] as List<dynamic>?)?.cast<String>() ??
                        [];

                if (topGenres.isEmpty && topMoods.isEmpty) {
                  return const SizedBox.shrink();
                }

                return _SectionCard(
                  title: 'Your Taste Profile',
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      if (topGenres.isNotEmpty) ...[
                        Text('Favorite Genres',
                            style: theme.textTheme.labelMedium),
                        const SizedBox(height: 6),
                        Wrap(
                          spacing: 8,
                          runSpacing: 8,
                          children: topGenres
                              .map((g) => Chip(
                                    label: Text(g),
                                    backgroundColor:
                                        AppColors.primary.withOpacity(0.15),
                                    labelStyle: const TextStyle(
                                        color: AppColors.primary,
                                        fontSize: 12),
                                    materialTapTargetSize:
                                        MaterialTapTargetSize.shrinkWrap,
                                    visualDensity: VisualDensity.compact,
                                  ))
                              .toList(),
                        ),
                      ],
                      if (topMoods.isNotEmpty) ...[
                        const SizedBox(height: 14),
                        Text('Preferred Moods',
                            style: theme.textTheme.labelMedium),
                        const SizedBox(height: 6),
                        Wrap(
                          spacing: 8,
                          runSpacing: 8,
                          children: topMoods
                              .map((m) => Chip(
                                    label: Text(m),
                                    backgroundColor:
                                        AppColors.accent.withOpacity(0.15),
                                    labelStyle: const TextStyle(
                                        color: AppColors.accent,
                                        fontSize: 12),
                                    materialTapTargetSize:
                                        MaterialTapTargetSize.shrinkWrap,
                                    visualDensity: VisualDensity.compact,
                                  ))
                              .toList(),
                        ),
                      ],
                    ],
                  ),
                ).animate().fadeIn(delay: 250.ms, duration: 350.ms);
              },
              loading: () => const ShimmerLoading(
                  height: 120, borderRadius: 14),
              error: (_, __) => const SizedBox.shrink(),
            ),

            const SizedBox(height: 16),

            // ── Quick Links ──────────────────────────────────────
            _SectionCard(
              title: 'Quick Links',
              child: Column(
                children: [
                  _LinkTile(
                    icon: Icons.history_rounded,
                    label: 'Watch History',
                    onTap: () {},
                  ),
                  _LinkTile(
                    icon: Icons.tune_rounded,
                    label: 'Retake Questionnaire',
                    onTap: () => context.push(AppRoutes.onboarding),
                  ),
                  _LinkTile(
                    icon: Icons.settings_rounded,
                    label: 'Settings',
                    onTap: () => context.push(AppRoutes.settings),
                  ),
                ],
              ),
            ).animate().fadeIn(delay: 350.ms, duration: 350.ms),

            const SizedBox(height: 16),

            // ── Logout ───────────────────────────────────────────
            SizedBox(
              width: double.infinity,
              child: OutlinedButton.icon(
                onPressed: () async {
                  await ref.read(authServiceProvider).logout();
                  if (context.mounted) context.go(AppRoutes.login);
                },
                icon: const Icon(Icons.logout_rounded,
                    color: AppColors.error),
                label: const Text('Log Out',
                    style: TextStyle(color: AppColors.error)),
                style: OutlinedButton.styleFrom(
                  side: const BorderSide(color: AppColors.error),
                  padding: const EdgeInsets.symmetric(vertical: 14),
                ),
              ),
            ).animate().fadeIn(delay: 400.ms, duration: 350.ms),

            const SizedBox(height: 80),
          ],
        ),
      ),
    );
  }
}

// ── Helpers ───────────────────────────────────────────────────────────

class _StatBox extends StatelessWidget {
  final String label;
  final String value;

  const _StatBox({required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 16),
        decoration: BoxDecoration(
          color: AppColors.surface,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: AppColors.border, width: 0.5),
        ),
        child: Column(
          children: [
            Text(
              value,
              style: const TextStyle(
                fontSize: 22,
                fontWeight: FontWeight.w700,
                color: AppColors.primary,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              label,
              style: const TextStyle(
                fontSize: 11,
                color: AppColors.textTertiary,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _SectionCard extends StatelessWidget {
  final String title;
  final Widget child;

  const _SectionCard({required this.title, required this.child});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.card,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppColors.border, width: 0.5),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title,
              style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 12),
          child,
        ],
      ),
    );
  }
}

class _LinkTile extends StatelessWidget {
  final IconData icon;
  final String label;
  final VoidCallback onTap;

  const _LinkTile(
      {required this.icon, required this.label, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(10),
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 12),
        child: Row(
          children: [
            Icon(icon, size: 20, color: AppColors.textSecondary),
            const SizedBox(width: 14),
            Text(label,
                style: Theme.of(context).textTheme.bodyLarge),
            const Spacer(),
            const Icon(Icons.chevron_right_rounded,
                color: AppColors.textTertiary),
          ],
        ),
      ),
    );
  }
}
