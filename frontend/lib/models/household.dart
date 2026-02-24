class Household {
  final int id;
  final String name;
  final String? description;
  final String? address;
  final String? inviteCode;
  final DateTime createdAt;
  final List<dynamic>? members;

  Household({
    required this.id,
    required this.name,
    this.description,
    this.address,
    this.inviteCode,
    required this.createdAt,
    this.members,
  });

  factory Household.fromJson(Map<String, dynamic> json) {
    return Household(
      id: json['id'],
      name: json['name'],
      description: json['description'],
      address: json['address'],
      inviteCode: json['invite_code'],
      createdAt: DateTime.parse(json['created_at']),
      members: json['members'],
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'name': name,
      'description': description,
      'address': address,
      'invite_code': inviteCode,
      'created_at': createdAt.toIso8601String(),
    };
  }
}
