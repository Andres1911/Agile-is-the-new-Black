import 'package:flutter/material.dart';
import '../services/api_service.dart';
import '../models/expense.dart';
import '../models/household.dart';
import '../models/user.dart';
import 'add_household_screen.dart';
import 'login_screen.dart';
import 'pay_expense_screen.dart';
import 'outstanding_expenses_screen.dart';
import 'scan_receipt_screen.dart';
import 'requested_expenses_screen.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  int _pendingApprovalsCount = 0;
  final _apiService = ApiService();
  List<Expense> _expenses = [];
  Household? _household;
  User? _currentUser;
  bool _isLoading = false;
  int _selectedIndex = 0;
  String? _errorBanner;
  bool _showErrorBanner = false;

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  Future<void> _loadPendingCount() async {
    try {
      final raw = await _apiService.getRequestedExpenses();
      if (!mounted) return;
      final pendingOnly = raw.where((e) => e['vote_status'] == 'PENDING').toList();
      setState(() => _pendingApprovalsCount = pendingOnly.length);
    } catch (e) {
      debugPrint('_loadPendingCount error: $e');
    }
}
  Future<void> _loadData() async {
    setState(() {
      _isLoading = true;
      _errorBanner = null;
    });

    User? loadedUser;
    Household? loadedHousehold;
    List<Expense> loadedExpenses = [];
    String? error;

    try {
      final userJson = await _apiService.getCurrentUser();
      loadedUser = User.fromJson(userJson);

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
        _currentUser = loadedUser;
        _household = loadedHousehold;
        _expenses = loadedExpenses;
        _isLoading = false;
      });
      if (error != null) {
        _showError(error);
      }
      _loadPendingCount();
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
    setState(() => _selectedIndex = index);
  }

  void _showError(String message) {
    setState(() {
      _errorBanner = message;
      _showErrorBanner = true;
    });
    Future.delayed(const Duration(seconds: 5), () {
      if (!mounted) return;
      if (_errorBanner == message) {
        setState(() {
          _showErrorBanner = false;
        });
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    final List<Widget> widgetOptions = <Widget>[
      _buildExpensesTab(),
      _buildHouseholdsTab(),
      _buildProfileTab(),
    ];

    return Scaffold(
      appBar: AppBar(
        title: const Text('Expense Tracker'),
        actions: [
          Stack(
            children: [
              IconButton(
                icon: const Icon(Icons.how_to_vote_outlined),
                tooltip: 'My Expense Shares',
                onPressed: () {
                  Navigator.push(
                    context,
                    MaterialPageRoute(
                      builder: (context) => const RequestedExpensesScreen(),
                    ),
                  ).then((_) => _loadPendingCount());
                },
              ),
              if (_pendingApprovalsCount > 0)
                Positioned(
                  right: 8,
                  top: 8,
                  child: Badge(
                    label: Text('$_pendingApprovalsCount'),
                  ),
                ),
            ],
          ),
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
      body: Stack(
        children: [
          if (_isLoading)
            const Center(child: CircularProgressIndicator())
          else
            widgetOptions.elementAt(_selectedIndex),
          IgnorePointer(
            ignoring: !_showErrorBanner,
            child: AnimatedSlide(
              offset: _showErrorBanner ? Offset.zero : const Offset(0, -1),
              duration: const Duration(milliseconds: 300),
              curve: Curves.easeInOutCubic,
              child: AnimatedOpacity(
                opacity: _showErrorBanner ? 1 : 0,
                duration: const Duration(milliseconds: 300),
                child: SafeArea(
                  child: Align(
                    alignment: Alignment.topCenter,
                    child: Padding(
                      padding:
                          const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                      child: ConstrainedBox(
                        constraints: const BoxConstraints(maxWidth: 420),
                        child: Material(
                          color: theme.colorScheme.errorContainer,
                          elevation: 6,
                          borderRadius: BorderRadius.circular(16),
                          child: Padding(
                            padding: const EdgeInsets.symmetric(
                              horizontal: 16,
                              vertical: 14,
                            ),
                            child: Row(
                              crossAxisAlignment: CrossAxisAlignment.center,
                              children: [
                                Icon(
                                  Icons.error_outline_rounded,
                                  color: theme.colorScheme.onErrorContainer,
                                ),
                                const SizedBox(width: 12),
                                Expanded(
                                  child: Text(
                                    _errorBanner ?? '',
                                    style: TextStyle(
                                      color:
                                          theme.colorScheme.onErrorContainer,
                                      fontWeight: FontWeight.w500,
                                    ),
                                  ),
                                ),
                                IconButton(
                                  visualDensity: VisualDensity.compact,
                                  icon: Icon(
                                    Icons.close,
                                    color: theme.colorScheme.onErrorContainer,
                                  ),
                                  onPressed: () {
                                    setState(() {
                                      _showErrorBanner = false;
                                    });
                                  },
                                ),
                              ],
                            ),
                          ),
                        ),
                      ),
                    ),
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
      bottomNavigationBar: BottomNavigationBar(
        items: <BottomNavigationBarItem>[
          BottomNavigationBarItem(
            icon: Badge(
              isLabelVisible: _pendingApprovalsCount > 0,
              label: Text('$_pendingApprovalsCount'),
              child: const Icon(Icons.attach_money),
            ),
            label: 'Expenses',
          ),
          const BottomNavigationBarItem(
            icon: Icon(Icons.home),
            label: 'Households',
          ),
          const BottomNavigationBarItem(
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

    final theme = Theme.of(context);

    // Group expenses by status
    final Map<String, List<Expense>> grouped = {};
    for (final expense in _expenses) {
      final status = expense.status ?? 'UNKNOWN';
      grouped.putIfAbsent(status, () => []).add(expense);
    }

    // Define display order and labels
    final statusOrder = [
      'PENDING',
      'DISPUTED',
      'FINALIZED',
      'PARTIALLY_SETTLED',
      'FULLY_SETTLED',
    ];

    final statusLabels = {
      'PENDING': 'Pending',
      'DISPUTED': 'Disputed',
      'FINALIZED': 'Finalized',
      'PARTIALLY_SETTLED': 'Partially Settled',
      'FULLY_SETTLED': 'Fully Settled',
    };

    final statusColors = {
      'PENDING': Colors.orange,
      'DISPUTED': Colors.red,
      'FINALIZED': Colors.blue,
      'PARTIALLY_SETTLED': Colors.teal,
      'FULLY_SETTLED': Colors.green,
    };

    // Build list of sections
    final List<Widget> sections = [];
    for (final status in statusOrder) {
      final expenses = grouped[status];
      if (expenses == null || expenses.isEmpty) continue;

      sections.add(
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 16, 16, 4),
          child: Row(
            children: [
              Container(
                width: 10,
                height: 10,
                decoration: BoxDecoration(
                  color: statusColors[status] ?? Colors.grey,
                  shape: BoxShape.circle,
                ),
              ),
              const SizedBox(width: 8),
              Text(
                statusLabels[status] ?? status,
                style: theme.textTheme.titleSmall?.copyWith(
                  fontWeight: FontWeight.w600,
                  color: statusColors[status] ?? Colors.grey,
                ),
              ),
              const SizedBox(width: 8),
              Expanded(child: Divider(color: statusColors[status]?.withOpacity(0.3) ?? Colors.grey)),
            ],
          ),
        ),
      );

      for (final expense in expenses) {
        sections.add(
          Card(
            margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
            child: ListTile(
              leading: CircleAvatar(
                radius: 22,
                backgroundColor: theme.colorScheme.primaryContainer,
                child: FittedBox(
                  fit: BoxFit.scaleDown,
                  child: Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 6),
                    child: Text(
                      '\$${expense.amount.toStringAsFixed(0)}',
                      style: theme.textTheme.labelLarge?.copyWith(
                        color: theme.colorScheme.onPrimaryContainer,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ),
                ),
              ),
              title: Text(expense.description),
              subtitle: Text(
                '${expense.category ?? 'Uncategorized'} - ${expense.date.toString().split(' ')[0]}',
              ),
              trailing: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  IconButton(
                    icon: const Icon(Icons.payment, color: Colors.green),
                    tooltip: 'Pay Share',
                    onPressed: () async {
                      final result = await Navigator.push(
                        context,
                        MaterialPageRoute(
                          builder: (context) =>
                              PayExpenseScreen(expense: expense),
                        ),
                      );
                      if (result == true) {
                        _loadData();
                      }
                    },
                  ),
                  IconButton(
                    icon: const Icon(Icons.delete, color: Colors.grey),
                    onPressed: () => _deleteExpense(expense.id!),
                  ),
                ],
              ),
            ),
          ),
        );
      }
    }

    return ListView(
      children: sections,
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
    final theme = Theme.of(context);
    final user = _currentUser;

    return Center(
      child: SingleChildScrollView(
        padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 480),
          child: Column(
            children: [
              CircleAvatar(
                radius: 40,
                backgroundColor: theme.colorScheme.primaryContainer,
                child: Text(
                  (user?.fullName?.isNotEmpty == true
                          ? user!.fullName![0]
                          : user?.username[0] ?? '?')
                      .toUpperCase(),
                  style: theme.textTheme.headlineMedium?.copyWith(
                    color: theme.colorScheme.onPrimaryContainer,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
              const SizedBox(height: 16),
              Text(
                user?.fullName?.isNotEmpty == true
                    ? user!.fullName!
                    : user?.username ?? 'Student',
                style: theme.textTheme.titleLarge?.copyWith(
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 4),
              if (user != null)
                Text(
                  '@${user.username}',
                  style: theme.textTheme.bodyMedium?.copyWith(
                    color: theme.colorScheme.onSurfaceVariant,
                  ),
                ),
              const SizedBox(height: 16),
              if (user != null)
                Card(
                  margin: const EdgeInsets.only(top: 8),
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Account',
                          style: theme.textTheme.titleMedium?.copyWith(
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                        const SizedBox(height: 12),
                        Row(
                          children: [
                            const Icon(Icons.email_outlined, size: 18),
                            const SizedBox(width: 8),
                            Expanded(
                              child: Text(
                                user.email,
                                style: theme.textTheme.bodyMedium,
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 8),
                        Row(
                          children: [
                            const Icon(Icons.calendar_today_outlined, size: 18),
                            const SizedBox(width: 8),
                            Text(
                              'Joined: ${user.createdAt.toLocal().toString().split(' ').first}',
                              style: theme.textTheme.bodyMedium,
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                ),
              const SizedBox(height: 24),
              SizedBox(
                width: double.infinity,
                height: 50,
                child: ElevatedButton.icon(
                  onPressed: _logout,
                  icon: const Icon(Icons.logout),
                  label: const Text('Logout'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.red,
                    foregroundColor: Colors.white,
                    padding: const EdgeInsets.symmetric(vertical: 14),
                  ),
                ),
              ),
            ],
          ),
        ),
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
      _showError('Failed to load household members: $e');
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
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      TextField(
                        controller: amountController,
                        decoration: const InputDecoration(
                          labelText: 'Total Amount',
                          prefixText: '\$ ',
                        ),
                        keyboardType: const TextInputType.numberWithOptions(
                          decimal: true,
                        ),
                      ),
                      const SizedBox(height: 12),
                      TextField(
                        controller: descriptionController,
                        decoration: const InputDecoration(
                          labelText: 'Description',
                        ),
                      ),
                      const SizedBox(height: 12),
                      TextField(
                        controller: categoryController,
                        decoration: const InputDecoration(
                          labelText: 'Category (Optional)',
                        ),
                      ),
                      const SizedBox(height: 16),
                      const Divider(height: 32),
                      SwitchListTile(
                        title: const Text('Split Evenly'),
                        value: splitEvenly,
                        onChanged: (val) =>
                            setStateDialog(() => splitEvenly = val),
                      ),
                      if (!splitEvenly) ...[
                        const Padding(
                          padding: EdgeInsets.symmetric(vertical: 8.0),
                          child: Text(
                            'Assign Individual Shares',
                            style: TextStyle(fontWeight: FontWeight.bold),
                          ),
                        ),
                        ...activeMembers.map((member) {
                          final int userId = member['id'];
                          final String name = userId == currentUserId
                              ? '${member['username']} (Me)'
                              : member['username'];

                          return Padding(
                            padding: const EdgeInsets.symmetric(vertical: 4.0),
                            child: Row(
                              children: [
                                Expanded(child: Text(name)),
                                const SizedBox(width: 8),
                                SizedBox(
                                  width: 96,
                                  child: TextField(
                                    decoration: const InputDecoration(
                                      isDense: true,
                                      border: OutlineInputBorder(),
                                      prefixText: '\$',
                                    ),
                                    keyboardType:
                                        const TextInputType.numberWithOptions(
                                      decimal: true,
                                    ),
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
                        }).toList(),
                      ],
                      if (splitEvenly)
                        CheckboxListTile(
                          title: const Text('Include Me'),
                          value: includeCreator,
                          onChanged: (val) => setStateDialog(
                            () => includeCreator = val ?? true,
                          ),
                        ),
                    ],
                  ),
                ),
              ),
              actions: [
                TextButton(
                  onPressed: () => Navigator.pop(context),
                  child: const Text('Cancel'),
                ),
                ElevatedButton(
                  onPressed: () async {
                    final totalStr = amountController.text.trim();
                    final total = double.tryParse(totalStr) ?? 0.0;
                    final description = descriptionController.text.trim();

                    if (description.isEmpty) {
                      Navigator.of(context).pop();
                      _showError('Please enter a description');
                      return;
                    }
                    if (totalStr.isEmpty ||
                        double.tryParse(totalStr) == null ||
                        total <= 0) {
                      Navigator.of(context).pop();
                      _showError('Please enter a valid total amount');
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
                          Navigator.of(context).pop();
                          _showError(
                            'Invalid amount for member $userId: "$rawValue"',
                          );
                          return;
                        }

                        sharesList.add({
                          'user_id': userId,
                          'amount': parsedValue,
                        });

                        if (userId == currentUserId) {
                          finalIncludeCreator = true;
                        }
                      }

                      if (sharesList.isEmpty) {
                        Navigator.of(context).pop();
                        _showError('Please fill at least one share');
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
                      _loadData(); 
                    } catch (e) {
                      if (!context.mounted) return;
                      _showError('Failed to create expense: $e');
                    }
                  },
                  style: ElevatedButton.styleFrom(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 20,
                      vertical: 14,
                    ),
                  ),
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
      _showError('Failed to delete expense: $e');
    }
  }
}
