import 'package:flutter/material.dart';

import '../core/theme/app_colors.dart';

/// Interactive star-rating input widget (1-5 stars, supports half-stars).
class RatingWidget extends StatefulWidget {
  final double rating;
  final ValueChanged<double> onRatingChanged;
  final double starSize;
  final bool allowHalf;
  final bool readOnly;

  const RatingWidget({
    super.key,
    this.rating = 0,
    required this.onRatingChanged,
    this.starSize = 32,
    this.allowHalf = true,
    this.readOnly = false,
  });

  @override
  State<RatingWidget> createState() => _RatingWidgetState();
}

class _RatingWidgetState extends State<RatingWidget> {
  late double _current;

  @override
  void initState() {
    super.initState();
    _current = widget.rating;
  }

  @override
  void didUpdateWidget(covariant RatingWidget oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.rating != widget.rating) {
      _current = widget.rating;
    }
  }

  void _handleTap(int index, Offset localPosition) {
    if (widget.readOnly) return;
    double value;
    if (widget.allowHalf && localPosition.dx < widget.starSize / 2) {
      value = index + 0.5;
    } else {
      value = index + 1.0;
    }
    setState(() => _current = value);
    widget.onRatingChanged(value);
  }

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: List.generate(5, (index) {
        IconData icon;
        Color color;

        if (_current >= index + 1) {
          icon = Icons.star_rounded;
          color = AppColors.ratingGold;
        } else if (_current >= index + 0.5) {
          icon = Icons.star_half_rounded;
          color = AppColors.ratingGold;
        } else {
          icon = Icons.star_outline_rounded;
          color = AppColors.textTertiary;
        }

        return GestureDetector(
          onTapUp: (details) => _handleTap(index, details.localPosition),
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 2),
            child: Icon(icon, size: widget.starSize, color: color),
          ),
        );
      }),
    );
  }
}

/// Read-only compact rating display.
class RatingBadge extends StatelessWidget {
  final double rating;

  const RatingBadge({super.key, required this.rating});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: AppColors.ratingGold.withOpacity(0.15),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(Icons.star_rounded, size: 14, color: AppColors.ratingGold),
          const SizedBox(width: 4),
          Text(
            rating.toStringAsFixed(1),
            style: const TextStyle(
              color: AppColors.ratingGold,
              fontWeight: FontWeight.w700,
              fontSize: 13,
            ),
          ),
        ],
      ),
    );
  }
}
