import 'package:flutter/material.dart';
import '../models/requested_expense.dart';
import '../services/api_service.dart';

class RequestedExpensesScreen extends StatefulWidget {
  const RequestedExpensesScreen({super.key});

  @override
  State<RequestedExpensesScreen> createState() => _RequestedExpensesScreenState();
}

class _RequestedExpensesScreenState extends State<RequestedExpensesScreen> {
  final ApiService _apiService = ApiService();

  bool _isLoading = false;
  String? _errorMessage;
  List<RequestedExpense> _items = [];

  // Notification banner state
  String? _bannerMessage;
  bool _bannerIsSuccess = true;
  bool _showBanner = false;

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

  Future<void> _respond(int expenseId, String decision) async {
    try {
      final message = await _apiService.respondToExpenseShare(expenseId, decision);
      if (!mounted) return;
      _showNotification(message, isSuccess: true);
      await _load();
    } catch (e) {
      if (!mounted) return;
      _showNotification(
        e.toString().replaceFirst('Exception: ', ''),
        isSuccess: false,
      );
    }
  }

  void _showNotification(String message, {required bool isSuccess}) {
    setState(() {
      _bannerMessage = message;
      _bannerIsSuccess = isSuccess;
      _showBanner = true;
    });
    Future.delayed(const Duration(seconds: 4), () {
      if (!mounted) return;
      if (_bannerMessage == message) {
        setState(() => _showBanner = false);
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Pending Approvals'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _isLoading ? null : _load,
          ),
        ],
      ),
      body: Stack(
        children: [
          // Main content
          _isLoading
              ? const Center(child: CircularProgressIndicator())
              : _errorMessage != null
                  ? _ErrorState(message: _errorMessage!, onRetry: _load)
                  : _items.isEmpty
                      ? const _EmptyState()
                      : ListView.builder(
                          padding: const EdgeInsets.only(top: 8, bottom: 24),
                          itemCount: _items.length,
                          itemBuilder: (context, index) {
                            final item = _items[index];
                            final dateStr =
                                item.date.toLocal().toString().split(' ')[0];
                            return Card(
                              margin: const EdgeInsets.symmetric(
                                horizontal: 16,
                                vertical: 8,
                              ),
                              child: Padding(
                                padding: const EdgeInsets.all(16),
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Row(
                                      children: [
                                        Expanded(
                                          child: Text(
                                            item.description,
                                            style: theme.textTheme.titleMedium
                                                ?.copyWith(
                                              fontWeight: FontWeight.bold,
                                            ),
                                          ),
                                        ),
                                        Container(
                                          padding: const EdgeInsets.symmetric(
                                            horizontal: 10,
                                            vertical: 4,
                                          ),
                                          decoration: BoxDecoration(
                                            color: theme
                                                .colorScheme.primaryContainer,
                                            borderRadius:
                                                BorderRadius.circular(12),
                                          ),
                                          child: Text(
                                            '\$${item.amountRequested.toStringAsFixed(2)}',
                                            style: theme.textTheme.labelLarge
                                                ?.copyWith(
                                              color: theme.colorScheme
                                                  .onPrimaryContainer,
                                              fontWeight: FontWeight.w700,
                                            ),
                                          ),
                                        ),
                                      ],
                                    ),
                                    const SizedBox(height: 6),
                                    Text(
                                      '${item.category ?? 'Uncategorized'} • $dateStr • by ${item.creatorUsername}',
                                      style: theme.textTheme.bodySmall
                                          ?.copyWith(
                                        color: theme
                                            .colorScheme.onSurfaceVariant,
                                      ),
                                    ),
                                    Text(
                                      'Total expense: \$${item.amountTotal.toStringAsFixed(2)}',
                                      style: theme.textTheme.bodySmall
                                          ?.copyWith(
                                        color: theme
                                            .colorScheme.onSurfaceVariant,
                                      ),
                                    ),
                                    const SizedBox(height: 14),
                                    Row(
                                      children: [
                                        Expanded(
                                          child: OutlinedButton.icon(
                                            onPressed: () => _respond(
                                              item.expenseId,
                                              'decline',
                                            ),
                                            icon: const Icon(
                                              Icons.close,
                                              color: Colors.red,
                                            ),
                                            label: const Text(
                                              'Decline',
                                              style: TextStyle(
                                                  color: Colors.red),
                                            ),
                                            style: OutlinedButton.styleFrom(
                                              side: const BorderSide(
                                                  color: Colors.red),
                                            ),
                                          ),
                                        ),
                                        const SizedBox(width: 12),
                                        Expanded(
                                          child: ElevatedButton.icon(
                                            onPressed: () => _respond(
                                              item.expenseId,
                                              'accept',
                                            ),
                                            icon: const Icon(Icons.check),
                                            label: const Text('Accept'),
                                            style: ElevatedButton.styleFrom(
                                              backgroundColor:
                                                  Colors.green.shade600,
                                              foregroundColor: Colors.white,
                                            ),
                                          ),
                                        ),
                                      ],
                                    ),
                                  ],
                                ),
                              ),
                            );
                          },
                        ),

          // Notification banner (matches HomeScreen style)
          IgnorePointer(
            ignoring: !_showBanner,
            child: AnimatedSlide(
              offset: _showBanner ? Offset.zero : const Offset(0, -1),
              duration: const Duration(milliseconds: 300),
              curve: Curves.easeInOutCubic,
              child: AnimatedOpacity(
                opacity: _showBanner ? 1 : 0,
                duration: const Duration(milliseconds: 300),
                child: SafeArea(
                  child: Align(
                    alignment: Alignment.topCenter,
                    child: Padding(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 16, vertical: 8),
                      child: ConstrainedBox(
                        constraints: const BoxConstraints(maxWidth: 420),
                        child: Material(
                          color: _bannerIsSuccess
                              ? Colors.green.shade600
                              : theme.colorScheme.errorContainer,
                          elevation: 6,
                          borderRadius: BorderRadius.circular(16),
                          child: Padding(
                            padding: const EdgeInsets.symmetric(
                              horizontal: 16,
                              vertical: 14,
                            ),
                            child: Row(
                              children: [
                                Icon(
                                  _bannerIsSuccess
                                      ? Icons.check_circle_outline_rounded
                                      : Icons.error_outline_rounded,
                                  color: _bannerIsSuccess
                                      ? Colors.white
                                      : theme.colorScheme.onErrorContainer,
                                ),
                                const SizedBox(width: 12),
                                Expanded(
                                  child: Text(
                                    _bannerMessage ?? '',
                                    style: TextStyle(
                                      color: _bannerIsSuccess
                                          ? Colors.white
                                          : theme
                                              .colorScheme.onErrorContainer,
                                      fontWeight: FontWeight.w500,
                                    ),
                                  ),
                                ),
                                IconButton(
                                  visualDensity: VisualDensity.compact,
                                  icon: Icon(
                                    Icons.close,
                                    color: _bannerIsSuccess
                                        ? Colors.white
                                        : theme.colorScheme.onErrorContainer,
                                  ),
                                  onPressed: () => setState(
                                      () => _showBanner = false),
                                ),
                              ],
                            ),
                          ),
                        ),
                      ),
                    ),
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
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
            Icon(Icons.check_circle_outline,
                size: 72, color: theme.colorScheme.primary),
            const SizedBox(height: 16),
            Text(
              'No pending approvals',
              style: theme.textTheme.headlineSmall
                  ?.copyWith(fontWeight: FontWeight.bold),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 8),
            Text(
              'You have no expense shares awaiting your response.',
              style: theme.textTheme.bodyMedium?.copyWith(
                  color: theme.colorScheme.onSurfaceVariant),
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
            Icon(Icons.error_outline, size: 72, color: theme.colorScheme.error),
            const SizedBox(height: 16),
            Text(
              'Could not load pending approvals',
              style: theme.textTheme.titleLarge
                  ?.copyWith(fontWeight: FontWeight.bold),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 8),
            Text(
              message,
              style: theme.textTheme.bodySmall?.copyWith(
                  color: theme.colorScheme.onSurfaceVariant),
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