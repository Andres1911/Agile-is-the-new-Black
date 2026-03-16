import 'package:flutter/material.dart';
import '../services/api_service.dart';
import '../models/expense.dart';
import '../models/household.dart';
import 'add_household_screen.dart';
import 'login_screen.dart';
import 'outstanding_expenses_screen.dart';
import 'scan_receipt_screen.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  final _apiService = ApiService();
  List<Expense> _expenses = [];
  Household? _household;
  bool _isLoading = false;
  int _selectedIndex = 0;

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  Future<void> _loadData() async {
    setState(() {
      _isLoading = true;
    });

    Household? loadedHousehold;
    List<Expense> loadedExpenses = [];
    String? error;

    try {
      final data = await _apiService.getMyHousehold();
      if (data != null) {
        loadedHousehold = Household.fromJson(data);

        try {
          final expensesData =
              await _apiService.getHouseholdExpenses(loadedHousehold.id);
          loadedExpenses =
              expensesData.map((e) => Expense.fromJson(e)).toList();
        } catch (e) {
          debugPrint('Failed to load expenses: $e');
          error = 'Failed to load expenses. Please try again.';
        }
      }
    } catch (e) {
      debugPrint('Failed to load household data: $e');
      error = 'Failed to load data. Please try again.';
    }

    if (mounted) {
      setState(() {
        _household = loadedHousehold;
        _expenses = loadedExpenses;
        _isLoading = false;
      });
      if (error != null) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(error),
            duration: const Duration(seconds: 5),
            action: SnackBarAction(label: 'Retry', onPressed: _loadData),
          ),
        );
      }
    }
  }

  Future<void> _logout() async {
    await _apiService.clearToken();
    if (!mounted) return;
    
    Navigator.pushReplacement(
      context,
      MaterialPageRoute(builder: (context) => const LoginScreen()),
    );
  }

  void _onItemTapped(int index) {
    setState(() {
      _selectedIndex = index;
    });
  }

  @override
  Widget build(BuildContext context) {
    final List<Widget> widgetOptions = <Widget>[
      _buildExpensesTab(),
      _buildHouseholdsTab(),
      _buildProfileTab(),
    ];

    return Scaffold(
      appBar: AppBar(
        title: const Text('Expense Tracker'),
        actions: [
          IconButton(
            icon: const Icon(Icons.pending_actions_outlined),
            tooltip: 'Outstanding',
            onPressed: () {
              Navigator.push(
                context,
                MaterialPageRoute(
                  builder: (context) => const OutstandingExpensesScreen(),
                ),
              );
            },
          ),
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _loadData,
          ),
        ],
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : widgetOptions.elementAt(_selectedIndex),
      bottomNavigationBar: BottomNavigationBar(
        items: const <BottomNavigationBarItem>[
          BottomNavigationBarItem(
            icon: Icon(Icons.attach_money),
            label: 'Expenses',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.home),
            label: 'Households',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.person),
            label: 'Profile',
          ),
        ],
        currentIndex: _selectedIndex,
        onTap: _onItemTapped,
      ),
      floatingActionButton: _selectedIndex == 0 && _household != null
          ? FloatingActionButton(
              onPressed: () => _showAddExpenseOptions(context),
              child: const Icon(Icons.add),
            )
          : _selectedIndex == 1 && _household == null
              ? FloatingActionButton(
                  onPressed: () async {
                    final result = await Navigator.push(
                      context,
                      MaterialPageRoute(
                          builder: (context) => const AddHouseholdScreen()),
                    );
                    if (result == true) _loadData();
                  },
                  child: const Icon(Icons.add),
                )
              : null,
    );
  }

  Widget _buildExpensesTab() {
    if (_expenses.isEmpty) {
      return const Center(
        child: Text('No expenses yet. Add your first expense!'),
      );
    }

    return ListView.builder(
      itemCount: _expenses.length,
      itemBuilder: (context, index) {
        final expense = _expenses[index];
        return Card(
          margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          child: ListTile(
            leading: CircleAvatar(
              child: Text('\$${expense.amount.toStringAsFixed(0)}'),
            ),
            title: Text(expense.description),
            subtitle: Text(
              '${expense.category ?? 'Uncategorized'} - ${expense.date.toString().split(' ')[0]}',
            ),
            trailing: IconButton(
              icon: const Icon(Icons.delete),
              onPressed: () => _deleteExpense(expense.id!),
            ),
          ),
        );
      },
    );
  }

  Widget _buildHouseholdsTab() {
    if (_household == null) {
      return const Center(
        child: Text('No households yet. Create your first household!'),
      );
    }

    final household = _household!;
    return ListView(
      padding: const EdgeInsets.symmetric(vertical: 8),
      children: [
        Card(
          margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          child: ListTile(
            leading: const CircleAvatar(
              child: Icon(Icons.home),
            ),
            title: Text(household.name),
            subtitle: Text(household.address ?? household.description ?? 'No description'),
            trailing: household.inviteCode != null
                ? Text(household.inviteCode!)
                : null,
          ),
        ),
      ],
    );
  }

  Widget _buildProfileTab() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Icon(Icons.person, size: 100),
          const SizedBox(height: 24),
          const Text(
            'Profile',
            style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 48),
          ElevatedButton.icon(
            onPressed: _logout,
            icon: const Icon(Icons.logout),
            label: const Text('Logout'),
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.red,
              foregroundColor: Colors.white,
            ),
          ),
        ],
      ),
    );
  }

  void _showAddExpenseOptions(BuildContext context) {
    showModalBottomSheet(
      context: context,
      builder: (ctx) {
        return SafeArea(
          child: Wrap(
            children: [
              ListTile(
                leading: const Icon(Icons.edit),
                title: const Text('Manual Entry'),
                onTap: () {
                  Navigator.pop(ctx);
                  _showAddExpenseDialog(context);
                },
              ),
              ListTile(
                leading: const Icon(Icons.camera_alt),
                title: const Text('Add Expense by Image'),
                onTap: () async {
                  Navigator.pop(ctx);
                  final result = await Navigator.push<ScannedReceiptData>(
                    context,
                    MaterialPageRoute(
                      builder: (context) => const ScanReceiptScreen(),
                    ),
                  );
                  if (result != null && mounted) {
                    _showAddExpenseDialogWithData(context, result);
                  }
                },
              ),
            ],
          ),
        );
      },
    );
  }

  Future<void> _showAddExpenseDialogWithData(
      BuildContext context, ScannedReceiptData data) async {
    List<dynamic> activeMembers = [];
    int? householdId;
    int? currentUserId;

    try {
      final membersData = await _apiService.fetchActiveMembers();
      activeMembers = membersData['members'];
      householdId = membersData['household_id'];
      currentUserId = membersData['current_user_id'];
    } catch (e) {
      if (!context.mounted) return;
      ScaffoldMessenger.of(context)
          .showSnackBar(SnackBar(content: Text("Error: $e")));
      return;
    }

    final amountController =
        TextEditingController(text: data.totalAmount?.toStringAsFixed(2) ?? '');
    final itemNames = data.items.map((i) => i['item'] as String).toList();
    final descriptionController =
        TextEditingController(text: itemNames.join(', '));
    final categoryController = TextEditingController();

    bool splitEvenly = true;
    bool includeCreator = true;
    Map<int, String> manualInputs = {};

    if (!context.mounted) return;

    return showDialog(
      context: context,
      builder: (context) {
        return StatefulBuilder(
          builder: (context, setStateDialog) {
            return AlertDialog(
              title: const Text('Add & Split Expense'),
              content: SizedBox(
                width: double.maxFinite,
                child: SingleChildScrollView(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      if (data.items.isNotEmpty) ...[
                        const Align(
                          alignment: Alignment.centerLeft,
                          child: Text('Scanned Items:',
                              style: TextStyle(
                                  fontWeight: FontWeight.bold, fontSize: 13)),
                        ),
                        const SizedBox(height: 4),
                        ...data.items.map((item) => Padding(
                              padding:
                                  const EdgeInsets.symmetric(vertical: 2),
                              child: Row(
                                mainAxisAlignment:
                                    MainAxisAlignment.spaceBetween,
                                children: [
                                  Text(item['item'] as String,
                                      style: const TextStyle(fontSize: 13)),
                                  Text(
                                      '\$${(item['amount'] as double).toStringAsFixed(2)}',
                                      style: const TextStyle(fontSize: 13)),
                                ],
                              ),
                            )),
                        const Divider(height: 20),
                      ],
                      TextField(
                        controller: amountController,
                        decoration: const InputDecoration(
                            labelText: 'Total Amount', prefixText: '\$ '),
                        keyboardType: const TextInputType.numberWithOptions(
                            decimal: true),
                      ),
                      TextField(
                          controller: descriptionController,
                          decoration:
                              const InputDecoration(labelText: 'Description')),
                      TextField(
                          controller: categoryController,
                          decoration: const InputDecoration(
                              labelText: 'Category (Optional)')),
                      const Divider(height: 30),
                      SwitchListTile(
                        title: const Text('Split Evenly'),
                        value: splitEvenly,
                        onChanged: (val) =>
                            setStateDialog(() => splitEvenly = val),
                      ),
                      if (!splitEvenly) ...[
                        const Padding(
                          padding: EdgeInsets.symmetric(vertical: 8.0),
                          child: Text("Assign Individual Shares:",
                              style: TextStyle(fontWeight: FontWeight.bold)),
                        ),
                        ...activeMembers.map((member) {
                          final int userId = member['id'];
                          final String name = userId == currentUserId
                              ? "${member['username']} (Me)"
                              : member['username'];
                          return Padding(
                            padding: const EdgeInsets.symmetric(vertical: 4.0),
                            child: Row(
                              children: [
                                Expanded(child: Text(name)),
                                SizedBox(
                                  width: 90,
                                  child: TextField(
                                    decoration: const InputDecoration(
                                        isDense: true,
                                        border: OutlineInputBorder(),
                                        prefixText: '\$'),
                                    keyboardType: TextInputType.text,
                                    onChanged: (val) {
                                      if (val.trim().isEmpty) {
                                        manualInputs.remove(userId);
                                      } else {
                                        manualInputs[userId] = val.trim();
                                        if (userId == currentUserId) {
                                          setStateDialog(
                                              () => includeCreator = true);
                                        }
                                      }
                                    },
                                  ),
                                ),
                              ],
                            ),
                          );
                        }),
                      ],
                      if (splitEvenly)
                        CheckboxListTile(
                          title: const Text('Include Me'),
                          value: includeCreator,
                          onChanged: (val) =>
                              setStateDialog(() => includeCreator = val ?? true),
                        ),
                    ],
                  ),
                ),
              ),
              actions: [
                TextButton(
                    onPressed: () => Navigator.pop(context),
                    child: const Text('Cancel')),
                ElevatedButton(
                  onPressed: () async {
                    final totalStr = amountController.text.trim();
                    final total = double.tryParse(totalStr) ?? 0.0;
                    final description = descriptionController.text.trim();

                    if (description.isEmpty) {
                      ScaffoldMessenger.of(context).showSnackBar(
                          const SnackBar(
                              content: Text('Please enter a description')));
                      return;
                    }
                    if (totalStr.isEmpty ||
                        double.tryParse(totalStr) == null ||
                        total <= 0) {
                      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(
                          content: Text('Please enter a valid total amount')));
                      return;
                    }

                    bool finalIncludeCreator =
                        splitEvenly ? includeCreator : false;
                    List<Map<String, dynamic>>? finalManualShares;

                    if (!splitEvenly) {
                      List<Map<String, dynamic>> sharesList = [];
                      for (var entry in manualInputs.entries) {
                        final userId = entry.key;
                        final rawValue = entry.value;
                        double? parsedValue = double.tryParse(rawValue);
                        if (parsedValue == null) {
                          ScaffoldMessenger.of(context).showSnackBar(SnackBar(
                              content: Text(
                                  'Invalid number for user $userId: "$rawValue"')));
                          return;
                        }
                        sharesList.add(
                            {'user_id': userId, 'amount': parsedValue});
                        if (userId == currentUserId) {
                          finalIncludeCreator = true;
                        }
                      }
                      if (sharesList.isEmpty) {
                        ScaffoldMessenger.of(context).showSnackBar(
                            const SnackBar(
                                content:
                                    Text('Please fill at least one share')));
                        return;
                      }
                      finalManualShares = sharesList;
                    }

                    try {
                      await _apiService.createAndSplitExpense({
                        'amount': total,
                        'description': description,
                        'category': categoryController.text.isEmpty
                            ? null
                            : categoryController.text,
                        'household_id': householdId,
                        'split_evenly': splitEvenly,
                        'include_creator': finalIncludeCreator,
                        'manual_shares':
                            splitEvenly ? null : finalManualShares,
                      });
                      if (!context.mounted) return;
                      Navigator.pop(context);
                      ScaffoldMessenger.of(context).showSnackBar(
                          const SnackBar(content: Text("Success!")));
                      _loadData();
                    } catch (e) {
                      if (!context.mounted) return;
                      ScaffoldMessenger.of(context).showSnackBar(
                          SnackBar(content: Text('Error: $e')));
                    }
                  },
                  child: const Text('Submit'),
                ),
              ],
            );
          },
        );
      },
    );
  }

  Future<void> _showAddExpenseDialog(BuildContext context) async {
    List<dynamic> activeMembers = [];
    int? householdId;
    int? currentUserId;

    try {
      final data = await _apiService.fetchActiveMembers();
      activeMembers = data['members'];
      householdId = data['household_id'];
      currentUserId = data['current_user_id'];
    } catch (e) {
      if (!context.mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("Error: $e")));
      return;
    }

    final amountController = TextEditingController();
    final descriptionController = TextEditingController();
    final categoryController = TextEditingController();
    
    bool splitEvenly = true;
    bool includeCreator = true; 
    // Map to store raw strings from the input fields
    Map<int, String> manualInputs = {};

    return showDialog(
      context: context,
      builder: (context) {
        return StatefulBuilder(
          builder: (context, setStateDialog) {
            return AlertDialog(
              title: const Text('Add & Split Expense'),
              content: SizedBox(
                width: double.maxFinite,
                child: SingleChildScrollView(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      TextField(
                        controller: amountController,
                        decoration: const InputDecoration(labelText: 'Total Amount', prefixText: '\$ '),
                        keyboardType: const TextInputType.numberWithOptions(decimal: true),
                      ),
                      TextField(controller: descriptionController, decoration: const InputDecoration(labelText: 'Description')),
                      TextField(controller: categoryController, decoration: const InputDecoration(labelText: 'Category (Optional)')),
                      const Divider(height: 30),
                      
                      SwitchListTile(
                        title: const Text('Split Evenly'),
                        value: splitEvenly,
                        onChanged: (val) => setStateDialog(() => splitEvenly = val),
                      ),

                      if (!splitEvenly) ...[
                        const Padding(
                          padding: EdgeInsets.symmetric(vertical: 8.0),
                          child: Text("Assign Individual Shares:", style: TextStyle(fontWeight: FontWeight.bold)),
                        ),
                        ...activeMembers.map((member) {
                          final int userId = member['id'];
                          final String name = userId == currentUserId ? "${member['username']} (Me)" : member['username'];

                          return Padding(
                            padding: const EdgeInsets.symmetric(vertical: 4.0),
                            child: Row(
                              children: [
                                Expanded(child: Text(name)),
                                SizedBox(
                                  width: 90,
                                  child: TextField(
                                    // Removed 'const' from parent or used static access correctly
                                    decoration: const InputDecoration(isDense: true, border: OutlineInputBorder(), prefixText: '\$'),
                                    keyboardType: TextInputType.text, 
                                    onChanged: (val) {
                                      if (val.trim().isEmpty) {
                                        manualInputs.remove(userId);
                                      } else {
                                        manualInputs[userId] = val.trim();
                                        
                                        // If user fills their own box, ensure include_creator is true
                                        if (userId == currentUserId) {
                                          setStateDialog(() => includeCreator = true);
                                        }
                                      }
                                    },
                                  ),
                                ),
                              ],
                            ),
                          );
                        }).toList(),
                      ],

                      if (splitEvenly)
                        CheckboxListTile(
                          title: const Text('Include Me'),
                          value: includeCreator,
                          onChanged: (val) => setStateDialog(() => includeCreator = val ?? true),
                        ),
                    ],
                  ),
                ),
              ),
              actions: [
                TextButton(onPressed: () => Navigator.pop(context), child: const Text('Cancel')),
                ElevatedButton(
                  onPressed: () async {
                    final totalStr = amountController.text.trim();
                    final total = double.tryParse(totalStr) ?? 0.0;
                    final description = descriptionController.text.trim();

                    if (description.isEmpty) {
                      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Please enter a description')));
                      return;
                    }
                    if (totalStr.isEmpty || double.tryParse(totalStr) == null || total <= 0) {
                      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Please enter a valid total amount')));
                      return;
                    }

                    bool finalIncludeCreator = splitEvenly ? includeCreator : false; 
                    List<Map<String, dynamic>>? finalManualShares;

                    if (!splitEvenly) {
                      List<Map<String, dynamic>> sharesList = [];
                      
                      for (var entry in manualInputs.entries) {
                        final userId = entry.key;
                        final rawValue = entry.value;

                        double? parsedValue = double.tryParse(rawValue);
                        if (parsedValue == null) {
                          // Throw error if it's not a number (e.g., "ddd")
                          ScaffoldMessenger.of(context).showSnackBar(
                            SnackBar(content: Text('Invalid number for user $userId: "$rawValue"'))
                          );
                          return;
                        }

                        // Add to DTO even if it's 0 or negative; backend will handle the logic
                        sharesList.add({
                          'user_id': userId,
                          'amount': parsedValue,
                        });

                        if (userId == currentUserId) {
                          finalIncludeCreator = true;
                        }
                      }

                      if (sharesList.isEmpty) {
                        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Please fill at least one share')));
                        return;
                      }
                      
                      finalManualShares = sharesList;
                    }

                    try {
                      await _apiService.createAndSplitExpense({
                        'amount': total,
                        'description': description,
                        'category': categoryController.text.isEmpty ? null : categoryController.text,
                        'household_id': householdId,
                        'split_evenly': splitEvenly,
                        'include_creator': finalIncludeCreator, 
                        'manual_shares': splitEvenly ? null : finalManualShares,
                      });

                      if (!context.mounted) return;
                      Navigator.pop(context);
                      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text("Success!")));
                      _loadData(); 
                    } catch (e) {
                      if (!context.mounted) return;
                      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Error: $e')));
                    }
                  },
                  child: const Text('Submit'),
                ),
              ],
            );
          },
        );
      },
    );
  }

  Future<void> _deleteExpense(int id) async {
    try {
      await _apiService.deleteExpense(id);
      _loadData();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Failed to delete expense: $e')),
      );
    }
  }
}
