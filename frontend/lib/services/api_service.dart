import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';
import 'package:http/http.dart' as http;
import 'package:http_parser/http_parser.dart';
import 'package:mime/mime.dart';
import 'package:shared_preferences/shared_preferences.dart';

class ApiService {
  // Change this to your backend URL in production
  static const String baseUrl = 'http://localhost:8000/api/v1';

  String? _token;

  Future<void> _loadToken() async {
    final prefs = await SharedPreferences.getInstance();
    _token = prefs.getString('auth_token');
  }

  Future<void> _saveToken(String token) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('auth_token', token);
    _token = token;
  }

  Future<void> clearToken() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('auth_token');
    _token = null;
  }

  Map<String, String> _getHeaders() {
    final headers = <String, String>{
      'Content-Type': 'application/json',
    };

    if (_token != null) {
      headers['Authorization'] = 'Bearer $_token';
    }

    return headers;
  }

  // Auth endpoints
  Future<Map<String, dynamic>> register(
    String email,
    String username,
    String password,
    String? fullName,
  ) async {
    await _loadToken();

    final response = await http.post(
      Uri.parse('$baseUrl/auth/register'),
      headers: _getHeaders(),
      body: jsonEncode({
        'email': email,
        'username': username,
        'password': password,
        'full_name': fullName,
      }),
    );

    if (response.statusCode == 200) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    } else {
      throw Exception('Failed to register: ${response.body}');
    }
  }

  Future<String> login(String username, String password) async {
    final response = await http.post(
      Uri.parse('$baseUrl/auth/login'),
      headers: {'Content-Type': 'application/x-www-form-urlencoded'},
      body: {
        'username': username,
        'password': password,
      },
    );

    if (response.statusCode == 200) {
      final data = jsonDecode(response.body) as Map<String, dynamic>;
      final token = data['access_token'] as String;
      await _saveToken(token);
      return token;
    } else {
      throw Exception('Failed to login: ${response.body}');
    }
  }

  Future<Map<String, dynamic>> getCurrentUser() async {
    await _loadToken();

    final response = await http.get(
      Uri.parse('$baseUrl/auth/me'),
      headers: _getHeaders(),
    );

    if (response.statusCode == 200) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    } else {
      throw Exception('Failed to get user: ${response.body}');
    }
  }

  // Expense endpoints
  Future<List<dynamic>> getExpenses() async {
    await _loadToken();

    final response = await http.get(
      Uri.parse('$baseUrl/expenses/'),
      headers: _getHeaders(),
    );

    if (response.statusCode == 200) {
      return jsonDecode(response.body) as List<dynamic>;
    } else {
      throw Exception('Failed to get expenses: ${response.body}');
    }
  }

  Future<Map<String, dynamic>> createExpense(
    Map<String, dynamic> expense,
  ) async {
    await _loadToken();

    final response = await http.post(
      Uri.parse('$baseUrl/expenses/'),
      headers: _getHeaders(),
      body: jsonEncode(expense),
    );

    if (response.statusCode == 201) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    } else {
      throw Exception('Failed to create expense: ${response.body}');
    }
  }

  Future<Map<String, dynamic>> updateExpense(
    int id,
    Map<String, dynamic> expense,
  ) async {
    await _loadToken();

    final response = await http.put(
      Uri.parse('$baseUrl/expenses/$id'),
      headers: _getHeaders(),
      body: jsonEncode(expense),
    );

    if (response.statusCode == 200) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    } else {
      throw Exception('Failed to update expense: ${response.body}');
    }
  }

  Future<void> deleteExpense(int id) async {
    await _loadToken();

    final response = await http.delete(
      Uri.parse('$baseUrl/expenses/$id'),
      headers: _getHeaders(),
    );

    if (response.statusCode != 204) {
      throw Exception('Failed to delete expense: ${response.body}');
    }
  }

  Future<List<dynamic>> getHouseholdExpenses(int householdId) async {
    await _loadToken();

    final response = await http.get(
      Uri.parse('$baseUrl/households/$householdId/expenses'),
      headers: _getHeaders(),
    );

    if (response.statusCode == 200) {
      return jsonDecode(response.body) as List<dynamic>;
    } else {
      throw Exception('Failed to get household expenses: ${response.body}');
    }
  }

  Future<void> createAndSplitExpense(Map<String, dynamic> data) async {
    await _loadToken();

    final response = await http.post(
      Uri.parse('$baseUrl/expenses/create-and-split'),
      headers: _getHeaders(),
      body: jsonEncode(data),
    );

    if (response.statusCode != 201) {
      final error = jsonDecode(response.body);
      throw Exception(error['detail'] ?? 'Failed to create expense');
    }
  }

  Future<Map<String, dynamic>> createRecurringExpense(
    Map<String, dynamic> data,
  ) async {
    await _loadToken();

    final response = await http.post(
      Uri.parse('$baseUrl/expenses/recurring'),
      headers: _getHeaders(),
      body: jsonEncode(data),
    );

    final decoded = jsonDecode(response.body);
    if (response.statusCode != 201) {
      if (decoded is Map<String, dynamic>) {
        throw Exception(decoded['detail'] ?? 'Failed to create recurring expense');
      }
      throw Exception('Failed to create recurring expense');
    }

    return decoded as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> fetchActiveMembers() async {
    await _loadToken();

    final response = await http.get(
      Uri.parse('$baseUrl/households/me/active-household-members'),
      headers: _getHeaders(),
    );

    if (response.statusCode == 200) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    } else {
      throw Exception('Failed to load members: ${response.body}');
    }
  }

  Future<void> payExpenseShare(int expenseId, double amount) async {
    await _loadToken();

    if (_token == null) {
      throw Exception('User not authenticated. Please log in again.');
    }

    final response = await http.post(
      Uri.parse('$baseUrl/expenses/$expenseId/confirm-payment'),
      headers: _getHeaders(),
      body: jsonEncode({'amount': amount}),
    );

    if (response.statusCode != 200) {
      throw Exception('Failed to process payment: ${response.body}');
    }
  }

  Future<List<dynamic>> getOutstandingExpenses() async {
    await _loadToken();

    final response = await http.get(
      Uri.parse('$baseUrl/expenses/outstanding'),
      headers: _getHeaders(),
    );

    if (response.statusCode == 200) {
      return jsonDecode(response.body) as List<dynamic>;
    } else {
      throw Exception('Failed to load outstanding expenses: ${response.body}');
    }
  }

  Future<Map<String, dynamic>> simplifyDebts(String householdName) async {
    await _loadToken();

    final response = await http.post(
      Uri.parse('$baseUrl/households/$householdName/debts/simplify'),
      headers: _getHeaders(),
    );

    if (response.statusCode == 200) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    } else {
      final error = jsonDecode(response.body);
      throw Exception(error['detail'] ?? 'Failed to simplify debts');
    }
  }

  // Household endpoints
  Future<Map<String, dynamic>?> getMyHousehold() async {
    await _loadToken();

    final response = await http.get(
      Uri.parse('$baseUrl/households/me'),
      headers: _getHeaders(),
    );

    if (response.statusCode == 200) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    } else if (response.statusCode == 404) {
      return null;
    } else {
      throw Exception('Failed to get household: ${response.body}');
    }
  }

  Future<Map<String, dynamic>> createHousehold(
    Map<String, dynamic> household,
  ) async {
    await _loadToken();

    final response = await http.post(
      Uri.parse('$baseUrl/households/'),
      headers: _getHeaders(),
      body: jsonEncode(household),
    );

    if (response.statusCode == 201) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    } else {
      try {
        final error = jsonDecode(response.body);
        String message = 'Failed to create household';

        if (error is Map<String, dynamic>) {
          final detail = error['detail'];

          if (detail is String && detail.isNotEmpty) {
            message = detail;
          } else if (detail is List && detail.isNotEmpty) {
            final first = detail.first;
            if (first is Map<String, dynamic> &&
                first['msg'] is String &&
                (first['msg'] as String).isNotEmpty) {
              message = first['msg'] as String;
            } else {
              message = jsonEncode(detail);
            }
          }
        } else if (error is List && error.isNotEmpty) {
          final first = error.first;
          if (first is Map<String, dynamic> &&
              first['msg'] is String &&
              (first['msg'] as String).isNotEmpty) {
            message = first['msg'] as String;
          } else {
            message = jsonEncode(error);
          }
        }

        if (message == 'Failed to create household' &&
            response.body.isNotEmpty) {
          message = 'Failed to create household: ${response.body}';
        }

        throw Exception(message);
      } on FormatException {
        throw Exception('Failed to create household');
      }
    }
  }

  Future<Map<String, dynamic>> getHousehold(int id) async {
    await _loadToken();

    final response = await http.get(
      Uri.parse('$baseUrl/households/$id'),
      headers: _getHeaders(),
    );

    if (response.statusCode == 200) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    } else {
      throw Exception('Failed to get household: ${response.body}');
    }
  }

  Future<Map<String, dynamic>> addMemberToHousehold(
    int householdId,
    int userId,
  ) async {
    await _loadToken();

    final response = await http.post(
      Uri.parse('$baseUrl/households/$householdId/members/$userId'),
      headers: _getHeaders(),
    );

    if (response.statusCode == 200) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    } else {
      throw Exception('Failed to add member: ${response.body}');
    }
  }

  Future<Map<String, dynamic>> removeMemberFromHousehold(
    int householdId,
    int userId,
  ) async {
    await _loadToken();

    final response = await http.delete(
      Uri.parse('$baseUrl/households/$householdId/members/$userId'),
      headers: _getHeaders(),
    );

    if (response.statusCode == 200) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    } else {
      throw Exception('Failed to remove member: ${response.body}');
    }
  }

  Future<Map<String, dynamic>> scanReceipt(File imageFile) async {
    final bytes = await imageFile.readAsBytes();
    final filename = imageFile.path.split('/').last;
    return scanReceiptBytes(bytes, filename);
  }

  Future<Map<String, dynamic>> scanReceiptBytes(
      Uint8List bytes, String filename) async {
    await _loadToken();

    final uri = Uri.parse('$baseUrl/expenses/scan-receipt');
    final request = http.MultipartRequest('POST', uri);

    if (_token != null) {
      request.headers['Authorization'] = 'Bearer $_token';
    }

    final mimeType = lookupMimeType(filename) ?? 'image/jpeg';

    request.files.add(
      http.MultipartFile.fromBytes(
        'file',
        bytes,
        filename: filename,
        contentType: MediaType.parse(mimeType),
      ),
    );

    final streamed = await request.send();
    final body = await streamed.stream.bytesToString();

    if (streamed.statusCode == 200) {
      return jsonDecode(body) as Map<String, dynamic>;
    } else {
      final error = jsonDecode(body);
      throw Exception(error['detail'] ?? 'Failed to scan receipt');
    }
  }

  Future<List<dynamic>> getRequestedExpenses() async {
    await _loadToken();
    final response = await http.get(
      Uri.parse('$baseUrl/expenses/requested'),
      headers: _getHeaders(),
    );

    if (response.statusCode == 200) {
      return jsonDecode(response.body) as List<dynamic>;
    } else {
      throw Exception('Failed to load requested expenses: ${response.body}');
    }
  }

  Future<String> respondToExpenseShare(int expenseId, String decision) async {
    await _loadToken();
    final response = await http.post(
      Uri.parse('$baseUrl/expenses/$expenseId/respond-share'),
      headers: _getHeaders(),
      body: jsonEncode({'decision': decision}),
    );

    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      return data['detail'] as String;
    } else {
      final error = jsonDecode(response.body);
      throw Exception(error['detail'] ?? 'Failed to respond to expense share');
    }
  }

  Future<List<dynamic>> getActiveHouseholdMembers() async {
    await _loadToken();
    final response = await http.get(
      Uri.parse('$baseUrl/households/me/active-household-members'),
      headers: _getHeaders(),
    );
    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      return (data['members'] as List<dynamic>? ?? []);
    }
    throw Exception('Failed to load members');
  }

  Future<void> leaveHousehold(int householdId) async {
    await _loadToken();
    final response = await http.post(
      Uri.parse('$baseUrl/households/$householdId/leave'),
      headers: _getHeaders(),
    );

    if (response.statusCode != 200) {
      final error = jsonDecode(response.body);
      throw Exception(error['detail'] ?? 'Failed to leave household');
    }
  }
}

  
