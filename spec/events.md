# AppCompass stream events (v1)

`POST /v1/sessions/{session_id}/messages` answers with a
[Server-Sent Events](https://html.spec.whatwg.org/multipage/server-sent-events.html)
stream (`Content-Type: text/event-stream`). Every client SDK, on every
platform, handles exactly these events. Nothing else is sent.

Each event has an `event:` name and a single-line JSON `data:` payload.
Events arrive in this order: zero or more `token`, zero or more `citation`,
zero or one `action`, zero or one `handoff`, then exactly one `done` or
`error`, which ends the stream.

| Event | Payload | Client does |
| --- | --- | --- |
| `token` | `{"text": "Open the "}` | Appends `text` to the answer bubble |
| `citation` | `{"article_id": "reschedule", "title": "Reschedule an appointment"}` | Shows a source link |
| `action` | `{"action_id": "navigate", "label": "Open My appointments", "params": {"screen_id": "appointments"}}` | Shows a button; on tap calls the host app's `onAction(action_id, params)` |
| `handoff` | `{"reason": "out_of_scope", "contact": "support@clinic-demo.example"}` | Shows a "Talk to a person" option |
| `error` | `{"code": "rate_limited", "message": "Too many requests, try again shortly."}` | Shows `message` with a retry option; stream ends |
| `done` | `{"message_id": "6f1c…", "latency_ms": 1840}` | Ends the turn; enables feedback buttons for `message_id` |

## Rules for SDK authors

1. Ignore unknown event names. New event types may be added in v1.x;
   removing or changing one requires v2.
2. Never execute an `action` automatically. Show it; the user taps; the host
   app decides in `onAction`. AppCompass never touches the host app directly.
3. Treat `params` as untrusted input in `onAction`: check `screen_id` against
   your own routes before navigating.
4. `handoff.reason` is one of `out_of_scope`, `low_confidence`,
   `user_requested`, `policy` (for example, a refused medical question).
5. `error.code` is one of `bad_request`, `unauthorized`, `session_expired`,
   `rate_limited`, `upstream_unavailable`, `internal`.

## Example stream

```
event: token
data: {"text": "To reschedule, open "}

event: token
data: {"text": "My appointments and tap the booking."}

event: citation
data: {"article_id": "reschedule", "title": "Reschedule an appointment"}

event: action
data: {"action_id": "navigate", "label": "Open My appointments", "params": {"screen_id": "appointments"}}

event: done
data: {"message_id": "6f1c2b7e-0d1a-4c55-9a7e-2a1b9e3c4d10", "latency_ms": 1840}
```
