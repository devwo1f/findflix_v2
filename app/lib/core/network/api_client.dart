import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../constants/api_constants.dart';
import 'api_interceptors.dart';

// ── Structured API Error ──────────────────────────────────────────────

class ApiError implements Exception {
  final int? statusCode;
  final String message;
  final dynamic data;

  const ApiError({this.statusCode, required this.message, this.data});

  factory ApiError.fromDioException(DioException e) {
    final response = e.response;
    String message;

    switch (e.type) {
      case DioExceptionType.connectionTimeout:
      case DioExceptionType.sendTimeout:
      case DioExceptionType.receiveTimeout:
        message = 'Connection timed out. Please check your internet.';
        break;
      case DioExceptionType.connectionError:
        message = 'Unable to connect to the server.';
        break;
      case DioExceptionType.cancel:
        message = 'Request was cancelled.';
        break;
      case DioExceptionType.badResponse:
        message = _extractMessage(response);
        break;
      default:
        message = 'An unexpected error occurred.';
    }

    return ApiError(
      statusCode: response?.statusCode,
      message: message,
      data: response?.data,
    );
  }

  static String _extractMessage(Response? response) {
    if (response?.data is Map) {
      final data = response!.data as Map;
      if (data['message'] is String) return data['message'] as String;
      if (data['error'] is String) return data['error'] as String;

      final detail = data['detail'];
      if (detail is String) return detail;
      if (detail is List && detail.isNotEmpty) {
        final first = detail.first;
        if (first is Map) {
          final msg = first['msg'] as String? ?? '';
          final loc = (first['loc'] as List?)?.join(' > ') ?? '';
          return loc.isNotEmpty ? '$loc: $msg' : msg;
        }
        return first.toString();
      }

      return 'Something went wrong (${response.statusCode})';
    }
    return 'Something went wrong (${response?.statusCode})';
  }

  @override
  String toString() => 'ApiError($statusCode): $message';
}

// ── API Client ────────────────────────────────────────────────────────

class ApiClient {
  late final Dio _dio;

  ApiClient(Ref ref) {
    _dio = Dio(
      BaseOptions(
        baseUrl: ApiConstants.baseUrl,
        connectTimeout: const Duration(milliseconds: ApiConstants.connectTimeout),
        receiveTimeout: const Duration(milliseconds: ApiConstants.receiveTimeout),
        sendTimeout: const Duration(milliseconds: ApiConstants.sendTimeout),
        headers: ApiConstants.defaultHeaders,
        responseType: ResponseType.json,
      ),
    );

    _dio.interceptors.addAll([
      AuthInterceptor(ref),
      RetryInterceptor(_dio),
      LoggingInterceptor(),
    ]);
  }

  // ── HTTP Methods ─────────────────────────────────────────────────

  Future<T> get<T>(
    String path, {
    Map<String, dynamic>? queryParameters,
    CancelToken? cancelToken,
  }) async {
    return _execute(() => _dio.get<T>(
          path,
          queryParameters: queryParameters,
          cancelToken: cancelToken,
        ));
  }

  Future<T> post<T>(
    String path, {
    dynamic data,
    Map<String, dynamic>? queryParameters,
    CancelToken? cancelToken,
  }) async {
    return _execute(() => _dio.post<T>(
          path,
          data: data,
          queryParameters: queryParameters,
          cancelToken: cancelToken,
        ));
  }

  Future<T> put<T>(
    String path, {
    dynamic data,
    Map<String, dynamic>? queryParameters,
    CancelToken? cancelToken,
  }) async {
    return _execute(() => _dio.put<T>(
          path,
          data: data,
          queryParameters: queryParameters,
          cancelToken: cancelToken,
        ));
  }

  Future<T> patch<T>(
    String path, {
    dynamic data,
    Map<String, dynamic>? queryParameters,
    CancelToken? cancelToken,
  }) async {
    return _execute(() => _dio.patch<T>(
          path,
          data: data,
          queryParameters: queryParameters,
          cancelToken: cancelToken,
        ));
  }

  Future<T> delete<T>(
    String path, {
    dynamic data,
    Map<String, dynamic>? queryParameters,
    CancelToken? cancelToken,
  }) async {
    return _execute(() => _dio.delete<T>(
          path,
          data: data,
          queryParameters: queryParameters,
          cancelToken: cancelToken,
        ));
  }

  // ── Execution wrapper ────────────────────────────────────────────

  Future<T> _execute<T>(Future<Response<T>> Function() request) async {
    try {
      final response = await request();
      return response.data as T;
    } on DioException catch (e) {
      throw ApiError.fromDioException(e);
    }
  }
}

// ── Provider ──────────────────────────────────────────────────────────

final apiClientProvider = Provider<ApiClient>((ref) {
  return ApiClient(ref);
});
