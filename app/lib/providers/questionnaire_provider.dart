import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/constants/api_constants.dart';
import '../core/network/api_client.dart';
import '../models/questionnaire.dart';

// ── Questionnaire Step Enum ───────────────────────────────────────────

enum QuestionnaireStep {
  genres,
  moods,
  pacing,
  tone,
  runtime,
  rewatch,
  complete,
}

// ── State ─────────────────────────────────────────────────────────────

class QuestionnaireState {
  final QuestionnaireStep currentStep;
  final QuestionnaireData data;
  final bool isSubmitting;
  final String? error;

  const QuestionnaireState({
    this.currentStep = QuestionnaireStep.genres,
    this.data = const QuestionnaireData(),
    this.isSubmitting = false,
    this.error,
  });

  int get stepIndex => currentStep.index;
  int get totalSteps => QuestionnaireStep.values.length - 1; // exclude complete
  double get progress => stepIndex / totalSteps;
  bool get isFirstStep => currentStep == QuestionnaireStep.genres;
  bool get isLastInputStep => currentStep == QuestionnaireStep.rewatch;

  bool get canProceed {
    switch (currentStep) {
      case QuestionnaireStep.genres:
        return data.genres.isNotEmpty;
      case QuestionnaireStep.moods:
        return data.moods.isNotEmpty;
      default:
        return true;
    }
  }

  QuestionnaireState copyWith({
    QuestionnaireStep? currentStep,
    QuestionnaireData? data,
    bool? isSubmitting,
    String? error,
  }) {
    return QuestionnaireState(
      currentStep: currentStep ?? this.currentStep,
      data: data ?? this.data,
      isSubmitting: isSubmitting ?? this.isSubmitting,
      error: error,
    );
  }
}

// ── Notifier ──────────────────────────────────────────────────────────

class QuestionnaireNotifier extends StateNotifier<QuestionnaireState> {
  final Ref _ref;

  QuestionnaireNotifier(this._ref) : super(const QuestionnaireState());

  void nextStep() {
    if (!state.canProceed) return;
    final steps = QuestionnaireStep.values;
    final nextIndex = state.stepIndex + 1;
    if (nextIndex < steps.length) {
      state = state.copyWith(currentStep: steps[nextIndex]);
    }
  }

  void previousStep() {
    final steps = QuestionnaireStep.values;
    final prevIndex = state.stepIndex - 1;
    if (prevIndex >= 0) {
      state = state.copyWith(currentStep: steps[prevIndex]);
    }
  }

  void goToStep(QuestionnaireStep step) {
    state = state.copyWith(currentStep: step);
  }

  // ── Genre helpers ────────────────────────────────────────────────

  void toggleGenre(String genreId) {
    final current = List<String>.from(state.data.genres);
    if (current.contains(genreId)) {
      current.remove(genreId);
    } else {
      current.add(genreId);
    }
    state = state.copyWith(data: state.data.copyWith(genres: current));
  }

  // ── Mood helpers ─────────────────────────────────────────────────

  void toggleMood(String moodId) {
    final current = List<String>.from(state.data.moods);
    if (current.contains(moodId)) {
      current.remove(moodId);
    } else {
      current.add(moodId);
    }
    state = state.copyWith(data: state.data.copyWith(moods: current));
  }

  // ── Slider helpers ───────────────────────────────────────────────

  void setPacing(double value) {
    state = state.copyWith(data: state.data.copyWith(pacing: value));
  }

  void setTone(double value) {
    state = state.copyWith(data: state.data.copyWith(tone: value));
  }

  // ── Runtime ──────────────────────────────────────────────────────

  void setRuntimePreference(String pref) {
    state =
        state.copyWith(data: state.data.copyWith(runtimePreference: pref));
  }

  // ── Rewatch ──────────────────────────────────────────────────────

  void setRewatchTolerance(String value) {
    state =
        state.copyWith(data: state.data.copyWith(rewatchTolerance: value));
  }

  // ── Submit ───────────────────────────────────────────────────────

  Future<bool> submit() async {
    state = state.copyWith(isSubmitting: true, error: null);
    try {
      final api = _ref.read(apiClientProvider);
      await api.post(
        ApiConstants.submitQuestionnaire,
        data: state.data.toJson(),
      );
      state = state.copyWith(
        isSubmitting: false,
        currentStep: QuestionnaireStep.complete,
      );
      return true;
    } catch (e) {
      state = state.copyWith(
        isSubmitting: false,
        error: 'Failed to save preferences. Please try again.',
      );
      return false;
    }
  }

  void reset() {
    state = const QuestionnaireState();
  }
}

// ── Providers ─────────────────────────────────────────────────────────

final questionnaireProvider =
    StateNotifierProvider<QuestionnaireNotifier, QuestionnaireState>((ref) {
  return QuestionnaireNotifier(ref);
});

/// Whether the current user has already completed the questionnaire.
final hasCompletedQuestionnaireProvider = FutureProvider<bool>((ref) async {
  try {
    final api = ref.read(apiClientProvider);
    await api.get<Map<String, dynamic>>(ApiConstants.getQuestionnaire);
    return true;
  } catch (_) {
    return false;
  }
});
