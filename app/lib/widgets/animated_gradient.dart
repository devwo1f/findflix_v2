import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../core/theme/app_colors.dart';

class AnimatedGradientBackground extends StatefulWidget {
  final Widget child;
  final double opacity;
  final Duration duration;
  final BorderRadius? borderRadius;

  const AnimatedGradientBackground({
    super.key,
    required this.child,
    this.opacity = 1.0,
    this.duration = const Duration(seconds: 6),
    this.borderRadius,
  });

  @override
  State<AnimatedGradientBackground> createState() =>
      _AnimatedGradientBackgroundState();
}

class _AnimatedGradientBackgroundState extends State<AnimatedGradientBackground>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(vsync: this, duration: widget.duration)
      ..repeat();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _controller,
      builder: (context, child) {
        final t = _controller.value;
        final angle = t * 2 * math.pi;
        return DecoratedBox(
          decoration: BoxDecoration(
            borderRadius: widget.borderRadius,
            gradient: LinearGradient(
              begin: Alignment(math.cos(angle), math.sin(angle)),
              end: Alignment(-math.cos(angle), -math.sin(angle)),
              colors: [
                AppColors.gradientPurple.withOpacity(widget.opacity),
                AppColors.gradientBlue.withOpacity(widget.opacity),
                AppColors.gradientRed.withOpacity(widget.opacity),
                AppColors.gradientPurple.withOpacity(widget.opacity),
              ],
              stops: const [0.0, 0.33, 0.66, 1.0],
            ),
          ),
          child: child,
        );
      },
      child: widget.child,
    );
  }
}

class GradientText extends StatelessWidget {
  final String text;
  final TextStyle? style;
  final Gradient gradient;

  const GradientText(
    this.text, {
    super.key,
    this.style,
    this.gradient = AppColors.brandGradient,
  });

  @override
  Widget build(BuildContext context) {
    return ShaderMask(
      shaderCallback: (bounds) => gradient.createShader(bounds),
      child: Text(
        text,
        style: (style ?? const TextStyle()).copyWith(color: Colors.white),
      ),
    );
  }
}
