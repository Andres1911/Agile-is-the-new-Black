import 'package:flutter/material.dart';

class ExpenseResponseNotificationCard extends StatelessWidget {
  final String title;
  final String message;
  final bool isAccepted;
  final VoidCallback? onDismiss;

  const ExpenseResponseNotificationCard({
    super.key,
    required this.title,
    required this.message,
    required this.isAccepted,
    this.onDismiss,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final icon = isAccepted ? Icons.check_circle_outline : Icons.cancel_outlined;
    final containerColor = isAccepted
        ? theme.colorScheme.primaryContainer
        : theme.colorScheme.errorContainer;
    final foregroundColor = isAccepted
        ? theme.colorScheme.onPrimaryContainer
        : theme.colorScheme.onErrorContainer;

    return Card(
      color: containerColor,
      margin: const EdgeInsets.fromLTRB(16, 16, 16, 8),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(icon, color: foregroundColor),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: theme.textTheme.titleSmall?.copyWith(
                      fontWeight: FontWeight.w700,
                      color: foregroundColor,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    message,
                    style: theme.textTheme.bodyMedium?.copyWith(
                      color: foregroundColor,
                    ),
                  ),
                ],
              ),
            ),
            if (onDismiss != null)
              IconButton(
                onPressed: onDismiss,
                icon: Icon(Icons.close, color: foregroundColor),
                visualDensity: VisualDensity.compact,
              ),
          ],
        ),
      ),
    );
  }
}