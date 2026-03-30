import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import '../services/api_service.dart';

class ScannedReceiptData {
  String? date;
  double? totalAmount;
  List<Map<String, dynamic>> items;

  ScannedReceiptData({this.date, this.totalAmount, required this.items});
}

class ScanReceiptScreen extends StatefulWidget {
  const ScanReceiptScreen({super.key});

  @override
  State<ScanReceiptScreen> createState() => _ScanReceiptScreenState();
}

class _ScanReceiptScreenState extends State<ScanReceiptScreen> {
  final _apiService = ApiService();
  final _picker = ImagePicker();

  bool _isProcessing = false;
  String? _errorMessage;
  String? _successMessage;
  Uint8List? _selectedImageBytes;

  String? _date;
  double? _totalAmount;
  List<Map<String, dynamic>> _items = [];

  final _dateController = TextEditingController();
  final _totalController = TextEditingController();
  final List<TextEditingController> _itemNameControllers = [];
  final List<TextEditingController> _itemAmountControllers = [];

  bool _hasResults = false;

  @override
  void dispose() {
    _dateController.dispose();
    _totalController.dispose();
    for (final c in _itemNameControllers) {
      c.dispose();
    }
    for (final c in _itemAmountControllers) {
      c.dispose();
    }
    super.dispose();
  }

  Future<void> _pickImage(ImageSource source) async {
    try {
      final picked = await _picker.pickImage(
        source: source,
        maxWidth: 2048,
        maxHeight: 2048,
        imageQuality: 85,
      );
      if (picked == null) return;

      final bytes = await picked.readAsBytes();
      final name = picked.name;

      setState(() {
        _selectedImageBytes = bytes;
        _errorMessage = null;
        _successMessage = null;
        _hasResults = false;
      });

      await _processImage(bytes, name);
    } catch (e) {
      if (!mounted) return;
      if (e.toString().contains('camera_access_denied') ||
          e.toString().contains('photo_access_denied')) {
        setState(() {
          _errorMessage =
              'Camera access denied. Please enable camera permissions or choose an image from your gallery';
        });
      } else {
        setState(() {
          _errorMessage = 'Failed to pick image: $e';
        });
      }
    }
  }

  Future<void> _processImage(Uint8List bytes, String filename) async {
    setState(() {
      _isProcessing = true;
      _errorMessage = null;
    });

    try {
      final result = await _apiService.scanReceiptBytes(bytes, filename);

      _date = result['date'] as String?;
      _totalAmount = result['totalAmount'] != null
          ? (result['totalAmount'] as num).toDouble()
          : null;
      final rawItems = result['items'] as List<dynamic>? ?? [];
      _items = rawItems.map((e) {
        final m = e as Map<String, dynamic>;
        return <String, dynamic>{
          'item': m['item'] as String,
          'amount': (m['amount'] as num).toDouble(),
        };
      }).toList();

      _dateController.text = _date ?? '';
      _totalController.text =
          _totalAmount != null ? _totalAmount!.toStringAsFixed(2) : '';

      for (final c in _itemNameControllers) {
        c.dispose();
      }
      for (final c in _itemAmountControllers) {
        c.dispose();
      }
      _itemNameControllers.clear();
      _itemAmountControllers.clear();

      for (final item in _items) {
        _itemNameControllers
            .add(TextEditingController(text: item['item'] as String));
        _itemAmountControllers.add(TextEditingController(
            text: (item['amount'] as double).toStringAsFixed(2)));
      }

      setState(() {
        _hasResults = true;
        _successMessage = result['message'] as String? ?? 'Receipt scanned successfully';
      });
    } catch (e) {
      setState(() {
        _errorMessage = e.toString().replaceFirst('Exception: ', '');
      });
    } finally {
      if (mounted) {
        setState(() {
          _isProcessing = false;
        });
      }
    }
  }

  void _addItem() {
    setState(() {
      _items.add({'item': '', 'amount': 0.0});
      _itemNameControllers.add(TextEditingController());
      _itemAmountControllers.add(TextEditingController());
    });
  }

  void _removeItem(int index) {
    setState(() {
      _items.removeAt(index);
      _itemNameControllers[index].dispose();
      _itemAmountControllers[index].dispose();
      _itemNameControllers.removeAt(index);
      _itemAmountControllers.removeAt(index);
    });
  }

