-- =========================================
-- Chat entre usuarios (conversaciones 1 a 1)
-- =========================================
-- Idempotente: se puede aplicar sobre una base ya existente.

-- Una conversación por pareja de usuarios. Se guarda siempre con
-- user_low_id < user_high_id para que (A, B) y (B, A) sean la misma.
CREATE TABLE IF NOT EXISTS chat_conversations (
    id                 SERIAL PRIMARY KEY,
    user_low_id        INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    user_high_id       INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    -- Último mensaje leído por cada participante (para contar no leídos)
    low_last_read_id   INTEGER NOT NULL DEFAULT 0,
    high_last_read_id  INTEGER NOT NULL DEFAULT 0,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_low_id, user_high_id),
    CHECK (user_low_id < user_high_id)
);

CREATE TABLE IF NOT EXISTS chat_messages (
    id              SERIAL PRIMARY KEY,
    conversation_id INTEGER NOT NULL REFERENCES chat_conversations(id) ON DELETE CASCADE,
    sender_id       INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    body            TEXT NOT NULL CHECK (length(body) BETWEEN 1 AND 2000),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_chat_conv_high     ON chat_conversations(user_high_id);
CREATE INDEX IF NOT EXISTS idx_chat_messages_conv ON chat_messages(conversation_id, id);

-- "Escribiendo…": última pulsación de cada participante
ALTER TABLE chat_conversations ADD COLUMN IF NOT EXISTS low_typing_at  TIMESTAMPTZ;
ALTER TABLE chat_conversations ADD COLUMN IF NOT EXISTS high_typing_at TIMESTAMPTZ;

-- "En línea" / "últ. vez": se actualiza con la actividad en la aplicación
CREATE TABLE IF NOT EXISTS chat_presence (
    user_id      INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
