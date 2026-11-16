// Northwind Clinic (demo): a fictional clinic app that hosts the AppCompass
// assistant. Screen ids below match examples/clinic_demo/manifest.json.

import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';

import 'screens/appointments_screen.dart';
import 'screens/book_screen.dart';
import 'screens/help_screen.dart';
import 'screens/home_screen.dart';
import 'screens/profile_screen.dart';

void main() => runApp(const ClinicDemoApp());

/// The screen ids declared in the manifest, in navigation-bar order.
const List<String> kScreenIds = ['home', 'book', 'appointments', 'profile', 'help'];

class ClinicDemoApp extends StatefulWidget {
  const ClinicDemoApp({super.key});

  @override
  State<ClinicDemoApp> createState() => _ClinicDemoAppState();
}

class _ClinicDemoAppState extends State<ClinicDemoApp> {
  Locale _locale = const Locale('en');

  void _setLocale(Locale locale) => setState(() => _locale = locale);

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Northwind Clinic (demo)',
      debugShowCheckedModeBanner: false,
      locale: _locale,
      supportedLocales: const [Locale('en'), Locale('ar')],
      localizationsDelegates: const [
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
      ],
      theme: ThemeData(colorSchemeSeed: const Color(0xFF0E7C7B), useMaterial3: true),
      home: ClinicShell(onLocaleChanged: _setLocale, locale: _locale),
    );
  }
}

/// Holds the current screen id. In Week 3 the AppCompass SDK reads this so the
/// assistant knows which screen the user is asking from.
class ScreenTracker extends ValueNotifier<String> {
  ScreenTracker() : super('home');
}

class ClinicShell extends StatefulWidget {
  const ClinicShell({super.key, required this.onLocaleChanged, required this.locale});

  final ValueChanged<Locale> onLocaleChanged;
  final Locale locale;

  static ClinicShellState of(BuildContext context) =>
      context.findAncestorStateOfType<ClinicShellState>()!;

  @override
  State<ClinicShell> createState() => ClinicShellState();
}

class ClinicShellState extends State<ClinicShell> {
  final ScreenTracker tracker = ScreenTracker();
  int _index = 0;

  /// Navigate by manifest screen id. This is what the host app's `onAction`
  /// will call for the `navigate` action. Unknown ids are ignored on purpose:
  /// action params from the assistant are untrusted input (spec/events.md).
  bool goTo(String screenId) {
    final i = kScreenIds.indexOf(screenId);
    if (i < 0) return false;
    setState(() => _index = i);
    tracker.value = screenId;
    return true;
  }

  @override
  void dispose() {
    tracker.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final screens = <Widget>[
      const HomeScreen(),
      const BookScreen(),
      const AppointmentsScreen(),
      ProfileScreen(locale: widget.locale, onLocaleChanged: widget.onLocaleChanged),
      const HelpScreen(),
    ];
    return Scaffold(
      body: SafeArea(child: IndexedStack(index: _index, children: screens)),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('AppCompass assistant arrives in Week 3 (screen: ${tracker.value})')),
        ),
        icon: const Icon(Icons.explore_outlined),
        label: const Text('Ask'),
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _index,
        onDestinationSelected: (i) => goTo(kScreenIds[i]),
        destinations: const [
          NavigationDestination(icon: Icon(Icons.home_outlined), label: 'Home'),
          NavigationDestination(icon: Icon(Icons.add_circle_outline), label: 'Book'),
          NavigationDestination(icon: Icon(Icons.event_note_outlined), label: 'Appointments'),
          NavigationDestination(icon: Icon(Icons.person_outline), label: 'Profile'),
          NavigationDestination(icon: Icon(Icons.help_outline), label: 'Help'),
        ],
      ),
    );
  }
}

/// Small date formatter so the demo needs no extra packages.
String formatDateTime(DateTime d) {
  const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  final hh = d.hour.toString().padLeft(2, '0');
  final mm = d.minute.toString().padLeft(2, '0');
  return '${days[d.weekday - 1]} ${d.day} ${months[d.month - 1]}, $hh:$mm';
}
