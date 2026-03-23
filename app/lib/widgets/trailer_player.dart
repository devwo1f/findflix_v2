import 'dart:html' as html;
import 'dart:ui_web' as ui_web;

import 'package:flutter/material.dart';

import '../core/theme/app_colors.dart';

class TrailerPlayer extends StatefulWidget {
  final String youtubeKey;
  final String? backdropUrl;
  final double height;

  const TrailerPlayer({
    super.key,
    required this.youtubeKey,
    this.backdropUrl,
    this.height = 420,
  });

  @override
  State<TrailerPlayer> createState() => _TrailerPlayerState();
}

class _TrailerPlayerState extends State<TrailerPlayer> {
  bool _isMuted = true;
  late final String _viewType;
  html.IFrameElement? _iframe;

  @override
  void initState() {
    super.initState();
    _viewType =
        'yt-bg-${widget.youtubeKey}-${DateTime.now().millisecondsSinceEpoch}';
    _registerView();
  }

  void _registerView() {
    ui_web.platformViewRegistry.registerViewFactory(_viewType, (int viewId) {
      final key = widget.youtubeKey;
      final embedUrl = 'https://www.youtube.com/embed/$key'
          '?autoplay=1&mute=1&controls=0&showinfo=0'
          '&rel=0&modestbranding=1&playsinline=1'
          '&loop=1&playlist=$key&enablejsapi=1'
          '&iv_load_policy=3&disablekb=1&fs=0';

      _iframe = html.IFrameElement()
        ..src = embedUrl
        ..allow = 'autoplay; encrypted-media'
        ..setAttribute('allowfullscreen', 'false');

      // Scale the iframe 2x and center it so YouTube UI is clipped away.
      // pointer-events:none prevents accidental interaction.
      _iframe!.style
        ..border = 'none'
        ..position = 'absolute'
        ..top = '50%'
        ..left = '50%'
        ..width = '200%'
        ..height = '200%'
        ..setProperty('transform', 'translate(-50%, -50%)')
        ..setProperty('pointer-events', 'none')
        ..setProperty('object-fit', 'cover');

      final wrapper = html.DivElement()
        ..style.position = 'relative'
        ..style.overflow = 'hidden'
        ..style.width = '100%'
        ..style.height = '100%'
        ..style.background = '#000';
      wrapper.append(_iframe!);

      return wrapper;
    });
  }

  void _toggleMute() {
    if (_iframe?.contentWindow != null) {
      final func = _isMuted ? 'unMute' : 'mute';
      _iframe!.contentWindow!.postMessage(
        '{"event":"command","func":"$func","args":""}',
        '*',
      );
    }
    setState(() => _isMuted = !_isMuted);
  }

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: widget.height,
      child: Stack(
        fit: StackFit.expand,
        children: [
          // Backdrop image shows instantly while trailer loads
          if (widget.backdropUrl != null)
            Image.network(widget.backdropUrl!, fit: BoxFit.cover),

          // YouTube trailer layer (sits on top, hides backdrop once loaded)
          Positioned.fill(
            child: HtmlElementView(viewType: _viewType),
          ),

          // Top gradient (fades into app bar)
          const Positioned(
            top: 0,
            left: 0,
            right: 0,
            height: 80,
            child: DecoratedBox(
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  begin: Alignment.topCenter,
                  end: Alignment.bottomCenter,
                  colors: [AppColors.background, Colors.transparent],
                ),
              ),
            ),
          ),

          // Bottom gradient (fades into content)
          const Positioned(
            bottom: 0,
            left: 0,
            right: 0,
            height: 140,
            child: DecoratedBox(
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  begin: Alignment.topCenter,
                  end: Alignment.bottomCenter,
                  colors: [Colors.transparent, AppColors.background],
                ),
              ),
            ),
          ),

          // Mute / unmute button
          Positioned(
            bottom: 24,
            right: 16,
            child: _MuteButton(isMuted: _isMuted, onTap: _toggleMute),
          ),
        ],
      ),
    );
  }
}

class _MuteButton extends StatelessWidget {
  final bool isMuted;
  final VoidCallback onTap;
  const _MuteButton({required this.isMuted, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        width: 36,
        height: 36,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          border: Border.all(color: Colors.white54, width: 1.2),
          color: Colors.black45,
        ),
        child: Icon(
          isMuted ? Icons.volume_off_rounded : Icons.volume_up_rounded,
          color: Colors.white,
          size: 18,
        ),
      ),
    );
  }
}
