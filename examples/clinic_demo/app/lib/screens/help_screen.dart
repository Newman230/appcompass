import 'package:flutter/material.dart';

class HelpScreen extends StatelessWidget {
  const HelpScreen({super.key});

  static const _topics = [
    'Book an appointment',
    'Reschedule an appointment',
    'Cancel an appointment',
    'Join a video visit',
    'Add a family member',
    "Can't sign in or forgot password",
    'How your data is used',
    'Medical questions and emergencies',
  ];

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Text('Help', style: Theme.of(context).textTheme.headlineSmall),
        const SizedBox(height: 8),
        const Card(
          child: ListTile(
            leading: Icon(Icons.explore_outlined),
            title: Text('Ask the AppCompass assistant'),
            subtitle: Text('Tap Ask on any screen. It helps with using the app, not medical questions.'),
          ),
        ),
        for (final t in _topics)
          ListTile(leading: const Icon(Icons.article_outlined), title: Text(t), trailing: const Icon(Icons.chevron_right)),
        const Divider(),
        const ListTile(
          leading: Icon(Icons.support_agent_outlined),
          title: Text('Contact support'),
          subtitle: Text('Sun–Thu 07:00–21:00 · Sat 08:00–14:00'),
        ),
      ],
    );
  }
}
