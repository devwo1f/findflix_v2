import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/theme/app_colors.dart';
import '../../models/recommendation.dart';
import '../../providers/vibe_check_provider.dart';

class VibeCheckScreen extends ConsumerWidget {
  const VibeCheckScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(vibeCheckProvider);

    return Scaffold(
      backgroundColor: AppColors.background,
      body: SafeArea(
        child: state.isComplete
            ? _ResultsView(state: state)
            : _QuizView(state: state),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Quiz flow
// ---------------------------------------------------------------------------

class _QuizView extends ConsumerWidget {
  final VibeCheckState state;
  const _QuizView({required this.state});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final notifier = ref.read(vibeCheckProvider.notifier);

    return Column(
      children: [
        _Header(
          step: state.step,
          onBack: state.step > 0 ? () => notifier.goBack() : null,
          onClose: () {
            notifier.reset();
            context.pop();
          },
        ),

        _StepIndicator(current: state.step, total: 4),

        Expanded(
          child: AnimatedSwitcher(
            duration: const Duration(milliseconds: 350),
            switchInCurve: Curves.easeOut,
            switchOutCurve: Curves.easeIn,
            transitionBuilder: (child, animation) => SlideTransition(
              position: Tween<Offset>(
                begin: const Offset(0.15, 0),
                end: Offset.zero,
              ).animate(animation),
              child: FadeTransition(opacity: animation, child: child),
            ),
            child: _buildStep(context, ref),
          ),
        ),
      ],
    );
  }

  Widget _buildStep(BuildContext context, WidgetRef ref) {
    final notifier = ref.read(vibeCheckProvider.notifier);

    switch (state.step) {
      case 0:
        return _QuestionPage(
          key: const ValueKey('mood'),
          title: "How are you feeling\nright now?",
          subtitle: "Pick the mood that matches your vibe",
          options: _moodOptions,
          onSelect: notifier.selectMood,
        );
      case 1:
        return _QuestionPage(
          key: const ValueKey('time'),
          title: "How much time\ndo you have?",
          subtitle: "We'll find the perfect length",
          options: _timeOptions,
          onSelect: notifier.selectTime,
        );
      case 2:
        return _QuestionPage(
          key: const ValueKey('type'),
          title: "Movie or\nTV show?",
          subtitle: "Or leave it up to us",
          options: _typeOptions,
          onSelect: notifier.selectContentType,
        );
      case 3:
        return _QuestionPage(
          key: const ValueKey('vibe'),
          title: "Pick a vibe",
          subtitle: "What kind of experience are you craving?",
          options: _vibeOptions,
          onSelect: (v) => notifier.selectVibeAndSubmit(v),
        );
      default:
        return const SizedBox.shrink();
    }
  }
}

// ---------------------------------------------------------------------------
// Option data
// ---------------------------------------------------------------------------

class _OptionData {
  final String value;
  final String label;
  final String emoji;
  final Color color;

  const _OptionData(this.value, this.label, this.emoji, this.color);
}

const _moodOptions = [
  _OptionData('happy', 'Happy', '😊', Color(0xFFFBBF24)),
  _OptionData('sad', 'Sad', '😢', Color(0xFF60A5FA)),
  _OptionData('excited', 'Excited', '🤩', Color(0xFFF97316)),
  _OptionData('relaxed', 'Relaxed', '😌', Color(0xFF34D399)),
  _OptionData('tense', 'On Edge', '😰', Color(0xFFEF4444)),
  _OptionData('romantic', 'Romantic', '💕', Color(0xFFEC4899)),
  _OptionData('curious', 'Curious', '🧐', Color(0xFF8B5CF6)),
  _OptionData('scared', 'Spooky', '👻', Color(0xFF6B7280)),
];

const _timeOptions = [
  _OptionData('quick', 'Quick\n< 1 hour', '⚡', Color(0xFFFBBF24)),
  _OptionData('standard', 'Standard\n1-2 hours', '🎬', Color(0xFF6C63FF)),
  _OptionData('long', 'Long\n2+ hours', '🍿', Color(0xFFEC4899)),
  _OptionData('marathon', 'All Night\nMarathon', '🌙', Color(0xFF8B5CF6)),
];

const _typeOptions = [
  _OptionData('movie', 'Movie', '🎥', Color(0xFFF97316)),
  _OptionData('tv', 'TV Show', '📺', Color(0xFF60A5FA)),
  _OptionData('any', 'Surprise Me', '🎲', Color(0xFF34D399)),
];

const _vibeOptions = [
  _OptionData('mind-bending', 'Mind-Bending', '🌀', Color(0xFF8B5CF6)),
  _OptionData('feel-good', 'Feel-Good', '☀️', Color(0xFFFBBF24)),
  _OptionData('edge-of-seat', 'Edge of Seat', '💥', Color(0xFFEF4444)),
  _OptionData('tear-jerker', 'Tear-Jerker', '💧', Color(0xFF60A5FA)),
  _OptionData('laugh-out-loud', 'Laugh Out Loud', '😂', Color(0xFF34D399)),
  _OptionData('epic-adventure', 'Epic Adventure', '⚔️', Color(0xFFF97316)),
  _OptionData('cozy', 'Cozy', '🧸', Color(0xFFEC4899)),
  _OptionData('dark-gritty', 'Dark & Gritty', '🖤', Color(0xFF6B7280)),
];

// ---------------------------------------------------------------------------
// Question page
// ---------------------------------------------------------------------------

class _QuestionPage extends StatelessWidget {
  final String title;
  final String subtitle;
  final List<_OptionData> options;
  final ValueChanged<String> onSelect;

  const _QuestionPage({
    super.key,
    required this.title,
    required this.subtitle,
    required this.options,
    required this.onSelect,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const SizedBox(height: 32),
          Text(
            title,
            style: const TextStyle(
              fontSize: 28,
              fontWeight: FontWeight.w800,
              color: AppColors.textPrimary,
              height: 1.2,
            ),
          ).animate().fadeIn(duration: 300.ms).slideY(begin: -0.1),
          const SizedBox(height: 8),
          Text(
            subtitle,
            style: const TextStyle(
              fontSize: 15,
              color: AppColors.textSecondary,
            ),
          ).animate().fadeIn(delay: 100.ms, duration: 300.ms),
          const SizedBox(height: 32),
          Expanded(
            child: _OptionGrid(options: options, onSelect: onSelect),
          ),
        ],
      ),
    );
  }
}