  void _confirm() {
    final date = _dateController.text.trim();
    final totalStr = _totalController.text.trim();
    final total = double.tryParse(totalStr);

    if (total == null || total <= 0) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please enter a valid total amount')),
      );
      return;
    }

    List<Map<String, dynamic>> finalItems = [];
    for (int i = 0; i < _itemNameControllers.length; i++) {
      final name = _itemNameControllers[i].text.trim();
      final amt = double.tryParse(_itemAmountControllers[i].text.trim());
      if (name.isNotEmpty && amt != null && amt > 0) {
        finalItems.add({'item': name, 'amount': amt});
      }
    }

    final data = ScannedReceiptData(
      date: date.isNotEmpty ? date : null,
      totalAmount: total,
      items: finalItems,
    );

    Navigator.pop(context, data);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Scan Receipt')),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            if (!_hasResults && !_isProcessing) ...[
              const Text(
                'Add Expense by Image',
                style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 8),
              const Text('Take a photo of your receipt or choose an existing image.'),
              const SizedBox(height: 24),
              ElevatedButton.icon(
                onPressed: () => _pickImage(ImageSource.camera),
                icon: const Icon(Icons.camera_alt),
                label: const Text('Take Photo'),
                style: ElevatedButton.styleFrom(
                  minimumSize: const Size.fromHeight(48),
                ),
              ),
              const SizedBox(height: 12),
              OutlinedButton.icon(
                onPressed: () => _pickImage(ImageSource.gallery),
                icon: const Icon(Icons.photo_library),
                label: const Text('Choose from Gallery'),
                style: OutlinedButton.styleFrom(
                  minimumSize: const Size.fromHeight(48),
                ),
              ),
            ],

            if (_isProcessing) ...[
              const SizedBox(height: 48),
              const Center(child: CircularProgressIndicator()),
              const SizedBox(height: 16),
              const Center(child: Text('Processing receipt...')),
            ],

            if (_errorMessage != null) ...[
              const SizedBox(height: 16),
              Card(
                color: Colors.red.shade50,
                child: Padding(
                  padding: const EdgeInsets.all(12),
                  child: Row(
                    children: [
                      Icon(Icons.error_outline, color: Colors.red.shade700),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          _errorMessage!,
                          style: TextStyle(color: Colors.red.shade700),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 12),
              OutlinedButton(
                onPressed: () {
                  setState(() {
                    _errorMessage = null;
                  });
                },
                child: const Text('Try Again'),
              ),
            ],

            if (_hasResults) ...[
              if (_successMessage != null) ...[
                Card(
                  color: Colors.green.shade50,
                  child: Padding(
                    padding: const EdgeInsets.all(12),
                    child: Row(
                      children: [
                        Icon(Icons.check_circle_outline, color: Colors.green.shade700),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Text(
                            _successMessage!,
                            style: TextStyle(color: Colors.green.shade700),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 16),
              ],

              if (_selectedImageBytes != null) ...[
                ClipRRect(
                  borderRadius: BorderRadius.circular(8),
                  child: Image.memory(
                    _selectedImageBytes!,
                    height: 150,
                    fit: BoxFit.cover,
                  ),
                ),
                const SizedBox(height: 16),
              ],

              TextField(
                controller: _dateController,
                decoration: InputDecoration(
                  labelText: 'Date',
                  hintText: 'YYYY-MM-DD',
                  border: const OutlineInputBorder(),
                  suffixIcon: _date == null
                      ? Icon(Icons.warning_amber, color: Colors.orange.shade700)
                      : null,
                ),
              ),
              const SizedBox(height: 12),

              TextField(
                controller: _totalController,
                decoration: const InputDecoration(
                  labelText: 'Total Amount',
                  prefixText: '\$ ',
                  border: OutlineInputBorder(),
                ),
                keyboardType: const TextInputType.numberWithOptions(decimal: true),
              ),
              const SizedBox(height: 20),

              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  const Text(
                    'Items',
                    style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                  ),
                  TextButton.icon(
                    onPressed: _addItem,
                    icon: const Icon(Icons.add, size: 18),
                    label: const Text('Add Item'),
                  ),
                ],
              ),
              const SizedBox(height: 8),

              if (_itemNameControllers.isEmpty)
                Card(
                  color: Colors.orange.shade50,
                  child: Padding(
                    padding: const EdgeInsets.all(12),
                    child: Text(
                      'No individual items detected. Please add items manually.',
                      style: TextStyle(color: Colors.orange.shade800),
                    ),
                  ),
                ),

              ...List.generate(_itemNameControllers.length, (i) {
                return Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: Row(
                    children: [
                      Expanded(
                        flex: 3,
                        child: TextField(
                          controller: _itemNameControllers[i],
                          decoration: InputDecoration(
                            labelText: 'Item ${i + 1}',
                            isDense: true,
                            border: const OutlineInputBorder(),
                          ),
                        ),
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        flex: 2,
                        child: TextField(
                          controller: _itemAmountControllers[i],
                          decoration: const InputDecoration(
                            labelText: 'Amount',
                            prefixText: '\$ ',
                            isDense: true,
                            border: OutlineInputBorder(),
                          ),
                          keyboardType:
                              const TextInputType.numberWithOptions(decimal: true),
                        ),
                      ),
                      IconButton(
                        icon: const Icon(Icons.remove_circle_outline, color: Colors.red),
                        onPressed: () => _removeItem(i),
                        iconSize: 20,
                      ),
                    ],
                  ),
                );
              }),

              const SizedBox(height: 24),

              Row(
                children: [
                  Expanded(
                    child: OutlinedButton(
                      onPressed: () {
                        setState(() {
                          _hasResults = false;
                          _selectedImageBytes = null;
                          _successMessage = null;
                        });
                      },
                      child: const Text('Rescan'),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    flex: 2,
                    child: ElevatedButton(
                      onPressed: _confirm,
                      child: const Text('Confirm & Create Expense'),
                    ),
                  ),
                ],
              ),
            ],
          ],
        ),
      ),
    );
  }
}
