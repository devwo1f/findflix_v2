import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/router/app_router.dart';
import '../../core/theme/app_colors.dart';
import '../../providers/auth_provider.dart';

class SettingsScreen extends ConsumerStatefulWidget {
  const SettingsScreen({super.key});

  @override
  ConsumerState<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends ConsumerState<SettingsScreen> {
  String _region = 'US';
  String _language = 'English';
  bool _notificationsEnabled = true;
  bool _darkMode = true;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final user = ref.watch(currentUserProvider);
    final isAdmin = user.asData?.value?.isAdmin ?? false;

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(title: const Text('Settings')),
      body: ListView(
        padding: const EdgeInsets.symmetric(vertical: 8),
        children: [
          // ── Region ─────────────────────────────────────────────
          _SectionHeader(label: 'Preferences'),
          _SettingsTile(
            icon: Icons.language_rounded,
            title: 'Region',
            subtitle: _region,
            onTap: () => _showRegionPicker(),
          ),
          _SettingsTile(
            icon: Icons.translate_rounded,
            title: 'Language',
            subtitle: _language,
            onTap: () => _showLanguagePicker(),
          ),

          // ── Notifications ──────────────────────────────────────
          _SectionHeader(label: 'Notifications'),
          SwitchListTile(
            secondary:
                const Icon(Icons.notifications_outlined, color: AppColors.textSecondary),
            title: const Text('Push Notifications'),
            subtitle: const Text('New recommendations and updates'),
            value: _notificationsEnabled,
            onChanged: (v) =>
                setState(() => _notificationsEnabled = v),
            activeColor: AppColors.primary,
          ),

          // ── Appearance ─────────────────────────────────────────
          _SectionHeader(label: 'Appearance'),
          SwitchListTile(
            secondary:
                const Icon(Icons.dark_mode_outlined, color: AppColors.textSecondary),
            title: const Text('Dark Mode'),
            subtitle: const Text('Toggle dark / light theme'),
            value: _darkMode,
            onChanged: (v) => setState(() => _darkMode = v),
            activeColor: AppColors.primary,
          ),

          // ── Account ────────────────────────────────────────────
          _SectionHeader(label: 'Account'),
          _SettingsTile(
            icon: Icons.tune_rounded,
            title: 'Retake Questionnaire',
            subtitle: 'Update your taste profile',
            onTap: () => context.push(AppRoutes.onboarding),
          ),
          _SettingsTile(
            icon: Icons.delete_sweep_outlined,
            title: 'Clear Watch History',
            subtitle: 'Remove all watched items',
            onTap: () => _confirmClearHistory(),
            destructive: true,
          ),

          if (isAdmin) ...[
            _SectionHeader(label: 'Admin'),
            _SettingsTile(
              icon: Icons.admin_panel_settings_outlined,
              title: 'Admin Dashboard',
              subtitle: 'System stats and controls',
              onTap: () => context.push(AppRoutes.admin),
            ),
          ],

          // ── About ──────────────────────────────────────────────
          _SectionHeader(label: 'About'),
          _SettingsTile(
            icon: Icons.info_outline_rounded,
            title: 'About FindFlix',
            subtitle: 'Version 1.0.0',
            onTap: () => _showAbout(),
          ),
          _SettingsTile(
            icon: Icons.description_outlined,
            title: 'Terms of Service',
            onTap: () {},
          ),
          _SettingsTile(
            icon: Icons.privacy_tip_outlined,
            title: 'Privacy Policy',
            onTap: () {},
          ),

          const SizedBox(height: 24),

          // ── Logout ─────────────────────────────────────────────
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: OutlinedButton.icon(
              onPressed: () async {
                await ref.read(authServiceProvider).logout();
                if (context.mounted) context.go(AppRoutes.login);
              },
              icon: const Icon(Icons.logout_rounded,
                  color: AppColors.error),
              label: const Text('Log Out',
                  style: TextStyle(color: AppColors.error)),
              style: OutlinedButton.styleFrom(
                side: const BorderSide(color: AppColors.error),
                padding: const EdgeInsets.symmetric(vertical: 14),
              ),
            ),
          ),
          const SizedBox(height: 40),
        ],
      ),
    );
  }

  // ── Dialogs ─────────────────────────────────────────────────────────

  void _showRegionPicker() {
    final regions = ['US', 'UK', 'CA', 'AU', 'DE', 'FR', 'JP', 'IN', 'BR'];
    showModalBottomSheet(
      context: context,
      builder: (_) => ListView(
        shrinkWrap: true,
        children: regions
            .map((r) => ListTile(
                  title: Text(r),
                  trailing: _region == r
                      ? const Icon(Icons.check, color: AppColors.primary)
                      : null,
                  onTap: () {
                    setState(() => _region = r);
                    Navigator.pop(context);
                  },
                ))
            .toList(),
      ),
    );
  }

  void _showLanguagePicker() {
    final languages = [
      'English',
      'Spanish',
      'French',
      'German',
      'Japanese',
      'Portuguese',
      'Hindi'
    ];
    showModalBottomSheet(
      context: context,
      builder: (_) => ListView(
        shrinkWrap: true,
        children: languages
            .map((l) => ListTile(
                  title: Text(l),
                  trailing: _language == l
                      ? const Icon(Icons.check, color: AppColors.primary)
                      : null,
                  onTap: () {
                    setState(() => _language = l);
                    Navigator.pop(context);
                  },
                ))
            .toList(),
      ),
    );
  }

  void _confirmClearHistory() {
    showDialog(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('Clear Watch History?'),
        content: const Text(
            'This will permanently remove all items from your watch history. This cannot be undone.'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () {
              Navigator.pop(context);
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(content: Text('Watch history cleared.')),
              );
            },
            child: const Text('Clear',
                style: TextStyle(color: AppColors.error)),
          ),
        ],
      ),
    );
  }

  void _showAbout() {
    showAboutDialog(
      context: context,
      applicationName: 'FindFlix',
      applicationVersion: '1.0.0',
      applicationIcon: Container(
        width: 48,
        height: 48,
        decoration: BoxDecoration(
          gradient: AppColors.primaryGradient,
          borderRadius: BorderRadius.circular(12),
        ),
        child: const Icon(Icons.movie_filter_rounded,
            color: Colors.white, size: 28),
      ),
      children: [
        const Text(
          'FindFlix is a premium movie and TV recommendation platform '
          'that uses machine learning to find your next favorite.',
        ),
      ],
    );
  }
}

