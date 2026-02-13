class Household {
  final int id;
  final String name;
  final String? description;
  final DateTime createdAt;
  final int createdBy;
  final List<dynamic>? members;

  Household({
    required this.id,
    required this.name,
    this.description,
    required this.createdAt,
    required this.createdBy,
    this.members,
  });

  factory Household.fromJson(Map<String, dynamic> json) {
    return Household(
      id: json['id'],
      name: json['name'],
      description: json['description'],
      createdAt: DateTime.parse(json['created_at']),
      createdBy: json['created_by'],
      members: json['members'],
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'name': name,
      'description': description,
      'created_at': createdAt.toIso8601String(),
      'created_by': createdBy,
    };
  }
}
