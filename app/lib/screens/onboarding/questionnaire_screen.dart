import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/router/app_router.dart';
import '../../core/theme/app_colors.dart';
import '../../models/questionnaire.dart';
import '../../providers/questionnaire_provider.dart';
import '../../widgets/genre_chip.dart';
import '../../widgets/mood_card.dart';

class QuestionnaireScreen extends ConsumerStatefulWidget {
  const QuestionnaireScreen({super.key});

  @override
  ConsumerState<QuestionnaireScreen> createState() =>
      _QuestionnaireScreenState();
}

class _QuestionnaireScreenState extends ConsumerState<QuestionnaireScreen> {
  late final PageController _pageCtrl;

  @override
  void initState() {
    super.initState();
    _pageCtrl = PageController();
  }

  @override
  void dispose() {
    _pageCtrl.dispose();
    super.dispose();
  }

  void _animateToPage(int page) {
    _pageCtrl.animateToPage(
      page,
      duration: const Duration(milliseconds: 400),
      curve: Curves.easeInOut,
    );
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(questionnaireProvider);
    final notifier = ref.read(questionnaireProvider.notifier);
    final theme = Theme.of(context);

    // Sync PageView when step changes via the notifier.
    ref.listen<QuestionnaireState>(questionnaireProvider, (prev, next) {
      if (prev?.stepIndex != next.stepIndex) {
        _animateToPage(next.stepIndex);
      }
      if (next.currentStep == QuestionnaireStep.complete) {
        Future.delayed(const Duration(seconds: 2), () {
          if (mounted) context.go(AppRoutes.home);
        });
      }
    });

    return Scaffold(
      backgroundColor: AppColors.background,
      body: SafeArea(
        child: Column(
          children: [
            // ── Top Bar ────────────────────────────────────────────
            Padding(
              padding:
                  const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
              child: Row(
                children: [
                  if (!state.isFirstStep &&
                      state.currentStep != QuestionnaireStep.complete)
                    IconButton(
                      onPressed: notifier.previousStep,
                      icon: const Icon(Icons.arrow_back_rounded),
                    )
                  else
                    const SizedBox(width: 48),
                  Expanded(
                    child: _ProgressBar(progress: state.progress),
                  ),
                  const SizedBox(width: 48),
                ],
              ),
            ),

            // ── Pages ──────────────────────────────────────────────
            Expanded(
              child: PageView(
                controller: _pageCtrl,
                physics: const NeverScrollableScrollPhysics(),
                children: [
                  _GenrePage(state: state, notifier: notifier),
                  _MoodPage(state: state, notifier: notifier),
                  _PacingPage(state: state, notifier: notifier),
                  _TonePage(state: state, notifier: notifier),
                  _RuntimePage(state: state, notifier: notifier),
                  _RewatchPage(state: state, notifier: notifier),
                  _CompletePage(),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// ── Progress Bar ──────────────────────────────────────────────────────

class _ProgressBar extends StatelessWidget {
  final double progress;
  const _ProgressBar({required this.progress});

  @override
  Widget build(BuildContext context) {
    return ClipRRect(
      borderRadius: BorderRadius.circular(4),
      child: LinearProgressIndicator(
        value: progress,
        minHeight: 4,
        backgroundColor: AppColors.border,
        valueColor:
            const AlwaysStoppedAnimation<Color>(AppColors.primary),
      ),
    );
  }
}

// ── Step Wrapper ──────────────────────────────────────────────────────

class _StepScaffold extends StatelessWidget {
  final String title;
  final String subtitle;
  final Widget child;
  final bool canProceed;
  final bool isLoading;
  final VoidCallback onNext;
  final String nextLabel;

  const _StepScaffold({
    required this.title,
    required this.subtitle,
    required this.child,
    required this.canProceed,
    this.isLoading = false,
    required this.onNext,
    this.nextLabel = 'Continue',
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const SizedBox(height: 16),
          Text(title, style: theme.textTheme.headlineLarge)
              .animate().fadeIn(duration: 350.ms),
          const SizedBox(height: 6),
          Text(
            subtitle,
            style: theme.textTheme.bodyMedium
                ?.copyWith(color: AppColors.textTertiary),
          ).animate().fadeIn(delay: 100.ms, duration: 350.ms),
          const SizedBox(height: 24),
          Expanded(child: child),
          const SizedBox(height: 12),
          SizedBox(
            width: double.infinity,
            height: 56,
            child: ElevatedButton(
              onPressed: canProceed && !isLoading ? onNext : null,
              child: isLoading
                  ? const SizedBox(
                      width: 22,
                      height: 22,
                      child: CircularProgressIndicator(
                          strokeWidth: 2.5, color: Colors.white),
                    )
                  : Text(nextLabel),
            ),
          ).animate().fadeIn(delay: 200.ms, duration: 350.ms),
          const SizedBox(height: 16),
        ],
      ),
    );
  }
}

// ── Step 1: Genres ────────────────────────────────────────────────────

class _GenrePage extends StatelessWidget {
  final QuestionnaireState state;
  final QuestionnaireNotifier notifier;

  const _GenrePage({required this.state, required this.notifier});

  @override
  Widget build(BuildContext context) {
    return _StepScaffold(
      title: "What's your vibe?",
      subtitle: 'Pick the genres you love (at least one)',
      canProceed: state.data.genres.isNotEmpty,
      onNext: notifier.nextStep,
      child: SingleChildScrollView(
        child: Wrap(
          spacing: 10,
          runSpacing: 10,
          children: availableGenres.map((genre) {
            final selected = state.data.genres.contains(genre.id);
            return GenreChip(
              label: genre.name,
              icon: genre.icon,
              isSelected: selected,
              onTap: () => notifier.toggleGenre(genre.id),
            );
          }).toList(),
        ),
      ),
    );
  }
}

// ── Step 2: Moods ─────────────────────────────────────────────────────

class _MoodPage extends StatelessWidget {
  final QuestionnaireState state;
  final QuestionnaireNotifier notifier;

  const _MoodPage({required this.state, required this.notifier});

  @override
  Widget build(BuildContext context) {
    return _StepScaffold(
      title: 'Set the mood',
      subtitle: 'What feelings do you enjoy in a story?',
      canProceed: state.data.moods.isNotEmpty,
      onNext: notifier.nextStep,
      child: GridView.count(
        crossAxisCount: 2,
        mainAxisSpacing: 12,
        crossAxisSpacing: 12,
        childAspectRatio: 1.15,
        children: availableMoods.map((mood) {
          final selected = state.data.moods.contains(mood.id);
          return MoodCard(
            mood: mood,
            isSelected: selected,
            onTap: () => notifier.toggleMood(mood.id),
          );
        }).toList(),
      ),
    );
  }
}

// ── Step 3: Pacing ────────────────────────────────────────────────────

class _PacingPage extends StatelessWidget {
  final QuestionnaireState state;
  final QuestionnaireNotifier notifier;

  const _PacingPage({required this.state, required this.notifier});

  @override
  Widget build(BuildContext context) {
    return _StepScaffold(
      title: 'How fast?',
      subtitle: 'Do you prefer slow burns or rapid rides?',
      canProceed: true,
      onNext: notifier.nextStep,
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text('Slow Burn',
                  style: TextStyle(color: AppColors.textSecondary)),
              Text('Fast-Paced',
                  style: TextStyle(color: AppColors.textSecondary)),
            ],
          ),
          const SizedBox(height: 8),
          Slider(
            value: state.data.pacing,
            onChanged: notifier.setPacing,
            divisions: 10,
          ),
          const SizedBox(height: 24),
          Icon(
            state.data.pacing < 0.4
                ? Icons.self_improvement_rounded
                : state.data.pacing > 0.6
                    ? Icons.bolt_rounded
                    : Icons.speed_rounded,
            size: 64,
            color: AppColors.primary,
          ).animate().fadeIn(duration: 300.ms),
        ],
      ),
    );
  }
}

// ── Step 4: Tone ──────────────────────────────────────────────────────

class _TonePage extends StatelessWidget {
  final QuestionnaireState state;
  final QuestionnaireNotifier notifier;

  const _TonePage({required this.state, required this.notifier});

  @override
  Widget build(BuildContext context) {
    return _StepScaffold(
      title: 'Serious or fun?',
      subtitle: 'Pick your tone sweet spot',
      canProceed: true,
      onNext: notifier.nextStep,
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text('Serious',
                  style: TextStyle(color: AppColors.textSecondary)),
              Text('Fun & Light',
                  style: TextStyle(color: AppColors.textSecondary)),
            ],
          ),
          const SizedBox(height: 8),
          Slider(
            value: state.data.tone,
            onChanged: notifier.setTone,
            divisions: 10,
          ),
          const SizedBox(height: 24),
          Icon(
            state.data.tone < 0.4
                ? Icons.theater_comedy_outlined
                : state.data.tone > 0.6
                    ? Icons.sentiment_very_satisfied_rounded
                    : Icons.balance_rounded,
            size: 64,
            color: AppColors.primary,
          ).animate().fadeIn(duration: 300.ms),
        ],
      ),
    );
  }
}

