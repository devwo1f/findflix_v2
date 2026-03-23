import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/constants/api_constants.dart';
import '../core/network/api_client.dart';
import '../models/recommendation.dart';

class VibeCheckState {
  final int step;
  final String? mood;
  final String? timeAvailable;
  final String? contentType;
  final String? vibe;
  final List<Recommendation> picks;
  final String vibeSummary;
  final bool isLoading;
  final String? error;

  const VibeCheckState({
    this.step = 0,
    this.mood,
    this.timeAvailable,
    this.contentType,
    this.vibe,
    this.picks = const [],
    this.vibeSummary = '',
    this.isLoading = false,
    this.error,
  });

  bool get isComplete => step >= 4;

  VibeCheckState copyWith({
    int? step,
    String? mood,
    String? timeAvailable,
    String? contentType,
    String? vibe,
    List<Recommendation>? picks,
    String? vibeSummary,
    bool? isLoading,
    String? error,
  }) {
    return VibeCheckState(
      step: step ?? this.step,
      mood: mood ?? this.mood,
      timeAvailable: timeAvailable ?? this.timeAvailable,
      contentType: contentType ?? this.contentType,
      vibe: vibe ?? this.vibe,
      picks: picks ?? this.picks,
      vibeSummary: vibeSummary ?? this.vibeSummary,
      isLoading: isLoading ?? this.isLoading,
      error: error,
    );
  }
}

class VibeCheckNotifier extends StateNotifier<VibeCheckState> {
  final Ref _ref;

  VibeCheckNotifier(this._ref) : super(const VibeCheckState());

  void selectMood(String mood) {
    state = state.copyWith(mood: mood, step: 1);
  }

  void selectTime(String time) {
    state = state.copyWith(timeAvailable: time, step: 2);
  }

  void selectContentType(String type) {
    state = state.copyWith(contentType: type, step: 3);
  }

  Future<void> selectVibeAndSubmit(String vibe) async {
    state = state.copyWith(vibe: vibe, step: 4, isLoading: true, error: null);
    try {
      final api = _ref.read(apiClientProvider);
      final data = await api.post<Map<String, dynamic>>(
        ApiConstants.vibeCheck,
        data: {
          'mood': state.mood,
          'time_available': state.timeAvailable,
          'content_type': state.contentType,
          'vibe': vibe,
        },
      );
      final list = data['picks'] as List<dynamic>? ?? [];
      final picks = list
          .map((e) => Recommendation.fromJson(e as Map<String, dynamic>))
          .toList();
      final summary = data['vibe_summary'] as String? ?? '';
      state = state.copyWith(
        picks: picks,
        vibeSummary: summary,
        isLoading: false,
      );
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: 'Could not fetch picks. Please try again.',
      );
    }
  }

  void reset() {
    state = const VibeCheckState();
  }

  void goBack() {
    if (state.step > 0) {
      state = state.copyWith(step: state.step - 1);
    }
  }
}

final vibeCheckProvider =
    StateNotifierProvider.autoDispose<VibeCheckNotifier, VibeCheckState>((ref) {
  return VibeCheckNotifier(ref);
});