class _OptionGrid extends StatelessWidget {
  final List<_OptionData> options;
  final ValueChanged<String> onSelect;

  const _OptionGrid({super.key, required this.options, required this.onSelect});

  @override
  Widget build(BuildContext context) {
    return GridView.builder(
      padding: const EdgeInsets.only(bottom: 24),
      physics: const BouncingScrollPhysics(),
      gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
        crossAxisCount: 2,
        mainAxisSpacing: 14,
        crossAxisSpacing: 14,
        childAspectRatio: 1.6,
      ),
      itemCount: options.length,
      itemBuilder: (context, i) {
        final opt = options[i];
        return _OptionTile(data: opt, onTap: () => onSelect(opt.value))
            .animate()
            .fadeIn(delay: (80 * i).ms, duration: 300.ms)
            .slideY(begin: 0.15, delay: (80 * i).ms, duration: 300.ms);
      },
    );
  }
}

class _OptionTile extends StatelessWidget {
  final _OptionData data;
  final VoidCallback onTap;

  const _OptionTile({required this.data, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(16),
        splashColor: data.color.withValues(alpha: 0.2),
        child: Ink(
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(16),
            gradient: LinearGradient(
              colors: [
                data.color.withValues(alpha: 0.15),
                data.color.withValues(alpha: 0.06),
              ],
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
            ),
            border: Border.all(
              color: data.color.withValues(alpha: 0.25),
              width: 1.2,
            ),
          ),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Text(data.emoji, style: const TextStyle(fontSize: 28)),
              const SizedBox(height: 6),
              Text(
                data.label,
                textAlign: TextAlign.center,
                style: TextStyle(
                  fontSize: 13,
                  fontWeight: FontWeight.w600,
                  color: data.color,
                  height: 1.2,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Header & step indicator
// ---------------------------------------------------------------------------

class _Header extends StatelessWidget {
  final int step;
  final VoidCallback? onBack;
  final VoidCallback onClose;

  const _Header({required this.step, this.onBack, required this.onClose});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(4, 8, 4, 0),
      child: Row(
        children: [
          if (onBack != null)
            IconButton(
              icon: const Icon(Icons.arrow_back_rounded, color: AppColors.textPrimary),
              onPressed: onBack,
            )
          else
            const SizedBox(width: 48),
          const Spacer(),
          ShaderMask(
            shaderCallback: (b) => AppColors.accentGradient.createShader(b),
            child: const Text(
              'Vibe Check',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.w800,
                color: Colors.white,
              ),
            ),
          ),
          const Spacer(),
          IconButton(
            icon: const Icon(Icons.close_rounded, color: AppColors.textSecondary),
            onPressed: onClose,
          ),
        ],
      ),
    );
  }
}

class _StepIndicator extends StatelessWidget {
  final int current;
  final int total;

  const _StepIndicator({required this.current, required this.total});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 40, vertical: 12),
      child: Row(
        children: List.generate(total, (i) {
          final active = i <= current;
          return Expanded(
            child: AnimatedContainer(
              duration: const Duration(milliseconds: 300),
              height: 4,
              margin: const EdgeInsets.symmetric(horizontal: 3),
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(2),
                color: active
                    ? AppColors.accent
                    : AppColors.textTertiary.withValues(alpha: 0.25),
              ),
            ),
          );
        }),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Results view
// ---------------------------------------------------------------------------

class _ResultsView extends ConsumerWidget {
  final VibeCheckState state;
  const _ResultsView({required this.state});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    if (state.isLoading) {
      return const _LoadingState();
    }

    if (state.error != null) {
      return _ErrorState(
        error: state.error!,
        onRetry: () => ref.read(vibeCheckProvider.notifier).reset(),
      );
    }

    final notifier = ref.read(vibeCheckProvider.notifier);

    return Column(
      children: [
        _Header(
          step: 4,
          onClose: () {
            notifier.reset();
            context.pop();
          },
        ),
        const SizedBox(height: 8),

        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 24),
          child: Text(
            state.vibeSummary,
            textAlign: TextAlign.center,
            style: const TextStyle(
              fontSize: 18,
              fontWeight: FontWeight.w700,
              color: AppColors.textPrimary,
            ),
          ),
        ).animate().fadeIn(duration: 400.ms),
        const SizedBox(height: 20),

        Expanded(
          child: state.picks.isEmpty
              ? _EmptyPicks(onRetry: () => notifier.reset())
              : ListView.builder(
                  padding: const EdgeInsets.symmetric(horizontal: 16),
                  physics: const BouncingScrollPhysics(),
                  itemCount: state.picks.length + 1,
                  itemBuilder: (context, i) {
                    if (i == state.picks.length) {
                      return _RetryButton(onRetry: () => notifier.reset());
                    }
                    return _PickCard(
                      pick: state.picks[i],
                      rank: i + 1,
                    ).animate()
                        .fadeIn(delay: (120 * i).ms, duration: 400.ms)
                        .slideX(begin: 0.08, delay: (120 * i).ms, duration: 400.ms);
                  },
                ),
        ),
      ],
    );
  }
}

