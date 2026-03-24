import 'package:flutter/material.dart';

import '../models/requested_expense.dart';
import '../services/api_service.dart';
import '../widgets/expense_response_notification_card.dart';

class RequestedExpensesScreen extends StatefulWidget {
  const RequestedExpensesScreen({super.key});

  @override
  State<RequestedExpensesScreen> createState() => _RequestedExpensesScreenState();
}

class _RequestedExpensesScreenState extends State<RequestedExpensesScreen> {
  final ApiService _apiService = ApiService();

  bool _isLoading = false;
  bool _hasUpdates = false;
  String? _errorMessage;
  List<RequestedExpense> _items = [];
  final Set<int> _processingIds = <int>{};
  _NotificationState? _notification;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final raw = await _apiService.getRequestedExpenses();
      final items = raw
          .map((e) => RequestedExpense.fromJson(e as Map<String, dynamic>))
          .toList();

      if (!mounted) return;
      setState(() {
        _items = items;
        _isLoading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _errorMessage = e.toString();
        _isLoading = false;
      });
    }
  }

  Future<void> _respondToShare(RequestedExpense item, String decision) async {
    setState(() {
      _processingIds.add(item.expenseId);
      _errorMessage = null;
    });

    try {
      await _apiService.respondToExpenseShare(item.expenseId, decision);

      if (!mounted) return;
      final isAccepted = decision == 'accept';
      setState(() {
        _hasUpdates = true;
        _processingIds.remove(item.expenseId);
        _items.removeWhere((expense) => expense.expenseId == item.expenseId);
        _notification = _NotificationState(
          isAccepted: isAccepted,
          title: isAccepted ? 'Share accepted' : 'Share declined',
          message:
              'The response for "${item.description}" was recorded. The expense issuer and household admin can review the updated expense status in the app.',
        );
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _processingIds.remove(item.expenseId);
        _errorMessage = e.toString();
      });
    }
  }

  Future<bool> _handleBack() async {
    Navigator.pop(context, _hasUpdates);
    return false;
  }

  @override
  Widget build(BuildContext context) {
    return WillPopScope(
      onWillPop: _handleBack,
      child: Scaffold(
        appBar: AppBar(
          leading: IconButton(
            icon: const Icon(Icons.arrow_back),
            onPressed: () => Navigator.pop(context, _hasUpdates),
          ),
          title: const Text('Requested Expenses'),
          actions: [
            IconButton(
              icon: const Icon(Icons.refresh),
              onPressed: _isLoading ? null : _load,
            ),
          ],
        ),
        body: Column(
          children: [
            if (_notification != null)
              ExpenseResponseNotificationCard(
                title: _notification!.title,
                message: _notification!.message,
                isAccepted: _notification!.isAccepted,
                onDismiss: () {
                  setState(() {
                    _notification = null;
                  });
                },
              ),
            Expanded(child: _buildBody()),
          ],
        ),
      ),
    );
  }

  Widget _buildBody() {
    if (_isLoading) {
      return const Center(child: CircularProgressIndicator());
    }

    if (_errorMessage != null) {
      return _ErrorState(
        message: _errorMessage!,
        onRetry: _load,
      );
    }

    if (_items.isEmpty) {
      return const _EmptyState();
    }

    final theme = Theme.of(context);

    return ListView.builder(
      itemCount: _items.length,
      itemBuilder: (context, index) {
        final item = _items[index];
        final dateStr = item.date.toLocal().toString().split(' ')[0];
        final isBusy = _processingIds.contains(item.expenseId);

        return Card(
          margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    CircleAvatar(
                      radius: 24,
                      backgroundColor: theme.colorScheme.primaryContainer,
                      child: Text(
                        '\$${item.amountRequested.toStringAsFixed(0)}',
                        style: theme.textTheme.labelLarge?.copyWith(
                          color: theme.colorScheme.onPrimaryContainer,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            item.description,
                            style: theme.textTheme.titleMedium?.copyWith(
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            '${item.category ?? 'Uncategorized'} • $dateStr • by ${item.creatorUsername}',
                            style: theme.textTheme.bodyMedium?.copyWith(
                              color: theme.colorScheme.onSurfaceVariant,
                            ),
                          ),
                        ],
                      ),
                    ),
                    Chip(
                      label: const Text('Pending'),
                      avatar: const Icon(Icons.hourglass_top, size: 18),
                      visualDensity: VisualDensity.compact,
                    ),
                  ],
                ),
                const SizedBox(height: 16),
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: theme.colorScheme.surfaceContainerHighest,
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Your share: \$${item.amountRequested.toStringAsFixed(2)}',
                        style: theme.textTheme.titleSmall?.copyWith(
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        'Total expense: \$${item.amountTotal.toStringAsFixed(2)}',
                        style: theme.textTheme.bodyMedium,
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 16),
                Row(
                  children: [
                    Expanded(
                      child: OutlinedButton.icon(
                        onPressed: isBusy
                            ? null
                            : () => _respondToShare(item, 'decline'),
                        icon: isBusy
                            ? const SizedBox(
                                width: 16,
                                height: 16,
                                child: CircularProgressIndicator(
                                  strokeWidth: 2,
                                ),
                              )
                            : const Icon(Icons.close),
                        label: const Text('Decline'),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: ElevatedButton.icon(
                        onPressed: isBusy
                            ? null
                            : () => _respondToShare(item, 'accept'),
                        icon: isBusy
                            ? const SizedBox(
                                width: 16,
                                height: 16,
                                child: CircularProgressIndicator(
                                  strokeWidth: 2,
                                  color: Colors.white,
                                ),
                              )
                            : const Icon(Icons.check),
                        label: const Text('Accept'),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        );
      },
    );
  }
}

class _NotificationState {
  final bool isAccepted;
  final String title;
  final String message;

  const _NotificationState({
    required this.isAccepted,
    required this.title,
    required this.message,
  });
}

class _EmptyState extends StatelessWidget {
  const _EmptyState();

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Center(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 24),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.inbox_outlined,
              size: 72,
              color: theme.colorScheme.primary,
            ),
            const SizedBox(height: 16),
            Text(
              'No requested expenses',
              style: theme.textTheme.headlineSmall?.copyWith(
                fontWeight: FontWeight.bold,
              ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 8),
            Text(
              'You do not have any pending expense shares to review right now.',
              style: theme.textTheme.bodyMedium?.copyWith(
                color: theme.colorScheme.onSurfaceVariant,
              ),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }
}

class _ErrorState extends StatelessWidget {
  final String message;
  final VoidCallback onRetry;

  const _ErrorState({required this.message, required this.onRetry});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Center(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 24),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.error_outline,
              size: 72,
              color: theme.colorScheme.error,
            ),
            const SizedBox(height: 16),
            Text(
              'Could not load requested expenses',
              style: theme.textTheme.titleLarge?.copyWith(
                fontWeight: FontWeight.bold,
              ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 8),
            Text(
              message,
              style: theme.textTheme.bodySmall?.copyWith(
                color: theme.colorScheme.onSurfaceVariant,
              ),
              textAlign: TextAlign.center,
              maxLines: 4,
              overflow: TextOverflow.ellipsis,
            ),
            const SizedBox(height: 16),
            ElevatedButton.icon(
              onPressed: onRetry,
              icon: const Icon(Icons.refresh),
              label: const Text('Retry'),
            ),
          ],
        ),
      ),
    );
  }
}