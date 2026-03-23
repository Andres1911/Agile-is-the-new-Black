class RequestedExpense {
  final int expenseId;
  final String description;
  final String? category;
  final DateTime date;
  final int householdId;
  final int creatorId;
  final String creatorUsername;
  final double amountTotal;
  final double amountRequested;
  final String voteStatus;

  RequestedExpense({
    required this.expenseId,
    required this.description,
    this.category,
    required this.date,
    required this.householdId,
    required this.creatorId,
    required this.creatorUsername,
    required this.amountTotal,
    required this.amountRequested,
    required this.voteStatus,
  });

  factory RequestedExpense.fromJson(Map<String, dynamic> json) {
    return RequestedExpense(
      expenseId: json['expense_id'] as int,
      description: json['description'] as String,
      category: json['category'] as String?,
      date: DateTime.parse(json['date'] as String),
      householdId: json['household_id'] as int,
      creatorId: json['creator_id'] as int,
      creatorUsername: json['creator_username'] as String,
      amountTotal: (json['amount_total'] as num).toDouble(),
      amountRequested: (json['amount_requested'] as num).toDouble(),
      voteStatus: json['vote_status'] as String,
    );
  }
}