-- =========================================
-- Help Desk: esquema de base de datos
-- =========================================

CREATE TABLE departments (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(100) NOT NULL UNIQUE,
    description TEXT
);

CREATE TABLE categories (
    id   SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE
);

CREATE TABLE priorities (
    id    SERIAL PRIMARY KEY,
    name  VARCHAR(50) NOT NULL UNIQUE,
    level INTEGER NOT NULL UNIQUE CHECK (level BETWEEN 1 AND 4)
);

CREATE TABLE users (
    id            SERIAL PRIMARY KEY,
    full_name     VARCHAR(150) NOT NULL,
    email         VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role          VARCHAR(20) NOT NULL DEFAULT 'user'
                  CHECK (role IN ('user', 'technician', 'admin')),
    department_id INTEGER REFERENCES departments(id) ON DELETE RESTRICT,
    is_active     BOOLEAN NOT NULL DEFAULT TRUE,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE technicians (
    id        SERIAL PRIMARY KEY,
    user_id   INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    specialty VARCHAR(100),
    level     VARCHAR(5) NOT NULL DEFAULT 'N1'
              CHECK (level IN ('N1', 'N2', 'N3')),
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE computers (
    id            SERIAL PRIMARY KEY,
    hostname      VARCHAR(100) NOT NULL UNIQUE,
    serial_number VARCHAR(100) UNIQUE,
    brand         VARCHAR(100),
    model         VARCHAR(100),
    os            VARCHAR(100),
    assigned_to   INTEGER REFERENCES users(id) ON DELETE SET NULL,
    department_id INTEGER REFERENCES departments(id) ON DELETE RESTRICT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE tickets (
    id                SERIAL PRIMARY KEY,
    title             VARCHAR(200) NOT NULL,
    description       TEXT NOT NULL,
    status            VARCHAR(20) NOT NULL DEFAULT 'Abierto'
                      CHECK (status IN ('Abierto', 'En progreso', 'Pendiente', 'Resuelto', 'Cerrado')),
    priority_id       INTEGER NOT NULL REFERENCES priorities(id) ON DELETE RESTRICT,
    category_id       INTEGER NOT NULL REFERENCES categories(id) ON DELETE RESTRICT,
    created_by        INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    assigned_to       INTEGER REFERENCES technicians(id) ON DELETE SET NULL,
    computer_id       INTEGER REFERENCES computers(id) ON DELETE SET NULL,
    diagnosis         TEXT,
    solution          TEXT,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at       TIMESTAMPTZ,
    resolution_minutes INTEGER CHECK (resolution_minutes >= 0),
    CHECK (resolved_at IS NULL OR resolved_at >= created_at)
);

CREATE TABLE ticket_comments (
    id         SERIAL PRIMARY KEY,
    ticket_id  INTEGER NOT NULL REFERENCES tickets(id) ON DELETE CASCADE,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    comment    TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE ticket_history (
    id         SERIAL PRIMARY KEY,
    ticket_id  INTEGER NOT NULL REFERENCES tickets(id) ON DELETE CASCADE,
    changed_by INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    field_name VARCHAR(50) NOT NULL,
    old_value  TEXT,
    new_value  TEXT,
    changed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =========================================
-- Índices (acelerar filtros y búsquedas)
-- =========================================
CREATE INDEX idx_tickets_status      ON tickets(status);
CREATE INDEX idx_tickets_priority    ON tickets(priority_id);
CREATE INDEX idx_tickets_assigned_to ON tickets(assigned_to);
CREATE INDEX idx_tickets_created_by  ON tickets(created_by);
CREATE INDEX idx_tickets_created_at  ON tickets(created_at);
CREATE INDEX idx_comments_ticket     ON ticket_comments(ticket_id);
CREATE INDEX idx_history_ticket      ON ticket_history(ticket_id);
CREATE INDEX idx_users_department    ON users(department_id);
