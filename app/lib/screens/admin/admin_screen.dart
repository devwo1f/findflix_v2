import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/constants/api_constants.dart';
import '../../core/network/api_client.dart';
import '../../core/theme/app_colors.dart';
import '../../widgets/shimmer_loading.dart';

// ── Providers ─────────────────────────────────────────────────────────

final adminStatsProvider =
    FutureProvider.autoDispose<Map<String, dynamic>>((ref) async {
  final api = ref.read(apiClientProvider);
  return await api.get<Map<String, dynamic>>(ApiConstants.adminStats);
});

final adminModelInfoProvider =
    FutureProvider.autoDispose<Map<String, dynamic>>((ref) async {
  final api = ref.read(apiClientProvider);
  return await api.get<Map<String, dynamic>>(ApiConstants.adminModelInfo);
});

// ── Screen ────────────────────────────────────────────────────────────

class AdminScreen extends ConsumerWidget {
  const AdminScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final stats = ref.watch(adminStatsProvider);
    final modelInfo = ref.watch(adminModelInfoProvider);
    final theme = Theme.of(context);

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(title: const Text('Admin Dashboard')),
      body: RefreshIndicator(
        color: AppColors.primary,
        backgroundColor: AppColors.surface,
        onRefresh: () async {
          ref.invalidate(adminStatsProvider);
          ref.invalidate(adminModelInfoProvider);
        },
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            // ── System Stats ─────────────────────────────────────
            Text('System Stats', style: theme.textTheme.headlineSmall)
                .animate()
                .fadeIn(duration: 300.ms),
            const SizedBox(height: 12),
            stats.when(
              data: (data) {
                final userCount = data['user_count'] ?? 0;
                final titleCount = data['title_count'] ?? 0;
                final recCount = data['recommendation_count'] ?? 0;
                final avgLatency = data['avg_latency_ms'] ?? 0;

                return Wrap(
                  spacing: 12,
                  runSpacing: 12,
                  children: [
                    _StatCard(
                      label: 'Users',
                      value: userCount.toString(),
                      icon: Icons.people_rounded,
                      color: AppColors.primary,
                    ),
                    _StatCard(
                      label: 'Titles',
                      value: titleCount.toString(),
                      icon: Icons.movie_rounded,
                      color: AppColors.accent,
                    ),
                    _StatCard(
                      label: 'Recommendations',
                      value: recCount.toString(),
                      icon: Icons.recommend_rounded,
                      color: AppColors.success,
                    ),
                    _StatCard(
                      label: 'Avg Latency',
                      value: '${avgLatency}ms',
                      icon: Icons.speed_rounded,
                      color: AppColors.warning,
                    ),
                  ],
                ).animate().fadeIn(delay: 100.ms, duration: 350.ms);
              },
              loading: () => const Wrap(
                spacing: 12,
                runSpacing: 12,
                children: [
                  ShimmerLoading(width: 170, height: 100, borderRadius: 14),
                  ShimmerLoading(width: 170, height: 100, borderRadius: 14),
                  ShimmerLoading(width: 170, height: 100, borderRadius: 14),
                  ShimmerLoading(width: 170, height: 100, borderRadius: 14),
                ],
              ),
              error: (e, _) => _ErrorCard(message: e.toString()),
            ),

            const SizedBox(height: 28),

            // ── Model Info ───────────────────────────────────────
            Text('ML Model Info', style: theme.textTheme.headlineSmall)
                .animate()
                .fadeIn(delay: 150.ms, duration: 300.ms),
            const SizedBox(height: 12),
            modelInfo.when(
              data: (data) {
                return Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    color: AppColors.card,
                    borderRadius: BorderRadius.circular(14),
                    border:
                        Border.all(color: AppColors.border, width: 0.5),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: data.entries.map((e) {
                      return Padding(
                        padding: const EdgeInsets.symmetric(vertical: 6),
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            SizedBox(
                              width: 130,
                              child: Text(
                                e.key,
                                style: const TextStyle(
                                  color: AppColors.textTertiary,
                                  fontSize: 13,
                                  fontWeight: FontWeight.w500,
                                ),
                              ),
                            ),
                            Expanded(
                              child: Text(
                                e.value.toString(),
                                style: const TextStyle(
                                  color: AppColors.textPrimary,
                                  fontSize: 13,
                                ),
                              ),
                            ),
                          ],
                        ),
                      );
                    }).toList(),
                  ),
                ).animate().fadeIn(delay: 200.ms, duration: 350.ms);
              },
              loading: () =>
                  const ShimmerLoading(height: 180, borderRadius: 14),
              error: (e, _) => _ErrorCard(message: e.toString()),
            ),

            const SizedBox(height: 28),

            // ── Actions ──────────────────────────────────────────
            Text('Actions', style: theme.textTheme.headlineSmall)
                .animate()
                .fadeIn(delay: 250.ms, duration: 300.ms),
            const SizedBox(height: 12),
            _ActionButton(
              icon: Icons.sync_rounded,
              label: 'Trigger TMDb Sync',
              subtitle: 'Pull latest title metadata from TMDb',
              onTap: () => _triggerSync(ref, context),
            ).animate().fadeIn(delay: 300.ms, duration: 350.ms),
            const SizedBox(height: 12),
            _ActionButton(
              icon: Icons.receipt_long_rounded,
              label: 'View Recommendation Logs',
              subtitle: 'Recent recommendation generation logs',
              onTap: () => _viewLogs(ref, context),
            ).animate().fadeIn(delay: 350.ms, duration: 350.ms),

            const SizedBox(height: 40),
          ],
        ),
      ),
    );
  }

  Future<void> _triggerSync(WidgetRef ref, BuildContext context) async {
    try {
      final api = ref.read(apiClientProvider);
      await api.post(ApiConstants.adminSync);
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('TMDb sync triggered successfully.')),
        );
      }
    } catch (e) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Sync failed: $e'),
            backgroundColor: AppColors.error,
          ),
        );
      }
    }
  }

  Future<void> _viewLogs(WidgetRef ref, BuildContext context) async {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      builder: (_) => DraggableScrollableSheet(
        expand: false,
        initialChildSize: 0.6,
        builder: (context, scrollCtrl) {
          return FutureBuilder(
            future: ref
                .read(apiClientProvider)
                .get<Map<String, dynamic>>(ApiConstants.adminLogs),
            builder: (context, snap) {
              if (snap.connectionState == ConnectionState.waiting) {
                return const Center(
                    child: CircularProgressIndicator(
                        color: AppColors.primary));
              }
              if (snap.hasError) {
                return Center(
                    child: Text('Error: ${snap.error}'));
              }
              final logs = (snap.data?['logs'] as List<dynamic>?) ?? [];
              return ListView.builder(
                controller: scrollCtrl,
                padding: const EdgeInsets.all(16),
                itemCount: logs.length,
                itemBuilder: (_, i) {
                  final log = logs[i];
                  return Card(
                    margin: const EdgeInsets.only(bottom: 8),
                    child: Padding(
                      padding: const EdgeInsets.all(12),
                      child: Text(
                        log.toString(),
                        style: const TextStyle(
                          fontSize: 12,
                          fontFamily: 'monospace',
                          color: AppColors.textSecondary,
                        ),
                      ),
                    ),
                  );
                },
              );
            },
          );
        },
      ),
    );
  }
}

