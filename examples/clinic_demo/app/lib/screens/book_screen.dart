import 'package:flutter/material.dart';

import '../data/fake_data.dart';

class BookScreen extends StatefulWidget {
  const BookScreen({super.key});

  @override
  State<BookScreen> createState() => _BookScreenState();
}

class _BookScreenState extends State<BookScreen> {
  String _specialty = FakeData.specialties.first;
  String _branch = FakeData.branches.first;
  bool _video = false;
  String _forWhom = 'You';

  @override
  Widget build(BuildContext context) {
    final doctors = FakeData.doctors.where((d) => d.specialty == _specialty).toList();
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Text('Book appointment', style: Theme.of(context).textTheme.headlineSmall),
        const SizedBox(height: 16),
        DropdownButtonFormField<String>(
          value: _specialty,
          decoration: const InputDecoration(labelText: 'Specialty'),
          items: [for (final s in FakeData.specialties) DropdownMenuItem(value: s, child: Text(s))],
          onChanged: (v) => setState(() => _specialty = v!),
        ),
        const SizedBox(height: 12),
        DropdownButtonFormField<String>(
          value: _branch,
          decoration: const InputDecoration(labelText: 'Clinic branch'),
          items: [for (final b in FakeData.branches) DropdownMenuItem(value: b, child: Text(b))],
          onChanged: (v) => setState(() => _branch = v!),
        ),
        const SizedBox(height: 12),
        SegmentedButton<bool>(
          segments: const [
            ButtonSegment(value: false, label: Text('In person'), icon: Icon(Icons.local_hospital_outlined)),
            ButtonSegment(value: true, label: Text('Video visit'), icon: Icon(Icons.videocam_outlined)),
          ],
          selected: {_video},
          onSelectionChanged: (s) => setState(() => _video = s.first),
        ),
        const SizedBox(height: 12),
        DropdownButtonFormField<String>(
          value: _forWhom,
          decoration: const InputDecoration(labelText: 'Who is this visit for?'),
          items: [
            const DropdownMenuItem(value: 'You', child: Text('You')),
            for (final f in FakeData.familyMembers) DropdownMenuItem(value: f, child: Text(f)),
          ],
          onChanged: (v) => setState(() => _forWhom = v!),
        ),
        const SizedBox(height: 16),
        Text('Doctors', style: Theme.of(context).textTheme.titleMedium),
        const ListTile(
          leading: Icon(Icons.bolt_outlined),
          title: Text('Any available doctor'),
          subtitle: Text('Earliest slot across all doctors'),
        ),
        for (final d in doctors)
          ListTile(
            leading: const CircleAvatar(child: Icon(Icons.person_outline)),
            title: Text(d.name),
            subtitle: Text('${d.languages.join(', ')} · next: ${d.nextSlot}'),
            trailing: FilledButton.tonal(
              onPressed: () => ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(content: Text('Demo only: booking ${d.name} for $_forWhom')),
              ),
              child: const Text('Choose'),
            ),
          ),
      ],
    );
  }
}