// ── Step 5: Runtime ───────────────────────────────────────────────────

class _RuntimePage extends StatelessWidget {
  final QuestionnaireState state;
  final QuestionnaireNotifier notifier;

  const _RuntimePage({required this.state, required this.notifier});

  static const _options = [
    ('<90', 'Under 90 min'),
    ('90-120', '90 – 120 min'),
    ('120-150', '120 – 150 min'),
    ('150+', '150 min +'),
    ('any', 'No preference'),
  ];

  @override
  Widget build(BuildContext context) {
    return _StepScaffold(
      title: 'How long?',
      subtitle: 'What runtime do you gravitate toward?',
      canProceed: true,
      onNext: notifier.nextStep,
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: _options.map((opt) {
          final selected = state.data.runtimePreference == opt.$1;
          return Padding(
            padding: const EdgeInsets.only(bottom: 12),
            child: GestureDetector(
              onTap: () => notifier.setRuntimePreference(opt.$1),
              child: AnimatedContainer(
                duration: const Duration(milliseconds: 250),
                width: double.infinity,
                padding: const EdgeInsets.symmetric(
                    horizontal: 20, vertical: 16),
                decoration: BoxDecoration(
                  color: selected
                      ? AppColors.primary.withOpacity(0.15)
                      : AppColors.surface,
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(
                    color:
                        selected ? AppColors.primary : AppColors.border,
                    width: selected ? 1.5 : 1,
                  ),
                ),
                child: Text(
                  opt.$2,
                  style: TextStyle(
                    color: selected
                        ? AppColors.textPrimary
                        : AppColors.textSecondary,
                    fontWeight:
                        selected ? FontWeight.w600 : FontWeight.w400,
                    fontSize: 15,
                  ),
                  textAlign: TextAlign.center,
                ),
              ),
            ),
          );
        }).toList(),
      ),
    );
  }
}

