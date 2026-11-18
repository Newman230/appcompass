-- Week 2: help-article chunks with embeddings, conversation messages, feedback.

-- The vector column has no fixed size, so any embedding model fits.
-- `embedder` records which model made each vector; search only compares
-- vectors from the same model. Small knowledge bases are searched exactly;
-- add an HNSW index per embedder when an app has many thousands of chunks.
CREATE TABLE doc_chunks (
    app_id        text NOT NULL REFERENCES apps(app_id) ON DELETE CASCADE,
    article_id    text NOT NULL,
    chunk_index   integer NOT NULL,
    title         text NOT NULL,
    text          text NOT NULL,
    locale        text NOT NULL,
    screen_ids    text[] NOT NULL DEFAULT '{}',
    embedder      text NOT NULL,
    embedding     vector NOT NULL,
    updated_at    timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (app_id, article_id, chunk_index)
);

CREATE INDEX doc_chunks_app_embedder_idx ON doc_chunks (app_id, embedder);

-- Current-session memory only: rows die with their session.
CREATE TABLE messages (
    message_id    uuid PRIMARY KEY,
    session_id    uuid NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    app_id        text NOT NULL REFERENCES apps(app_id) ON DELETE CASCADE,
    role          text NOT NULL CHECK (role IN ('user', 'assistant')),
    text          text NOT NULL,
    screen_id     text,
    cited         text[] NOT NULL DEFAULT '{}',
    created_at    timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE INDEX messages_session_idx ON messages (session_id, created_at);

CREATE TABLE feedback (
    message_id    uuid PRIMARY KEY REFERENCES messages(message_id) ON DELETE CASCADE,
    app_id        text NOT NULL REFERENCES apps(app_id) ON DELETE CASCADE,
    rating        text NOT NULL CHECK (rating IN ('up', 'down')),
    comment       text,
    created_at    timestamptz NOT NULL DEFAULT now()
);
