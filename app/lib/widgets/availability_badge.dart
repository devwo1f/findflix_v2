import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';

import '../core/theme/app_colors.dart';
import '../models/title_model.dart';

/// Badge showing a streaming-provider logo or fallback name.
class AvailabilityBadge extends StatelessWidget {
  final AvailabilityInfo info;
  final double size;

  const AvailabilityBadge({
    super.key,
    required this.info,
    this.size = 36,
  });

  @override
  Widget build(BuildContext context) {
    return Tooltip(
      message: '${info.providerName} (${_typeLabel(info.type)})',
      child: Container(
        width: size,
        height: size,
        decoration: BoxDecoration(
          color: _providerColor(info.providerName),
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: AppColors.border, width: 0.5),
        ),
        clipBehavior: Clip.antiAlias,
        child: info.logoUrl != null
            ? CachedNetworkImage(
                imageUrl: info.logoUrl!,
                fit: BoxFit.cover,
                errorWidget: (_, __, ___) => _fallbackLabel(),
              )
            : _fallbackLabel(),
      ),
    );
  }

  Widget _fallbackLabel() {
    return Center(
      child: Text(
        info.providerName.isNotEmpty
            ? info.providerName.substring(0, 1).toUpperCase()
            : '?',
        style: const TextStyle(
          color: Colors.white,
          fontWeight: FontWeight.bold,
          fontSize: 14,
        ),
      ),
    );
  }

  static String _typeLabel(String type) {
    switch (type) {
      case 'flatrate':
        return 'Stream';
      case 'rent':
        return 'Rent';
      case 'buy':
        return 'Buy';
      default:
        return type;
    }
  }

  static Color _providerColor(String name) {
    final lower = name.toLowerCase();
    if (lower.contains('netflix')) return AppColors.netflix;
    if (lower.contains('prime') || lower.contains('amazon')) {
      return AppColors.prime;
    }
    if (lower.contains('disney')) return AppColors.disney;
    if (lower.contains('hbo') || lower.contains('max')) return AppColors.hbo;
    if (lower.contains('hulu')) return AppColors.hulu;
    if (lower.contains('apple')) return AppColors.apple;
    if (lower.contains('peacock')) return AppColors.peacock;
    return AppColors.cardLight;
  }
}

/// Row of provider badges with optional "where to watch" label.
class AvailabilityRow extends StatelessWidget {
  final List<AvailabilityInfo> providers;
  final bool showLabel;

  const AvailabilityRow({
    super.key,
    required this.providers,
    this.showLabel = false,
  });

  @override
  Widget build(BuildContext context) {
    if (providers.isEmpty) return const SizedBox.shrink();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        if (showLabel)
          Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: Text(
              'Where to Watch',
              style: Theme.of(context).textTheme.titleSmall,
            ),
          ),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: providers
              .map((p) => AvailabilityBadge(info: p))
              .toList(),
        ),
      ],
    );
  }
}