// ── Step 6: Rewatch ───────────────────────────────────────────────────

class _RewatchPage extends StatelessWidget {
  final QuestionnaireState state;
  final QuestionnaireNotifier notifier;

  const _RewatchPage({required this.state, required this.notifier});

  static const _options = [
    ('yes', 'Yes, absolutely!', Icons.replay_rounded),
    ('sometimes', 'Sometimes', Icons.shuffle_rounded),
    ('no', 'Rarely / never', Icons.skip_next_rounded),
  ];

  @override
  Widget build(BuildContext context) {
    return _StepScaffold(
      title: 'Rewatch?',
      subtitle: 'Would you rewatch old favorites?',
      canProceed: true,
      isLoading: state.isSubmitting,
      nextLabel: 'Finish',
      onNext: () async {
        await notifier.submit();
      },
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: _options.map((opt) {
          final selected = state.data.rewatchTolerance == opt.$1;
          return Padding(
            padding: const EdgeInsets.only(bottom: 14),
            child: GestureDetector(
              onTap: () => notifier.setRewatchTolerance(opt.$1),
              child: AnimatedContainer(
                duration: const Duration(milliseconds: 250),
                width: double.infinity,
                padding: const EdgeInsets.symmetric(
                    horizontal: 20, vertical: 18),
                decoration: BoxDecoration(
                  color: selected
                      ? AppColors.primary.withOpacity(0.15)
                      : AppColors.surface,
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(
                    color:
                        selected ? AppColors.primary : AppColors.border,
                    width: selected ? 1.5 : 1,
                  ),
                ),
                child: Row(
                  children: [
                    Icon(
                      opt.$3,
                      color: selected
                          ? AppColors.primary
                          : AppColors.textTertiary,
                    ),
                    const SizedBox(width: 14),
                    Text(
                      opt.$2,
                      style: TextStyle(
                        color: selected
                            ? AppColors.textPrimary
                            : AppColors.textSecondary,
                        fontWeight:
                            selected ? FontWeight.w600 : FontWeight.w400,
                        fontSize: 16,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          );
        }).toList(),
      ),
    );
  }
}

// ── Complete ──────────────────────────────────────────────────────────

class _CompletePage extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 100,
            height: 100,
            decoration: BoxDecoration(
              gradient: AppColors.primaryGradient,
              shape: BoxShape.circle,
            ),
            child: const Icon(Icons.check_rounded,
                size: 56, color: Colors.white),
          )
              .animate()
              .scale(
                begin: const Offset(0, 0),
                end: const Offset(1, 1),
                duration: 600.ms,
                curve: Curves.elasticOut,
              )
              .fadeIn(duration: 300.ms),
          const SizedBox(height: 28),
          Text("You're all set!", style: theme.textTheme.displaySmall)
              .animate()
              .fadeIn(delay: 300.ms, duration: 400.ms),
          const SizedBox(height: 8),
          Text(
            'Your personalized recommendations are being prepared.',
            style: theme.textTheme.bodyMedium
                ?.copyWith(color: AppColors.textTertiary),
            textAlign: TextAlign.center,
          ).animate().fadeIn(delay: 500.ms, duration: 400.ms),
        ],
      ),
    );
  }
}