class _PickCard extends StatelessWidget {
  final Recommendation pick;
  final int rank;

  const _PickCard({required this.pick, required this.rank});

  @override
  Widget build(BuildContext context) {
    final title = pick.title;
    return GestureDetector(
      onTap: () => context.push('/title/${title.id}'),
      child: Container(
        margin: const EdgeInsets.only(bottom: 14),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(16),
          gradient: LinearGradient(
            colors: [
              AppColors.card,
              AppColors.cardLight.withValues(alpha: 0.7),
            ],
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
          ),
          border: Border.all(color: AppColors.border, width: 0.8),
        ),
        child: Row(
          children: [
            // Poster
            ClipRRect(
              borderRadius: const BorderRadius.only(
                topLeft: Radius.circular(16),
                bottomLeft: Radius.circular(16),
              ),
              child: SizedBox(
                width: 100,
                height: 150,
                child: title.posterUrl != null
                    ? CachedNetworkImage(
                        imageUrl: title.posterUrl!,
                        fit: BoxFit.cover,
                      )
                    : Container(
                        color: AppColors.surface,
                        child: const Icon(Icons.movie_outlined,
                            color: AppColors.textTertiary, size: 36),
                      ),
              ),
            ),

            Expanded(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(14, 12, 14, 12),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Container(
                          width: 26,
                          height: 26,
                          decoration: BoxDecoration(
                            shape: BoxShape.circle,
                            gradient: AppColors.accentGradient,
                          ),
                          child: Center(
                            child: Text(
                              '#$rank',
                              style: const TextStyle(
                                fontSize: 11,
                                fontWeight: FontWeight.w800,
                                color: Colors.white,
                              ),
                            ),
                          ),
                        ),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Text(
                            title.title,
                            maxLines: 2,
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(
                              fontSize: 15,
                              fontWeight: FontWeight.w700,
                              color: AppColors.textPrimary,
                            ),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 6),

                    if (pick.reason.isNotEmpty) ...[
                      Text(
                        pick.reason,
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(
                          fontSize: 12,
                          color: AppColors.accent,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                      const SizedBox(height: 6),
                    ],

                    Row(
                      children: [
                        if (title.voteAverage > 0) ...[
                          const Icon(Icons.star_rounded,
                              color: AppColors.ratingGold, size: 14),
                          const SizedBox(width: 3),
                          Text(
                            title.voteAverage.toStringAsFixed(1),
                            style: const TextStyle(
                              fontSize: 12,
                              color: AppColors.textSecondary,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                          const SizedBox(width: 12),
                        ],
                        if (title.releaseDate != null &&
                            title.releaseDate!.length >= 4)
                          Text(
                            title.releaseDate!.substring(0, 4),
                            style: const TextStyle(
                              fontSize: 12,
                              color: AppColors.textTertiary,
                            ),
                          ),
                        if (title.runtime != null && title.runtime! > 0) ...[
                          const SizedBox(width: 12),
                          Text(
                            '${title.runtime} min',
                            style: const TextStyle(
                              fontSize: 12,
                              color: AppColors.textTertiary,
                            ),
                          ),
                        ],
                      ],
                    ),

                    if (title.genres.isNotEmpty) ...[
                      const SizedBox(height: 8),
                      Wrap(
                        spacing: 6,
                        runSpacing: 4,
                        children: title.genres.take(3).map((g) {
                          return Container(
                            padding: const EdgeInsets.symmetric(
                                horizontal: 8, vertical: 3),
                            decoration: BoxDecoration(
                              borderRadius: BorderRadius.circular(8),
                              color: AppColors.primary.withValues(alpha: 0.12),
                            ),
                            child: Text(
                              g,
                              style: const TextStyle(
                                fontSize: 10,
                                color: AppColors.primaryLight,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                          );
                        }).toList(),
                      ),
                    ],
                  ],
                ),
              ),
            ),

            const Padding(
              padding: EdgeInsets.only(right: 12),
              child: Icon(Icons.chevron_right_rounded,
                  color: AppColors.textTertiary, size: 22),
            ),
          ],
        ),
      ),
    );
  }
}

class _LoadingState extends StatelessWidget {
  const _LoadingState();

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const SizedBox(
            width: 48,
            height: 48,
            child: CircularProgressIndicator(
              color: AppColors.accent,
              strokeWidth: 3,
            ),
          ),
          const SizedBox(height: 24),
          const Text(
            'Finding your perfect picks...',
            style: TextStyle(
              fontSize: 16,
              color: AppColors.textSecondary,
              fontWeight: FontWeight.w600,
            ),
          ).animate(onPlay: (c) => c.repeat()).shimmer(
              duration: 1500.ms, color: AppColors.primary.withValues(alpha: 0.3)),
        ],
      ),
    );
  }
}

