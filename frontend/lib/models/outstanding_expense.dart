class OutstandingExpense {
  final int expenseId;
  final String description;
  final String? category;
  final DateTime date;
  final int householdId;
  final int creatorId;
  final String creatorUsername;
  final double amountTotal;
  final double amountOwed;
  final double paidAmount;
  final double outstandingAmount;

  OutstandingExpense({
    required this.expenseId,
    required this.description,
    required this.category,
    required this.date,
    required this.householdId,
    required this.creatorId,
    required this.creatorUsername,
    required this.amountTotal,
    required this.amountOwed,
    required this.paidAmount,
    required this.outstandingAmount,
  });

  factory OutstandingExpense.fromJson(Map<String, dynamic> json) {
    return OutstandingExpense(
      expenseId: json['expense_id'] as int,
      description: json['description'] as String,
      category: json['category'] as String?,
      date: DateTime.parse(json['date'] as String),
      householdId: json['household_id'] as int,
      creatorId: json['creator_id'] as int,
      creatorUsername: json['creator_username'] as String,
      amountTotal: (json['amount_total'] as num).toDouble(),
      amountOwed: (json['amount_owed'] as num).toDouble(),
      paidAmount: (json['paid_amount'] as num).toDouble(),
      outstandingAmount: (json['outstanding_amount'] as num).toDouble(),
    );
  }
}
