# Writing an AppCompass SDK for another platform

The server does all the thinking. A platform SDK is a thin client that does
three things, and nothing else:

1. **Show the chat.** A sheet or panel with a text box, streamed answer
   bubbles, source links and action buttons. Right-to-left layout for Arabic.
2. **Report the screen.** Send the current manifest `screen_id` with every
   message.
3. **Hand actions back.** When the user taps an action button, call the host
   app's `onAction(actionId, params)`. Never navigate or change app state
   yourself.

## Checklist

- [ ] `POST /v1/sessions` on first open; keep the `session_id` in memory only
      (no disk, no user identity). Start a new session on `session_expired`.
- [ ] `POST /v1/sessions/{id}/messages` with `text`, `screen_id`, `locale`;
      read the response as Server-Sent Events.
- [ ] Handle every event in [`spec/events.md`](../spec/events.md); ignore
      unknown event names.
- [ ] Never execute an `action` without a user tap.
- [ ] Send the API key in `X-AppCompass-Key`. Document that apps should
      fetch it from their own backend, not hard-code it in a public build.
- [ ] Thumbs up/down calls `POST /v1/sessions/{id}/feedback` with the
      `message_id` from `done`.
- [ ] Ship an example app wired to the clinic demo manifest.

## Reference

The Flutter SDK (`sdk/flutter/appcompass`, Week 3) is the reference
implementation. Match its public API shape where the platform allows:

```dart
AppCompass(
  config: AppCompassConfig(baseUrl: ..., apiKey: ..., locale: 'en'),
  currentScreen: tracker,          // ValueListenable<String>
  onAction: (actionId, params) { /* host app decides */ },
)
```