// ── Helpers ───────────────────────────────────────────────────────────

class _StatCard extends StatelessWidget {
  final String label;
  final String value;
  final IconData icon;
  final Color color;

  const _StatCard({
    required this.label,
    required this.value,
    required this.icon,
    required this.color,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      width: (MediaQuery.of(context).size.width - 44) / 2,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.card,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: AppColors.border, width: 0.5),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, color: color, size: 22),
          const SizedBox(height: 10),
          Text(
            value,
            style: TextStyle(
              fontSize: 24,
              fontWeight: FontWeight.w700,
              color: color,
            ),
          ),
          const SizedBox(height: 2),
          Text(
            label,
            style: const TextStyle(
              fontSize: 12,
              color: AppColors.textTertiary,
            ),
          ),
        ],
      ),
    );
  }
}

class _ActionButton extends StatelessWidget {
  final IconData icon;
  final String label;
  final String subtitle;
  final VoidCallback onTap;

  const _ActionButton({
    required this.icon,
    required this.label,
    required this.subtitle,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(14),
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: AppColors.card,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: AppColors.border, width: 0.5),
        ),
        child: Row(
          children: [
            Container(
              width: 44,
              height: 44,
              decoration: BoxDecoration(
                color: AppColors.primary.withOpacity(0.1),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Icon(icon, color: AppColors.primary),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(label,
                      style: Theme.of(context).textTheme.titleSmall),
                  const SizedBox(height: 2),
                  Text(subtitle,
                      style: const TextStyle(
                          fontSize: 12, color: AppColors.textTertiary)),
                ],
              ),
            ),
            const Icon(Icons.chevron_right_rounded,
                color: AppColors.textTertiary),
          ],
        ),
      ),
    );
  }
}

class _ErrorCard extends StatelessWidget {
  final String message;
  const _ErrorCard({required this.message});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.error.withOpacity(0.1),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: AppColors.error.withOpacity(0.3)),
      ),
      child: Row(
        children: [
          const Icon(Icons.error_outline, color: AppColors.error),
          const SizedBox(width: 12),
          Expanded(
            child: Text(message,
                style:
                    const TextStyle(color: AppColors.error, fontSize: 13)),
          ),
        ],
      ),
    );
  }
}
