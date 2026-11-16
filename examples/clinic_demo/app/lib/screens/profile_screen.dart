import 'package:flutter/material.dart';

import '../data/fake_data.dart';

class ProfileScreen extends StatelessWidget {
  const ProfileScreen({super.key, required this.locale, required this.onLocaleChanged});

  final Locale locale;
  final ValueChanged<Locale> onLocaleChanged;

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Text('Profile and settings', style: Theme.of(context).textTheme.headlineSmall),
        const SizedBox(height: 8),
        const ListTile(
          leading: Icon(Icons.badge_outlined),
          title: Text(FakeData.patientName),
          subtitle: Text('Contact details · +000 0000 0000 · sam@example.invalid'),
        ),
        const Divider(),
        Text('Family members', style: Theme.of(context).textTheme.titleMedium),
        for (final f in FakeData.familyMembers)
          ListTile(leading: const Icon(Icons.child_care_outlined), title: Text(f)),
        const ListTile(leading: Icon(Icons.person_add_alt), title: Text('Add family member')),
        const Divider(),
        ListTile(
          leading: const Icon(Icons.language),
          title: const Text('Language'),
          subtitle: SegmentedButton<String>(
            segments: const [
              ButtonSegment(value: 'en', label: Text('English')),
              ButtonSegment(value: 'ar', label: Text('العربية')),
            ],
            selected: {locale.languageCode},
            onSelectionChanged: (s) => onLocaleChanged(Locale(s.first)),
          ),
        ),
        SwitchListTile(
          secondary: const Icon(Icons.notifications_outlined),
          title: const Text('Appointment reminders'),
          subtitle: const Text('24 hours and 2 hours before'),
          value: true,
          onChanged: (_) {},
        ),
      ],
    );
  }
}