class _ErrorState extends StatelessWidget {
  final String error;
  final VoidCallback onRetry;

  const _ErrorState({required this.error, required this.onRetry});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.wifi_off_rounded,
                color: AppColors.error, size: 48),
            const SizedBox(height: 16),
            Text(
              error,
              textAlign: TextAlign.center,
              style:
                  const TextStyle(color: AppColors.textSecondary, fontSize: 15),
            ),
            const SizedBox(height: 24),
            FilledButton.icon(
              onPressed: onRetry,
              icon: const Icon(Icons.refresh_rounded),
              label: const Text('Try Again'),
              style: FilledButton.styleFrom(
                backgroundColor: AppColors.accent,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _EmptyPicks extends StatelessWidget {
  final VoidCallback onRetry;
  const _EmptyPicks({required this.onRetry});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Text('🤷', style: TextStyle(fontSize: 48)),
          const SizedBox(height: 16),
          const Text(
            "We couldn't find matches for that combo.\nTry a different vibe!",
            textAlign: TextAlign.center,
            style: TextStyle(color: AppColors.textSecondary, fontSize: 15),
          ),
          const SizedBox(height: 24),
          FilledButton.icon(
            onPressed: onRetry,
            icon: const Icon(Icons.refresh_rounded),
            label: const Text('Start Over'),
            style: FilledButton.styleFrom(
              backgroundColor: AppColors.primary,
            ),
          ),
        ],
      ),
    );
  }
}

class _RetryButton extends StatelessWidget {
  final VoidCallback onRetry;
  const _RetryButton({required this.onRetry});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 20),
      child: Center(
        child: OutlinedButton.icon(
          onPressed: onRetry,
          icon: const Icon(Icons.refresh_rounded),
          label: const Text('Try Different Vibe'),
          style: OutlinedButton.styleFrom(
            foregroundColor: AppColors.accent,
            side: const BorderSide(color: AppColors.accent),
            padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
          ),
        ),
      ),
    );
  }
}
