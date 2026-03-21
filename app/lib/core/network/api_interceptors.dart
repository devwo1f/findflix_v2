import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Injects the Firebase ID token into every outgoing request.
class AuthInterceptor extends Interceptor {
  final Ref _ref;

  AuthInterceptor(this._ref);

  @override
  void onRequest(
    RequestOptions options,
    RequestInterceptorHandler handler,
  ) async {
    try {
      // Token is provided by tokenProvider (see auth_provider.dart).
      // We read it lazily so the interceptor doesn't create a circular dep.
      final token = _ref.read(_tokenStringProvider);
      if (token != null && token.isNotEmpty) {
        options.headers['Authorization'] = 'Bearer $token';
      }
    } catch (_) {
      // If we can't read the token we still let the request go through.
    }
    handler.next(options);
  }

  @override
  void onError(DioException err, ErrorInterceptorHandler handler) {
    if (err.response?.statusCode == 401) {
      // Could trigger a token refresh or logout here.
      debugPrint('[AuthInterceptor] 401 Unauthorized – token may be expired');
    }
    handler.next(err);
  }
}

/// Simple provider that holds the raw token string for injection.
/// This is set by the auth layer whenever the token changes.
final _tokenStringProvider = StateProvider<String?>((ref) => null);

/// Public alias so the auth layer can write to it.
final tokenStringProvider = _tokenStringProvider;

/// Logs request/response details in debug mode.
class LoggingInterceptor extends Interceptor {
  @override
  void onRequest(RequestOptions options, RequestInterceptorHandler handler) {
    if (kDebugMode) {
      debugPrint(
        '──▶ ${options.method} ${options.uri}',
      );
      if (options.data != null) {
        debugPrint('    Body: ${options.data}');
      }
    }
    handler.next(options);
  }

  @override
  void onResponse(Response response, ResponseInterceptorHandler handler) {
    if (kDebugMode) {
      debugPrint(
        '◀── ${response.statusCode} ${response.requestOptions.uri}',
      );
    }
    handler.next(response);
  }

  @override
  void onError(DioException err, ErrorInterceptorHandler handler) {
    if (kDebugMode) {
      debugPrint(
        '✖── ${err.response?.statusCode ?? 'NO_STATUS'} '
        '${err.requestOptions.uri} '
        '${err.message}',
      );
    }
    handler.next(err);
  }
}

/// Retries failed requests up to [maxRetries] times for transient errors.
class RetryInterceptor extends Interceptor {
  final Dio _dio;
  final int maxRetries;
  final Duration retryDelay;

  RetryInterceptor(
    this._dio, {
    this.maxRetries = 2,
    this.retryDelay = const Duration(seconds: 1),
  });

  @override
  void onError(DioException err, ErrorInterceptorHandler handler) async {
    final extra = err.requestOptions.extra;
    final retryCount = (extra['retryCount'] as int?) ?? 0;

    final isRetryable = _isRetryableError(err);

    if (isRetryable && retryCount < maxRetries) {
      await Future.delayed(retryDelay * (retryCount + 1));
      err.requestOptions.extra['retryCount'] = retryCount + 1;
      try {
        final response = await _dio.fetch(err.requestOptions);
        handler.resolve(response);
        return;
      } catch (e) {
        // Fall through to reject.
      }
    }

    handler.next(err);
  }

  bool _isRetryableError(DioException err) {
    if (err.type == DioExceptionType.connectionTimeout ||
        err.type == DioExceptionType.receiveTimeout ||
        err.type == DioExceptionType.connectionError) {
      return true;
    }
    final statusCode = err.response?.statusCode;
    if (statusCode != null && (statusCode == 502 || statusCode == 503 || statusCode == 504)) {
      return true;
    }
    return false;
  }
}
