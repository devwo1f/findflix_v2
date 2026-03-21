import 'package:flutter/material.dart';

/// FindFlix color palette - dark-first, cinematic, premium feel.
class AppColors {
  AppColors._();

  // ── Primary Palette ──────────────────────────────────────────────
  static const Color primary = Color(0xFF6C63FF);
  static const Color primaryLight = Color(0xFF9D97FF);
  static const Color primaryDark = Color(0xFF4A42DB);

  // ── Accent / Secondary ───────────────────────────────────────────
  static const Color accent = Color(0xFFFF6B6B);
  static const Color accentLight = Color(0xFFFF9E9E);
  static const Color accentDark = Color(0xFFD94848);

  // ── Backgrounds ──────────────────────────────────────────────────
  static const Color background = Color(0xFF0D0D0F);
  static const Color surface = Color(0xFF1A1A2E);
  static const Color card = Color(0xFF16213E);
  static const Color cardLight = Color(0xFF1E2D4D);
  static const Color dialogBackground = Color(0xFF1F1F33);

  // ── Text ─────────────────────────────────────────────────────────
  static const Color textPrimary = Color(0xFFF5F5F7);
  static const Color textSecondary = Color(0xFFB0B0C3);
  static const Color textTertiary = Color(0xFF6E6E82);
  static const Color textOnPrimary = Color(0xFFFFFFFF);

  // ── Borders & Dividers ───────────────────────────────────────────
  static const Color border = Color(0xFF2A2A3E);
  static const Color divider = Color(0xFF252540);

  // ── Status ───────────────────────────────────────────────────────
  static const Color success = Color(0xFF4ADE80);
  static const Color warning = Color(0xFFFBBF24);
  static const Color error = Color(0xFFEF4444);
  static const Color info = Color(0xFF38BDF8);

  // ── Ratings ──────────────────────────────────────────────────────
  static const Color ratingGold = Color(0xFFFFD700);
  static const Color matchHigh = Color(0xFF4ADE80);
  static const Color matchMedium = Color(0xFFFBBF24);
  static const Color matchLow = Color(0xFFEF4444);

  // ── Streaming Providers ──────────────────────────────────────────
  static const Color netflix = Color(0xFFE50914);
  static const Color prime = Color(0xFF00A8E1);
  static const Color disney = Color(0xFF113CCF);
  static const Color hbo = Color(0xFF6B3FA0);
  static const Color hulu = Color(0xFF1CE783);
  static const Color apple = Color(0xFFA2AAAD);
  static const Color peacock = Color(0xFFFBBB00);

  // ── Gradients ────────────────────────────────────────────────────
  static const LinearGradient primaryGradient = LinearGradient(
    colors: [primary, Color(0xFF8B5CF6)],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );

  static const LinearGradient accentGradient = LinearGradient(
    colors: [accent, Color(0xFFFF8E53)],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );

  static const LinearGradient backgroundGradient = LinearGradient(
    colors: [background, surface],
    begin: Alignment.topCenter,
    end: Alignment.bottomCenter,
  );

  static const LinearGradient cardGradient = LinearGradient(
    colors: [card, Color(0xFF0F3460)],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );

  static const LinearGradient shimmerGradient = LinearGradient(
    colors: [
      Color(0xFF1A1A2E),
      Color(0xFF252545),
      Color(0xFF1A1A2E),
    ],
    stops: [0.0, 0.5, 1.0],
    begin: Alignment(-1.0, -0.3),
    end: Alignment(1.0, 0.3),
  );

  /// Returns a match color based on percentage (0-100).
  static Color matchColor(double percentage) {
    if (percentage >= 80) return matchHigh;
    if (percentage >= 60) return matchMedium;
    return matchLow;
  }
}
