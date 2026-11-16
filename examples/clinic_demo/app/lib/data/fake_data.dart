// Fictional data for the demo. No real people, clinics or patients.

class Appointment {
  const Appointment({
    required this.id,
    required this.doctor,
    required this.specialty,
    required this.branch,
    required this.start,
    required this.isVideo,
    required this.forWhom,
    this.cancelled = false,
  });

  final String id;
  final String doctor;
  final String specialty;
  final String branch;
  final DateTime start;
  final bool isVideo;
  final String forWhom;
  final bool cancelled;
}

class Doctor {
  const Doctor(this.name, this.specialty, this.languages, this.nextSlot);
  final String name;
  final String specialty;
  final List<String> languages;
  final String nextSlot;
}

class FakeData {
  static const patientName = 'Sam Example';
  static const branches = ['West Bay Branch', 'Airport Road Branch', 'Old Town Branch'];
  static const specialties = ['Family Medicine', 'Dermatology', 'Paediatrics', 'Dental'];

  static const doctors = [
    Doctor('Dr. Lina Haddad', 'Family Medicine', ['English', 'Arabic'], 'Tomorrow 09:30'),
    Doctor('Dr. Omar Rahman', 'Family Medicine', ['English', 'Arabic', 'Urdu'], 'Tomorrow 11:00'),
    Doctor('Dr. Priya Nair', 'Dermatology', ['English', 'Malayalam'], 'Thu 16:15'),
    Doctor('Dr. Daniel Costa', 'Paediatrics', ['English', 'Portuguese'], 'Wed 10:45'),
  ];

  static const familyMembers = ['Maya Example (daughter)', 'Adam Example (son)'];

  static final upcoming = [
    Appointment(
      id: 'apt-101',
      doctor: 'Dr. Lina Haddad',
      specialty: 'Family Medicine',
      branch: 'West Bay Branch',
      start: DateTime.now().add(const Duration(days: 2, hours: 3)),
      isVideo: false,
      forWhom: 'You',
    ),
    Appointment(
      id: 'apt-102',
      doctor: 'Dr. Daniel Costa',
      specialty: 'Paediatrics',
      branch: 'Video visit',
      start: DateTime.now().add(const Duration(days: 6, hours: 1)),
      isVideo: true,
      forWhom: 'Maya Example',
    ),
  ];

  static final past = [
    Appointment(
      id: 'apt-090',
      doctor: 'Dr. Priya Nair',
      specialty: 'Dermatology',
      branch: 'Old Town Branch',
      start: DateTime.now().subtract(const Duration(days: 21)),
      isVideo: false,
      forWhom: 'You',
    ),
    Appointment(
      id: 'apt-085',
      doctor: 'Dr. Omar Rahman',
      specialty: 'Family Medicine',
      branch: 'Airport Road Branch',
      start: DateTime.now().subtract(const Duration(days: 45)),
      isVideo: false,
      forWhom: 'You',
      cancelled: true,
    ),
  ];
}
