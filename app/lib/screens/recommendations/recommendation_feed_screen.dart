import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/theme/app_colors.dart';
import '../../models/recommendation.dart';
import '../../providers/recommendation_provider.dart';
import '../../providers/user_provider.dart';
import '../../widgets/empty_state.dart';
import '../../widgets/recommendation_card.dart';

class RecommendationFeedScreen extends ConsumerWidget {
  const RecommendationFeedScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final feedState = ref.watch(recommendationFeedProvider);
    final feedNotifier = ref.read(recommendationFeedProvider.notifier);
    final feedbackService = ref.read(recommendationFeedbackProvider);
    final watchlistNotifier = ref.read(watchlistProvider.notifier);
    final markWatched = ref.read(markWatchedProvider);

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        title: const Text('For You'),
        actions: [
          IconButton(
            onPressed: feedNotifier.refresh,
            icon: const Icon(Icons.refresh_rounded),
            tooltip: 'Refresh',
          ),
        ],
      ),
      body: _buildBody(
        context,
        feedState,
        feedNotifier,
        feedbackService,
        watchlistNotifier,
        markWatched,
      ),
    );
  }

  Widget _buildBody(
    BuildContext context,
    RecommendationFeedState state,
    RecommendationFeedNotifier notifier,
    RecommendationFeedbackService feedbackService,
    WatchlistNotifier watchlistNotifier,
    MarkWatchedService markWatched,
  ) {
    if (state.isLoading && state.items.isEmpty) {
      return ListView.builder(
        itemCount: 3,
        itemBuilder: (_, __) =>
            const ShimmerRecommendationCardLarge(),
      );
    }

    if (state.error != null && state.items.isEmpty) {
      return EmptyState(
        icon: Icons.error_outline,
        title: 'Something went wrong',
        subtitle: state.error!,
        actionLabel: 'Retry',
        onAction: notifier.refresh,
      );
    }

    if (state.items.isEmpty) {
      return const EmptyState(
        icon: Icons.movie_filter_outlined,
        title: 'No recommendations yet',
        subtitle:
            'Complete the taste questionnaire to start receiving personalized picks.',
      );
    }

    return PageView.builder(
      scrollDirection: Axis.vertical,
      itemCount: state.items.length + (state.hasMore ? 1 : 0),
      onPageChanged: notifier.setCurrentIndex,
      itemBuilder: (context, index) {
        if (index >= state.items.length) {
          return const Center(
            child: CircularProgressIndicator(color: AppColors.primary),
          );
        }

        final rec = state.items[index];

        return Center(
          child: SingleChildScrollView(
            child: RecommendationCard(
              recommendation: rec,
              onWatchlist: () {
                watchlistNotifier.add(rec.title);
                feedbackService.submit(RecommendationFeedback(
                  recommendationId: rec.id,
                  titleId: rec.title.id,
                  action: RecommendationAction.watchlist,
                ));
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(
                    content: Text('${rec.title.title} added to watchlist'),
                    duration: const Duration(seconds: 2),
                  ),
                );
              },
              onWatched: () {
                markWatched.markWatched(rec.title.id);
                feedbackService.submit(RecommendationFeedback(
                  recommendationId: rec.id,
                  titleId: rec.title.id,
                  action: RecommendationAction.watched,
                ));
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(
                    content:
                        Text('${rec.title.title} marked as watched'),
                    duration: const Duration(seconds: 2),
                  ),
                );
              },
              onSkip: () {
                feedbackService.submit(RecommendationFeedback(
                  recommendationId: rec.id,
                  titleId: rec.title.id,
                  action: RecommendationAction.skip,
                ));
              },
            ),
          ),
        );
      },
    );
  }
}
