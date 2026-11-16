import 'package:flutter/material.dart';

import '../data/fake_data.dart';
import '../main.dart';

class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final next = FakeData.upcoming.first;
    final shell = ClinicShell.of(context);
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Text('Hello, ${FakeData.patientName}', style: Theme.of(context).textTheme.headlineSmall),
        const SizedBox(height: 4),
        const Text('Northwind Clinic (demo app, fictional data)'),
        const SizedBox(height: 16),
        Card(
          child: ListTile(
            leading: Icon(next.isVideo ? Icons.videocam_outlined : Icons.local_hospital_outlined),
            title: Text('Next: ${next.doctor}'),
            subtitle: Text('${formatDateTime(next.start)}\n${next.branch}'),
            isThreeLine: true,
            trailing: const Icon(Icons.chevron_right),
            onTap: () => shell.goTo('appointments'),
          ),
        ),
        const SizedBox(height: 8),
        Row(
          children: [
            Expanded(
              child: FilledButton.icon(
                onPressed: () => shell.goTo('book'),
                icon: const Icon(Icons.add),
                label: const Text('Book'),
              ),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: OutlinedButton.icon(
                onPressed: () => shell.goTo('help'),
                icon: const Icon(Icons.help_outline),
                label: const Text('Help'),
              ),
            ),
          ],
        ),
        const SizedBox(height: 24),
        Text('Our branches', style: Theme.of(context).textTheme.titleMedium),
        for (final b in FakeData.branches)
          ListTile(
            leading: const Icon(Icons.place_outlined),
            title: Text(b),
            subtitle: const Text('Sun–Thu 07:00–22:00 · Sat 08:00–16:00 · Fri closed'),
          ),
      ],
    );
  }
}
