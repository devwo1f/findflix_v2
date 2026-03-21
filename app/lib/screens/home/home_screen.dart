import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/router/app_router.dart';
import '../../widgets/bottom_nav_bar.dart';

/// Home shell that holds the bottom nav and hosts child routes.
class HomeScreen extends ConsumerStatefulWidget {
  final Widget child;

  const HomeScreen({super.key, required this.child});

  @override
  ConsumerState<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends ConsumerState<HomeScreen> {
  int _currentIndex = 0;

  static const _routes = [
    AppRoutes.home,
    '/home/search',
    '/home/watchlist',
    '/home/profile',
  ];

  void _onTabTapped(int index) {
    if (index == _currentIndex) return;
    setState(() => _currentIndex = index);
    context.go(_routes[index]);
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _syncIndex();
  }

  void _syncIndex() {
    final location = GoRouterState.of(context).matchedLocation;
    int newIndex = 0;
    if (location.startsWith('/home/search')) {
      newIndex = 1;
    } else if (location.startsWith('/home/watchlist')) {
      newIndex = 2;
    } else if (location.startsWith('/home/profile')) {
      newIndex = 3;
    }
    if (newIndex != _currentIndex) {
      setState(() => _currentIndex = newIndex);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: widget.child,
      bottomNavigationBar: FindFlixBottomNavBar(
        currentIndex: _currentIndex,
        onTap: _onTabTapped,
      ),
    );
  }
}
