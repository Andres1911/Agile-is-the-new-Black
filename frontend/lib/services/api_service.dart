import 'dart:convert';
import 'package:http/http.dart' as http;
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
    final headers = {
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
      return jsonDecode(response.body);
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
      final data = jsonDecode(response.body);
      final token = data['access_token'];
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
      return jsonDecode(response.body);
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
      return jsonDecode(response.body);
    } else {
      throw Exception('Failed to get expenses: ${response.body}');
    }
  }

  Future<Map<String, dynamic>> createExpense(Map<String, dynamic> expense) async {
    await _loadToken();
    final response = await http.post(
      Uri.parse('$baseUrl/expenses/'),
      headers: _getHeaders(),
      body: jsonEncode(expense),
    );

    if (response.statusCode == 201) {
      return jsonDecode(response.body);
    } else {
      throw Exception('Failed to create expense: ${response.body}');
    }
  }

  Future<Map<String, dynamic>> updateExpense(int id, Map<String, dynamic> expense) async {
    await _loadToken();
    final response = await http.put(
      Uri.parse('$baseUrl/expenses/$id'),
      headers: _getHeaders(),
      body: jsonEncode(expense),
    );

    if (response.statusCode == 200) {
      return jsonDecode(response.body);
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
      Uri.parse('$baseUrl/expenses/household/$householdId'),
      headers: _getHeaders(),
    );

    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    } else {
      throw Exception('Failed to get household expenses: ${response.body}');
    }
  }

  // Household endpoints
  Future<List<dynamic>> getHouseholds() async {
    await _loadToken();
    final response = await http.get(
      Uri.parse('$baseUrl/households/'),
      headers: _getHeaders(),
    );

    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    } else {
      throw Exception('Failed to get households: ${response.body}');
    }
  }

  Future<Map<String, dynamic>> createHousehold(Map<String, dynamic> household) async {
    await _loadToken();
    final response = await http.post(
      Uri.parse('$baseUrl/households/'),
      headers: _getHeaders(),
      body: jsonEncode(household),
    );

    if (response.statusCode == 201) {
      return jsonDecode(response.body);
    } else {
      throw Exception('Failed to create household: ${response.body}');
    }
  }

  Future<Map<String, dynamic>> getHousehold(int id) async {
    await _loadToken();
    final response = await http.get(
      Uri.parse('$baseUrl/households/$id'),
      headers: _getHeaders(),
    );

    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    } else {
      throw Exception('Failed to get household: ${response.body}');
    }
  }

  Future<Map<String, dynamic>> addMemberToHousehold(int householdId, int userId) async {
    await _loadToken();
    final response = await http.post(
      Uri.parse('$baseUrl/households/$householdId/members/$userId'),
      headers: _getHeaders(),
    );

    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    } else {
      throw Exception('Failed to add member: ${response.body}');
    }
  }

  Future<Map<String, dynamic>> removeMemberFromHousehold(int householdId, int userId) async {
    await _loadToken();
    final response = await http.delete(
      Uri.parse('$baseUrl/households/$householdId/members/$userId'),
      headers: _getHeaders(),
    );

    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    } else {
      throw Exception('Failed to remove member: ${response.body}');
    }
  }
}