// ── Helpers ───────────────────────────────────────────────────────────

class _SectionHeader extends StatelessWidget {
  final String label;
  const _SectionHeader({required this.label});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 20, 16, 8),
      child: Text(
        label.toUpperCase(),
        style: Theme.of(context).textTheme.labelSmall?.copyWith(
              letterSpacing: 1.2,
              color: AppColors.textTertiary,
            ),
      ),
    );
  }
}

class _SettingsTile extends StatelessWidget {
  final IconData icon;
  final String title;
  final String? subtitle;
  final VoidCallback onTap;
  final bool destructive;

  const _SettingsTile({
    required this.icon,
    required this.title,
    this.subtitle,
    required this.onTap,
    this.destructive = false,
  });

  @override
  Widget build(BuildContext context) {
    final color = destructive ? AppColors.error : AppColors.textSecondary;
    return ListTile(
      leading: Icon(icon, color: color),
      title: Text(title,
          style: TextStyle(
              color: destructive ? AppColors.error : AppColors.textPrimary)),
      subtitle: subtitle != null
          ? Text(subtitle!,
              style: const TextStyle(
                  fontSize: 12, color: AppColors.textTertiary))
          : null,
      trailing: const Icon(Icons.chevron_right_rounded,
          color: AppColors.textTertiary),
      onTap: onTap,
    );
  }
}
