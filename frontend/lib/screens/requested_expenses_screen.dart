
import 'package:flutter/material.dart';
import '../models/requested_expense.dart';
import '../services/api_service.dart';

class RequestedExpensesScreen extends StatefulWidget {
  const RequestedExpensesScreen({super.key});

  @override
  State<RequestedExpensesScreen> createState() =>
      _RequestedExpensesScreenState();
}

class _RequestedExpensesScreenState extends State<RequestedExpensesScreen> {
  final ApiService _apiService = ApiService();

  bool _isLoading = false;
  String? _errorMessage;
  List<RequestedExpense> _allItems = [];
  String _selectedFilter = 'PENDING';

  // Notification banner state
  String? _bannerMessage;
  bool _bannerIsSuccess = true;
  bool _showBanner = false;

  List<RequestedExpense> get _filteredItems =>
      _allItems.where((e) => e.voteStatus == _selectedFilter).toList();

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
        _allItems = items;
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
      final message =
          await _apiService.respondToExpenseShare(expenseId, decision);
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
        title: const Text('My Expense Shares'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _isLoading ? null : _load,
          ),
        ],
      ),
      body: Stack(
        children: [
          Column(
            children: [
              // Filter bar
              Padding(
                padding:
                    const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                child: Row(
                  children: [
                    _FilterChip(
                      label: 'Pending',
                      selected: _selectedFilter == 'PENDING',
                      color: Colors.orange,
                      onTap: () =>
                          setState(() => _selectedFilter = 'PENDING'),
                    ),
                    const SizedBox(width: 8),
                    _FilterChip(
                      label: 'Accepted',
                      selected: _selectedFilter == 'ACCEPTED',
                      color: Colors.green,
                      onTap: () =>
                          setState(() => _selectedFilter = 'ACCEPTED'),
                    ),
                    const SizedBox(width: 8),
                    _FilterChip(
                      label: 'Rejected',
                      selected: _selectedFilter == 'REJECTED',
                      color: Colors.red,
                      onTap: () =>
                          setState(() => _selectedFilter = 'REJECTED'),
                    ),
                  ],
                ),
              ),
              const Divider(height: 1),
              // Content
              Expanded(
                child: _isLoading
                    ? const Center(child: CircularProgressIndicator())
                    : _errorMessage != null
                        ? _ErrorState(
                            message: _errorMessage!, onRetry: _load)
                        : _filteredItems.isEmpty
                            ? _EmptyState(filter: _selectedFilter)
                            : ListView.builder(
                                padding: const EdgeInsets.only(
                                    top: 8, bottom: 24),
                                itemCount: _filteredItems.length,
                                itemBuilder: (context, index) {
                                  final item = _filteredItems[index];
                                  final dateStr = item.date
                                      .toLocal()
                                      .toString()
                                      .split(' ')[0];
                                  return Card(
                                    margin: const EdgeInsets.symmetric(
                                      horizontal: 16,
                                      vertical: 8,
                                    ),
                                    child: Padding(
                                      padding: const EdgeInsets.all(16),
                                      child: Column(
                                        crossAxisAlignment:
                                            CrossAxisAlignment.start,
                                        children: [
                                          Row(
                                            children: [
                                              Expanded(
                                                child: Text(
                                                  item.description,
                                                  style: theme
                                                      .textTheme.titleMedium
                                                      ?.copyWith(
                                                    fontWeight:
                                                        FontWeight.bold,
                                                  ),
                                                ),
                                              ),
                                              Container(
                                                padding:
                                                    const EdgeInsets.symmetric(
                                                  horizontal: 10,
                                                  vertical: 4,
                                                ),
                                                decoration: BoxDecoration(
                                                  color: theme.colorScheme
                                                      .primaryContainer,
                                                  borderRadius:
                                                      BorderRadius.circular(
                                                          12),
                                                ),
                                                child: Text(
                                                  '\$${item.amountRequested.toStringAsFixed(2)}',
                                                  style: theme
                                                      .textTheme.labelLarge
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
                                              color: theme.colorScheme
                                                  .onSurfaceVariant,
                                            ),
                                          ),
                                          Text(
                                            'Total expense: \$${item.amountTotal.toStringAsFixed(2)}',
                                            style: theme.textTheme.bodySmall
                                                ?.copyWith(
                                              color: theme.colorScheme
                                                  .onSurfaceVariant,
                                            ),
                                          ),
                                          // Only show buttons for PENDING
                                          if (_selectedFilter == 'PENDING') ...[
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
                                                    style: OutlinedButton
                                                        .styleFrom(
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
                                                    icon: const Icon(
                                                        Icons.check),
                                                    label: const Text(
                                                        'Accept'),
                                                    style: ElevatedButton
                                                        .styleFrom(
                                                      backgroundColor:
                                                          Colors.green.shade600,
                                                      foregroundColor:
                                                          Colors.white,
                                                    ),
                                                  ),
                                                ),
                                              ],
                                            ),
                                          ],
                                          // Show status badge for accepted/rejected
                                          if (_selectedFilter != 'PENDING') ...[
                                            const SizedBox(height: 10),
                                            Container(
                                              padding:
                                                  const EdgeInsets.symmetric(
                                                horizontal: 10,
                                                vertical: 4,
                                              ),
                                              decoration: BoxDecoration(
                                                color: _selectedFilter ==
                                                        'ACCEPTED'
                                                    ? Colors.green.shade50
                                                    : Colors.red.shade50,
                                                borderRadius:
                                                    BorderRadius.circular(8),
                                              ),
                                              child: Text(
                                                _selectedFilter == 'ACCEPTED'
                                                    ? 'You accepted this expense'
                                                    : 'You declined this expense',
                                                style: TextStyle(
                                                  color: _selectedFilter ==
                                                          'ACCEPTED'
                                                      ? Colors.green.shade700
                                                      : Colors.red.shade700,
                                                  fontSize: 12,
                                                  fontWeight: FontWeight.w500,
                                                ),
                                              ),
                                            ),
                                          ],
                                        ],
                                      ),
                                    ),
                                  );
                                },
                              ),
              ),
            ],
          ),

          // Notification banner
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
                              : Theme.of(context).colorScheme.errorContainer,
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
                                      : Theme.of(context)
                                          .colorScheme
                                          .onErrorContainer,
                                ),
                                const SizedBox(width: 12),
                                Expanded(
                                  child: Text(
                                    _bannerMessage ?? '',
                                    style: TextStyle(
                                      color: _bannerIsSuccess
                                          ? Colors.white
                                          : Theme.of(context)
                                              .colorScheme
                                              .onErrorContainer,
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
                                        : Theme.of(context)
                                            .colorScheme
                                            .onErrorContainer,
                                  ),
                                  onPressed: () =>
                                      setState(() => _showBanner = false),
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

// ── Filter chip widget ────────────────────────────────────────────────────────

class _FilterChip extends StatelessWidget {
  final String label;
  final bool selected;
  final Color color;
  final VoidCallback onTap;

  const _FilterChip({
    required this.label,
    required this.selected,
    required this.color,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        padding:
            const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        decoration: BoxDecoration(
          color: selected ? color : Colors.transparent,
          border: Border.all(color: color),
          borderRadius: BorderRadius.circular(20),
        ),
        child: Text(
          label,
          style: TextStyle(
            color: selected ? Colors.white : color,
            fontWeight: FontWeight.w600,
            fontSize: 13,
          ),
        ),
      ),
    );
  }
}

// ── Empty state ───────────────────────────────────────────────────────────────

class _EmptyState extends StatelessWidget {
  final String filter;
  const _EmptyState({required this.filter});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final message = filter == 'PENDING'
        ? 'No pending approvals'
        : filter == 'ACCEPTED'
            ? 'No accepted expenses yet'
            : 'No declined expenses yet';
    final sub = filter == 'PENDING'
        ? 'You have no expense shares awaiting your response.'
        : filter == 'ACCEPTED'
            ? 'Expenses you accept will appear here.'
            : 'Expenses you decline will appear here.';

    return Center(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 24),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              filter == 'PENDING'
                  ? Icons.check_circle_outline
                  : filter == 'ACCEPTED'
                      ? Icons.thumb_up_outlined
                      : Icons.thumb_down_outlined,
              size: 72,
              color: theme.colorScheme.primary,
            ),
            const SizedBox(height: 16),
            Text(
              message,
              style: theme.textTheme.headlineSmall
                  ?.copyWith(fontWeight: FontWeight.bold),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 8),
            Text(
              sub,
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

// ── Error state ───────────────────────────────────────────────────────────────

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
            Icon(Icons.error_outline,
                size: 72, color: theme.colorScheme.error),
            const SizedBox(height: 16),
            Text(
              'Could not load expenses',
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
