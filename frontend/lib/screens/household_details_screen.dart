import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../models/household.dart';
import '../models/user.dart';
import '../services/api_service.dart';

class HouseholdDetailsScreen extends StatefulWidget {
  final Household household;
  final User currentUser;

  const HouseholdDetailsScreen({
    super.key,
    required this.household,
    required this.currentUser,
  });

  @override
  State<HouseholdDetailsScreen> createState() => _HouseholdDetailsScreenState();
}

class _HouseholdDetailsScreenState extends State<HouseholdDetailsScreen> {
  final ApiService _apiService = ApiService();
  bool _isLoadingMembers = true;
  List<dynamic> _activeMembers = [];

  @override
  void initState() {
    super.initState();
    _fetchMembers();
  }

  Future<void> _fetchMembers() async {
    try {
      final members = await _apiService.getActiveHouseholdMembers();
      print("DEBUG: Received members from API: $members"); 
      
      setState(() {
        _activeMembers = members;
        _isLoadingMembers = false;
      });
    } catch (e) {
      print("DEBUG: API Error: $e");
      setState(() => _isLoadingMembers = false);
    }
  }

  Future<void> _handleLeave() async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Leave Household?'),
        content: const Text('Are you sure? You cannot leave if you have outstanding debts.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Cancel')),
          TextButton(
            onPressed: () => Navigator.pop(context, true),
            style: TextButton.styleFrom(foregroundColor: Colors.red),
            child: const Text('Leave'),
          ),
        ],
      ),
    );

    if (confirm != true) return;

    try {
      // Calling the POST /{id}/leave endpoint from your backend
      await _apiService.leaveHousehold(widget.household.id);
      if (!mounted) return;
      Navigator.pop(context, true); // Return true to trigger refresh on Home
    } catch (e) {
      _showError(e.toString());
    }
  }

  void _showError(String message) {
    String displayMessage = message;
    // Handle the specific business logic error from households.py
    if (message.contains('outstanding debt')) {
      displayMessage = 'You cannot leave yet. Please settle your outstanding debts first.';
    }

    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Action Blocked'),
        content: Text(displayMessage),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context), child: const Text('OK'))
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Scaffold(
      appBar: AppBar(title: const Text('Manage Household')),
      body: RefreshIndicator(
        onRefresh: _fetchMembers,
        child: ListView(
          padding: const EdgeInsets.all(24),
          children: [
            // Household Identity Card
            Center(
              child: Column(
                children: [
                  CircleAvatar(
                    radius: 40,
                    backgroundColor: theme.colorScheme.primaryContainer,
                    child: Icon(Icons.home_work_rounded, size: 40, color: theme.colorScheme.primary),
                  ),
                  const SizedBox(height: 16),
                  Text(widget.household.name, style: theme.textTheme.headlineMedium),
                  if (widget.household.address != null)
                    Text(widget.household.address!, style: theme.textTheme.bodyMedium),
                ],
              ),
            ),
            const SizedBox(height: 32),

            // Invite Code Section (Logical for sharing)
            Text('Invite Code', style: theme.textTheme.labelLarge),
            const SizedBox(height: 8),
            Card(
              elevation: 0,
              color: theme.colorScheme.surfaceVariant.withOpacity(0.3),
              child: ListTile(
                title: Text(widget.household.inviteCode ?? '---',
                    style: const TextStyle(fontWeight: FontWeight.bold, letterSpacing: 2)),
                trailing: IconButton(
                  icon: const Icon(Icons.copy),
                  onPressed: () {
                    Clipboard.setData(ClipboardData(text: widget.household.inviteCode ?? ''));
                    ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Code copied!')));
                  },
                ),
              ),
            ),

            const SizedBox(height: 32),

            // Roommates Section
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text('Roommates', style: theme.textTheme.titleMedium),
                if (_isLoadingMembers) const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2)),
              ],
            ),
            const SizedBox(height: 8),
            ..._activeMembers.map((member) {
              final String username = member['username'] ?? 'User';
              final String fullName = member['full_name'] ?? '';
              final int userId = member['id'] ?? -1;

              return ListTile(
                contentPadding: EdgeInsets.zero,
                leading: CircleAvatar(
                  backgroundColor: theme.colorScheme.primaryContainer,
                  child: Text(username[0].toUpperCase()),
                ),
                title: Text(username, style: const TextStyle(fontWeight: FontWeight.w600)),
                subtitle: Text(fullName.isNotEmpty ? fullName : 'Member'),
                trailing: userId == widget.currentUser.id 
                  ? const Badge(label: Text('You'), backgroundColor: Colors.grey)
                  : null,
              );
            }),

            const SizedBox(height: 48),

            // Danger Zone
            const Divider(),
            const SizedBox(height: 16),
            ElevatedButton.icon(
              onPressed: _handleLeave,
              icon: const Icon(Icons.logout),
              label: const Text('Leave Household'),
              style: ElevatedButton.styleFrom(
                backgroundColor: theme.colorScheme.errorContainer,
                foregroundColor: theme.colorScheme.error,
              ),
            ),
          ],
        ),
      ),
    );
  }
}