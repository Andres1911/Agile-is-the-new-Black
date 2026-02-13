class Expense {
  final int? id;
  final double amount;
  final String description;
  final String? category;
  final DateTime date;
  final int? userId;
  final int? householdId;
  final DateTime? createdAt;

  Expense({
    this.id,
    required this.amount,
    required this.description,
    this.category,
    required this.date,
    this.userId,
    this.householdId,
    this.createdAt,
  });

  factory Expense.fromJson(Map<String, dynamic> json) {
    return Expense(
      id: json['id'],
      amount: (json['amount'] as num).toDouble(),
      description: json['description'],
      category: json['category'],
      date: DateTime.parse(json['date']),
      userId: json['user_id'],
      householdId: json['household_id'],
      createdAt: json['created_at'] != null 
          ? DateTime.parse(json['created_at']) 
          : null,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'amount': amount,
      'description': description,
      'category': category,
      'date': date.toIso8601String(),
      'household_id': householdId,
    };
  }
}
