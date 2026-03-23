import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/constants/api_constants.dart';
import '../core/network/api_client.dart';
import '../models/title_model.dart';

/// Detects user's country via IP geolocation.
/// Falls back to browser locale, then "US".
final userCountryProvider = FutureProvider<String>((ref) async {
  // Try IP geolocation first (most accurate)
  try {
    final dio = Dio(BaseOptions(
      connectTimeout: const Duration(seconds: 5),
      receiveTimeout: const Duration(seconds: 5),
    ));
    final resp = await dio.get('https://ipapi.co/json/');
    if (resp.statusCode == 200 && resp.data is Map) {
      final code = resp.data['country_code'] as String?;
      if (code != null && code.length == 2) {
        return code.toUpperCase();
      }
    }
  } catch (_) {}

  // Fallback: browser locale
  if (kIsWeb) {
    try {
      final locale = PlatformDispatcher.instance.locale;
      final country = locale.countryCode;
      if (country != null && country.length == 2) {
        return country.toUpperCase();
      }
    } catch (_) {}
  }

  return 'US';
});

/// Fetches streaming availability for a specific title in the user's region.
final titleAvailabilityProvider = FutureProvider.autoDispose
    .family<List<AvailabilityInfo>, String>((ref, titleId) async {
  final api = ref.read(apiClientProvider);
  final region = await ref.watch(userCountryProvider.future);

  final data = await api.get<List<dynamic>>(
    ApiConstants.titleAvailability(titleId),
    queryParameters: {'region': region},
  );

  return data
      .map((e) => AvailabilityInfo.fromJson(e as Map<String, dynamic>))
      .toList();
});
