-- AppCompass v1, Week 1 schema.
-- Every table carries app_id so one deployment can serve many apps (tenants).

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE apps (
    app_id        text PRIMARY KEY,
    name          text NOT NULL,
    key_prefix    text NOT NULL,          -- first characters of the key, for support and logs
    key_hash      text NOT NULL UNIQUE,   -- sha256 of the full key; the key itself is never stored
    created_at    timestamptz NOT NULL DEFAULT now(),
    disabled_at   timestamptz
);

CREATE TABLE manifests (
    app_id        text NOT NULL REFERENCES apps(app_id) ON DELETE CASCADE,
    version       integer NOT NULL,
    body          jsonb NOT NULL,
    stored_at     timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (app_id, version)
);

CREATE TABLE sessions (
    session_id    uuid PRIMARY KEY,
    app_id        text NOT NULL REFERENCES apps(app_id) ON DELETE CASCADE,
    locale        text NOT NULL,
    client        jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at    timestamptz NOT NULL DEFAULT now(),
    expires_at    timestamptz NOT NULL
);

CREATE INDEX sessions_app_idx ON sessions (app_id, created_at DESC);
