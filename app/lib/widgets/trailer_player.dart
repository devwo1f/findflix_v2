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
    this.height = 360,
  });

  @override
  State<TrailerPlayer> createState() => _TrailerPlayerState();
}

class _TrailerPlayerState extends State<TrailerPlayer> {
  bool _isMuted = true;
  bool _showTrailer = true;
  late final String _viewType;
  html.IFrameElement? _iframe;

  @override
  void initState() {
    super.initState();
    _viewType = 'yt-trailer-${widget.youtubeKey}-${DateTime.now().millisecondsSinceEpoch}';
    _registerView();
  }

  void _registerView() {
    ui_web.platformViewRegistry.registerViewFactory(_viewType, (int viewId) {
      _iframe = html.IFrameElement()
        ..src = _buildUrl()
        ..style.border = 'none'
        ..style.width = '100%'
        ..style.height = '100%'
        ..allow = 'autoplay; encrypted-media'
        ..setAttribute('allowfullscreen', 'true');
      return _iframe!;
    });
  }

  String _buildUrl() {
    final key = widget.youtubeKey;
    final mute = _isMuted ? '1' : '0';
    return 'https://www.youtube.com/embed/$key'
        '?autoplay=1&mute=$mute&controls=0&showinfo=0'
        '&rel=0&modestbranding=1&playsinline=1&loop=1&playlist=$key&enablejsapi=1';
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

  void _toggleTrailer() {
    setState(() => _showTrailer = !_showTrailer);
  }

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: widget.height,
      child: Stack(
        fit: StackFit.expand,
        children: [
          if (_showTrailer)
            HtmlElementView(viewType: _viewType)
          else if (widget.backdropUrl != null)
            Image.network(widget.backdropUrl!, fit: BoxFit.cover),

          // Gradient overlay at bottom
          const Positioned(
            bottom: 0,
            left: 0,
            right: 0,
            height: 100,
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

          // Controls
          Positioned(
            bottom: 16,
            right: 16,
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                _ControlButton(
                  icon: _showTrailer ? Icons.image_rounded : Icons.play_arrow_rounded,
                  tooltip: _showTrailer ? 'Show poster' : 'Play trailer',
                  onTap: _toggleTrailer,
                ),
                if (_showTrailer) ...[
                  const SizedBox(width: 8),
                  _ControlButton(
                    icon: _isMuted
                        ? Icons.volume_off_rounded
                        : Icons.volume_up_rounded,
                    tooltip: _isMuted ? 'Unmute' : 'Mute',
                    onTap: _toggleMute,
                  ),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _ControlButton extends StatelessWidget {
  final IconData icon;
  final String tooltip;
  final VoidCallback onTap;

  const _ControlButton({
    required this.icon,
    required this.tooltip,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Tooltip(
      message: tooltip,
      child: Material(
        color: Colors.black54,
        shape: const CircleBorder(),
        clipBehavior: Clip.antiAlias,
        child: InkWell(
          onTap: onTap,
          child: Padding(
            padding: const EdgeInsets.all(10),
            child: Icon(icon, color: Colors.white, size: 20),
          ),
        ),
      ),
    );
  }
}
