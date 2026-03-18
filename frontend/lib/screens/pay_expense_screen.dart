import 'package:flutter/material.dart';
import '../models/expense.dart';
import '../services/api_service.dart';

class PayExpenseScreen extends StatefulWidget {
  final Expense expense;
  const PayExpenseScreen({super.key, required this.expense});

  @override
  State<PayExpenseScreen> createState() => _PayExpenseScreenState();
}

class _PayExpenseScreenState extends State<PayExpenseScreen> {
  final _formKey = GlobalKey<FormState>();
  final _amountController = TextEditingController();
  final _apiService = ApiService();
  bool _isLoading = false;

  Future<void> _submitPayment() async {
    if (_formKey.currentState!.validate()) {
      setState(() => _isLoading = true);
      try {
        final amount = double.parse(_amountController.text);
        await _apiService.payExpenseShare(widget.expense.id!, amount);

        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Payment recorded!')));
        Navigator.pop(context, true); // Return true to refresh home screen
      } catch (e) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Error: $e')));
      } finally {
        if (mounted) setState(() => _isLoading = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Pay Share')),
      body: Padding(
        padding: const EdgeInsets.all(24.0),
        child: Form(
          key: _formKey,
          child: Column(
            children: [
              Text(widget.expense.description, style: Theme.of(context).textTheme.headlineSmall),
              const SizedBox(height: 10),
              Text('Total Expense: \$${widget.expense.amount.toStringAsFixed(2)}'),
              const SizedBox(height: 30),
              TextFormField(
                controller: _amountController,
                decoration: const InputDecoration(labelText: 'Amount to Pay', prefixText: '\$'),
                keyboardType: const TextInputType.numberWithOptions(decimal: true),
                validator: (val) => (val == null || double.tryParse(val) == null) ? 'Enter a valid amount' : null,
              ),
              const SizedBox(height: 40),
              SizedBox(
                width: double.infinity,
                height: 50,
                child: ElevatedButton(
                  onPressed: _isLoading ? null : _submitPayment,
                  child: _isLoading ? const CircularProgressIndicator() : const Text('Confirm Payment'),
                ),
              )
            ],
          ),
        ),
      ),
    );
  }
}