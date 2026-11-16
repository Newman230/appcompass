import 'package:flutter/material.dart';

import '../data/fake_data.dart';
import '../main.dart';

class AppointmentsScreen extends StatelessWidget {
  const AppointmentsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return DefaultTabController(
      length: 2,
      child: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 16, 16, 0),
            child: Align(
              alignment: AlignmentDirectional.centerStart,
              child: Text('My appointments', style: Theme.of(context).textTheme.headlineSmall),
            ),
          ),
          const TabBar(tabs: [Tab(text: 'Upcoming'), Tab(text: 'Past')]),
          Expanded(
            child: TabBarView(
              children: [
                ListView(children: [for (final a in FakeData.upcoming) _AppointmentTile(a, upcoming: true)]),
                ListView(children: [for (final a in FakeData.past) _AppointmentTile(a, upcoming: false)]),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _AppointmentTile extends StatelessWidget {
  const _AppointmentTile(this.a, {required this.upcoming});

  final Appointment a;
  final bool upcoming;

  @override
  Widget build(BuildContext context) {
    return ListTile(
      leading: Icon(a.isVideo ? Icons.videocam_outlined : Icons.local_hospital_outlined),
      title: Text('${a.doctor} · ${a.specialty}'),
      subtitle: Text('${formatDateTime(a.start)}\n${a.branch} · for ${a.forWhom}${a.cancelled ? ' · Cancelled' : ''}'),
      isThreeLine: true,
      onTap: upcoming ? () => _showActions(context) : null,
    );
  }

  void _showActions(BuildContext context) {
    void demo(String what) {
      Navigator.pop(context);
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Demo only: $what')));
    }

    showModalBottomSheet<void>(
      context: context,
      builder: (_) => SafeArea(
        child: Wrap(
          children: [
            ListTile(leading: const Icon(Icons.schedule), title: const Text('Reschedule'), onTap: () => demo('reschedule')),
            ListTile(leading: const Icon(Icons.cancel_outlined), title: const Text('Cancel appointment'), onTap: () => demo('cancel')),
            if (a.isVideo)
              ListTile(leading: const Icon(Icons.videocam_outlined), title: const Text('Join video visit'), onTap: () => demo('join video visit')),
            ListTile(leading: const Icon(Icons.calendar_month_outlined), title: const Text('Add to calendar'), onTap: () => demo('add to calendar')),
            if (!a.isVideo)
              ListTile(leading: const Icon(Icons.call_outlined), title: const Text('Call branch'), onTap: () => demo('call branch')),
          ],
        ),
      ),
    );
  }
}
