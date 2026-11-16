# Clinic demo (fictional)

Northwind Clinic is a made-up clinic used to show AppCompass inside a real
Flutter app. No real clinic, people or patient data.

| Path | What it is |
| --- | --- |
| `manifest.json` | Screens, actions and rules AppCompass uses for this app |
| `help/` | 16 help articles the assistant answers from (Markdown + front matter) |
| `app/` | The Flutter app (5 screens, fake data) |

Screen ids in `app/lib/main.dart` (`kScreenIds`) must match `manifest.json`.
The server's contract tests check that every help article points at a real
screen.

## Run the app

```bash
cd app
flutter create . --platforms=android,ios --project-name clinic_demo   # first time only: adds android/ and ios/
flutter pub get
flutter run
```

The **Ask** button is a placeholder until the AppCompass Flutter SDK lands in Week 3.
