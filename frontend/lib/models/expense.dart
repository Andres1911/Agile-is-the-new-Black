class Expense {
  final int? id;
  final double amount;
  final String description;
  final String? category;
  final DateTime date;
  final int? creatorId;
  final int? householdId;
  final DateTime? createdAt;
  final String? status;

  Expense({
    this.id,
    required this.amount,
    required this.description,
    this.category,
    required this.date,
    this.creatorId,
    this.householdId,
    this.createdAt,
    this.status,
  });

  // optional compatibility getter in case some older code still uses userId
  int? get userId => creatorId;

  factory Expense.fromJson(Map<String, dynamic> json) {
    return Expense(
      id: json['id'] as int?,
      amount: (json['amount'] as num).toDouble(),
      description: json['description'] as String,
      category: json['category'] as String?,
      date: DateTime.parse(json['date'] as String),
      creatorId: json['creator_id'] as int?,
      householdId: json['household_id'] as int?,
      createdAt: json['created_at'] != null
          ? DateTime.parse(json['created_at'] as String)
          : null,
      status: json['status']?.toString(),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'amount': amount,
      'description': description,
      'category': category,
      'date': date.toIso8601String(),
      'household_id': householdId,
      'creator_id': creatorId,
      'status': status,
    };
  }
}