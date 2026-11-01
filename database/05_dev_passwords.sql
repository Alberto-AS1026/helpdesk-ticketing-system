-- Contraseñas de desarrollo para los usuarios del seed (solo laboratorio).
-- Cada usuario: su nombre sin espacios + "Help2026" (p. ej. TecnicoAHelp2026).
-- Equivale a backend/scripts/set_dev_passwords.py, pero se ejecuta en el
-- arranque inicial del contenedor de PostgreSQL. bcrypt de Python acepta
-- los hashes $2a$ que genera pgcrypto.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

UPDATE users
SET password_hash = crypt(replace(full_name, ' ', '') || 'Help2026', gen_salt('bf', 12))
WHERE email LIKE '%@empresa.test';
